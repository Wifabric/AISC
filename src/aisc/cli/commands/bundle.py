"""``aisc bundle`` command group (0.1.0 A3, guide 3.3.3).

fetch / list / remove / path over the data-root bundle store
(``<data-root>/bundles/<ver>/``). Non-interactive by contract; all output
is JSON-serializable for the aisc.cli/v1 envelope; text mode prints a
short summary. Network failures fail CLOSED with the three manual escape
hatches in the copy (manual URL / --from-file / --aisc-root).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from aisc import __version__
from aisc.application.bundle_fetch import (
    AISC_RELEASE_REPO,
    BundleFetchError,
    BundleFetcher,
)
from aisc.application.data_root import shared_root
from aisc.domain.models import CliError


def _map_error(exc: BundleFetchError) -> CliError:
    return CliError(message=exc.message, exit_code=1, error_code="AISC_ERR_GENERAL")


def _active_root() -> Optional[Path]:
    from aisc.application.resources import locate_aisc_root

    try:
        return locate_aisc_root()
    except Exception:
        return None


def cmd_bundle_fetch(
    *,
    version: Optional[str] = None,
    from_file: Optional[str] = None,
    sha256: Optional[str] = None,
    allow_mismatch: bool = False,
) -> Dict[str, Any]:
    fetcher = BundleFetcher()
    try:
        return fetcher.fetch(
            shared_root(),
            __version__,
            version=version,
            from_file=Path(from_file) if from_file else None,
            sha256=sha256,
            allow_mismatch=allow_mismatch,
        )
    except BundleFetchError as exc:
        raise _map_error(exc) from exc


def cmd_bundle_list() -> Dict[str, Any]:
    fetcher = BundleFetcher()
    versions = fetcher.installed_versions(shared_root())
    active = _active_root()
    active_version = None
    if active is not None:
        # bundles/<ver>/aisc-bundle -> <ver>
        try:
            active_version = active.resolve().parent.name
        except OSError:
            active_version = None
    return {
        "repo": AISC_RELEASE_REPO,
        "installed": versions,
        "active_version": active_version,
        "cli_version": __version__,
    }


def cmd_bundle_remove(version: str) -> Dict[str, Any]:
    fetcher = BundleFetcher()
    try:
        return fetcher.remove(shared_root(), version, _active_root())
    except BundleFetchError as exc:
        raise _map_error(exc) from exc


def cmd_bundle_path() -> Dict[str, Any]:
    return {"bundles_root": str(BundleFetcher().bundles_root(shared_root()))}


def print_bundle_text(sub: str, data: Any) -> None:
    """Minimal human-readable output for text mode."""
    if not isinstance(data, dict):
        return
    if sub == "fetch":
        print(f"status : {data.get('status')}")
        print(f"version: {data.get('version')}")
        print(f"path   : {data.get('path')}")
    elif sub == "list":
        print(f"repo   : {data.get('repo')}")
        print(f"cli    : {data.get('cli_version')}")
        for v in data.get("installed", []):
            mark = " (active)" if v == data.get("active_version") else ""
            print(f"  {v}{mark}")
    elif sub == "remove":
        print(f"removed: {data.get('version')}")
    elif sub == "path":
        print(data.get("bundles_root", ""))
