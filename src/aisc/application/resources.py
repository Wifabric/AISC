"""Resource location — find the AISC root directory.

Priority:
  1. Explicit ``--aisc-root`` / *explicit_root* parameter
  2. Environment variable ``AISC_ROOT``
  3. Frozen executable: adjacent ``aisc-bundle/`` directory
     (bundle missing → continue to repo discovery; bundle corrupt → raise)
  4. Walk up from *cwd* discovering a repo (``.git`` + structure markers)
  5. Data-root bundles: ``<data-root>/bundles/<ver>/aisc-bundle`` installed
     by ``aisc bundle fetch`` (0.1.0 A3). Inserted AFTER cwd-repo so a
     developer running in the repo keeps hitting the working tree, and
     BEFORE package ancestors so pip installs resolve fetched bundles.
     Incompatible manifests are skipped, not errors (guide 3.3.1).
  6. Installed package ancestor fallback: walk ancestors of the aisc package
     source (``Path(__file__).resolve()``) looking for structure markers.
     Supports editable installs; ordinary site-packages wheels return ``None``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable, Optional, List, Tuple


# ---------------------------------------------------------------------------
# Structure markers
# ---------------------------------------------------------------------------

# A2 (guide 3.2): the VERSION marker is dual-shape — repo checkouts carry
# src/aisc/VERSION (package-data since the migration), while staged bundles
# and frozen builds keep VERSION at their root (the bundle layout is an
# installed-artifact contract that must not move). The other two markers
# are single-shape.
_VERSION_MARKERS: List[str] = ["VERSION", "src/aisc/VERSION"]
_STRUCTURE_MARKERS: List[str] = ["container/Dockerfile", "config/versions.env"]


def _is_root(path: Path) -> bool:
    if not any((path / m).is_file() for m in _VERSION_MARKERS):
        return False
    return all((path / m).is_file() for m in _STRUCTURE_MARKERS)


def _has_git(path: Path) -> bool:
    return (path / ".git").exists()


def _find_repo_root(start: Path) -> Optional[Path]:
    current = start.resolve()
    while True:
        if _has_git(current) and _is_root(current):
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


# ---------------------------------------------------------------------------
# Data-root bundle layer (0.1.0 A3, guide 3.3.1)
# ---------------------------------------------------------------------------

def _bundle_manifest_compatible(bundle_root: Path) -> bool:
    """Runtime manifest gate at RESOLUTION time: an incompatible bundle is
    skipped (not an error) — the chain continues. Imported lazily so this
    module stays importable without the fetch machinery (resources.py is a
    zero-dependency leaf by design)."""
    from aisc import __version__
    from aisc.application.bundle_fetch import bundle_compatible

    ok, _reason = bundle_compatible(bundle_root, __version__)
    return ok


def find_data_root_bundles(data_root: Path) -> Tuple[List[Path], List[str]]:
    """Compatible bundle roots under ``<data_root>/bundles/<ver>/aisc-bundle``.

    Returns (compatible_roots, skipped_notes) — incompatible/corrupt entries
    are skipped with a note for the failure-path error copy (guide 3.3.1:
    全链失败时错误信息列出「发现 bundle X 但要求 CLI 版本 Y」).
    """
    bundles = data_root / "bundles"
    if not bundles.is_dir():
        return [], []
    roots: List[Path] = []
    skipped: List[str] = []
    for child in sorted(bundles.iterdir(), reverse=True):
        bundle = child / "aisc-bundle"
        if not bundle.is_dir():
            continue
        if not _is_root(bundle):
            skipped.append(f"{bundle}: missing structure markers")
            continue
        if not _bundle_manifest_compatible(bundle):
            skipped.append(f"{bundle}: manifest does not allow this CLI version")
            continue
        roots.append(bundle)
    return roots, skipped


def _find_installed_root(package_start: Optional[Path] = None) -> Optional[Path]:
    """Walk ancestors of *package_start* looking for a valid AISC root.

    Used as the final fallback when no explicit/env/frozen/repo root is found.
    Supports editable installs where ``Path(__file__).resolve()`` points into
    the actual repo tree.  For ordinary wheel installs the walk will reach the
    filesystem root without matching structure markers and return ``None``.
    """
    start = (package_start or Path(__file__).resolve()).parent
    current = start
    while True:
        if _is_root(current):
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


# ---------------------------------------------------------------------------
# Lightweight error-info helper
# ---------------------------------------------------------------------------

class _RootSourceError(Exception):
    """Indicates a root source is invalid.  Carries the source label."""

    def __init__(self, message: str, source: str) -> None:
        super().__init__(message)
        self.source = source  # "--aisc-root", "AISC_ROOT", "frozen-bundle"
        self.message = message  # duplicate for clarity


# ---------------------------------------------------------------------------
# Frozen helper (reads nothing — fully parametric)
# ---------------------------------------------------------------------------

def _resolve_frozen_bundle(exe_path: str) -> Optional[Path]:
    """Look for an adjacent ``aisc-bundle/`` relative to *exe_path*.

    Returns the bundle path if valid, ``None`` when absent,
    raises ``_RootSourceError`` when the bundle exists but is corrupt.
    """
    exe_dir = Path(exe_path).resolve().parent
    bundle = exe_dir / "aisc-bundle"
    if not bundle.is_dir():
        return None
    if not _is_root(bundle):
        raise _RootSourceError(
            f"Frozen bundle at {bundle} is corrupt: missing structure markers",
            source="frozen-bundle",
        )
    return bundle


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def locate_aisc_root(
    explicit_root: Optional[str] = None,
    cwd: Optional[Path] = None,
    is_frozen: Optional[Callable[[], bool]] = None,
    executable_path: Optional[str] = None,
    package_start: Optional[Path] = None,
    data_root: Optional[Path] = None,
) -> Optional[Path]:
    """Find the AISC root directory.

    Parameters
    ----------
    explicit_root:
        Explicit path supplied via ``--aisc-root``.
    cwd:
        Starting directory for repo discovery.  Defaults to ``os.getcwd()``.
    is_frozen:
        Callable that returns ``True`` when we are a frozen executable.
        Default: ``getattr(sys, 'frozen', False)`` (lazy, at call time).
    executable_path:
        Path to the executable when frozen.  Default: ``sys.executable``.
    package_start:
        Path to use as starting point for installed-package ancestor walk.
        Default: ``Path(__file__).resolve()`` in this module.
        Injection point for deterministic tests.
    data_root:
        Data root for the fetched-bundles layer (step 5). Default: lazily
        ``aisc.application.data_root.shared_root()`` (local import — this
        module stays a zero-dependency leaf; build.py:67 pattern).

    Returns
    -------
    Path
        The AISC root, or ``None`` if no root could be located.

    Raises
    ------
    _RootSourceError
        When an explicit/bundle/env source is provided but invalid.
        The ``source`` attribute distinguishes the origin.
    """
    # -- 1. Explicit --
    if explicit_root is not None:
        p = Path(explicit_root).resolve()
        if not p.is_dir():
            raise _RootSourceError(
                f"--aisc-root {explicit_root}: not a directory",
                source="--aisc-root",
            )
        if not _is_root(p):
            raise _RootSourceError(
                f"--aisc-root {explicit_root}: missing required structure markers",
                source="--aisc-root",
            )
        return p

    # -- 2. Environment variable --
    env_root = os.environ.get("AISC_ROOT")
    if env_root is not None:
        p = Path(env_root).resolve()
        if not p.is_dir():
            raise _RootSourceError(
                f"AISC_ROOT={env_root}: not a directory",
                source="AISC_ROOT",
            )
        if not _is_root(p):
            raise _RootSourceError(
                f"AISC_ROOT={env_root}: missing required structure markers",
                source="AISC_ROOT",
            )
        return p

    # -- 3. Frozen bundle --
    # Production defaults: lazy-read sys at call time (not at import)
    frozen_check = is_frozen if is_frozen is not None else (
        lambda: getattr(sys, "frozen", False)
    )
    if frozen_check():
        exe = executable_path if executable_path is not None else sys.executable
        if exe:
            bundle = _resolve_frozen_bundle(exe)
            if bundle is not None:
                return bundle
        # Bundle not found → fall through to repo discovery

    # -- 4. Repo discovery --
    start = cwd if cwd is not None else Path.cwd()
    repo = _find_repo_root(start)
    if repo is not None:
        return repo

    # -- 5. Data-root bundles (aisc bundle fetch) --
    if data_root is None:
        from aisc.application.data_root import shared_root

        try:
            data_root = shared_root()
        except Exception:
            data_root = None
    if data_root is not None:
        candidates, _skipped = find_data_root_bundles(data_root)
        if candidates:
            return candidates[0]

    # -- 6. Installed package ancestor fallback --
    # Walks up from the aisc package source. Supports editable installs.
    # Ordinary site-packages wheels will reach filesystem root and return None.
    return _find_installed_root(package_start)
