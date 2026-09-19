"""``aisc update`` (0.1.0 A4, D-7): self-update for the frozen CLI forms.

Forms and behavior:

- **frozen (Workbench sidecar / portable install)**: download the target
  release archive (shared, verified path with ``bundle fetch``), verify the
  bundle + manifest gate, then atomically replace the executable and the
  adjacent ``aisc-bundle/``. The Windows rename dance: a RUNNING exe cannot
  be overwritten but CAN be renamed — old becomes ``<name>.old-<ts>`` and
  the new bytes land at the original path. Workbench's pooled local serve
  sessions key on exe mtime, so the next command respawns from the new
  binary automatically (serve.rs:610-647) — no Workbench restart needed.
  ``--rebuild`` chains the installer-style ``maintenance docker-rebuild``
  through the NEW executable (also a boot smoke test).
- **pip/pipx**: guidance only (``pipx upgrade aisc-cli``) — the package
  manager owns the files (D-18: remote machines are out of scope).
- **source checkout**: refused — git owns the files.

Downgrade guard: latest-final resolution never moves backwards; an
explicit ``--version`` is honored as user intent.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import aisc
from aisc.application.bundle_fetch import (
    BundleFetchError,
    BundleFetcher,
    _parse_archive_name,
    bundle_compatible,
    safe_extract_archive,
    verify_staged_bundle,
)

UPDATE_ERROR_USAGE = "aisc.update/usage"
UPDATE_ERROR_STATE = "aisc.update/state"


class UpdateError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _version_key(v: str) -> Tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", v)[:3])


def detect_install_form(
    *,
    frozen: Optional[bool] = None,
    executable: Optional[str] = None,
    package_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Pure-ish form detection (injectable for tests)."""
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if not is_frozen:
        pkg = Path(package_file or aisc.__file__).resolve()
        s = str(pkg)
        if "site-packages" in s:
            return {"form": "pip", "package": str(pkg)}
        return {"form": "source", "package": str(pkg)}
    exe = Path(executable or sys.executable).resolve()
    adjacent = exe.parent / "aisc-bundle"
    return {
        "form": "frozen",
        "exe": str(exe),
        "adjacent_bundle": str(adjacent) if adjacent.is_dir() else None,
    }


def sweep_old_files(exe_dir: Path) -> list:
    """Remove pre-existing ``.old-<ts>`` leftovers from earlier updates.

    Called BEFORE the replace dance: by then nothing references the old
    .old files (they were the previous-previous binary)."""
    removed = []
    if not exe_dir.is_dir():
        return removed
    for p in exe_dir.iterdir():
        if p.is_file() and ".old-" in p.name:
            try:
                p.unlink()
                removed.append(p.name)
            except OSError:
                pass
    for p in exe_dir.glob("aisc-bundle.old-*"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            removed.append(p.name)
    return removed


def _replace_exe(exe: Path, new_bytes: bytes) -> Optional[Path]:
    """Atomically swap the executable. Windows: rename dance (a running exe
    can be renamed, not overwritten). POSIX: plain os.replace (inode swap,
    running processes keep the old image). Returns the preserved old path
    on Windows, None elsewhere."""
    if os.name == "nt":
        old = exe.with_name(f"{exe.stem}.old-{int(time.time())}{exe.suffix}")
        os.rename(exe, old)
        exe.write_bytes(new_bytes)
        return old
    tmp = exe.with_name(f"{exe.name}.new-{int(time.time())}")
    tmp.write_bytes(new_bytes)
    os.replace(tmp, exe)
    return None


def _swap_adjacent_bundle(adjacent: Path, new_bundle: Path) -> Optional[Path]:
    old = adjacent.with_name(f"{adjacent.name}.old-{int(time.time())}")
    os.rename(adjacent, old)
    shutil.move(str(new_bundle), str(adjacent))
    return old


def build_check_report(
    *,
    cli_version: str,
    form: Dict[str, Any],
    fetcher: BundleFetcher,
    requested_version: Optional[str] = None,
) -> Dict[str, Any]:
    """--check / dry-run plan. Never touches disk. Network is only touched
    for the frozen form (pip/source answers are local facts)."""
    report: Dict[str, Any] = {
        "form": form["form"],
        "cli_version": cli_version,
        "latest_final": None,
        "requested_version": requested_version,
    }
    if form["form"] == "pip":
        report["update_available"] = None
        report["action"] = "pipx upgrade aisc-cli (package manager owns the files)"
        return report
    if form["form"] == "source":
        report["update_available"] = None
        report["action"] = "refused: git checkout — update via git pull"
        return report

    latest = fetcher.latest_final_version()
    report["latest_final"] = latest
    target = requested_version or latest
    if target is None:
        report["update_available"] = False
        report["action"] = "no final release published yet; nothing to update to"
    else:
        newer = _version_key(target) > _version_key(cli_version)
        report["target_version"] = target
        report["update_available"] = newer or bool(requested_version)
        report["action"] = (
            f"download AISC-{target} release archive, verify, replace exe"
            + (f" + adjacent bundle at {form['adjacent_bundle']}"
               if form.get("adjacent_bundle") else " (bundle store via aisc bundle fetch)")
        )
    return report


def perform_update(
    *,
    cli_version: str,
    form: Dict[str, Any],
    fetcher: BundleFetcher,
    version: Optional[str] = None,
    from_file: Optional[Path] = None,
    sha256: Optional[str] = None,
    rebuild: bool = False,
    workdir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute the update for the FROZEN form. Returns the report dict.

    ``workdir`` overrides the exe directory (tests). Raises UpdateError /
    BundleFetchError fail-closed; nothing is replaced unless every check
    passed.

    D-8 (2026-09-19): releases no longer ship CLI archives — the NSIS
    installer IS the CLI+UI update channel for frozen installs, and pip is
    the other. The download path therefore only works with an explicit
    ``--from-file`` archive (manual/offline updates)."""
    import hashlib

    if form["form"] == "pip":
        raise UpdateError(
            UPDATE_ERROR_USAGE,
            "pip/pipx install: the package manager owns the files — run "
            "`pipx upgrade aisc-cli` (or pip install -U aisc-cli in a venv)")
    if form["form"] == "source":
        raise UpdateError(
            UPDATE_ERROR_USAGE,
            "source checkout: git owns the files — update via git pull, "
            "then rebuild the sidecar if needed")

    target = version or fetcher.latest_final_version()
    if target is None:
        raise UpdateError(
            UPDATE_ERROR_STATE,
            "no final release published yet — nothing to update to "
            "(explicit --version <ver> to force)")
    if not from_file and not version and _version_key(target) <= _version_key(cli_version):
        return {"status": "up-to-date", "cli_version": cli_version, "latest_final": target}
    # D-8 (2026-09-19): releases no longer ship CLI archives. The online
    # sidecar-swap is retired — NSIS installs update the CLI with the
    # Workbench, pip installs via pip. Manual/offline updates keep working
    # through --from-file.
    if not from_file:
        raise UpdateError(
            UPDATE_ERROR_USAGE,
            "aisc update no longer downloads CLI archives (releases ship "
            "the Workbench installer only). Update paths: pip install -U "
            "aisc-cli · Workbench 检查更新（自带最新 CLI）· or --from-file "
            "<archive> --sha256 <hex> for a manual archive")

    exe = Path(form["exe"]) if not workdir else workdir / Path(form["exe"]).name
    exe_dir = exe.parent

    with tempfile.TemporaryDirectory(prefix="aisc-update-") as td:
        tdp = Path(td)
        if from_file is not None:
            archive = Path(from_file).resolve()
            if not archive.is_file():
                raise UpdateError(UPDATE_ERROR_USAGE, f"--from-file not found: {archive}")
            expected = (sha256 or "").strip().lower()
            if not expected:
                raise UpdateError(
                    UPDATE_ERROR_USAGE,
                    "--from-file requires --sha256 (same strength as the online path)")
            actual = hashlib.sha256(archive.read_bytes()).hexdigest()
            if actual != expected:
                raise UpdateError(
                    UPDATE_ERROR_USAGE,
                    f"--from-file digest mismatch: expected {expected[:16]}..., "
                    f"got {actual[:16]}...")
        else:
            archive = fetcher.download_archive(target, tdp / "dl")

        parsed = _parse_archive_name(archive.name)
        archive_version = parsed[0] if parsed else None
        if archive_version and archive_version != target and not version:
            raise UpdateError(
                UPDATE_ERROR_STATE,
                f"archive is version {archive_version}, latest-final said {target}")

        extracted = tdp / "x"
        errs = safe_extract_archive(archive, extracted)
        if errs:
            raise UpdateError(UPDATE_ERROR_STATE, f"archive failed validation: {errs[0]}")
        tops = [c for c in extracted.iterdir() if c.is_dir()]
        if len(tops) != 1:
            raise UpdateError(UPDATE_ERROR_STATE, "archive must have exactly one top-level dir")
        top = tops[0]
        exe_name = "aisc.exe" if os.name == "nt" else "aisc"
        new_exe = top / exe_name
        new_bundle = top / "aisc-bundle"
        if not new_exe.is_file() or not new_bundle.is_dir():
            raise UpdateError(UPDATE_ERROR_STATE, "archive lacks aisc executable or aisc-bundle/")

        errs = verify_staged_bundle(new_bundle)
        if errs:
            raise UpdateError(UPDATE_ERROR_STATE, f"bundle verification failed: {errs[0]}")
        ok, reason = bundle_compatible(new_bundle, archive_version or target)
        if not ok:
            raise UpdateError(UPDATE_ERROR_STATE, f"manifest gate: {reason}")

        sweep_old_files(exe_dir)
        old_exe = _replace_exe(exe, new_exe.read_bytes())
        old_bundle = None
        adjacent = Path(form["adjacent_bundle"]) if form.get("adjacent_bundle") else None
        if adjacent is not None and not workdir:
            old_bundle = _swap_adjacent_bundle(adjacent, new_bundle)

        report = {
            "status": "updated",
            "from_version": cli_version,
            "to_version": archive_version or target,
            "exe": str(exe),
        }
        if old_exe is not None:
            report["preserved_old_exe"] = str(old_exe)
        if old_bundle is not None:
            report["preserved_old_bundle"] = str(old_bundle)

        if rebuild:
            rebuild_root = str(adjacent) if adjacent is not None and not workdir else str(new_bundle)
            cmd = [str(exe), "maintenance", "docker-rebuild", "--root", rebuild_root,
                   "--format", "json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2700)
            report["rebuild_exit"] = proc.returncode
            if proc.returncode != 0:
                report["status"] = "updated-rebuild-failed"
                report["rebuild_tail"] = (proc.stdout or proc.stderr)[-2000:]
        return report
