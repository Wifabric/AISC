#!/usr/bin/env python3
"""cc-switch provider TEMPLATES — the add-provider fact source.

2.1.12 (D-1/D-6, 2026-09-18): the module no longer PRE-SEEDS provider rows
(images stop writing keyless cards — provider rows come exclusively from
「添加 provider」). It is the data source for the template picker (the
adapter's `templates` op reports ``provider_templates_manifest()``) and
composes each template's full settings_config at simple-add time. A
one-shot migration (``migrate_deprovisioned``) removes the historical
preset rows from existing volumes, fingerprint-guarded.

Stage 8c legacy (CS-03/CS-04, D8-06/D8-11): the DeepSeek template is driven by the
official-docs fixture (``deepseek-official-facts.json`` next to this module)
— nothing about models, endpoints or the ``[1m]`` suffix is hardcoded here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Any, TextIO

FIXTURE_PATH = Path(__file__).parent / "deepseek-official-facts.json"
FIXTURE_SCHEMA = "aisc.deepseek-official-facts/v1"
# Env keys the official Claude Code integration page defines; the fixture
# must carry every one of them (the AUTH_TOKEN is user-owned and never
# written by the preset — the preset env template simply omits it).
_REQUIRED_FIXTURE_ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_EFFORT_LEVEL",
)
# The user's token env key — preset-owned env never includes it.
USER_ONLY_ENV_KEYS = frozenset({"ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"})

# Retest round 2 (2026-08-21): upstream's claude switch REPLACES settings.json
# with the provider row's settings_config wholesale (live-probed) — an
# env-only row wipes the user's statusLine/enabledPlugins. Every claude
# settings_config this module (or the adapter) builds therefore carries the
# image's non-env base template. In the image it ships next to this module;
# in the repo/tests it is container/claude-settings.json one level up.
CLAUDE_SETTINGS_BASE_CANDIDATES = (
    Path(__file__).parent / "aisc-claude-settings-base.json",
    Path(__file__).parent.parent / "claude-settings.json",
)


def load_claude_settings_base() -> dict[str, Any]:
    """Non-env base template for claude settings_config (env never included).

    Unreadable/missing candidates → {} — rows degrade to env-only (the
    historical shape), never a startup failure.
    """
    for path in CLAUDE_SETTINGS_BASE_CANDIDATES:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k != "env"}
    return {}


def load_deepseek_fixture(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    """Strictly validate the official-docs fixture (fail closed)."""
    try:
        fixture = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"DeepSeek fixture unreadable at {path}: {exc}") from exc
    if fixture.get("schema") != FIXTURE_SCHEMA:
        raise RuntimeError(
            f"DeepSeek fixture schema {fixture.get('schema')!r} != {FIXTURE_SCHEMA!r}"
        )
    env = fixture.get("claude_code_official_env")
    if not isinstance(env, dict):
        raise RuntimeError("DeepSeek fixture is missing claude_code_official_env")
    missing = [k for k in _REQUIRED_FIXTURE_ENV_KEYS if k not in env]
    if missing:
        raise RuntimeError(f"DeepSeek fixture env is missing keys: {', '.join(missing)}")
    models = fixture.get("models", {}).get("official_ids")
    if not isinstance(models, list) or not models:
        raise RuntimeError("DeepSeek fixture is missing models.official_ids")
    if not fixture.get("base_url_anthropic"):
        raise RuntimeError("DeepSeek fixture is missing base_url_anthropic")
    return fixture


def deepseek_provider_from_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Build the DeepSeek preset entry from the official fixture.

    ``claude_env`` is the FULL official environment set minus the user-owned
    token keys — the preset writes exactly these and owns exactly these.
    ``_env_history`` lists every value earlier AISC presets (or cc-switch's
    MODEL fan-out) historically wrote, so a refresh can tell "old preset
    value → upgrade" apart from "user override → keep" (CS-04).
    """
    env = dict(fixture["claude_code_official_env"])
    for key in USER_ONLY_ENV_KEYS:
        env.pop(key, None)
    # Historical preset-written values for the model keys: the deprecated
    # official ids, the bare v4 name, and the [1m] forms. The role-model
    # keys also carry these because cc-switch's `provider add` fans
    # ANTHROPIC_MODEL out to the three DEFAULT_* keys verbatim.
    model_history = [
        "deepseek-chat",
        "deepseek-reasoner",
        "deepseek-v4-pro",
        "deepseek-v4-pro[1m]",
        "deepseek-v4-flash",
        "deepseek-v4-flash[1m]",
    ]
    history: dict[str, list[str]] = {
        "ANTHROPIC_BASE_URL": [
            "https://api.deepseek.com",
            "https://api.deepseek.com/v1",
            "https://api.deepseek.com/anthropic",
        ],
        "ANTHROPIC_MODEL": list(model_history),
        "ANTHROPIC_DEFAULT_OPUS_MODEL": list(model_history),
        "ANTHROPIC_DEFAULT_SONNET_MODEL": list(model_history),
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": list(model_history),
        "CLAUDE_CODE_SUBAGENT_MODEL": list(model_history),
        # First revision shipping this key: nothing historical wrote it.
        "CLAUDE_CODE_EFFORT_LEVEL": [],
    }
    official_ids = list(fixture["models"]["official_ids"])
    return {
        "id": "deepseek",
        "name": "DeepSeek",
        "base_url": fixture.get("base_url_openai", "https://api.deepseek.com"),
        "anthropic_base_url": fixture["base_url_anthropic"],
        # Codex side keeps the official pro id (fixture-verified).
        "model": "deepseek-v4-pro" if "deepseek-v4-pro" in official_ids else official_ids[-1],
        # Codex 模型目录（codex-adapt 修复轮 2026-08-20）：cc-switch 的
        # `modelCatalog.models` 数据源——切换 codex 供应商时上游生成
        # models 目录文件并向 ~/.codex/config.toml 注入 `model_catalog_json`，
        # codex /model 随之显示本目录而非官方内置列表；目录条目的
        # contextWindow 同时取代 codex 的 fallback 元数据（消「Model
        # metadata not found」）。数值 fixture 冻结（context_length=1M）。
        "model_catalog": _codex_model_catalog(official_ids, fixture),
        # S9a (2026-08-29 user ruling, supersedes S8g): BOTH agents speak
        # Anthropic to the upstream — the cc-switch local router translates
        # codex's Responses into Anthropic Messages against the provider's
        # anthropic endpoint. The user runs this shape manually on every
        # provider and reports it as the most stable path (one endpoint per
        # provider; these relays' anthropic sides are their best-maintained
        # surfaces). web_search gets disabled for anthropic-format codex
        # (the transform drops that hosted tool).
        "codex_api_format": "anthropic",
        "claude_env": env,
        "_env_history": history,
        "_retired_env_keys": [],
        "description": (
            "DeepSeek V4 (official Anthropic-compatible endpoint; "
            "pro[1m] main + flash for haiku/subagent per official docs)"
        ),
    }


def _context_window_from_length(raw: Any) -> int:
    """Fixture `context_length` ("1M"/"384K"/"131072") → tokens."""
    if isinstance(raw, (int, float)):
        return int(raw)
    text = str(raw or "").strip().upper()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    if text and text[-1] in multipliers:
        try:
            return int(float(text[:-1]) * multipliers[text[-1]])
        except ValueError:
            return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _codex_model_catalog(official_ids: list[str], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    """Catalog rows for cc-switch `modelCatalog.models` (codex side).

    Order = /model 列表优先级（cc-switch priority = 1000 + index）：主推
    pro 在前。contextWindow 取 fixture 的 context_length（"1M"→1_000_000，
    与用户实测工作配置的 mapping 行一致）；缺省 128k。
    """
    context_window = _context_window_from_length(
        fixture.get("models", {}).get("context_length")
    ) or 128_000
    preferred = ["deepseek-v4-pro", "deepseek-v4-flash"]
    ordered = [m for m in preferred if m in official_ids]
    ordered += [m for m in official_ids if m not in ordered]
    return [{"model": m, "contextWindow": context_window} for m in ordered]


# D-6.4 (2026-09-18): codesome serves the same model list as OpenAI
# official. The static seed mirrors the official models page
# (platform.openai.com/docs/models, fetched 2026-09-18) plus the two
# codesome-documented relay ids first (terra is the tutorial-mandated
# default; sol carries the official 1,050,000 window from the codesome
# 1M-context doc — terra's window is ⚠️ AISC-chosen 1M, unrecorded
# upstream). Entries without a sourced window fall back to the pipeline's
# 128k default; the live /models merge (fetch-models / catalog-sync --live)
# tops the catalog up per key at runtime.
_CODESOME_MODEL_CATALOG = [
    {"model": "gpt-5.6-terra", "contextWindow": 1_000_000,
     # D-6/D-7: per-model thinking levels (codex /model picks model, then
     # level) — canonical ids from upstream cc-switch's effort table.
     "reasoning_levels": ["none", "minimal", "low", "medium", "high", "xhigh"],
     "default_reasoning_level": "high"},
    {"model": "gpt-5.6-sol", "contextWindow": 1_050_000,
     "reasoning_levels": ["none", "minimal", "low", "medium", "high", "xhigh"],
     "default_reasoning_level": "high"},
    {"model": "gpt-5.2", "reasoning_levels": ["none", "minimal", "low", "medium", "high", "xhigh"],
     "default_reasoning_level": "medium"},
    {"model": "gpt-5.2-codex", "reasoning_levels": ["none", "minimal", "low", "medium", "high", "xhigh"],
     "default_reasoning_level": "medium"},
    {"model": "gpt-5.2-pro", "reasoning_levels": ["none", "minimal", "low", "medium", "high", "xhigh"],
     "default_reasoning_level": "high"},
    {"model": "gpt-5.1", "reasoning_levels": ["none", "minimal", "low", "medium", "high"],
     "default_reasoning_level": "medium"},
    {"model": "gpt-5.1-codex", "reasoning_levels": ["none", "minimal", "low", "medium", "high"],
     "default_reasoning_level": "medium"},
    {"model": "gpt-5.1-codex-max", "reasoning_levels": ["none", "minimal", "low", "medium", "high", "xhigh"],
     "default_reasoning_level": "medium"},
    {"model": "gpt-5.1-codex-mini", "reasoning_levels": ["none", "minimal", "low", "medium", "high"],
     "default_reasoning_level": "low"},
    {"model": "gpt-5", "reasoning_levels": ["none", "minimal", "low", "medium", "high"],
     "default_reasoning_level": "medium"},
    {"model": "gpt-5-codex", "reasoning_levels": ["none", "minimal", "low", "medium", "high"],
     "default_reasoning_level": "medium"},
    {"model": "gpt-5-pro", "reasoning_levels": ["none", "minimal", "low", "medium", "high", "xhigh"],
     "default_reasoning_level": "high"},
    {"model": "gpt-5-mini", "reasoning_levels": ["none", "minimal", "low", "medium", "high"],
     "default_reasoning_level": "medium"},
    {"model": "gpt-5-nano", "reasoning_levels": ["none", "minimal", "low", "medium"],
     "default_reasoning_level": "low"},
    {"model": "codex-mini-latest", "reasoning_levels": ["none", "minimal", "low", "medium", "high"],
     "default_reasoning_level": "medium"},
]


def build_preset_providers(fixture_path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    fixture = load_deepseek_fixture(fixture_path)
    return [
        deepseek_provider_from_fixture(fixture),
        {
            "id": "volcengine-ark",
            "name": "Volcengine Ark",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            # Ark anthropic-compat endpoint (documented; anthropic_base_url
            # is what the S9a unified codex rows point at).
            "anthropic_base_url": "https://ark.cn-beijing.volces.com/api/v3/anthropic",
            "model": "",
            # IDEA-5 (5c): historical preset-written MODEL values — the
            # ownership-merge discriminator (in-list → upgrade on refresh;
            # anything else is a user override and survives). Empty: this
            # preset never wrote a model.
            "_model_history": [],
            "codex_api_format": "anthropic",
            "description": "Volcengine Ark inference service; configure an endpoint ID",
        },
        {
            "id": "zhipu",
            "name": "Zhipu GLM",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "anthropic_base_url": "https://open.bigmodel.cn/api/anthropic",
            # S8g-2 fix (2026-08-29 user correction): GLM-5.3 is the current
            # flagship (official migrate guide: glm-5.3, context 1M, output
            # 128K). glm-5.2 stays in _model_history — it was preset-written,
            # so existing volumes upgrade on refresh instead of sticking.
            "model": "glm-5.3",
            "_model_history": ["glm-5.2", "glm-5.3"],
            "codex_api_format": "anthropic",
            # S8g-2 (2026-08-29, user field report): without a model catalog
            # codex /model lists NOTHING (the catalog IS the picker's data
            # source). GLM-5.3: 1M context per docs.bigmodel.cn.
            "model_catalog": [{"model": "glm-5.3", "contextWindow": 1_000_000}],
            "description": "Zhipu GLM-5.3 flagship model service",
        },
        {
            "id": "kimi",
            "name": "Kimi",
            "base_url": "https://api.moonshot.cn/v1",
            "anthropic_base_url": "https://api.moonshot.cn/anthropic",
            "model": "kimi-k3",
            "_model_history": ["kimi-k3"],
            "codex_api_format": "anthropic",
            # Kimi K3: up to 1M context (2.8T params, tiered by plan).
            "model_catalog": [{"model": "kimi-k3", "contextWindow": 1_000_000}],
            "description": "Moonshot Kimi K3 model service",
        },
        {
            # D-6 (2026-09-18): codesome splits into TWO product-line
            # templates (was one mixed "codesome" row — the root cause of
            # the cross-wired configs: V3 gateway on the codex side, V5
            # /api on the claude side, in ONE row). V3 (Claude/GPT 月卡 +
            # 按量): sk- keys created in the V3 dashboard (redeem code
            # first — the redeem code is NOT the key; group bound at key
            # creation, rates dynamic per the day's backend). One gateway
            # domain serves both agents: claude speaks Anthropic to
            # cc.codesome.ai; codex rides the S9a translation to the same
            # endpoint (official native fallback: cc.codesome.ai/v1).
            "id": "codesome-v3",
            "name": "Codesome V3",
            "base_url": "https://cc.codesome.ai",
            "anthropic_base_url": "https://cc.codesome.ai",
            "claude_env": {
                "ANTHROPIC_BASE_URL": "https://cc.codesome.ai",
                # Official "core three" (doc.codesome.ai v3-claude): the
                # attribution header MUST be 0 (their #1 common error);
                # NONESSENTIAL_TRAFFIC rides the method-2 quartet (D-6.5).
                "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            },
            # NO claude-side model keys: the official「大扫除」list requires
            # clearing ANTHROPIC_MODEL etc. — the key's server-side group
            # routes models.
            "model": "gpt-5.6-terra",
            "_model_history": ["gpt-5.6-sol", "gpt-5.6-terra"],
            "codex_api_format": "anthropic",
            "model_catalog": _CODESOME_MODEL_CATALOG,
            "description": "Codesome V3 relay (月卡/按量; sk- key)",
            "key_prefix": "sk-",
            "acquire_url": "https://meta.codesome.cn/?aff=FAP2ASVX",
        },
        {
            # 二合一 (V5): the cr- card secret from the order IS the key —
            # no redemption, no key creation, no group (flat 1.5x, both
            # model families). Claude speaks Anthropic to /api; codex
            # S9a-translates to the same (official native fallback:
            # v5.codesome.cn/openai). Mixing the V3 domain or an sk- key
            # here is the documented common-error pair.
            "id": "codesome-2in1",
            "name": "Codesome 二合一",
            "base_url": "https://v5.codesome.cn/openai",
            "anthropic_base_url": "https://v5.codesome.cn/api",
            "claude_env": {
                "ANTHROPIC_BASE_URL": "https://v5.codesome.cn/api",
                "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            },
            "model": "gpt-5.6-terra",
            "_model_history": ["gpt-5.6-sol", "gpt-5.6-terra"],
            "codex_api_format": "anthropic",
            "model_catalog": _CODESOME_MODEL_CATALOG,
            "description": "Codesome 二合一 (V5) relay (cr- key)",
            "key_prefix": "cr-",
            "acquire_url": "https://meta.codesome.cn/?aff=FAP2ASVX",
        },
    ]


PRESET_PROVIDERS = build_preset_providers()

SUPPORTED_AGENTS = ("claude", "codex")
MARKER_TEMPLATE = ".aisc-preset-providers-{agent}.sha256"
# v6 (retest round 2, 2026-08-21): claude settings_config gains the non-env
# base template (statusLine/enabledPlugins) — the revision must bump so
# EXISTING volumes refresh their rows instead of keeping env-only shapes
# (an env-only row wipes the user's setup on the next switch).
# v7 (S8g, 2026-08-29): every codex preset's upstream format becomes
# openai_responses (DeepSeek flips off the anthropic translation and its
# codex base off /anthropic), and the codesome preset joins — existing
# volumes must refresh their codex rows and metas.
# v8 (S8g-2, 2026-08-29): zhipu/kimi/codesome gain model catalogs — without
# one codex /model lists nothing. Existing volumes refresh their codex rows.
# v9 (S9a, 2026-08-29): ALL codex upstreams unify on the Anthropic endpoint
# + format (user ruling: manually proven most stable; the S8g same-day
# "native Responses" experiment is retired). The meta migration also learns
# "chat" — cc-switch's own daemon/proxy-enable seeds it and the v8 upgrade
# rule wrongly treated it as a user choice (fresh-workspace field report).
# v10 (2.1.12, D-6.7, 2026-09-18): de-seed. Images stop pre-seeding keyless
# provider cards entirely — templates replace presets as the add-provider
# data source, and the one-shot migration removes the historical third-
# party preset rows (fingerprint-guarded) from existing volumes.
PRESET_FORMAT_VERSION = 10
# Provider ids that no longer exist as templates, mapped to a fingerprint
# that identifies the old preset's settings_config. The migration deletes
# an id only if its stored config still carries the fingerprint, so a user
# who repurposed the id with their own config is left alone. v10 retires
# the whole seeded third-party set (D-6.7): users re-add from templates.
RETIRED_PROVIDER_IDS = {
    "codex-claude": "codex.so",
    "deepseek": "api.deepseek.com",
    "volcengine-ark": "ark.cn-beijing.volces.com",
    "zhipu": "open.bigmodel.cn",
    "kimi": "api.moonshot.cn",
    "codesome": "codesome",
}
REQUIRED_PROVIDER_COLUMNS = {
    "id",
    "app_type",
    "name",
    "settings_config",
    "website_url",
    "category",
    "created_at",
    "sort_index",
    "notes",
    "icon",
    "icon_color",
    "meta",
    "is_current",
    "in_failover_queue",
}


def marker_path(config_dir: Path, agent: str) -> Path:
    if agent not in SUPPORTED_AGENTS:
        raise ValueError(f"unsupported agent: {agent}")
    return config_dir / MARKER_TEMPLATE.format(agent=agent)


def preset_revision(agent: str) -> str:
    """Return a revision derived only from the provider payload and schema."""
    payload = {
        "format": PRESET_FORMAT_VERSION,
        "agent": agent,
        "providers": PRESET_PROVIDERS,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _toml_string(value: str) -> str:
    """Encode a string using JSON's TOML-compatible quoted-string syntax."""
    return json.dumps(value, ensure_ascii=True)


def _codex_upstream_base(provider: dict[str, Any]) -> str:
    """The URL codex's model_providers entry points at (S8g).

    ``openai_responses`` upstreams (the ruling default): the OpenAI-side
    base_url — codex speaks Responses straight to it, no translation.
    An ``anthropic`` upstream keeps the historical translation shape: the
    local router converts Responses→Anthropic against anthropic_base_url.
    """
    if provider.get("codex_api_format") == "openai_responses":
        return provider["base_url"]
    return provider.get("anthropic_base_url") or provider["base_url"]


def _settings_config(
    agent: str, provider: dict[str, Any], *, api_key: str = "",
    reasoning_effort: str = "", compact_token_limit: int = 0,
    base_url_override: str = "",
) -> dict[str, Any]:
    if agent == "claude":
        # Fixture-driven providers (Stage 8c) carry the full official env set.
        if "claude_env" in provider:
            env = dict(provider["claude_env"])
        else:
            # Third-party providers expose a separate Anthropic-compatible
            # endpoint (e.g. /anthropic) distinct from their OpenAI base_url.
            # Prefer it when present so Claude Code speaks the Messages API
            # to the right URL.
            base_url = provider.get("anthropic_base_url") or provider["base_url"]
            env = {"ANTHROPIC_BASE_URL": base_url}
            # A provider may expose a Claude-specific model name (e.g.
            # DeepSeek's docs recommend deepseek-v4-pro[1m] for Claude Code)
            # distinct from the OpenAI model used by codex; prefer it when
            # present.
            claude_model = provider.get("anthropic_model") or provider["model"]
            if claude_model:
                env["ANTHROPIC_MODEL"] = claude_model
        # D-6 (add-page endpoint field): an explicit form override wins over
        # the template's declared endpoint.
        if base_url_override:
            env["ANTHROPIC_BASE_URL"] = base_url_override
        # The ADD path (adapter simple-add) passes the user's token here —
        # it rides the stdin request only and lands in the row env. Seeding
        # never passes api_key, so the template data stays token-free.
        if api_key:
            env["ANTHROPIC_AUTH_TOKEN"] = api_key
        # D-7: claude-side auto-compact rides the provider env (official
        # compaction page: ENABLED + WINDOW, both strings).
        if compact_token_limit:
            env["CLAUDE_AUTO_COMPACT_ENABLED"] = "true"
            env["CLAUDE_AUTO_COMPACT_WINDOW"] = str(int(compact_token_limit))
        return {"env": env, **load_claude_settings_base()}

    if agent == "codex":
        provider_id = provider["id"]
        lines = [
            f"model_provider = {_toml_string(provider_id)}",
        ]
        if provider["model"]:
            lines.append(f"model = {_toml_string(provider['model'])}")
        # codex-adapt: with a catalog the active entry's window wins; this
        # top-level key is the no-catalog fallback (official codex config
        # key — keeps token accounting sane even if the catalog file goes
        # away), taken from the first catalog row.
        catalog_rows = provider.get("model_catalog") or []
        if catalog_rows and catalog_rows[0].get("contextWindow"):
            lines.append(
                f"model_context_window = {int(catalog_rows[0]['contextWindow'])}"
            )
        # D-7 (2026-09-18): user-configurable thinking depth (cc-switch
        # desktop parity) and auto-compact watermark. Empty effort keeps the
        # historical "high" default; a zero/absent limit omits the key
        # entirely (auto-compact off). Official codex order: model,
        # context window, auto-compact limit.
        if compact_token_limit:
            lines.append(f"model_auto_compact_token_limit = {int(compact_token_limit)}")
        lines.extend(
            [
                f'model_reasoning_effort = {_toml_string(reasoning_effort or "high")}',
                "",
                f"[model_providers.{provider_id}]",
                f"name = {_toml_string(provider_id)}",
                # S8g (2026-08-29): codex presets speak Responses to the
                # upstream DIRECTLY (apiFormat=openai_responses) — base is the
                # OpenAI-side base_url, never the anthropic mirror. A provider
                # still declaring an anthropic upstream keeps the translation
                # shape (router talks Anthropic to anthropic_base_url).
                f"base_url = {_toml_string(base_url_override or _codex_upstream_base(provider))}",
                'wire_api = "responses"',
                "requires_openai_auth = true",
            ]
        )
        # api_key is the one user-owned field that must survive a preset
        # refresh; it is only re-injected when refreshing an existing provider.
        if api_key:
            lines.append(f"api_key = {_toml_string(api_key)}")
        lines.append("")
        # Upstream `provider switch` refuses a codex settings_config without
        # an "auth" object ("Codex 供应商配置缺少 'auth' 字段"); its own
        # official rows seed {"auth":{},"config":""}. The user's key rides
        # auth.OPENAI_API_KEY — the channel live ~/.codex/auth.json is
        # written from on switch, and the one the local proxy worker
        # captures at enable time (live-probed 2026-08-21: the router
        # neither reads the TOML api_key line nor passes the client bearer
        # through) — mirrored into the TOML line for legacy rows/masks.
        auth = {"OPENAI_API_KEY": api_key} if api_key else {}
        settings: dict[str, Any] = {"auth": auth, "config": "\n".join(lines)}
        # codex-adapt 修复轮: providers carrying a model catalog get it into
        # settings — cc-switch then generates the models file + injects
        # `model_catalog_json` on switch (see _codex_model_catalog).
        catalog = provider.get("model_catalog")
        if isinstance(catalog, list) and catalog:
            settings["modelCatalog"] = {"models": catalog}
        return settings

    raise ValueError(f"unsupported agent: {agent}")


def _parse_json_settings(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _validate_schema(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(providers)")}
    missing = REQUIRED_PROVIDER_COLUMNS - columns
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise RuntimeError(
            "cc-switch providers schema is incompatible; "
            f"missing columns: {missing_text}"
        )


def preset_required(config_dir: Path, agent: str, revision: str) -> tuple[bool, str]:
    """Check whether this agent's preset revision has been applied."""
    marker = marker_path(config_dir, agent)
    if not marker.is_file():
        return True, "first initialization"

    try:
        existing_revision = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return True, "marker is unreadable"

    if existing_revision != revision:
        return True, "preset revision changed"
    return False, "current"


def _remove_retired_providers(
    conn: sqlite3.Connection,
    agent: str,
    existing: dict[str, str | None],
    log: TextIO,
) -> int:
    """Delete retired preset ids that still look like the old preset."""
    count = 0
    for retired_id, fingerprint in RETIRED_PROVIDER_IDS.items():
        if retired_id not in existing:
            continue
        if fingerprint not in (existing.get(retired_id) or ""):
            # The id exists but no longer matches the old preset shape; the
            # user likely repurposed it, so leave it alone.
            print(
                f"Retired id {retired_id} looks repurposed; keeping",
                file=log,
            )
            continue
        conn.execute(
            "DELETE FROM providers WHERE id = ? AND app_type = ?",
            (retired_id, agent),
        )
        print(f"Removed retired provider: {retired_id}", file=log)
        count += 1
    return count


def migrate_deprovisioned(
    config_dir: Path, agent: str, revision: str, log: TextIO
) -> int:
    """D-6.7 one-shot: remove retired preset rows, then stamp the marker.

    Rows are deleted only when their stored settings_config still carries
    the retired preset's fingerprint — a user who repurposed an id keeps
    their row (RETIRED_PROVIDER_IDS semantics, applied to the whole seeded
    third-party set). Returns the number of rows removed.
    """
    db_path = config_dir / "cc-switch.db"
    if not db_path.is_file():
        # Fresh volume (or cc-switch not yet initialized): nothing seeded,
        # nothing to remove — stamp the marker so this never runs twice.
        removed = 0
    else:
        conn = sqlite3.connect(db_path, timeout=10)
        removed = 0
        try:
            conn.execute("BEGIN IMMEDIATE")
            _validate_schema(conn)
            existing = {
                str(row[0]): (row[1] if row[1] is not None else "")
                for row in conn.execute(
                    "SELECT id, settings_config FROM providers WHERE app_type = ?",
                    (agent,),
                )
            }
            removed = _remove_retired_providers(conn, agent, existing, log)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    marker = marker_path(config_dir, agent)
    temp_marker = marker.with_name(f"{marker.name}.tmp")
    temp_marker.write_text(f"{revision}\n", encoding="utf-8")
    temp_marker.replace(marker)
    return removed


# Manifest fields beyond id/name the add-provider picker consumes
# (TEMPLATE-level metadata; secrets are structurally absent — the key only
# ever rides the simple-add request's stdin channel).
TEMPLATE_MANIFEST_FIELDS = ("description", "key_prefix", "acquire_url")


def provider_templates_manifest() -> list[dict[str, Any]]:
    """The add-provider template manifest (adapter `templates` op, D-6.8).

    Single-source guarantee: the manifest is derived from the very same
    PRESET_PROVIDERS payload that composes each template's settings_config
    at simple-add time — the picker and the seeds cannot drift.
    """
    manifest: list[dict[str, Any]] = []
    for provider in PRESET_PROVIDERS:
        entry: dict[str, Any] = {"id": provider["id"], "name": provider["name"]}
        for field in TEMPLATE_MANIFEST_FIELDS:
            if provider.get(field):
                entry[field] = provider[field]
        entry["default_model"] = provider.get("model") or ""
        # D-6 (add-page endpoint display): both agents' declared endpoints —
        # the same values simple-add bakes into the settings_config.
        entry["claude_endpoint"] = (
            provider.get("anthropic_base_url") or provider["base_url"])
        entry["codex_endpoint"] = _codex_upstream_base(provider)
        # The provider's OpenAI-side base — the endpoint behind the NATIVE
        # Responses format (when the user flips the upstream format off the
        # S9a anthropic translation, the URL must switch with it).
        entry["codex_endpoint_native"] = provider["base_url"]
        entry["codex_api_format"] = provider.get("codex_api_format") or "anthropic"
        manifest.append(entry)
    return manifest


# ---------------------------------------------------------------------------
# Post-init reconcile (retest round 2, 2026-08-21): the provider-page choice
# owns BOTH agents' local proxy routes. Container start re-asserts the
# invariant so volumes created by older images (claude route force-enabled
# while sitting on the imported "default" row) self-heal.
# ---------------------------------------------------------------------------

OFFICIAL_ROW_IDS = {"claude": "claude-official", "codex": "codex-official"}


def _claude_row_real(settings: dict[str, Any]) -> bool:
    env = settings.get("env")
    return isinstance(env, dict) and bool(env.get("ANTHROPIC_BASE_URL"))


def _codex_row_real(settings: dict[str, Any]) -> bool:
    text = settings.get("config")
    if not isinstance(text, str) or not text:
        return False
    try:
        toml = tomllib.loads(text)
    except Exception:
        return False
    providers = toml.get("model_providers")
    if isinstance(providers, dict):
        for entry in providers.values():
            if isinstance(entry, dict) and entry.get("base_url"):
                return True
    return False


def _is_pristine_default_import(agent: str, pid: str, settings: dict[str, Any]) -> bool:
    """cc-switch's first-init import row ("default") before any user input:
    a settings.json snapshot with NO env (no endpoint, no token). Any env the
    user added means the row was repurposed — never touch it."""
    if agent != "claude" or pid != "default":
        return False
    env = settings.get("env")
    if not isinstance(env, dict):
        return True
    return not any(env.values())


def _proxy_port_from_show(text: str, agent: str) -> "int | None":
    """THIS agent's route port from `proxy show` human output. The output
    lists every app ("- Claude: ... configured 15721" first) — anchor to
    the agent's own line or the verify checks the wrong port (user report
    2026-08-21). No parse → None → skip."""
    import re

    match = re.search(
        rf"(?im)^\s*-\s*{re.escape(agent)}\s*:[^\n]*\bconfigured\s+(\d{{2,5}})",
        text or "",
    )
    return int(match.group(1)) if match else None


def _tcp_listening(port: int, attempts: int = 3, delay: float = 0.4) -> bool:
    """Ground truth for "the route serves" (the daemon's own status
    snapshots are exactly what goes stale — manual round 3, 2026-08-21)."""
    import socket

    for _ in range(attempts):
        sock = socket.socket()
        sock.settimeout(1.0)
        try:
            sock.connect(("127.0.0.1", port))
            return True
        except OSError:
            time.sleep(delay)
        finally:
            sock.close()
    return False


def reconcile_runtime_state(
    config_dir: Path, log: TextIO, runner=subprocess.run
) -> list[str]:
    """Re-assert the proxy/default invariants at container start.

    1. Official rows exist for both agents (the cancel-proxy targets) —
       created when missing; claude-official gets the settings base keys
       while it is still cc-switch's bare seed shape (the claude switch
       replaces settings.json wholesale, so even the official row must
       carry the statusLine/plugin base).
    2. A PRISTINE imported "default" row is deleted; when it was current,
       current re-points to claude-official (user decision 2026-08-21 —
       "claude 出现 default 配置" was the confusing symptom). A row the
       user configured is never touched.
    3. Per agent: proxy route ON iff the current provider row is a real
       third-party endpoint. enable/disable are idempotent (live-probed
       2026-08-21), so unconditional calls converge legacy states.

    Best-effort by contract: a failing cc-switch call logs and continues;
    returns the actions taken (entrypoint echo + tests).
    """
    actions: list[str] = []
    db_path = config_dir / "cc-switch.db"
    if not db_path.is_file():
        return actions
    conn = sqlite3.connect(db_path, timeout=15)
    try:
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("BEGIN IMMEDIATE")
        current: dict[str, tuple[str, dict[str, Any]]] = {}
        for agent in SUPPORTED_AGENTS:
            row = conn.execute(
                "SELECT id, settings_config FROM providers "
                "WHERE app_type = ? AND is_current = 1 LIMIT 1",
                (agent,),
            ).fetchone()
            if row is not None:
                current[agent] = (str(row[0]), _parse_json_settings(row[1]))

        now = int(time.time() * 1000)
        for agent in SUPPORTED_AGENTS:
            official_id = OFFICIAL_ROW_IDS[agent]
            existing = conn.execute(
                "SELECT settings_config FROM providers "
                "WHERE id = ? AND app_type = ?",
                (official_id, agent),
            ).fetchone()
            if existing is None:
                settings = (
                    {"env": {}, **load_claude_settings_base()}
                    if agent == "claude"
                    else {"auth": {}, "config": ""}
                )
                next_sort = conn.execute(
                    "SELECT COALESCE(MAX(sort_index), -1) + 1 FROM providers "
                    "WHERE app_type = ?",
                    (agent,),
                ).fetchone()[0]
                conn.execute(
                    "INSERT INTO providers ("
                    "id, app_type, name, settings_config, website_url, "
                    "category, created_at, sort_index, notes, icon, "
                    "icon_color, meta, is_current, in_failover_queue"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        official_id, agent,
                        "Claude Official" if agent == "claude" else "OpenAI Official",
                        json.dumps(settings, ensure_ascii=False,
                                   separators=(",", ":")),
                        "", "custom", now, next_sort, "", None, None,
                        "{}", 0, 0,
                    ),
                )
                if agent not in current:
                    # No current row at all — the fresh official row is the
                    # only candidate (env-less → proxy stays off).
                    current[agent] = (official_id, settings)
                actions.append(f"created {agent} official row")
                print(f"Created missing official row: {official_id}", file=log)
            elif agent == "claude":
                settings = _parse_json_settings(existing[0])
                if set(settings.keys()) <= {"env"}:
                    settings = {"env": settings.get("env") or {},
                                **load_claude_settings_base()}
                    conn.execute(
                        "UPDATE providers SET settings_config = ? "
                        "WHERE id = ? AND app_type = ?",
                        (json.dumps(settings, ensure_ascii=False,
                                    separators=(",", ":")),
                         official_id, agent),
                    )
                    if current.get(agent, ("", {}))[0] == official_id:
                        current[agent] = (official_id, settings)
                    actions.append("seeded claude-official settings base")
                    print("Seeded settings base into claude-official", file=log)

        claude_row = current.get("claude")
        if claude_row is not None and _is_pristine_default_import(
            "claude", claude_row[0], claude_row[1]
        ):
            conn.execute(
                "UPDATE providers SET is_current = 0 WHERE app_type = 'claude'"
            )
            conn.execute(
                "UPDATE providers SET is_current = 1 "
                "WHERE id = ? AND app_type = 'claude'",
                (OFFICIAL_ROW_IDS["claude"],),
            )
            conn.execute(
                "DELETE FROM providers WHERE id = 'default' AND app_type = 'claude'"
            )
            current["claude"] = (OFFICIAL_ROW_IDS["claude"], {})
            actions.append("removed imported claude 'default' row "
                           "(current -> claude-official)")
            print("Removed pristine 'default' import; current -> claude-official",
                  file=log)
        else:
            # Leftover sweep: a pristine non-current 'default' import (the
            # user already switched away) is deleted too — the TUI clutter
            # was the complaint. Repurposed rows survive, as above.
            for pid, raw in conn.execute(
                "SELECT id, settings_config FROM providers "
                "WHERE app_type = 'claude'"
            ).fetchall():
                if _is_pristine_default_import(
                    "claude", str(pid), _parse_json_settings(raw)
                ):
                    conn.execute(
                        "DELETE FROM providers "
                        "WHERE id = ? AND app_type = 'claude'",
                        (str(pid),),
                    )
                    actions.append("removed leftover claude 'default' row")
                    print("Removed leftover pristine 'default' import", file=log)
        conn.commit()
    except sqlite3.Error as exc:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        print(f"Reconcile DB step failed (continuing to proxy calls): {exc}",
              file=log)
    finally:
        conn.close()

    real_check = {"claude": _claude_row_real, "codex": _codex_row_real}
    for agent in SUPPORTED_AGENTS:
        row = current.get(agent)
        real = row is not None and real_check[agent](row[1])
        verb = "enable" if real else "disable"
        try:
            completed = runner(
                ["cc-switch", "proxy", "-a", agent, verb],
                capture_output=True, text=True, timeout=30,
            )
        except Exception as exc:  # timeout / spawn failure — best-effort
            print(f"proxy {verb} {agent} could not run: {exc}", file=log)
            continue
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:200]
            print(f"proxy {verb} {agent} failed (exit "
                  f"{completed.returncode}): {detail}", file=log)
            continue
        actions.append(f"proxy {agent} {verb}d")
        print(f"Proxy route {agent}: {verb}d", file=log)
        if real:
            # Manual round 3 (2026-08-21): enable can silently no-op (stale
            # supervisor state / dead daemon) while printing success —
            # verify the route port listens; recover via daemon restart +
            # re-enable. Best-effort: boot never fails over this.
            try:
                show = runner(["cc-switch", "proxy", "-a", agent, "show"],
                              capture_output=True, text=True, timeout=30)
                port = _proxy_port_from_show(show.stdout or "", agent)
            except Exception as exc:
                print(f"route verify {agent}: show failed: {exc}", file=log)
                port = None
            if port is not None and not _tcp_listening(port):
                print(f"route {agent} port {port} not listening; "
                      "restarting daemon + re-enabling", file=log)
                recovery = [
                    (0.5, ["cc-switch", "daemon", "stop"]),
                    (1.0, ["cc-switch", "daemon", "start", "--detach"]),
                    (0.0, ["cc-switch", "proxy", "-a", agent, "enable"]),
                ]
                for delay, recover_argv in recovery:
                    if delay:
                        time.sleep(delay)
                    try:
                        runner(recover_argv, capture_output=True,
                               text=True, timeout=30)
                    except Exception as exc:
                        print(f"recovery step {recover_argv} failed: {exc}",
                              file=log)
                if _tcp_listening(port):
                    actions.append(f"recovered {agent} route (daemon restart)")
                    print(f"recovered {agent} route after daemon restart",
                          file=log)
                else:
                    print(f"WARNING: {agent} route port {port} still not "
                          "listening after daemon restart", file=log)
    return actions


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="cc-switch provider templates + deprovision migration"
    )
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--agent", choices=SUPPORTED_AGENTS + ("all",), default="claude")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument(
        "--reconcile", action="store_true",
        help="post-init invariant pass only (official rows, pristine default "
             "import, proxy on/off per current provider)",
    )
    parser.add_argument(
        "--print-manifest", action="store_true",
        help="emit the provider template manifest as JSON (stdout) and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.print_manifest:
        print(json.dumps(provider_templates_manifest(),
                         ensure_ascii=False, separators=(",", ":")))
        return 0

    args.config_dir.mkdir(parents=True, exist_ok=True)
    args.log.parent.mkdir(parents=True, exist_ok=True)

    if args.reconcile:
        with args.log.open("a", encoding="utf-8") as log:
            try:
                actions = reconcile_runtime_state(args.config_dir, log)
            except Exception as exc:  # never fail container start
                print(f"Runtime state reconcile failed: {exc}", file=log)
                return 1
            print("reconciled" if actions else "current")
            for action in actions:
                print(f"  - {action}", file=log)
            return 0

    # PERF P9 (D-13): `--agent all` runs both agents in ONE python3 spawn.
    # Contract: sequential best-effort, NOT atomic — a later failure leaves
    # earlier agents migrated; the next container start retries the
    # idempotent migration rather than rolling back user-visible state.
    if args.agent == "all":
        import contextlib
        import io

        statuses: list[str] = []
        for agent in SUPPORTED_AGENTS:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                sub = main(["--agent", agent,
                            "--config-dir", str(args.config_dir),
                            "--log", str(args.log)])
            if sub != 0:
                print("failed")
                return 1
            statuses.append(buf.getvalue().strip())
        # migrated > current (per the single-agent vocabulary).
        print("migrated" if "migrated" in statuses else "current")
        return 0

    revision = preset_revision(args.agent)
    with args.log.open("a", encoding="utf-8") as log:
        try:
            required, reason = preset_required(args.config_dir, args.agent, revision)
            if not required:
                print("current")
                return 0

            print(f"Deprovision migration for {args.agent}: {reason}", file=log)
            removed = migrate_deprovisioned(
                config_dir=args.config_dir,
                agent=args.agent,
                revision=revision,
                log=log,
            )
            print("migrated" if removed else "current")
            print(f"Removed {removed} retired preset rows", file=log)
            return 0
        except Exception as exc:
            print(f"Deprovision migration failed: {exc}", file=log)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
