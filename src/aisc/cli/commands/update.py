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


def _to_cli_error(exc: Exception) -> CliError:
    if isinstance(exc, (UpdateError, BundleFetchError)):
        return CliError(message=exc.message, exit_code=1, error_code="AISC_ERR_GENERAL")
    raise exc


def cmd_update_check(version: Optional[str] = None) -> Dict[str, Any]:
    form = detect_install_form()
    try:
        fetcher = BundleFetcher()
        return build_check_report(
            cli_version=aisc.__version__,
            form=form,
            fetcher=fetcher,
            requested_version=version,
        )
    except (UpdateError, BundleFetchError) as exc:
        raise _to_cli_error(exc) from exc


def cmd_update(
    *,
    version: Optional[str] = None,
    from_file: Optional[str] = None,
    sha256: Optional[str] = None,
    rebuild: bool = False,
) -> Dict[str, Any]:
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
    else:
        print(f"status: {data.get('status')}")
        if data.get("to_version"):
            print(f"version: {data.get('from_version')} -> {data.get('to_version')}")
        if data.get("preserved_old_exe"):
            print(f"old exe kept at: {data['preserved_old_exe']} (rollback copy)")
        if data.get("rebuild_exit") is not None:
            print(f"rebuild exit: {data['rebuild_exit']}")
