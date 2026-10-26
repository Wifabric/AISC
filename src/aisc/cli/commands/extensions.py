"""``aisc extensions`` command layer (v2.1.16 b5).

Thin argv->application mapping for the extensions data plane
(``aisc.extensions/v1``): skills / MCP / plugins list + lifecycle ops.
All ops non-interactive, ``--format json`` machine-compatible.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from aisc.domain.models import CliError


def _runtime(args: argparse.Namespace):
    return args.runtime_id, args.workspace


def cmd_extensions_list(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_list

    runtime_id, workspace = _runtime(args)
    return extensions_list(runtime_id, args.kind, workspace, None)


def cmd_extensions_toggle(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_toggle

    runtime_id, workspace = _runtime(args)
    return extensions_toggle(
        runtime_id, args.kind, args.id, args.agent, args.enable,
        workspace, None,
    )


def cmd_extensions_delete(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_delete

    runtime_id, workspace = _runtime(args)
    return extensions_delete(runtime_id, args.kind, args.id, workspace, None)


def cmd_extensions_skill_install(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_skill_install

    runtime_id, workspace = _runtime(args)
    return extensions_skill_install(runtime_id, args.spec, workspace, None)


def cmd_extensions_skill_install_group(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_skill_install_group

    runtime_id, workspace = _runtime(args)
    specs = [spec.strip() for spec in args.specs.split(",") if spec.strip()]
    return extensions_skill_install_group(runtime_id, specs, workspace, None)


def cmd_extensions_skill_update(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_skill_update

    runtime_id, workspace = _runtime(args)
    return extensions_skill_update(runtime_id, args.spec, workspace, None)


def cmd_extensions_mcp_add(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_mcp_add

    runtime_id, workspace = _runtime(args)
    raw = sys.stdin.read().strip()
    if not raw:
        raise CliError(message="MCP config JSON required on stdin",
                       exit_code=2, error_code="AISC_ERR_USAGE")
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CliError(message=f"invalid MCP config JSON: {exc}",
                       exit_code=2, error_code="AISC_ERR_USAGE") from exc
    return extensions_mcp_add(runtime_id, config, args.apps, workspace, None)


def cmd_extensions_plugin_install(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_plugin_install

    runtime_id, workspace = _runtime(args)
    return extensions_plugin_install(runtime_id, args.id, workspace, None)


def cmd_extensions_plugin_uninstall(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_plugin_uninstall

    runtime_id, workspace = _runtime(args)
    return extensions_plugin_uninstall(runtime_id, args.id, workspace, None)


def cmd_extensions_plugin_update(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_plugin_update

    runtime_id, workspace = _runtime(args)
    return extensions_plugin_update(runtime_id, args.id, workspace, None)


def print_extensions_text(data: Dict[str, Any]) -> None:
    items = data.get("items")
    if items is None:
        print(json.dumps(data, ensure_ascii=False))
        return
    kind = data.get("kind", "")
    for item in items:
        if kind == "skills":
            flags = ("claude" if item.get("enabled_claude") else "-") + \
                    ("/" if item.get("enabled_codex") else "")
            print(f"{item.get('name', '')}\t{flags}\t{item.get('repo', '')}\t{item.get('description', '')[:60]}")
        elif kind == "mcp":
            flags = ("claude" if item.get("enabled_claude") else "-") + \
                    ("/" if item.get("enabled_codex") else "")
            target = item.get("url") or item.get("command") or ""
            print(f"{item.get('id', '')}\t{item.get('name', '')}\t{item.get('transport', '')}\t{flags}\t{target}")
        else:
            print(f"{item.get('id', '')}\t{item.get('version', '')}\t{item.get('scope', '')}\t{item.get('last_updated', '')}")

def cmd_extensions_skill_search(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_call_raw

    runtime_id, workspace = _runtime(args)
    return extensions_call_raw(runtime_id, "skill-search", workspace, None,
                               query=args.query)


def cmd_extensions_deeplink(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_call_raw

    runtime_id, workspace = _runtime(args)
    return extensions_call_raw(runtime_id, "deeplink", workspace, None,
                               url=args.url)


def cmd_extensions_skill_repo_add(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_call_raw

    runtime_id, workspace = _runtime(args)
    return extensions_call_raw(runtime_id, "skill-repo-add", workspace, None,
                               item_id=args.id)


def cmd_extensions_plugin_market_list(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_call_raw

    runtime_id, workspace = _runtime(args)
    return extensions_call_raw(runtime_id, "plugin-market-list", workspace, None)


def cmd_extensions_plugin_market_add(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_call_raw

    runtime_id, workspace = _runtime(args)
    return extensions_call_raw(runtime_id, "plugin-market-add", workspace, None,
                               item_id=args.id)


def cmd_extensions_plugin_search(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_call_raw

    runtime_id, workspace = _runtime(args)
    return extensions_call_raw(runtime_id, "plugin-search", workspace, None,
                               query=args.query)


def cmd_extensions_mcp_search(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_call_raw

    runtime_id, workspace = _runtime(args)
    return extensions_call_raw(runtime_id, "mcp-search", workspace, None,
                               query=args.query)


def cmd_extensions_mcp_market_install(args: argparse.Namespace) -> Dict[str, Any]:
    from aisc.application.extensions import extensions_call_raw

    runtime_id, workspace = _runtime(args)
    return extensions_call_raw(runtime_id, "mcp-market-install", workspace, None,
                               item_id=args.id)
