"""Stage 8c (CS-03/CS-04, D8-06/D8-11) + 2.1.12 (D-1/D-6): fixture-driven
DeepSeek template, the codesome dual product-line templates, the add-provider
manifest, and the deprovision migration.

The DeepSeek template must generate the official Claude Code env set VERBATIM
from ``container/lib/deepseek-official-facts.json`` (never a hardcoded copy)
and never write the user's token keys. The codesome templates (D-6) split the
two product lines apart (V3 sk- / 二合一 cr-). The migration (D-6.7) removes
the historical seeded rows fingerprint-guarded and never touches repurposed
user rows.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "container" / "lib" / "deepseek-official-facts.json"

_spec = importlib.util.spec_from_file_location(
    "aisc_cc_switch_preset_8c", ROOT / "container" / "lib" / "cc_switch_preset_providers.py"
)
assert _spec and _spec.loader
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)

FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def deepseek() -> dict:
    """A deep copy — tests mutate provider entries (e.g. _retired_env_keys)
    and must never pollute the shared module-level list."""
    return json.loads(json.dumps(
        next(p for p in H.PRESET_PROVIDERS if p["id"] == "deepseek")
    ))


class FixtureDrivenPresetTests(unittest.TestCase):
    def test_claude_env_is_the_official_set_minus_user_token_keys(self):
        env = H._settings_config("claude", deepseek())["env"]
        official = dict(FIXTURE["claude_code_official_env"])
        expected = {k: v for k, v in official.items() if k not in H.USER_ONLY_ENV_KEYS}
        self.assertEqual(env, expected)

    def test_agent_all_aggregates_both_agents_in_one_spawn(self):
        """PERF P9 (D-13): `--agent all` runs both agents and aggregates the
        status (migrated > current; any failure -> exit 1). D-6.7: the
        default action is the deprovision migration, not seeding."""
        import io
        import contextlib

        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "cc"
            config_dir.mkdir()
            # Minimal providers table (same shape the runtime tests seed) —
            # the migration writes the db directly (daemon-independent).
            db = sqlite3.connect(config_dir / "cc-switch.db")
            db.execute(
                "CREATE TABLE providers (id TEXT, app_type TEXT, name TEXT, "
                "settings_config TEXT, website_url TEXT, category TEXT, "
                "created_at INTEGER, sort_index INTEGER, notes TEXT, icon TEXT, "
                "icon_color TEXT, meta TEXT, is_current INTEGER, "
                "in_failover_queue INTEGER)"
            )
            db.commit()
            db.close()
            log = Path(tmp) / "migrate.log"
            # First run on an unmarked volume: the migration stamps markers
            # (nothing seeded to remove -> "current" aggregate either way —
            # the marker flip alone is not a "migrated" signal).
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = H.main(["--agent", "all",
                             "--config-dir", str(config_dir),
                             "--log", str(log)])
            self.assertEqual(rc, 0)
            self.assertIn(out.getvalue().strip(), {"current", "migrated"})
            # Second run: markers current -> aggregate "current" (idempotent).
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc = H.main(["--agent", "all",
                             "--config-dir", str(config_dir),
                             "--log", str(log)])
            self.assertEqual(rc, 0)
            self.assertEqual(out.getvalue().strip(), "current")

    def test_agent_all_is_sequential_best_effort_on_partial_failure(self):
        """The aggregate is not atomic: rc 1 after a later-agent failure."""
        import io
        import contextlib

        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp) / "cc"
            config_dir.mkdir()
            log = Path(tmp) / "migrate.log"
            with mock.patch.object(
                H,
                "migrate_deprovisioned",
                side_effect=[0, RuntimeError("codex failed")],
            ) as migrate:
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    rc = H.main([
                        "--agent", "all", "--config-dir", str(config_dir),
                        "--log", str(log),
                    ])
            self.assertEqual(rc, 1)
            self.assertEqual(out.getvalue().strip(), "failed")
            self.assertEqual(migrate.call_count, 2)

    def test_1m_suffix_rules_match_the_fixture(self):
        env = H._settings_config("claude", deepseek())["env"]
        suffix = FIXTURE["one_million_context_suffix"]
        for key in suffix["applies_to"]:
            self.assertIn("[1m]", env[key], f"{key} must carry [1m]")
        for key in suffix["not_applicable_to"]:
            self.assertNotIn("[1m]", env[key], f"{key} must NOT carry [1m]")

    def test_official_model_ids_and_endpoint(self):
        env = H._settings_config("claude", deepseek())["env"]
        official_ids = FIXTURE["models"]["official_ids"]
        for key in (
            "ANTHROPIC_MODEL",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
        ):
            base = env[key].removesuffix("[1m]")
            self.assertIn(base, official_ids)
        for key in ("ANTHROPIC_DEFAULT_HAIKU_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL"):
            self.assertIn(env[key], official_ids)
            self.assertEqual(env[key], "deepseek-v4-flash")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], FIXTURE["base_url_anthropic"])
        self.assertEqual(env["CLAUDE_CODE_EFFORT_LEVEL"], "max")

    def test_deprecated_ids_never_generated(self):
        # A-CS03: the deprecated deepseek-chat/reasoner defaults must never
        # come back, and the bare pro name must not appear without [1m] on
        # the [1m]-carrying keys.
        env = H._settings_config("claude", deepseek())["env"]
        for key, value in env.items():
            self.assertNotIn("deepseek-chat", value)
            self.assertNotIn("deepseek-reasoner", value)
        self.assertNotEqual(env["ANTHROPIC_MODEL"], "deepseek-v4-pro")
        self.assertNotEqual(env["ANTHROPIC_DEFAULT_SONNET_MODEL"], "deepseek-v4-pro")

    def test_fresh_install_writes_no_token_keys(self):
        env = H._settings_config("claude", deepseek())["env"]
        for key in H.USER_ONLY_ENV_KEYS:
            self.assertNotIn(key, env)

    def test_preset_format_bumped_and_revision_is_fixture_sensitive(self):
        # v10 (D-6.7): de-seed — templates replace presets, the migration
        # removes historical rows, so the format version is part of the
        # revision hash (a bumped version re-runs the migration).
        self.assertEqual(H.PRESET_FORMAT_VERSION, 10)
        base_revision = H.preset_revision("claude")
        # A mutated fixture must yield a different revision (refresh triggers).
        mutated = json.loads(json.dumps(deepseek()))
        mutated["claude_env"]["ANTHROPIC_MODEL"] = "deepseek-v4-flash"
        payload = {
            "format": H.PRESET_FORMAT_VERSION,
            "agent": "claude",
            "providers": [mutated] + [p for p in H.PRESET_PROVIDERS if p["id"] != "deepseek"],
        }
        import hashlib

        other = hashlib.sha256(
            json.dumps(payload, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertNotEqual(base_revision, other)

    def test_codex_settings_carry_auth_field(self):
        # Upstream `provider switch` refuses codex rows without an "auth"
        # object (IDEA-4 manual test on the real container).
        for provider in H.PRESET_PROVIDERS:
            settings = H._settings_config("codex", provider)
            self.assertIn("auth", settings)
            self.assertIsInstance(settings["auth"], dict)

    def test_codex_api_key_rides_auth_channel(self):
        # 2026-08-21 live probe: the local proxy worker serves the token it
        # captures from live ~/.codex/auth.json at enable time — which is
        # written from settings auth on switch. The key must live THERE,
        # with the TOML api_key line as a legacy mirror.
        settings = H._settings_config("codex", deepseek(), api_key="sk-x-1234")
        self.assertEqual(settings["auth"], {"OPENAI_API_KEY": "sk-x-1234"})
        self.assertIn('api_key = "sk-x-1234"', settings["config"])
        self.assertEqual(H._settings_config("codex", deepseek())["auth"], {})

    def test_bad_fixture_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps({"schema": "nope"}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                H.load_deepseek_fixture(bad)
            bad.write_text(
                json.dumps({**FIXTURE, "claude_code_official_env": {"ANTHROPIC_BASE_URL": "x"}}),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                H.load_deepseek_fixture(bad)


def legacy(pid: str) -> dict:
    """Deep copy of a legacy (non-claude_env) preset row."""
    return json.loads(json.dumps(
        next(p for p in H.PRESET_PROVIDERS if p["id"] == pid)
    ))


class CodexModelCatalogTests(unittest.TestCase):
    """codex-adapt 修复轮（2026-08-20）：codex settings 携带 cc-switch
    `modelCatalog.models` —— 上游切换时生成模型目录文件并注入
    `model_catalog_json`，codex /model 随之显示供应商模型列表（并取代
    fallback 元数据，消「Model metadata not found」）。"""

    def test_deepseek_codex_settings_carry_model_catalog(self):
        settings = H._settings_config("codex", deepseek())
        catalog = settings.get("modelCatalog", {}).get("models", [])
        self.assertEqual(
            [row["model"] for row in catalog],
            ["deepseek-v4-pro", "deepseek-v4-flash"],  # 主推 pro 在前
        )
        # contextWindow：fixture "1M" → 1_000_000（与用户实测 mapping 行一致）
        self.assertEqual(catalog[0]["contextWindow"], 1_000_000)
        self.assertEqual(catalog[1]["contextWindow"], 1_000_000)
        # 既有形态 + 用户实测工作形状：anthropic 端点 + responses（本地路由接管）
        # S8g (2026-08-29): codex presets speak Responses DIRECTLY to the
        # OpenAI-side base (official guides/responses_api) — no translation.
        self.assertIn("auth", settings)
        self.assertIn('base_url = "https://api.deepseek.com/anthropic"', settings["config"])
        self.assertIn('wire_api = "responses"', settings["config"])
        self.assertIn("model_context_window = 1000000", settings["config"])

    def test_providers_without_catalog_omit_the_key(self):
        legacy = {"id": "x", "base_url": "https://x", "model": "m"}
        settings = H._settings_config("codex", legacy)
        self.assertNotIn("modelCatalog", settings)

    def test_context_window_parsing(self):
        f = lambda v: H._context_window_from_length(v)
        self.assertEqual(f("1M"), 1_000_000)
        self.assertEqual(f("384K"), 384_000)
        self.assertEqual(f("131072"), 131072)
        self.assertEqual(f(""), 0)
        self.assertEqual(f("garbage"), 0)


class S8gUpstreamFormatTests(unittest.TestCase):
    """S9a (2026-08-29 user ruling, supersedes S8g): every codex preset
    upstream is the ANTHROPIC endpoint + format — the cc-switch local router
    translates codex Responses into Anthropic Messages. codex rows point at
    each provider anthropic_base_url (one endpoint per provider)."""

    def test_every_preset_declares_anthropic(self):
        for provider in H.PRESET_PROVIDERS:
            self.assertEqual(
                provider.get("codex_api_format"),
                "anthropic",
                f"{provider['id']} must declare anthropic",
            )

    def test_codex_rows_use_the_anthropic_side_base(self):
        for provider in H.PRESET_PROVIDERS:
            expected = provider.get("anthropic_base_url") or provider["base_url"]
            config = H._settings_config("codex", provider)["config"]
            self.assertIn(f'base_url = "{expected}"', config)

    def test_anthropic_format_still_routes_to_the_anthropic_base(self):
        # Legacy translation branch: a provider declaring anthropic keeps
        # pointing codex at anthropic_base_url (the router converts).
        legacy = {
            "id": "legacy", "base_url": "https://x.example",
            "anthropic_base_url": "https://x.example/anthropic",
            "model": "m", "codex_api_format": "anthropic",
        }
        config = H._settings_config("codex", legacy)["config"]
        self.assertIn('base_url = "https://x.example/anthropic"', config)

    def test_codesome_dual_template_shapes(self):
        """D-6: two product-line templates — the cross-wired single row is
        the root cause this split fixes."""
        v3 = next(p for p in H.PRESET_PROVIDERS if p["id"] == "codesome-v3")
        two_in_one = next(p for p in H.PRESET_PROVIDERS if p["id"] == "codesome-2in1")
        self.assertNotIn("codesome", [p["id"] for p in H.PRESET_PROVIDERS])
        # V3: one gateway domain for BOTH agents (claude speaks Anthropic
        # there; codex S9a-translates to the same).
        self.assertEqual(v3["model"], "gpt-5.6-terra")
        self.assertEqual(v3["base_url"], "https://cc.codesome.ai")
        v3_claude = H._settings_config("claude", v3)
        self.assertEqual(v3_claude["env"]["ANTHROPIC_BASE_URL"], "https://cc.codesome.ai")
        v3_codex = H._settings_config("codex", v3)["config"]
        self.assertIn('base_url = "https://cc.codesome.ai"', v3_codex)
        self.assertIn('model = "gpt-5.6-terra"', v3_codex)
        # 二合一 (V5): claude on /api, codex S9a-translates to the same;
        # the OpenAI-side base_url is the official native /openai.
        self.assertEqual(two_in_one["base_url"], "https://v5.codesome.cn/openai")
        self.assertEqual(two_in_one["anthropic_base_url"], "https://v5.codesome.cn/api")
        self.assertEqual(two_in_one["model"], "gpt-5.6-terra")
        two_claude = H._settings_config("claude", two_in_one)
        self.assertEqual(
            two_claude["env"]["ANTHROPIC_BASE_URL"], "https://v5.codesome.cn/api"
        )
        two_codex = H._settings_config("codex", two_in_one)["config"]
        self.assertIn('base_url = "https://v5.codesome.cn/api"', two_codex)
        self.assertIn('model = "gpt-5.6-terra"', two_codex)

    def test_codesome_claude_env_is_official_core_set(self):
        """D-6.5 + the official core-three/method-2 facts: the attribution
        header MUST be 0, NONESSENTIAL_TRAFFIC rides along, and — critically
        — NO model keys (the official大扫除 requires clearing ANTHROPIC_MODEL
        residues; the key's server-side group routes models)."""
        for pid in ("codesome-v3", "codesome-2in1"):
            provider = next(p for p in H.PRESET_PROVIDERS if p["id"] == pid)
            claude = H._settings_config("claude", provider)
            self.assertEqual(claude["env"]["CLAUDE_CODE_ATTRIBUTION_HEADER"], "0")
            self.assertEqual(
                claude["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"], "1")
            for key in (
                "ANTHROPIC_MODEL",
                "ANTHROPIC_DEFAULT_OPUS_MODEL",
                "ANTHROPIC_DEFAULT_SONNET_MODEL",
                "ANTHROPIC_DEFAULT_HAIKU_MODEL",
                "CLAUDE_CODE_SUBAGENT_MODEL",
                "CLAUDE_CODE_EFFORT_LEVEL",
            ):
                self.assertNotIn(key, claude["env"], pid)
            self.assertNotIn("ANTHROPIC_AUTH_TOKEN", claude["env"], pid)

    def test_preset_revision_bumped_for_the_format_migration(self):
        # v10 (D-6.7): de-seed + dual codesome templates; existing volumes
        # re-run the one-shot migration.
        self.assertEqual(H.PRESET_FORMAT_VERSION, 10)

    def test_every_preset_carries_a_codex_model_catalog(self):
        # S8g-2 (user field report): without model_catalog the cc-switch
        # switch generates no catalog file and codex /model shows NOTHING.
        # Exception: volcengine-ark carries no model at all (the user
        # configures an endpoint ID) — nothing to catalog.
        for provider in H.PRESET_PROVIDERS:
            if not provider.get("model"):
                self.assertNotIn(
                    "modelCatalog",
                    H._settings_config("codex", provider),
                    provider["id"],
                )
                continue
            catalog = provider.get("model_catalog") or []
            self.assertTrue(
                catalog and catalog[0].get("model"),
                f"{provider['id']} must carry a codex model catalog",
            )
            settings = H._settings_config("codex", provider)
            self.assertIn("modelCatalog", settings, provider["id"])
            self.assertIn("model_context_window", settings["config"], provider["id"])


class ClaudeSettingsBaseTests(unittest.TestCase):
    """Retest round 2 (2026-08-21): upstream's claude switch replaces
    settings.json with the row's settings_config WHOLESALE — preset rows must
    carry the non-env base (statusLine/enabledPlugins/...) or the user's
    setup is wiped on the first switch."""

    def test_base_loads_the_repo_template(self):
        base = H.load_claude_settings_base()
        self.assertIn("statusLine", base)
        self.assertIn("enabledPlugins", base)
        self.assertIn("extraKnownMarketplaces", base)
        self.assertNotIn("env", base)

    def test_fresh_claude_settings_carry_base(self):
        settings = H._settings_config("claude", deepseek())
        self.assertIn("statusLine", settings)
        self.assertIn("enabledPlugins", settings)
        self.assertTrue(settings["env"]["ANTHROPIC_BASE_URL"])

    def test_custom_preset_path_carries_base_too(self):
        kimi = next(p for p in H.PRESET_PROVIDERS if p["id"] == "kimi")
        settings = H._settings_config("claude", kimi)
        self.assertIn("statusLine", settings)


class DeprovisionMigrationTests(unittest.TestCase):
    """D-6.7: the one-shot migration removes the historical seeded rows
    fingerprint-guarded; repurposed rows and anything else survive."""

    def _mk_db(self, config_dir: Path) -> None:
        db = sqlite3.connect(config_dir / "cc-switch.db")
        db.execute(
            "CREATE TABLE providers (id TEXT, app_type TEXT, name TEXT, "
            "settings_config TEXT, website_url TEXT, category TEXT, "
            "created_at INTEGER, sort_index INTEGER, notes TEXT, icon TEXT, "
            "icon_color TEXT, meta TEXT, is_current INTEGER, "
            "in_failover_queue INTEGER)"
        )
        db.commit()
        db.close()

    def _insert(self, config_dir: Path, agent: str, pid: str, settings: str) -> None:
        db = sqlite3.connect(config_dir / "cc-switch.db")
        db.execute(
            "INSERT INTO providers (id, app_type, name, settings_config, "
            "website_url, category, created_at, sort_index, notes, icon, "
            "icon_color, meta, is_current, in_failover_queue) "
            "VALUES (?, ?, ?, ?, '', 'custom', 0, 0, '', NULL, NULL, '{}', 0, 0)",
            (pid, agent, pid, settings),
        )
        db.commit()
        db.close()

    def _ids(self, config_dir: Path, agent: str) -> set:
        db = sqlite3.connect(config_dir / "cc-switch.db")
        rows = db.execute(
            "SELECT id FROM providers WHERE app_type = ?", (agent,)
        ).fetchall()
        db.close()
        return {r[0] for r in rows}

    def test_retired_preset_rows_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            self._mk_db(config_dir)
            old_codesome = json.dumps({
                "env": {"ANTHROPIC_BASE_URL": "https://v5.codesome.cn/api",
                        "ANTHROPIC_MODEL": "gpt-5.6-sol"},
            })
            self._insert(config_dir, "claude", "codesome", old_codesome)
            self._insert(config_dir, "claude", "kimi",
                         json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://api.moonshot.cn/anthropic"}}))
            log = config_dir / "m.log"
            removed = H.migrate_deprovisioned(
                config_dir, "claude", H.preset_revision("claude"), log.open("w", encoding="utf-8"))
            self.assertEqual(removed, 2)
            self.assertEqual(self._ids(config_dir, "claude"), set())

    def test_repurposed_rows_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            self._mk_db(config_dir)
            # Same id, but the config no longer carries the preset fingerprint —
            # the user repurposed it; the migration must leave it alone.
            self._insert(config_dir, "claude", "codesome",
                         json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://my.own Relay".replace(" ", "")}}))
            self._insert(config_dir, "claude", "user-row",
                         json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://user.example"}}))
            removed = H.migrate_deprovisioned(
                config_dir, "claude", H.preset_revision("claude"),
                (config_dir / "m.log").open("w", encoding="utf-8"))
            self.assertEqual(removed, 0)
            self.assertEqual(
                self._ids(config_dir, "claude"), {"codesome", "user-row"})

    def test_marker_makes_migration_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            self._mk_db(config_dir)
            self._insert(config_dir, "codex", "codesome",
                         json.dumps({"auth": {}, "config": 'base_url = "https://cc.codesome.ai"'}))
            revision = H.preset_revision("codex")
            removed = H.migrate_deprovisioned(
                config_dir, "codex", revision, (config_dir / "m.log").open("w", encoding="utf-8"))
            self.assertEqual(removed, 1)
            # Second run: marker matches -> preset_required reports current.
            required, _reason = H.preset_required(config_dir, "codex", revision)
            self.assertFalse(required)

    def test_missing_db_is_a_clean_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            removed = H.migrate_deprovisioned(
                config_dir, "claude", H.preset_revision("claude"),
                (config_dir / "m.log").open("w", encoding="utf-8"))
            self.assertEqual(removed, 0)
            self.assertTrue(H.marker_path(config_dir, "claude").is_file())


class TemplateManifestTests(unittest.TestCase):
    """D-6.8: the add-provider picker's data — derived from the same
    PRESET_PROVIDERS payload as the simple-add seeds (no drift possible)."""

    def test_manifest_lists_all_templates_with_metadata(self):
        manifest = H.provider_templates_manifest()
        self.assertEqual(
            [t["id"] for t in manifest],
            ["deepseek", "volcengine-ark", "zhipu", "kimi", "codesome-v3", "codesome-2in1"],
        )
        v3 = next(t for t in manifest if t["id"] == "codesome-v3")
        self.assertEqual(v3["key_prefix"], "sk-")
        self.assertIn("meta.codesome.cn", v3["acquire_url"])
        two = next(t for t in manifest if t["id"] == "codesome-2in1")
        self.assertEqual(two["key_prefix"], "cr-")
        self.assertEqual(two["default_model"], "gpt-5.6-terra")
        # Non-sponsor templates carry no acquire URL (D-3: no affiliate
        # placement outside codesome).
        for t in manifest:
            if not t["id"].startswith("codesome"):
                self.assertNotIn("acquire_url", t)

    def test_manifest_is_secret_free(self):
        blob = json.dumps(H.provider_templates_manifest())
        for forbidden in ("api_key", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"):
            self.assertNotIn(forbidden, blob)

    def test_print_manifest_flag_emits_json(self):
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = H.main([
                    "--agent", "claude",  # unused by the manifest path
                    "--config-dir", str(Path(tmp)),
                    "--log", str(Path(tmp) / "x.log"),
                    "--print-manifest",
                ])
            self.assertEqual(rc, 0)
            parsed = json.loads(out.getvalue())
            self.assertEqual(parsed[0]["id"], "deepseek")


class CodesomeCodexOptionsTests(unittest.TestCase):
    """D-7: thinking depth + auto-compact watermark flow into the codex
    TOML and the claude env."""

    def test_codex_reasoning_effort_and_compact(self):
        v3 = next(p for p in H.PRESET_PROVIDERS if p["id"] == "codesome-v3")
        settings = H._settings_config(
            "codex", v3, api_key="sk-x", reasoning_effort="medium",
            compact_token_limit=900_000)
        config = settings["config"]
        self.assertIn('model_reasoning_effort = "medium"', config)
        self.assertIn("model_auto_compact_token_limit = 900000", config)
        # Official order: context window, then auto-compact limit.
        self.assertLess(
            config.index("model_context_window"),
            config.index("model_auto_compact_token_limit"))

    def test_codex_defaults_unchanged_when_flags_absent(self):
        v3 = next(p for p in H.PRESET_PROVIDERS if p["id"] == "codesome-v3")
        config = H._settings_config("codex", v3)["config"]
        self.assertIn('model_reasoning_effort = "high"', config)
        self.assertNotIn("model_auto_compact_token_limit", config)

    def test_claude_compact_rides_env(self):
        two = next(p for p in H.PRESET_PROVIDERS if p["id"] == "codesome-2in1")
        env = H._settings_config("claude", two, compact_token_limit=150_000)["env"]
        self.assertEqual(env["CLAUDE_AUTO_COMPACT_ENABLED"], "true")
        self.assertEqual(env["CLAUDE_AUTO_COMPACT_WINDOW"], "150000")


class ReconcileTests(unittest.TestCase):
    """Post-init invariant (retest round 2): proxy on ⟺ the current
    provider is a real third-party endpoint; a PRISTINE imported 'default'
    row is removed with current re-pointed to the named official row."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config_dir = Path(self.tmp.name)
        db = sqlite3.connect(self.config_dir / "cc-switch.db")
        db.execute(
            "CREATE TABLE providers (id TEXT, app_type TEXT, name TEXT, "
            "settings_config TEXT, website_url TEXT, category TEXT, "
            "created_at INTEGER, sort_index INTEGER, notes TEXT, icon TEXT, "
            "icon_color TEXT, meta TEXT, is_current INTEGER, "
            "in_failover_queue INTEGER)"
        )
        db.commit()
        db.close()
        self.runner_calls: list[list[str]] = []

    def _seed(self, pid: str, agent: str, settings: dict, *, current=False,
              name=None):
        db = sqlite3.connect(self.config_dir / "cc-switch.db")
        db.execute(
            "INSERT INTO providers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, agent, name or pid, json.dumps(settings),
             "", "custom", 1, 0, "", None, None, "{}",
             1 if current else 0, 0),
        )
        db.commit()
        db.close()

    def _rows(self, agent: str) -> dict:
        db = sqlite3.connect(self.config_dir / "cc-switch.db")
        try:
            return {
                row[0]: (row[1], json.loads(row[2]))
                for row in db.execute(
                    "SELECT id, is_current, settings_config FROM providers "
                    "WHERE app_type = ?", (agent,))
            }
        finally:
            db.close()

    def _reconcile(self, rc=0):
        import subprocess as _sp

        def fake_runner(argv, **_kwargs):
            self.runner_calls.append(list(argv))
            return _sp.CompletedProcess(argv, rc, stdout="", stderr="boom"
                                        if rc else "")

        log_path = self.config_dir / "reconcile.log"
        with log_path.open("w", encoding="utf-8") as log_io:
            return H.reconcile_runtime_state(self.config_dir, log_io,
                                             runner=fake_runner)

    def test_pristine_default_removed_and_routes_disabled(self):
        # The legacy volume shape: claude sitting on cc-switch's imported
        # 'default' snapshot with the route force-enabled by the old
        # entrypoint; codex already on its official placeholder.
        self._seed("default", "claude",
                   {"statusLine": {"type": "command", "command": "x"}},
                   current=True, name="default")
        self._seed("claude-official", "claude", {"env": {}})
        self._seed("deepseek", "claude", {
            "env": {"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
                    "ANTHROPIC_AUTH_TOKEN": "sk-user"}})
        self._seed("codex-official", "codex", {"auth": {}, "config": ""},
                   current=True)
        actions = self._reconcile()

        rows = self._rows("claude")
        self.assertNotIn("default", rows)                       # artifact gone
        self.assertEqual(rows["claude-official"][0], 1)         # re-pointed
        self.assertIn("statusLine", rows["claude-official"][1])  # base seeded
        self.assertEqual(rows["deepseek"][0], 0)                # untouched
        # Invariant: both current rows are non-real → both routes off.
        self.assertEqual(
            self.runner_calls,
            [["cc-switch", "proxy", "-a", "claude", "disable"],
             ["cc-switch", "proxy", "-a", "codex", "disable"]])
        self.assertTrue(any("default" in a for a in actions))

    def test_real_current_provider_enables_route(self):
        self._seed("claude-official", "claude", {"env": {}}, current=True)
        self._seed("deepseek", "claude", {
            "env": {"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic"}},
            current=False)
        self._seed("codex-official", "codex", {"auth": {}, "config": ""})
        self._seed("deepseek", "codex", {
            "auth": {}, "config": 'model_provider = "deepseek"\n'
                                  "[model_providers.deepseek]\n"
                                  'base_url = "https://api.deepseek.com"\n'},
            current=True)
        self._reconcile()
        self.assertEqual(
            self.runner_calls,
            [["cc-switch", "proxy", "-a", "claude", "disable"],   # official row
             ["cc-switch", "proxy", "-a", "codex", "enable"],     # real row
             ["cc-switch", "proxy", "-a", "codex", "show"]])      # route verify

    def test_repurposed_default_is_kept(self):
        self._seed("default", "claude", {
            "env": {"ANTHROPIC_BASE_URL": "https://my-proxy.example.com",
                    "ANTHROPIC_AUTH_TOKEN": "sk-mine"}}, current=True)
        self._seed("claude-official", "claude", {"env": {}})
        self._seed("codex-official", "codex", {"auth": {}, "config": ""},
                   current=True)
        self._reconcile()
        rows = self._rows("claude")
        self.assertIn("default", rows)                    # user's row survives
        self.assertEqual(rows["default"][0], 1)           # …and stays current
        self.assertEqual(rows["claude-official"][0], 0)
        self.assertIn(["cc-switch", "proxy", "-a", "claude", "enable"],
                      self.runner_calls)                  # real row → route on

    def test_missing_official_rows_are_created(self):
        self._seed("deepseek", "claude", {
            "env": {"ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic"}},
            current=True)
        self._seed("deepseek", "codex", {
            "auth": {}, "config": 'model_provider = "d"\n'
                                  "[model_providers.d]\n"
                                  'base_url = "https://x"\n'},
            current=True)
        self._reconcile()
        rows = self._rows("claude")
        self.assertIn("claude-official", rows)
        self.assertIn("statusLine", rows["claude-official"][1])
        self.assertEqual(rows["claude-official"][0], 0)   # current untouched
        self.assertIn("codex-official", self._rows("codex"))
        self.assertEqual(
            self.runner_calls,
            [["cc-switch", "proxy", "-a", "claude", "enable"],
             ["cc-switch", "proxy", "-a", "claude", "show"],
             ["cc-switch", "proxy", "-a", "codex", "enable"],
             ["cc-switch", "proxy", "-a", "codex", "show"]])

    def test_second_run_is_steady(self):
        self._seed("claude-official", "claude", {"env": {}}, current=True)
        self._seed("codex-official", "codex", {"auth": {}, "config": ""},
                   current=True)
        self._reconcile()
        self._reconcile()
        rows = self._rows("claude")
        self.assertEqual(list(rows), ["claude-official"])
        self.assertEqual(rows["claude-official"][0], 1)

    def test_runner_failure_never_raises(self):
        self._seed("claude-official", "claude", {"env": {}}, current=True)
        self._seed("codex-official", "codex", {"auth": {}, "config": ""},
                   current=True)
        actions = self._reconcile(rc=1)
        self.assertFalse(any(a.startswith("proxy") for a in actions))
        # The DB steps still committed.
        self.assertIn("statusLine", self._rows("claude")["claude-official"][1])

    def test_enable_verifies_route_and_recovers_via_daemon_restart(self):
        # Manual round 3 (2026-08-21): enable can silently no-op with a
        # stale/dead daemon — the reconcile verifies the port listens and
        # recovers (daemon stop→start→re-enable), never failing boot.
        import socket as _socket
        import subprocess as _sp

        sock = _socket.socket()
        sock.bind(("127.0.0.1", 0))
        closed_port = sock.getsockname()[1]
        sock.close()

        self._seed("claude-official", "claude", {"env": {}}, current=True)
        self._seed("deepseek", "codex", {
            "auth": {}, "config": 'model_provider = "d"\n'
                                  "[model_providers.d]\n"
                                  'base_url = "https://x"\n'},
            current=True)

        listener: list = []
        calls: list[list[str]] = []

        def fake_runner(argv, **_kwargs):
            calls.append(list(argv))
            joined = " ".join(argv)
            stdout = ""
            if "show" in argv:
                stdout = f"- Codex: enabled, configured {closed_port}\n"
            if "enable" in joined and len(calls) > 3 and not listener:
                # the recovery re-enable → bring the route up for real
                server = _socket.socket()
                server.bind(("127.0.0.1", closed_port))
                server.listen(4)
                listener.append(server)
            return _sp.CompletedProcess(argv, 0, stdout=stdout, stderr="")

        self.addCleanup(lambda: listener and listener[0].close())
        log_path = self.config_dir / "reconcile.log"
        with log_path.open("w", encoding="utf-8") as log_io:
            actions = H.reconcile_runtime_state(self.config_dir, log_io,
                                                runner=fake_runner)
        joined = [" ".join(c) for c in calls]
        self.assertTrue(any("daemon" in a and "stop" in a for a in joined))
        self.assertTrue(any("daemon" in a and "start" in a for a in joined))
        self.assertTrue(any("recovered codex route" in a for a in actions))


if __name__ == "__main__":
    unittest.main()
