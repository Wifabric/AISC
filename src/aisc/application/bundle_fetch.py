"""Bundle fetch/install machinery (0.1.0 A3, guide 3.3).

Two halves:

1. MIGRATED from ``packaging/artifact.py`` (guide 3.3.3: sdist/wheel do not
   contain ``packaging/`` — pip environments must import these): archive
   member validation + safe extraction, manifest write, and staged-bundle
   verification. ``packaging/artifact.py`` re-exports the original symbols
   so ``tests/packaging/test_artifact.py`` and the packaging CLI are
   untouched consumers of the SAME implementation.

2. NEW: the runtime fetch path — resolve a same-version ``AISC-<ver>-<plat>-
   <arch>`` asset from GitHub Releases, verify the API digest, safe-extract,
   verify the ``aisc-bundle/`` subtree, and atomically install it under
   ``<data-root>/bundles/<ver>/``. Trust model (guide 3.3.3, ADR-002 bound):
   transport integrity + GitHub account trust; the same-source ``.sha256``
   sidecar alone proves nothing about tampering, so the API-reported digest
   is the required root and offline ``--from-file`` must pin its own hash.
   Fail-closed everywhere; three manual escape hatches in every network
   error copy (manual URL / --from-file / --aisc-root).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Platform tags (migrated; the runtime needs the same names as the packager)
# ---------------------------------------------------------------------------

_PLAT_TAG = {"linux": "linux", "darwin": "macos", "win32": "windows"}.get(sys.platform, sys.platform)


def _detect_arch() -> str:
    machine = os.uname().machine if hasattr(os, "uname") else os.environ.get("PROCESSOR_ARCHITECTURE", "x86_64")
    if machine in ("x86_64", "AMD64", "amd64"):
        return "x86_64"
    if machine in ("aarch64", "arm64", "ARM64"):
        return "arm64"
    return machine


ARCH_TAG = _detect_arch()

#: AISC's own release repo (CLI updates + bundle archives live here).
AISC_RELEASE_REPO = "wangyuncepu/AISC"

DEFAULT_API_BASE = "https://api.github.com"
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_MAX_PAGES = 10

BUNDLE_FETCH_ERROR_NETWORK = "aisc.bundle-fetch/network"
BUNDLE_FETCH_ERROR_NOT_FOUND = "aisc.bundle-fetch/not-found"
BUNDLE_FETCH_ERROR_INTEGRITY = "aisc.bundle-fetch/integrity"
BUNDLE_FETCH_ERROR_INVALID = "aisc.bundle-fetch/invalid"
BUNDLE_FETCH_ERROR_CONFLICT = "aisc.bundle-fetch/conflict"


class BundleFetchError(Exception):
    """Fail-closed fetch failure. ``code`` maps to a stable CLI error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Archive member validation + safe extraction (migrated verbatim in behavior)
# ---------------------------------------------------------------------------

def _norm_path(p: str) -> str:
    return re.sub(r'/+', '/', p.replace("\\", "/")).strip("/")


def _validate_archive_path(name: str) -> Optional[str]:
    """Validate archive member path. Returns error or None."""
    raw = name
    if "\x00" in raw:
        return "NUL byte in path"
    r = raw.lstrip()
    if r.startswith("//") or r.startswith("\\\\"):
        return f"UNC path: {raw!r}"
    if r.startswith("/"):
        return f"POSIX absolute path: {raw!r}"
    if re.match(r'^[a-zA-Z]:[/\\\\]', r):
        return f"Windows drive path: {raw!r}"
    n = _norm_path(raw)
    if not n or n == ".":
        return f"empty or '.' path: {raw!r}"
    parts = n.split("/")
    if ".." in parts:
        return f"path escape (..): {raw!r}"
    if "." in parts:
        return f"path with '.' segment: {raw!r}"
    return None


def _normalised_key(name: str) -> str:
    """Casefolded normalised path for duplicate detection."""
    return _norm_path(name).casefold()


def validate_tar_members(tar: tarfile.TarFile) -> List[str]:
    """Validate all tar members. Only REGTYPE/DIRTYPE allowed.

    Rejects symlink, hardlink, FIFO, char/block device; checks for
    normalised+casefold duplicate targets.
    """
    errors: List[str] = []
    seen: Set[str] = set()
    for m in tar.getmembers():
        e = _validate_archive_path(m.name)
        if e:
            errors.append(e)
            continue
        if m.type not in (tarfile.REGTYPE, tarfile.DIRTYPE):
            tname = {tarfile.SYMTYPE: "symlink", tarfile.LNKTYPE: "hardlink",
                     tarfile.FIFOTYPE: "fifo", tarfile.CHRTYPE: "chardev",
                     tarfile.BLKTYPE: "blockdev"}.get(m.type, f"type({m.type})")
            errors.append(f"forbidden tar member type {tname}: {m.name}")
            if m.linkname:
                le = _validate_archive_path(m.linkname)
                if le:
                    errors.append(f"unsafe tar link target: {m.linkname} ({le})")
            continue
        nk = _normalised_key(m.name)
        if nk in seen:
            errors.append(f"duplicate path in tar: {m.name}")
        seen.add(nk)
    return errors


def validate_zip_members(zf: zipfile.ZipFile) -> List[str]:
    """Validate zip members. Rejects unsafe paths, special file types,
    Unix symlinks, casefold duplicates."""
    errors: List[str] = []
    seen: Set[str] = set()
    for zi in zf.infolist():
        e = _validate_archive_path(zi.filename)
        if e:
            errors.append(e)
            continue
        full_mode = (zi.external_attr >> 16) & 0xFFFF
        if zi.create_system == 3 and full_mode != 0:
            if stat.S_ISLNK(full_mode):
                errors.append(f"zip contains Unix symlink: {zi.filename}")
            elif not (stat.S_ISREG(full_mode) or stat.S_ISDIR(full_mode)):
                ftype = "unknown"
                if stat.S_ISFIFO(full_mode):
                    ftype = "fifo"
                elif stat.S_ISCHR(full_mode):
                    ftype = "chardev"
                elif stat.S_ISBLK(full_mode):
                    ftype = "blockdev"
                elif stat.S_ISSOCK(full_mode):
                    ftype = "socket"
                errors.append(f"zip contains forbidden file type {ftype}: {zi.filename}")
            if zi.is_dir() and not stat.S_ISDIR(full_mode):
                errors.append(f"zip directory flag vs mode mismatch: {zi.filename}")
            if stat.S_ISDIR(full_mode) and not zi.is_dir():
                errors.append(f"zip mode says dir but not flagged as dir: {zi.filename}")
        elif zi.create_system != 3 and full_mode != 0:
            if stat.S_ISLNK(full_mode):
                errors.append(f"zip contains symlink (non-Unix): {zi.filename}")
        nk = _normalised_key(zi.filename)
        if nk in seen:
            errors.append(f"duplicate path in zip: {zi.filename}")
        seen.add(nk)
    return errors


def _check_containment(dest_dir: Path, target: Path) -> Optional[str]:
    """Check target resolves inside dest_dir. Returns error or None."""
    try:
        target.resolve().relative_to(dest_dir.resolve())
    except ValueError:
        return f"extraction escapes dest: {target}"
    return None


def safe_extract_tar(tar: tarfile.TarFile, dest_dir: Path) -> List[str]:
    errors = validate_tar_members(tar)
    if errors:
        return errors
    for m in tar.getmembers():
        if m.type == tarfile.DIRTYPE:
            continue  # dirs created implicitly
        target = dest_dir / m.name
        ce = _check_containment(dest_dir, target)
        if ce:
            errors.append(ce)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tar.extractfile(m) as src:
            if src is None:
                errors.append(f"cannot read tar member: {m.name}")
                continue
            target.write_bytes(src.read())
        target.chmod(m.mode & 0o777)
    return errors


def safe_extract_zip(zf: zipfile.ZipFile, dest_dir: Path) -> List[str]:
    errors = validate_zip_members(zf)
    if errors:
        return errors
    for zi in zf.infolist():
        if zi.is_dir():
            continue  # dirs created implicitly
        target = dest_dir / zi.filename
        ce = _check_containment(dest_dir, target)
        if ce:
            errors.append(ce)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(zf.read(zi.filename))
        mode = (zi.external_attr >> 16) & 0o777
        target.chmod(mode if mode else 0o644)
    return errors


def safe_extract_archive(archive_path: Path, dest_dir: Path) -> List[str]:
    """Safely extract archive to dest_dir (created; must be empty if exists).

    Validates all members before writing anything. Returns error list.
    """
    if dest_dir.exists():
        if not dest_dir.is_dir():
            return [f"extraction dest is not a directory: {dest_dir}"]
        if any(dest_dir.iterdir()):
            return [f"extraction dest is not empty: {dest_dir}"]
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = archive_path.name.lower().rsplit(".", 1)[-1] if "." in archive_path.name else ""
    try:
        if archive_path.name.lower().endswith(".tar.gz") or archive_path.name.lower().endswith(".tgz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                return safe_extract_tar(tar, dest_dir)
        if suffix == "zip":
            with zipfile.ZipFile(archive_path) as zf:
                return safe_extract_zip(zf, dest_dir)
        if suffix == "tar":
            with tarfile.open(archive_path, "r:") as tar:
                return safe_extract_tar(tar, dest_dir)
    except (tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
        return [f"archive open/read failed: {exc}"]
    return [f"unsupported archive type: {archive_path.name}"]


def _parse_archive_name(name: str) -> Optional[Tuple[str, str, str]]:
    """``AISC-<version>-<platform>-<arch>`` -> (version, platform, arch)."""
    m = re.match(r"^AISC-(.+?)-([a-z0-9]+)-([a-z0-9_]+)\.(?:tar\.gz|zip|tgz)$", name)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


# ---------------------------------------------------------------------------
# Manifest + staged-bundle verification (migrated; verify side stays whole)
# ---------------------------------------------------------------------------

BUNDLE_REQUIRED = ["VERSION", "README.md", "LICENSE", ".dockerignore", "config/versions.env"]
BUNDLE_FORBIDDEN_TOP = ["tools", "scripts", "packaging", "tests", "docs", ".git", "aisc-bundle"]

# _glob_module indirection kept so tests can shim glob behaviour (migrated
# alongside _verify_dockerfile_sources which is its only consumer).
import glob as _glob_module  # noqa: E402  (deliberate: mirrors packaging layout)


def bundle_version(bundle_root: Path) -> Optional[str]:
    """First non-empty line of the bundle's VERSION (dual-shape root read:
    staged bundles/frozen roots carry it at the root; repo checkouts at
    src/aisc/VERSION)."""
    for rel in ("VERSION", "src/aisc/VERSION"):
        vf = bundle_root / rel
        if vf.is_file():
            text = vf.read_text(encoding="utf-8").strip()
            if text:
                return text
    return None


def _write_manifest(path: Path, data: dict) -> None:
    sv, vs = data.get("schema_version", 1), sorted(data.get("compatible_cli_versions", []))
    path.write_text('{\n  "schema_version": ' + json.dumps(sv) + ',\n  "compatible_cli_versions": ' + json.dumps(vs) + '\n}\n',
                    encoding="utf-8", newline="")


def verify_staged_bundle(bundle_root: Path) -> List[str]:
    errors: List[str] = []
    mp = bundle_root / "manifest.json"
    if not mp.is_file():
        return ["manifest.json missing from staged bundle"]
    try:
        mt = mp.read_text(encoding="utf-8")
        if "\r" in mt:
            errors.append("manifest.json contains CR (must be LF)")
        if not mt.endswith("\n"):
            errors.append("manifest.json does not end with newline")
        m = json.loads(mt)
    except json.JSONDecodeError as e:
        return [f"manifest.json is not valid JSON: {e}"]
    if m.get("schema_version") != 1:
        errors.append(f"manifest.json schema_version={m.get('schema_version')}, expected 1")
    compat = m.get("compatible_cli_versions")
    if not isinstance(compat, list):
        errors.append("manifest.json compatible_cli_versions is not a list")
    elif len(compat) == 0:
        errors.append("manifest.json compatible_cli_versions is empty")
    else:
        pv = bundle_version(bundle_root)
        seen: Set[str] = set()
        for v in compat:
            if not isinstance(v, str):
                errors.append(f"manifest.json version not string: {v}")
            elif v in seen:
                errors.append(f"manifest.json duplicate version: {v}")
            seen.add(v)
        if pv not in compat:
            errors.append(f"manifest.json allowlist missing current version {pv}")
    for k in ("timestamp", "platform", "arch", "checksums"):
        if k in m:
            errors.append(f"manifest.json contains forbidden field: {k}")
    for k in m:
        if k not in ("schema_version", "compatible_cli_versions"):
            errors.append(f"manifest.json contains unknown field: {k}")
    for fn in BUNDLE_REQUIRED:
        if not (bundle_root / fn).is_file():
            errors.append(f"Required file missing: {fn}")
    if not (bundle_root / "config" / "versions.env").is_file():
        errors.append("config/versions.env missing")
    df = bundle_root / "container" / "Dockerfile"
    if df.is_file():
        errors.extend(_verify_dockerfile_sources(df, bundle_root))
    else:
        errors.append("container/Dockerfile missing")
    errors.extend(_verify_vendor_checksums(bundle_root))
    errors.extend(_audit_forbidden(bundle_root))
    if not (bundle_root / "container" / "_bundle" / "plugins").exists():
        errors.append("container/_bundle/plugins missing")
    if not (bundle_root / "container" / "downloads").exists():
        errors.append("container/downloads missing")
    return errors


def _audit_forbidden(bundle_root: Path) -> List[str]:
    es = []
    for dp, dns, fns in os.walk(str(bundle_root)):
        rp = Path(dp).relative_to(bundle_root)
        rs = str(rp).replace("\\", "/")
        for dn in dns:
            if dn == "__pycache__" or dn.startswith(".pytest_cache"):
                es.append(f"Forbidden dir: {rs}/{dn}")
        for fn in fns:
            fr = (rs + "/" + fn) if rs != "." else fn
            if fn.endswith(".pyc"):
                es.append(f"Forbidden .pyc: {fr}")
            if fn in (".env", "api-keys", ".git-credentials") and len(fr.split("/")) > 1:
                es.append(f"Forbidden file: {fr}")
    for fb in BUNDLE_FORBIDDEN_TOP:
        if (bundle_root / fb).exists():
            es.append(f"Forbidden top-level: {fb}")
    return es


def _verify_dockerfile_sources(df: Path, br: Path) -> List[str]:
    es = []
    for no, line in enumerate(df.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if not s.upper().startswith("COPY"):
            continue
        if s.startswith("COPY [") or s.startswith("COPY["):
            es.append(f"Dockerfile line {no}: JSON-form COPY not supported")
            continue
        if "--FROM" in s.upper():
            es.append(f"Dockerfile line {no}: COPY --from not supported")
            continue
        parts = s.split()
        if len(parts) < 3:
            continue
        cargs = [p for p in parts[1:] if not p.startswith("--")]
        if len(cargs) < 2:
            continue
        for src in cargs[:-1]:
            sp = src.lstrip("/")
            if "*" in sp or "?" in sp:
                if not _glob_module.glob(str(br / sp)):
                    es.append(f"Dockerfile line {no}: COPY source glob not found: {sp}")
            elif not (br / sp.rstrip("/")).exists():
                es.append(f"Dockerfile line {no}: COPY source not found: {sp}")
    return es


def _verify_vendor_checksums(bundle_root: Path) -> List[str]:
    es = []
    cf = bundle_root / "vendor" / "checksums.txt"
    if not cf.is_file():
        return ["vendor/checksums.txt missing from bundle"]
    for no, line in enumerate(cf.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r'^([0-9a-fA-F]{64})\s+(.+)$', s)
        if not m:
            es.append(f"vendor/checksums.txt line {no}: malformed: {s[:80]}")
            continue
        eh, rp = m.group(1).lower(), m.group(2).strip()
        if rp.startswith("/") or ".." in rp.replace("\\", "/").split("/"):
            es.append(f"vendor/checksums.txt line {no}: unsafe path: {rp}")
            continue
        target = (bundle_root / rp).resolve()
        try:
            target.relative_to(bundle_root.resolve())
        except ValueError:
            es.append(f"vendor/checksums.txt line {no}: path escapes bundle: {rp}")
            continue
        if not target.is_file():
            es.append(f"vendor/checksums line {no}: file not found: {rp}")
            continue
        ah = hashlib.sha256(target.read_bytes()).hexdigest()
        if ah != eh:
            es.append(f"vendor/checksums line {no}: hash mismatch for {rp}: expected {eh[:16]}..., got {ah[:16]}...")
    return es


def bundle_compatible(bundle_root: Path, cli_version: str) -> Tuple[bool, str]:
    """Runtime manifest gate (guide 3.3.2 — the check ADR-001 described but
    never shipped). Fail-closed: missing/corrupt manifest, wrong schema, or
    a version not in ``compatible_cli_versions`` are ALL incompatible.

    Note the semantic split: ``verify_staged_bundle`` enforces the PACKAGING
    invariant (bundle's own VERSION must be in the allowlist — self-
    consistency); this is the RUNTIME gate (the RUNNING cli must be in the
    allowlist). First version set: exact match only."""
    mp = bundle_root / "manifest.json"
    try:
        m = json.loads(mp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"manifest unreadable: {exc}"
    if m.get("schema_version") != 1:
        return False, f"manifest schema_version={m.get('schema_version')!r}, expected 1"
    compat = m.get("compatible_cli_versions")
    if not isinstance(compat, list) or not all(isinstance(v, str) for v in compat):
        return False, "manifest compatible_cli_versions malformed"
    if cli_version in compat:
        return True, ""
    return False, (
        f"bundle {bundle_version(bundle_root) or '?'} requires CLI "
        f"{'/'.join(compat)} (running {cli_version})"
    )


# ---------------------------------------------------------------------------
# GitHub Releases asset resolution + streaming download
# ---------------------------------------------------------------------------

#: JSON metadata transport: (url, headers, timeout) -> (status, headers, body).
#: Same shape as cc_switch_resolver.Transport so fakes are interchangeable.
Transport = Callable[[str, Dict[str, str], float], Tuple[int, Dict[str, str], Any]]

#: Streaming binary transport: (url, headers, timeout, sink) -> status.
#: ``sink(chunk: bytes)`` receives the body in bounded chunks — the 60MB
#: asset must never ride a full-body read.
DownloadTransport = Callable[[str, Dict[str, str], float, Callable[[bytes], None]], int]


def default_transport(url: str, headers: Dict[str, str], timeout: float) -> Tuple[int, Dict[str, str], Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "aisc-bundle-fetch", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        try:
            body: Any = json.loads(raw.decode("utf-8", errors="replace")) if raw else {}
        except json.JSONDecodeError:
            body = {"message": raw.decode("utf-8", errors="replace")}
        return int(exc.code), {k.lower(): v for k, v in exc.headers.items()}, body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BundleFetchError(
            BUNDLE_FETCH_ERROR_NETWORK, _network_error_copy(f"github api unreachable: {exc}")) from exc
    try:
        body = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BundleFetchError(
            BUNDLE_FETCH_ERROR_NETWORK, _network_error_copy(f"github api body unparseable: {exc}")) from exc
    return int(resp.status), {k.lower(): v for k, v in resp.headers.items()}, body


def default_download_transport(url: str, headers: Dict[str, str], timeout: float,
                               sink: Callable[[bytes], None]) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "aisc-bundle-fetch", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    return int(resp.status)
                sink(chunk)
    except urllib.error.HTTPError as exc:
        raise BundleFetchError(
            BUNDLE_FETCH_ERROR_NETWORK,
            _network_error_copy(f"asset download failed: HTTP {exc.code}")) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BundleFetchError(
            BUNDLE_FETCH_ERROR_NETWORK, _network_error_copy(f"asset download failed: {exc}")) from exc


def _network_error_copy(detail: str) -> str:
    return (
        f"{detail}. Three manual paths: (1) download the release archive "
        f"from {AISC_RELEASE_REPO} releases and run `aisc bundle fetch "
        f"--from-file <archive> --sha256 <digest>`; (2) point --aisc-root at "
        f"an extracted bundle; (3) retry with network/proxy access. "
        f"(AISC_GH_API_BASE / AISC_GH_API_TOKEN knobs apply.)"
    )


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class ReleaseAssets:
    """One release page's worth of parsed assets (name -> {digest, size, url})."""

    def __init__(self, tag: str, assets: Dict[str, Dict[str, str]]):
        self.tag = tag
        self.assets = assets


class BundleFetcher:
    """Resolve + download + verify + install release bundle archives.

    Every I/O seam is injectable (fake-transport test matrix, guide 3.3.3).
    """

    def __init__(
        self,
        *,
        transport: Transport = default_transport,
        download: DownloadTransport = default_download_transport,
        repo: str = AISC_RELEASE_REPO,
        api_base: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_S,
        max_pages: int = DEFAULT_MAX_PAGES,
    ):
        self._transport = transport
        self._download = download
        self._repo = repo
        self._api_base = (api_base or os.environ.get("AISC_GH_API_BASE") or DEFAULT_API_BASE).rstrip("/")
        self._token = token or os.environ.get("AISC_GH_API_TOKEN") or ""
        self._timeout = timeout
        self._max_pages = max_pages

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github+json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _rate_limited(self, status: int, headers: Dict[str, str], body: Any) -> bool:
        if status == 403 or status == 429:
            remaining = headers.get("x-ratelimit-remaining", "")
            if remaining == "0" or status == 429:
                return True
            msg = str(body.get("message", "") if isinstance(body, dict) else "")
            return "rate limit" in msg.lower()
        return False

    def list_release_assets(self) -> List[ReleaseAssets]:
        """All releases (newest first), each with parsed asset metadata."""
        out: List[ReleaseAssets] = []
        for page in range(1, self._max_pages + 1):
            url = f"{self._api_base}/repos/{self._repo}/releases?per_page=50&page={page}"
            status, headers, body = self._transport(url, self._headers(), self._timeout)
            if self._rate_limited(status, headers, body):
                raise BundleFetchError(
                    BUNDLE_FETCH_ERROR_NETWORK,
                    _network_error_copy("github api rate limited (set AISC_GH_API_TOKEN to raise the cap)"))
            if status != 200:
                raise BundleFetchError(
                    BUNDLE_FETCH_ERROR_NETWORK,
                    _network_error_copy(f"github api listing failed: HTTP {status}"))
            releases = body if isinstance(body, list) else []
            if not releases:
                break
            for rel in releases:
                assets: Dict[str, Dict[str, str]] = {}
                for a in rel.get("assets", []) or []:
                    name = a.get("name", "")
                    if _parse_archive_name(name) is None:
                        continue  # exe/sha256/SBOM assets are not bundle archives
                    assets[name] = {
                        "digest": str(a.get("digest") or ""),
                        "size": str(a.get("size") or ""),
                        "url": str(a.get("url") or ""),
                        "browser_download_url": str(a.get("browser_download_url") or ""),
                    }
                out.append(ReleaseAssets(str(rel.get("tag_name", "")), assets))
            if len(releases) < 50:
                break
        return out

    def resolve_asset(self, version: str, platform: str = _PLAT_TAG, arch: str = ARCH_TAG) -> Tuple[str, Dict[str, str], List[str]]:
        """Exact-version asset lookup. Returns (asset_name, meta, recent_versions)."""
        releases = self.list_release_assets()
        recent: List[str] = []
        for rel in releases:
            pv, pp, pa = _parse_archive_name(next(iter(rel.assets))) if len(rel.assets) == 1 else (None, None, None)
            for name, meta in rel.assets.items():
                parsed = _parse_archive_name(name)
                if not parsed:
                    continue
                v, p, a = parsed
                if v not in recent:
                    recent.append(v)
                if v == version and p == platform and a == arch:
                    return name, meta, recent
        raise BundleFetchError(
            BUNDLE_FETCH_ERROR_NOT_FOUND,
            f"no release asset for version {version} ({platform}/{arch}). "
            f"Recent available versions: {', '.join(recent[:5]) or '(none)'}. "
            f"Use --version <ver> to pick one explicitly.")

    # --- install lifecycle ------------------------------------------------

    def bundles_root(self, data_root: Path) -> Path:
        return data_root / "bundles"

    def installed_versions(self, data_root: Path) -> List[str]:
        root = self.bundles_root(data_root)
        if not root.is_dir():
            return []
        out = []
        for child in root.iterdir():
            if child.is_dir() and (child / "aisc-bundle" / "VERSION").is_file():
                out.append(child.name)
        return sorted(out)

    def sweep_tmp(self, data_root: Path) -> List[str]:
        """Remove half-installed ``.tmp-*`` leftovers from crashed fetches."""
        root = self.bundles_root(data_root)
        removed = []
        if not root.is_dir():
            return removed
        for child in root.iterdir():
            if child.is_dir() and child.name.startswith(".tmp-"):
                shutil.rmtree(child, ignore_errors=True)
                removed.append(child.name)
        return removed

    def download_archive(self, version: str, dest_dir: Path) -> Path:
        """Resolve + stream-download the verified archive for *version*.

        Shared by ``fetch`` (bundle store) and the A4 updater (needs the exe
        too). Raises BundleFetchError fail-closed; returns the verified
        archive path inside *dest_dir* (caller owns cleanup).
        """
        name, meta, _recent = self.resolve_asset(version)
        digest = meta.get("digest", "").lower()
        if not digest.startswith("sha256:"):
            raise BundleFetchError(
                BUNDLE_FETCH_ERROR_INTEGRITY,
                f"release asset {name} has no API digest (refusing unverified download)")
        dest_dir.mkdir(parents=True, exist_ok=True)
        archive = dest_dir / name
        expected = digest.split(":", 1)[1]
        hasher = hashlib.sha256()

        def sink(chunk: bytes) -> None:
            hasher.update(chunk)
            with open(archive, "ab") as f:
                f.write(chunk)

        archive.write_bytes(b"")  # truncate before streaming append
        url = meta.get("browser_download_url") or meta.get("url")
        self._download(url, {"Accept": "application/octet-stream"}, self._timeout, sink)
        actual = hasher.hexdigest()
        if actual != expected:
            raise BundleFetchError(
                BUNDLE_FETCH_ERROR_INTEGRITY,
                f"download digest mismatch: API said {expected[:16]}..., got {actual[:16]}... "
                f"(transport integrity check — re-run the fetch)")
        return archive

    def latest_final_version(self) -> Optional[str]:
        """Highest FINAL X.Y.Z across release tags (D-17: prereleases and
        dev tags never count — pip users must not be pointed at them)."""
        best: Optional[Tuple[Tuple[int, int, int], str]] = None
        for rel in self.list_release_assets():
            tag = rel.tag or ""
            v = tag[1:] if tag.startswith("v") else tag
            if not re.fullmatch(r"\d+\.\d+\.\d+", v):
                continue
            key = tuple(int(p) for p in v.split("."))
            if best is None or key > best[0]:
                best = (key, v)  # type: ignore[assignment]
        return best[1] if best else None

    def fetch(
        self,
        data_root: Path,
        cli_version: str,
        *,
        version: Optional[str] = None,
        from_file: Optional[Path] = None,
        sha256: Optional[str] = None,
        allow_mismatch: bool = False,
    ) -> Dict[str, Any]:
        """Download (or take from ``--from-file``), verify, and install.

        Returns a report dict (idempotent no-op included). Fail-closed on
        every integrity check; nothing is installed on any error.
        """
        target_version = version or cli_version
        bundles = self.bundles_root(data_root)
        bundles.mkdir(parents=True, exist_ok=True)
        self.sweep_tmp(data_root)

        dest = bundles / target_version
        if dest.is_dir() and (dest / "aisc-bundle" / "VERSION").is_file():
            # Idempotent: same-version verified install already present.
            errs = verify_staged_bundle(dest / "aisc-bundle")
            if errs:
                raise BundleFetchError(
                    BUNDLE_FETCH_ERROR_CONFLICT,
                    f"existing install at {dest} failed verification: {errs[0]} "
                    f"(remove it via `aisc bundle remove {target_version}` and re-fetch)")
            return {"status": "already-installed", "version": target_version, "path": str(dest)}

        tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=str(bundles)))
        try:
            if from_file is not None:
                archive = Path(from_file).resolve()
                if not archive.is_file():
                    raise BundleFetchError(BUNDLE_FETCH_ERROR_INVALID, f"--from-file not found: {archive}")
                expected = (sha256 or "").strip().lower()
                if not expected:
                    raise BundleFetchError(
                        BUNDLE_FETCH_ERROR_INTEGRITY,
                        "--from-file requires --sha256 (same strength as the online path: "
                        "the GitHub API digest is unavailable offline)")
                actual = _sha256_file(archive)
                if actual != expected:
                    raise BundleFetchError(
                        BUNDLE_FETCH_ERROR_INTEGRITY,
                        f"--from-file digest mismatch: expected {expected[:16]}..., got {actual[:16]}...")
                parsed = _parse_archive_name(archive.name)
                archive_version = parsed[0] if parsed else None
            else:
                archive = self.download_archive(target_version, tmp)
                archive_version = _parse_archive_name(archive.name)[0]

            if archive_version is not None and archive_version != target_version and not allow_mismatch:
                raise BundleFetchError(
                    BUNDLE_FETCH_ERROR_CONFLICT,
                    f"archive is version {archive_version}, requested {target_version} "
                    f"(manifest gate would reject it; pass --allow-mismatch to override)")

            extracted = tmp / "extracted"
            errs = safe_extract_archive(archive, extracted)
            if errs:
                raise BundleFetchError(BUNDLE_FETCH_ERROR_INVALID, f"archive failed validation: {errs[0]}")

            tops = [c for c in extracted.iterdir() if c.is_dir()]
            if len(tops) != 1:
                raise BundleFetchError(
                    BUNDLE_FETCH_ERROR_INVALID,
                    f"archive must contain exactly one top-level directory, found {len(tops)}")
            inner = tops[0] / "aisc-bundle"
            if not inner.is_dir():
                raise BundleFetchError(
                    BUNDLE_FETCH_ERROR_INVALID, "archive has no aisc-bundle/ directory")

            errs = verify_staged_bundle(inner)
            if errs:
                raise BundleFetchError(BUNDLE_FETCH_ERROR_INVALID, f"bundle verification failed: {errs[0]}")

            bundle_ver = bundle_version(inner) or "?"
            if bundle_ver != target_version and not allow_mismatch:
                raise BundleFetchError(
                    BUNDLE_FETCH_ERROR_CONFLICT,
                    f"bundle VERSION {bundle_ver} != requested {target_version} (--allow-mismatch to override)")

            ok, reason = bundle_compatible(inner, cli_version)
            if not ok and not allow_mismatch:
                raise BundleFetchError(BUNDLE_FETCH_ERROR_CONFLICT, f"manifest gate: {reason}")

            final = bundles / bundle_ver
            if final.exists():
                # Race or version switch: verified bundle already present.
                shutil.rmtree(tmp, ignore_errors=True)
                return {"status": "already-installed", "version": bundle_ver, "path": str(final)}
            os.replace(inner.parent, final)
            return {"status": "installed", "version": bundle_ver, "path": str(final)}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def remove(self, data_root: Path, version: str, active_root: Optional[Path]) -> Dict[str, Any]:
        target = self.bundles_root(data_root) / version
        bundle = target / "aisc-bundle"
        if not bundle.is_dir():
            raise BundleFetchError(BUNDLE_FETCH_ERROR_NOT_FOUND, f"no installed bundle for version {version}")
        if active_root is not None:
            try:
                active_root.resolve().relative_to(bundle.resolve())
                raise BundleFetchError(
                    BUNDLE_FETCH_ERROR_CONFLICT,
                    f"version {version} is the ACTIVE resolution root — refusing; "
                    f"fetch another version first or unset AISC_ROOT")
            except ValueError:
                pass  # active root lives elsewhere — safe to remove
        shutil.rmtree(target)
        return {"status": "removed", "version": version}
