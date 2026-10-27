"""Read-only facts about the running CLI and its selected resources."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

from aisc import __version__
from aisc.application.bundle_fetch import bundle_compatible
from aisc.application.version import _read_version_file
from aisc.domain.models import CheckResult, CheckStatus


# PEP 440 syntax only: no ordering or normalization is needed for the exact
# manifest allowlist. Keep dev/pre/post/local versions valid without adding a
# runtime dependency on packaging (which is only present in build tooling).
_VERSION_PATTERN = re.compile(r"""
    v? (?:[0-9]+!)? [0-9]+(?:\.[0-9]+)*
    (?:[-_.]?(?:alpha|a|beta|b|preview|pre|c|rc)[-_.]?[0-9]*)?
    (?:-[0-9]+|[-_.]?(?:post|rev|r)[-_.]?[0-9]*)?
    (?:[-_.]?dev[-_.]?[0-9]*)?
    (?:\+[a-z0-9]+(?:[-_.][a-z0-9]+)*)?
""", re.VERBOSE | re.IGNORECASE | re.ASCII)


def _known_version(value: Optional[str]) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    if value.casefold().removeprefix("v") in {"unknown", "0+unknown"}:
        return False
    return _VERSION_PATTERN.fullmatch(value) is not None


def pairing_health(
    root: Optional[Path], *, cli_version: str = __version__, executable: Optional[str] = None,
) -> dict:
    """Use the already resolved root; never discover a different bundle here.

    Workbench and remote CLI versions are independent. This process can only
    attest to its own executable and resources; it does not guess a GUI version.
    """
    root = root.resolve() if root is not None else None
    report = {
        "cliPath": executable if executable is not None else sys.executable,
        "cliEntrypoint": str(Path(sys.argv[0]).resolve()) if sys.argv else None,
        "cliVersion": cli_version or None,
        "bundlePath": str(root) if root is not None else None,
        "bundleVersion": None,
        "manifestSchema": None,
        "compatibleCliVersions": None,
        "status": "unknown",
        "reason": "bundle-not-resolved",
    }
    if root is None:
        return report
    try:
        report["bundleVersion"] = _read_version_file(root)
    except (OSError, UnicodeError):
        pass
    if not _known_version(cli_version) or not _known_version(report["bundleVersion"]):
        report["reason"] = "version-unknown"
        return report
    manifest = root / "manifest.json"
    if not manifest.exists() and (root / ".git").exists():
        report["reason"] = "source-checkout-without-release-manifest"
        return report
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        data = None
    if isinstance(data, dict):
        schema = data.get("schema_version")
        report["manifestSchema"] = schema if type(schema) is int else None
        versions = data.get("compatible_cli_versions")
        if isinstance(versions, list) and all(isinstance(v, str) for v in versions):
            report["compatibleCliVersions"] = versions
    compatible, reason = bundle_compatible(root, cli_version)
    report.update(status="compatible" if compatible else "incompatible", reason=reason or "manifest-allows-running-cli")
    return report


def pairing_check(root: Optional[Path]) -> CheckResult:
    report = pairing_health(root)
    state = report["status"]
    return CheckResult(
        name="cli-bundle-pairing",
        status=CheckStatus.PASS if state == "compatible" else CheckStatus.WARN,
        message=f"CLI/bundle pairing: {state} ({report['reason']})",
        detail=json.dumps(report, ensure_ascii=False, sort_keys=True),
        hint=None if state == "compatible" else "Verify the selected CLI and its bundle; fetch a compatible bundle or reinstall the matching Workbench package.",
    )
