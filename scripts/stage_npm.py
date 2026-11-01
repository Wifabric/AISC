#!/usr/bin/env python3
"""Stage pinned npm/yazi families; publish only after official digest checks.

No third-party Python dependencies or archive extraction. The registry mirror
provides bytes, while registry.npmjs.org provides the authoritative SHA512.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request

OFFICIAL_REGISTRY = "https://registry.npmjs.org"
DEFAULT_REGISTRY = "https://registry.npmmirror.com"
DEFAULT_MIRRORS = ("https://ghfast.top/", "https://gh-proxy.com/", "https://github.moeyy.xyz/", "")
ARCHES = {"x64": "x86_64-unknown-linux-musl", "arm64": "aarch64-unknown-linux-musl"}
FAMILIES = {"@anthropic-ai/claude-code": "claude-code", "@openai/codex": "codex"}
VERSION_PATTERN = r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?(?:\+[0-9A-Za-z.-]+)?"
EXACT_VERSION = re.compile(VERSION_PATTERN + r"\Z", re.ASCII)


class StageError(RuntimeError):
    pass


def _https(url: str) -> str:
    if not isinstance(url, str) or urllib.parse.urlsplit(url).scheme != "https":
        raise StageError("metadata tarball URL must use HTTPS")
    return url


def _open(url, timeout):
    request = urllib.request.Request(_https(url), headers={"User-Agent": "AISC-stage-pinned", "Accept": "application/json, */*"})
    for attempt in range(3):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def read_json(url):
    with _open(url, 30) as response:
        body = response.read(4 * 1024 * 1024 + 1)
    if len(body) > 4 * 1024 * 1024:
        raise StageError("registry metadata exceeds 4 MiB")
    return json.loads(body)


def download(url, target):
    with _open(url, 120) as response, Path(target).open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)


def digest(path, algorithm):
    hasher = hashlib.new(algorithm)
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.digest()


def matches(path, algorithm, expected):
    try:
        return not path.is_symlink() and path.is_file() and digest(path, algorithm) == expected
    except OSError:
        return False


def _exact_version(version):
    if not isinstance(version, str) or not EXACT_VERSION.fullmatch(version):
        raise StageError("an exact pinned npm version is required")
    return version


def _metadata(value, package, version):
    if not isinstance(value, dict) or value.get("name") != package or value.get("version") != version:
        raise StageError(f"registry identity mismatch for {package}@{version}")
    dist = value.get("dist")
    if not isinstance(dist, dict):
        raise StageError(f"registry dist metadata missing for {package}@{version}")
    _https(dist.get("tarball"))
    return dist


def _sha512(dist):
    integrity = dist.get("integrity")
    if isinstance(integrity, str):
        for entry in integrity.split():
            if not entry.startswith("sha512-"):
                continue
            try:
                expected = base64.b64decode(entry[len("sha512-"):], validate=True)
            except (ValueError, binascii.Error):
                continue
            if len(expected) == 64:
                return expected
    raise StageError("official npm dist.integrity has no valid SHA512")


def package_json(path, package, version):
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            member = archive.getmember("package/package.json")
            if not member.isfile() or member.size > 1024 * 1024:
                raise StageError("package.json must be a regular file below 1 MiB")
            stream = archive.extractfile(member)
            if stream is None:
                raise StageError("package.json is unreadable")
            with stream:
                value = json.load(stream)
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        raise StageError("invalid npm package/package.json") from error
    if not isinstance(value, dict) or value.get("name") != package or value.get("version") != version:
        raise StageError(f"tarball package identity mismatch for {package}@{version}")
    return value


def companion(main, package, arch):
    name = f"{package}-linux-{arch}"
    optional = main.get("optionalDependencies")
    spec = optional.get(name) if isinstance(optional, dict) else None
    if not isinstance(spec, str):
        raise StageError(f"optionalDependencies companion missing: {name}")
    real, version = name, spec
    if spec.startswith("npm:"):
        real, separator, version = spec[4:].rpartition("@")
        if not separator or not re.fullmatch(r"(?:@[a-zA-Z0-9_.-]+/)?[a-zA-Z0-9_.-]+", real):
            raise StageError(f"invalid pinned npm alias for companion {name}")
    return real, _exact_version(version)


class Stager:
    def __init__(self, downloads, *, registry=DEFAULT_REGISTRY, get_json=read_json, fetch=download, mirrors=DEFAULT_MIRRORS):
        self.downloads = Path(downloads)
        self.downloads.mkdir(parents=True, exist_ok=True)
        self.registry = _https(registry).rstrip("/")
        self.get_json = get_json
        self.fetch = fetch
        self.mirrors = tuple(mirrors)

    def _verified_download(self, urls, path, algorithm, expected):
        for url in dict.fromkeys(urls):
            try:
                self.fetch(_https(url), path)
                if matches(path, algorithm, expected):
                    return path
            except (OSError, ValueError):
                pass
            path.unlink(missing_ok=True)
        raise StageError(f"{algorithm} integrity verification failed for {path.name}; all sources exhausted")

    def _npm(self, package, version, filename, temporary):
        escaped = urllib.parse.quote(package, safe="@")
        authoritative = self.get_json(f"{OFFICIAL_REGISTRY}/{escaped}/{version}")
        dist = _metadata(authoritative, package, version)
        expected = _sha512(dist)
        current = self.downloads / filename
        if matches(current, "sha512", expected):
            return current
        urls = []
        if self.registry != OFFICIAL_REGISTRY:
            try:
                mirror = self.get_json(f"{self.registry}/{escaped}/{version}")
                urls.append(_metadata(mirror, package, version)["tarball"])
            except (OSError, ValueError, StageError):
                pass
        urls.append(dist["tarball"])
        return self._verified_download(urls, temporary / filename, "sha512", expected)

    def _publish(self, temporary, desired, owns):
        """Publish validated files, retaining old bytes if rollback also fails."""
        replacements = {name: path for name, path in desired.items() if path.parent != self.downloads}
        obsolete = [path for path in self.downloads.iterdir() if owns(path.name) and path.name not in desired and (path.is_file() or path.is_symlink())]
        # Keep backups outside TemporaryDirectory from the outset. A failed
        # restore must never let its context manager delete the last old copy.
        backup = Path(tempfile.mkdtemp(prefix=".stage-recovery-", dir=self.downloads))
        moved, installed = [], []
        try:
            for path in obsolete + [self.downloads / name for name in replacements if os.path.lexists(self.downloads / name)]:
                os.replace(path, backup / path.name)
                moved.append(path.name)
            for name, path in replacements.items():
                os.replace(path, self.downloads / name)
                installed.append(name)
        except BaseException as error:
            recovery_errors = []
            for name in installed:
                try:
                    (self.downloads / name).unlink(missing_ok=True)
                except OSError as exc:
                    recovery_errors.append(f"remove {name}: {exc}")
            for name in moved:
                try:
                    os.replace(backup / name, self.downloads / name)
                except OSError as exc:
                    recovery_errors.append(f"restore {name}: {exc}")
            if recovery_errors:
                raise StageError(
                    f"publish failed ({error}); rollback incomplete; recovery backup retained at "
                    f"{backup.resolve()}: {'; '.join(recovery_errors)}"
                ) from error
            backup.rmdir()
            raise
        shutil.rmtree(backup)
        for name in sorted(desired):
            print(f"verified: {name}")

    def stage_family(self, package, version, arches, *, no_companions=False):
        version = _exact_version(version)
        prefix = FAMILIES[package]
        self._arches(arches)
        owned = re.compile(rf"{re.escape(prefix)}-(?:linux-(?:x64|arm64)-)?{VERSION_PATTERN}\.tgz\Z")
        with tempfile.TemporaryDirectory(prefix=f".stage-{prefix}-", dir=self.downloads) as directory:
            temporary = Path(directory)
            main_name = f"{prefix}-{version}.tgz"
            main_path = self._npm(package, version, main_name, temporary)
            main = package_json(main_path, package, version)
            if main.get("dependencies"):
                raise StageError(f"{package}@{version} dependencies break the offline closure")
            desired = {main_name: main_path}
            if not no_companions:
                for arch in arches:
                    real, native_version = companion(main, package, arch)
                    filename = f"{prefix}-linux-{arch}-{native_version}.tgz"
                    path = self._npm(real, native_version, filename, temporary)
                    native = package_json(path, real, native_version)
                    dependencies = native.get("dependencies", {})
                    if not isinstance(dependencies, dict) or dependencies:
                        raise StageError(f"{real}@{native_version} companion dependencies break the offline closure")
                    for key, target in (("cpu", arch), ("os", "linux")):
                        if native.get(key) != [target]:
                            raise StageError(f"{real}@{native_version} companion {key} platform must be [{target}]")
                    desired[filename] = path
            self._publish(temporary, desired, owned.fullmatch)

    @staticmethod
    def _arches(arches):
        if not arches or any(arch not in ARCHES for arch in arches) or len(set(arches)) != len(arches):
            raise StageError("architectures must be unique x64/arm64 values")

    def stage_yazi(self, version, arches, pins):
        version = _exact_version(version.removeprefix("v"))
        self._arches(arches)
        tag = f"v{version}"
        owned = re.compile(rf"yazi-(?:x86_64|aarch64)-unknown-linux-musl-v{VERSION_PATTERN}\.zip\Z")
        with tempfile.TemporaryDirectory(prefix=".stage-yazi-", dir=self.downloads) as directory:
            temporary = Path(directory)
            desired = {}
            for arch in arches:
                triple = ARCHES[arch]
                asset = f"yazi-{triple}.zip"
                pin_arch = "X86_64" if arch == "x64" else "ARM64"
                digest = str(pins.get(f"YAZI_{pin_arch}_SHA256", "")).strip().lower()
                size = str(pins.get(f"YAZI_{pin_arch}_BYTES", "")).strip()
                if not re.fullmatch(r"[0-9a-f]{64}", digest) or not size.isdigit():
                    raise StageError(f"official yazi SHA256/size pin missing or invalid for {arch}")
                expected = bytes.fromhex(digest)
                url = f"https://github.com/sxyazi/yazi/releases/download/{tag}/{asset}"
                filename = f"yazi-{triple}-{tag}.zip"
                current = self.downloads / filename
                if matches(current, "sha256", expected):
                    desired[filename] = current
                else:
                    urls = [mirror + url for mirror in self.mirrors]
                    if url not in urls:
                        urls.append(url)
                    path = self._verified_download(urls, temporary / filename, "sha256", expected)
                    actual_size = path.stat().st_size
                    if actual_size != int(size):
                        raise StageError(
                            f"official yazi size mismatch for {asset}: expected {size}, got {actual_size}"
                        )
                    desired[filename] = path
            self._publish(temporary, desired, owned.fullmatch)



def versions_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        key, separator, value = line.partition("=")
        if separator:
            values[key.strip()] = value.strip()
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    parser.add_argument("--yazi", action="store_true")
    parser.add_argument("--all-arches", action="store_true")
    parser.add_argument("--no-companions", action="store_true", help="stage main npm tarballs only (CI Git presets)")
    parser.add_argument("--latest", action="store_true", help="explicitly override npm pins with official stable latest tags")
    parser.add_argument("--github-mirror", action="append", default=None)
    args = parser.parse_args(argv)
    values = versions_env(args.root / "config" / "versions.env")
    native = "arm64" if platform.machine().lower() in {"arm64", "aarch64"} else "x64"
    arches = ["x64", "arm64"] if args.all_arches else [native]
    stager = Stager(args.root / "container" / "downloads", registry=args.registry, mirrors=args.github_mirror if args.github_mirror is not None else DEFAULT_MIRRORS)
    for package, key in (("@anthropic-ai/claude-code", "CLAUDE_CODE_VERSION"), ("@openai/codex", "CODEX_VERSION")):
        version = values.get(key, "")
        if args.latest:
            version = read_json(f"{OFFICIAL_REGISTRY}/{urllib.parse.quote(package, safe='@')}/latest").get("version", "")
            if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
                raise StageError("official npm latest is not a stable release")
        stager.stage_family(package, version, arches, no_companions=args.no_companions)
    if args.yazi:
        yazi_pins = {key: value for key, value in values.items() if key.startswith("YAZI_")}
        stager.stage_yazi(values.get("YAZI_VERSION", ""), arches, yazi_pins)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (StageError, OSError, ValueError) as error:
        print(f"staging failed: {error}", file=sys.stderr)
        sys.exit(1)
