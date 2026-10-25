"""Extensions (skills / MCP / plugins) host-side data plane (v2.1.16 b5).

Mirrors ``aisc.application.cc_switch_provider``: resolves the running
container for a runtime, then ``docker exec -i``s the in-container adapter
(``aisc-extensions-adapter``). The adapter speaks ``aisc.extensions/v1``;
this layer validates the envelope and maps adapter failures onto CliError
with the adapter's stable codes. No secret crosses argv — the MCP config
rides stdin (same channel discipline as the provider adapter).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from aisc.application.runtime import resolve_running_container
from aisc.domain.models import CliError, RuntimeExitCode

from aisc.application.cc_switch_provider import _SCOPE_WRAPPER

PROTOCOL = "aisc.extensions/v1"
ADAPTER_PATH = "/usr/local/bin/aisc-extensions-adapter"

_OPS = (
    "list", "toggle", "delete", "skill-install", "mcp-add",
    "plugin-install", "plugin-uninstall", "plugin-update",
    "skill-search", "deeplink", "skill-repo-add",
    "skill-update", "plugin-market-list", "plugin-market-add", "plugin-search",
    "mcp-search", "mcp-market-install",
)
_KINDS = ("skills", "mcp", "plugins")
_AGENTS = ("claude", "codex")


def _validate(op: str, kind: Optional[str], agent: Optional[str]) -> None:
    if op not in _OPS:
        raise CliError(
            message=f"Invalid extensions op: {op}",
            exit_code=RuntimeExitCode.USAGE_ERROR,
            error_code="AISC_ERR_USAGE",
        )
    if kind is not None and kind not in _KINDS:
        raise CliError(
            message=f"Invalid extensions kind: {kind}",
            exit_code=RuntimeExitCode.USAGE_ERROR,
            error_code="AISC_ERR_USAGE",
        )
    if agent is not None and agent not in _AGENTS:
        raise CliError(
            message=f"Invalid extensions agent: {agent}",
            exit_code=RuntimeExitCode.USAGE_ERROR,
            error_code="AISC_ERR_USAGE",
        )


def _exec_adapter(
    runtime_id: str,
    registry_root: Any,
    executor: Any,
    op: str,
    *,
    kind: Optional[str] = None,
    item_id: Optional[str] = None,
    agent: Optional[str] = None,
    on: Optional[bool] = None,
    spec: Optional[str] = None,
    apps: Optional[str] = None,
    query: Optional[str] = None,
    url: Optional[str] = None,
    stdin_text: str = "",
) -> Dict[str, Any]:
    from aisc.adapters.docker_ import RealDockerExecutor

    executor = executor or RealDockerExecutor()
    argv = ["exec", "-i"]
    container = resolve_running_container(runtime_id, executor, registry_root)
    argv.append(container)
    argv.extend([
        "bash", "-c",
        _SCOPE_WRAPPER,
        "aisc-scope", "/proc/1/environ", "--",
        ADAPTER_PATH, op,
    ])
    if kind:
        argv.extend(["--kind", kind])
    if item_id:
        argv.extend(["--id", item_id])
    if agent:
        argv.extend(["--agent", agent])
    if on is not None:
        argv.extend(["--on", "true" if on else "false"])
    if spec:
        argv.extend(["--spec", spec])
    if apps:
        argv.extend(["--apps", apps])
    if query:
        argv.extend(["--query", query])
    if url:
        argv.extend(["--url", url])

    result = executor.run_captured(argv, timeout=600.0, input_text=stdin_text)
    if result.exit_code != 0 and not (result.stdout or "").strip():
        raise CliError(
            message=f"extensions {op} failed: {(result.stderr or '').strip()[:200]}",
            exit_code=1,
            error_code="AISC_ERR_EXTENSIONS_EXEC_FAILED",
        )
    try:
        envelope = json.loads((result.stdout or "").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise CliError(
            message=f"invalid extensions adapter output for {op}: {exc}",
            exit_code=1,
            error_code="AISC_ERR_EXTENSIONS_EXEC_FAILED",
        ) from exc
    if not isinstance(envelope, dict) or envelope.get("schema") != PROTOCOL:
        raise CliError(
            message=f"extensions adapter envelope schema mismatch for {op}",
            exit_code=1,
            error_code="AISC_ERR_EXTENSIONS_EXEC_FAILED",
        )
    if not envelope.get("ok"):
        error = envelope.get("error") or {}
        raise CliError(
            message=str(error.get("message") or f"extensions {op} failed"),
            exit_code=1,
            error_code=str(error.get("code") or "AISC_ERR_EXTENSIONS_EXEC_FAILED"),
        )
    return envelope


def _registry_root(workspace: Optional[str]) -> Path:
    from aisc.application.data_root import workspace_state_dir

    ws_path = Path(workspace).resolve() if workspace else Path.cwd()
    return workspace_state_dir(ws_path)


def extensions_list(runtime_id: str, kind: str, workspace: Optional[str],
                    executor: Any) -> Dict[str, Any]:
    _validate("list", kind, None)
    envelope = _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "list", kind=kind
    )
    return {"kind": kind, "items": envelope.get("items") or [],
            "operation_id": envelope.get("operation_id")}


def extensions_toggle(runtime_id: str, kind: str, item_id: str, agent: str,
                      on: bool, workspace: Optional[str], executor: Any) -> Dict[str, Any]:
    _validate("toggle", kind, agent)
    _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "toggle",
        kind=kind, item_id=item_id, agent=agent, on=on,
    )
    return {"kind": kind, "id": item_id, "agent": agent, "on": on}


def extensions_delete(runtime_id: str, kind: str, item_id: str,
                      workspace: Optional[str], executor: Any) -> Dict[str, Any]:
    _validate("delete", kind, None)
    _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "delete",
        kind=kind, item_id=item_id,
    )
    return {"kind": kind, "id": item_id}


def extensions_skill_install(runtime_id: str, spec: str,
                             workspace: Optional[str], executor: Any) -> Dict[str, Any]:
    _validate("skill-install", None, None)
    _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "skill-install", spec=spec
    )
    return {"kind": "skills", "spec": spec}


def extensions_skill_update(runtime_id: str, spec: str,
                             workspace: Optional[str], executor: Any) -> Dict[str, Any]:
    _validate("skill-update", None, None)
    _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "skill-update", spec=spec
    )
    return {"kind": "skills", "spec": spec}


def extensions_mcp_add(runtime_id: str, config: Dict[str, Any], apps: str,
                       workspace: Optional[str], executor: Any) -> Dict[str, Any]:
    _validate("mcp-add", None, None)
    envelope = _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "mcp-add",
        apps=apps, stdin_text=json.dumps(config, ensure_ascii=False),
    )
    return {"kind": "mcp", "apps": apps,
            "operation_id": envelope.get("operation_id")}


def extensions_plugin_install(runtime_id: str, plugin_id: str,
                              workspace: Optional[str], executor: Any) -> Dict[str, Any]:
    _validate("plugin-install", None, None)
    _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "plugin-install",
        item_id=plugin_id,
    )
    return {"kind": "plugins", "id": plugin_id}


def extensions_plugin_uninstall(runtime_id: str, plugin_id: str,
                                workspace: Optional[str], executor: Any) -> Dict[str, Any]:
    _validate("plugin-uninstall", None, None)
    _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "plugin-uninstall",
        kind="plugins", item_id=plugin_id,
    )
    return {"kind": "plugins", "id": plugin_id}


def extensions_plugin_update(runtime_id: str, plugin_id: str,
                             workspace: Optional[str], executor: Any) -> Dict[str, Any]:
    _validate("plugin-update", None, None)
    _exec_adapter(
        runtime_id, _registry_root(workspace), executor, "plugin-update",
        item_id=plugin_id,
    )
    return {"kind": "plugins", "id": plugin_id}

def extensions_call_raw(runtime_id: str, op: str, workspace: Optional[str],
                        executor: Any, *, kind: Optional[str] = None,
                        item_id: Optional[str] = None, query: Optional[str] = None,
                        url: Optional[str] = None) -> Dict[str, Any]:
    """b7 商城通用透传（skill-search / deeplink / repos / marketplaces）。"""
    _validate(op, kind, None)
    envelope = _exec_adapter(
        runtime_id, _registry_root(workspace), executor, op,
        kind=kind, item_id=item_id, query=query, url=url,
    )
    return {"op": op, "items": envelope.get("items") or [],
            "operation_id": envelope.get("operation_id")}