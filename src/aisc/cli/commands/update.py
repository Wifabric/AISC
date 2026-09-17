"""``aisc update`` command surface (0.1.0 A4, D-7).

``--check`` prints the plan; the bare form performs the frozen-exe update.
Envelope-compatible JSON in ``--format json``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import aisc
from aisc.application.bundle_fetch import BundleFetchError, BundleFetcher
from aisc.application.update import (
    UPDATE_ERROR_STATE,
    UPDATE_ERROR_USAGE,
    UpdateError,
    build_check_report,
    detect_install_form,
    perform_update,
)
from aisc.domain.models import CliError


def _root_for_tools() -> Path:
    from aisc.application.resources import locate_aisc_root

    root = locate_aisc_root()
    if root is None:
        raise CliError(
            message="tool pins need an AISC root (repo or bundle) to layer "
                    "against — run `aisc bundle fetch` first or use --aisc-root",
            exit_code=1, error_code="AISC_ERR_GENERAL")
    return root


def _data_root() -> Path:
    from aisc.application.data_root import shared_root

    return shared_root()


def _to_cli_error(exc: Exception) -> CliError:
    if isinstance(exc, (UpdateError, BundleFetchError)):
        return CliError(message=exc.message, exit_code=1, error_code="AISC_ERR_GENERAL")
    raise exc


def cmd_update_check(version: Optional[str] = None) -> Dict[str, Any]:
    from aisc.application.tool_versions import tools_check_section

    form = detect_install_form()
    try:
        fetcher = BundleFetcher()
        report = build_check_report(
            cli_version=aisc.__version__,
            form=form,
            fetcher=fetcher,
            requested_version=version,
        )
    except (UpdateError, BundleFetchError) as exc:
        raise _to_cli_error(exc) from exc
    # A5: the tools block is network-tolerant (latest=null on registry
    # failure) — a check must never fail because the network did.
    report["tools"] = tools_check_section(_root_for_tools())
    return report


def cmd_update(
    *,
    version: Optional[str] = None,
    from_file: Optional[str] = None,
    sha256: Optional[str] = None,
    rebuild: bool = False,
    pin_tool: Optional[list] = None,
) -> Dict[str, Any]:
    if pin_tool:
        from aisc.application.tool_versions import write_user_pins

        pins: Dict[str, str] = {}
        for spec in pin_tool:
            if "=" not in spec:
                raise CliError(
                    message=f"--pin-tool expects KEY=VALUE, got {spec!r} "
                            f"(pinnable: CLAUDE_CODE_VERSION, CODEX_VERSION, CC_SWITCH_VERSION)",
                    exit_code=2, error_code="AISC_ERR_USAGE")
            k, v = spec.split("=", 1)
            pins[k.strip()] = v.strip()
        _root_for_tools()  # fail fast when there is no root to layer against
        try:
            path = write_user_pins(_data_root(), pins)
        except ValueError as exc:
            raise CliError(message=str(exc), exit_code=2,
                           error_code="AISC_ERR_USAGE") from exc
        return {
            "status": "pinned",
            "path": str(path),
            "pins": pins,
            "note": "pins apply at the next image build (aisc build / docker-rebuild); "
                    "they survive CLI updates, installer upgrades and bundle fetches",
        }
    form = detect_install_form()
    try:
        return perform_update(
            cli_version=aisc.__version__,
            form=form,
            fetcher=BundleFetcher(),
            version=version,
            from_file=Path(from_file) if from_file else None,
            sha256=sha256,
            rebuild=rebuild,
        )
    except (UpdateError, BundleFetchError) as exc:
        raise _to_cli_error(exc) from exc


def print_update_text(sub: str, data: Any) -> None:
    if not isinstance(data, dict):
        return
    if sub == "check":
        print(f"form     : {data.get('form')}")
        print(f"current  : {data.get('cli_version')}")
        print(f"latest   : {data.get('latest_final') or '(none)'}")
        print(f"action   : {data.get('action')}")
        if data.get("update_available") is not None:
            print(f"available: {data.get('update_available')}")
        for t in data.get("tools") or []:
            latest = t.get("latest") or "unknown"
            mark = "*" if t.get("source") == "user" else " "
            print(f" tool {mark} {t.get('tool')}: current {t.get('current')} "
                  f"({t.get('source')}) | latest {latest}")
    else:
        if data.get("status") == "pinned":
            print(f"status : pinned -> {data.get('path')}")
            for k, v in (data.get("pins") or {}).items():
                print(f"  {k}={v}")
            print(f"note   : {data.get('note')}")
            return
        print(f"status: {data.get('status')}")
        if data.get("to_version"):
            print(f"version: {data.get('from_version')} -> {data.get('to_version')}")
        if data.get("preserved_old_exe"):
            print(f"old exe kept at: {data['preserved_old_exe']} (rollback copy)")
        if data.get("rebuild_exit") is not None:
            print(f"rebuild exit: {data['rebuild_exit']}")
