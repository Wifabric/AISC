"""Pinned staging verifies official identities before publishing a whole family."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage-npm.sh"
HELPER = ROOT / "scripts" / "stage_npm.py"
OFFICIAL = "https://registry.npmjs.org"
MIRROR = "https://mirror.test"
CLAUDE = "@anthropic-ai/claude-code"
CODEX = "@openai/codex"


def tgz(package, version, optional=None, dependencies=None, payload=b"native", **extra):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        metadata = json.dumps({"name": package, "version": version, "optionalDependencies": optional or {}, "dependencies": dependencies or {}, **extra}).encode()
        for name, content in (("package/package.json", metadata), ("package/payload", payload)):
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
    return stream.getvalue()


class Registry:
    def __init__(self):
        self.json = {}
        self.bytes = {}
        self.requests = []
        self.downloads = []

    def add(self, package, version, body, *, alias_url=None):
        escaped = package.replace("/", "%2F")
        official_tarball = f"{OFFICIAL}/{package}/-/actual-{version}.tgz"
        dist = {"tarball": official_tarball, "integrity": "sha512-" + base64.b64encode(hashlib.sha512(body).digest()).decode()}
        self.json[f"{OFFICIAL}/{escaped}/{version}"] = {"name": package, "version": version, "dist": dist}
        mirror_tarball = alias_url or f"{MIRROR}/blobs/{package.rsplit('/', 1)[-1]}-{version}.tgz"
        self.json[f"{MIRROR}/{escaped}/{version}"] = {"name": package, "version": version, "dist": {**dist, "tarball": mirror_tarball}}
        self.bytes[official_tarball] = body
        self.bytes[mirror_tarball] = body
        return official_tarball, mirror_tarball

    def get_json(self, url):
        self.requests.append(url)
        if url not in self.json:
            raise OSError("fixture metadata unavailable")
        return self.json[url]

    def fetch(self, url, target):
        self.downloads.append(url)
        value = self.bytes.get(url)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise OSError("fixture bytes unavailable")
        Path(target).write_bytes(value)


def helper():
    if not HELPER.exists():
        pytest.fail("verified family staging helper is not implemented")
    spec = importlib.util.spec_from_file_location("stage_npm_under_test", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage(tmp_path, registry):
    return helper().Stager(tmp_path, registry=MIRROR, get_json=registry.get_json, fetch=registry.fetch, mirrors=["https://ghfast.top/", ""])


def family(registry, package=CODEX, version="0.164.0"):
    optional = {}
    prefix = package.rsplit("/", 1)[-1]
    expected = {f"{prefix}-{version}.tgz"}
    for arch in ("x64", "arm64"):
        dependency = f"{package}-linux-{arch}"
        if package == CODEX:
            real, native_version = package, f"{version}-linux-{arch}"
            optional[dependency] = f"npm:{real}@{native_version}"
        else:
            real, native_version = dependency, version
            optional[dependency] = native_version
        registry.add(real, native_version, tgz(real, native_version, cpu=[arch], os=["linux"]))
        expected.add(f"{prefix}-linux-{arch}-{native_version}.tgz")
    registry.add(package, version, tgz(package, version, optional))
    return expected


def snapshot(path):
    return {file.name: file.read_bytes() for file in path.iterdir() if file.is_file()}


def test_shell_rejects_bad_mirror_bytes_and_preserves_old_family(tmp_path):
    """Exercise the old shell's real no-companions path for the initial RED."""
    registry = Registry()
    good = tgz(CLAUDE, "2.1.311")
    official_url, mirror_url = registry.add(CLAUDE, "2.1.311", good)
    bad = tgz(CLAUDE, "2.1.311", payload=b"tampered mirror")
    registry.bytes[official_url] = registry.bytes[mirror_url] = bad
    registry.bytes[f"{MIRROR}/{CLAUDE}/-/claude-code-2.1.311.tgz"] = bad
    codex = tgz(CODEX, "0.164.0")
    registry.add(CODEX, "0.164.0", codex)
    registry.bytes[f"{MIRROR}/{CODEX}/-/codex-0.164.0.tgz"] = codex
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy2(SCRIPT, scripts / SCRIPT.name)
    if HELPER.exists():
        shutil.copy2(HELPER, scripts / HELPER.name)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "versions.env").write_text("CLAUDE_CODE_VERSION=2.1.311\nCODEX_VERSION=0.164.0\nYAZI_VERSION=26.9.1\n")
    downloads = tmp_path / "container" / "downloads"
    downloads.mkdir(parents=True)
    (downloads / "claude-code-2.1.273.tgz").write_bytes(b"previous working family")
    fixtures = tmp_path / "network.json"
    fixtures.write_text(json.dumps({**{url: base64.b64encode(value).decode() for url, value in registry.bytes.items()}, **{url: base64.b64encode(json.dumps(value).encode()).decode() for url, value in registry.json.items()}}))
    network = tmp_path / "network"
    network.mkdir()
    (network / "sitecustomize.py").write_text('''import base64, io, json, os, urllib.request
def fixture_open(request, *args, **kwargs):
    url = request.full_url if hasattr(request, "full_url") else request
    with open(os.environ["STAGE_FIXTURES"]) as source:
        rows = json.load(source)
    if url not in rows:
        raise OSError("fixture URL unavailable: " + url)
    return io.BytesIO(base64.b64decode(rows[url]))
urllib.request.urlopen = fixture_open
''')
    curl_py = network / "curl.py"
    curl_py.write_text('''import base64, json, os, sys
args = sys.argv[1:]
url = next(arg for arg in args if arg.startswith("https://"))
with open(os.environ["STAGE_FIXTURES"]) as source:
    data = base64.b64decode(json.load(source)[url])
if "-o" in args:
    with open(args[args.index("-o") + 1], "wb") as output:
        output.write(data)
else:
    sys.stdout.buffer.write(data)
''')
    (network / "curl").write_text('#!/usr/bin/env bash\nexec python "$STAGE_CURL" "$@"\n')
    (network / "curl").chmod(0o755)
    bash_env = network / "bash_env.sh"
    bash_env.write_text('if command -v cygpath >/dev/null 2>&1; then export PATH="$(cygpath -u "$STAGE_NETWORK"):$PATH"; else export PATH="$STAGE_NETWORK:$PATH"; fi\n')
    env = {**os.environ, "STAGE_FIXTURES": str(fixtures), "STAGE_CURL": str(curl_py), "PYTHONPATH": str(network), "STAGE_NETWORK": str(network), "BASH_ENV": str(bash_env)}
    # Git Bash converts Windows PATH entries to POSIX before resolving curl.
    env["PATH"] = str(network) + os.pathsep + str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
    bash = shutil.which("bash")
    if os.name == "nt":
        bash = str(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "bin" / "bash.exe")
    result = subprocess.run([bash, str(scripts / SCRIPT.name), "--registry", MIRROR, "--no-companions"], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "integrity" in (result.stdout + result.stderr).lower()
    assert snapshot(downloads) == {"claude-code-2.1.273.tgz": b"previous working family"}


@pytest.mark.parametrize("package,version", [(CODEX, "0.164.0"), (CLAUDE, "2.1.311")])
def test_all_arches_resolves_real_companions_and_metadata_tarball(tmp_path, package, version):
    registry = Registry()
    expected = family(registry, package, version)
    stage(tmp_path, registry).stage_family(package, version, ["x64", "arm64"])
    assert set(snapshot(tmp_path)) == expected
    assert all("/blobs/" in url for url in registry.downloads)
    assert len(registry.downloads) == 3


def test_cache_skip_validates_every_exact_current_artifact(tmp_path):
    registry = Registry()
    expected = family(registry)
    stager = stage(tmp_path, registry)
    stager.stage_family(CODEX, "0.164.0", ["x64", "arm64"])
    registry.downloads.clear()
    stager.stage_family(CODEX, "0.164.0", ["x64", "arm64"])
    assert registry.downloads == []
    stale = tmp_path / "codex-linux-x64-0.154.0-linux-x64.tgz"
    stale.write_bytes(b"obsolete")
    current = tmp_path / "codex-linux-x64-0.164.0-linux-x64.tgz"
    current.write_bytes(b"corrupt current cache")
    stager.stage_family(CODEX, "0.164.0", ["x64", "arm64"])
    assert len(registry.downloads) == 1
    assert set(snapshot(tmp_path)) == expected


def test_old_companion_never_satisfies_current_main_cache(tmp_path):
    registry = Registry()
    family(registry)
    main_url = registry.json[f"{OFFICIAL}/@openai%2Fcodex/0.164.0"]["dist"]["tarball"]
    (tmp_path / "codex-0.164.0.tgz").write_bytes(registry.bytes[main_url])
    (tmp_path / "codex-linux-x64-0.154.0-linux-x64.tgz").write_bytes(b"old companion")
    stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64"])
    assert len(registry.downloads) == 1
    assert set(snapshot(tmp_path)) == {"codex-0.164.0.tgz", "codex-linux-x64-0.164.0-linux-x64.tgz"}


@pytest.mark.parametrize("optional", [{}, {"@openai/codex-linux-x64": "^0.164.0"}])
def test_missing_or_unpinned_companion_fails_before_publishing(tmp_path, optional):
    registry = Registry()
    registry.add(CODEX, "0.164.0", tgz(CODEX, "0.164.0", optional))
    (tmp_path / "codex-0.154.0.tgz").write_bytes(b"old")
    with pytest.raises(Exception, match="(?i)(companion|optionalDependencies|exact|pinned)"):
        stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64"])
    assert snapshot(tmp_path) == {"codex-0.154.0.tgz": b"old"}


def test_main_pins_and_both_architectures_come_from_versions_env(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "versions.env").write_text("CLAUDE_CODE_VERSION=2.1.311\nCODEX_VERSION=0.164.0\nYAZI_VERSION=26.9.1 # stable\n")
    module = helper()
    calls = []
    class FakeStager:
        def stage_family(self, *args, **kwargs):
            calls.append((args, kwargs))
        def stage_yazi(self, *args):
            calls.append((args, {}))
    monkeypatch.setattr(module, "Stager", lambda *args, **kwargs: FakeStager())
    assert module.main(["--root", str(tmp_path), "--all-arches", "--yazi"]) == 0
    assert calls == [((CLAUDE, "2.1.311", ["x64", "arm64"]), {"no_companions": False}), ((CODEX, "0.164.0", ["x64", "arm64"]), {"no_companions": False}), (("26.9.1", ["x64", "arm64"]), {})]


def test_official_integrity_rejects_bad_mirror_and_falls_back_to_official(tmp_path):
    registry = Registry()
    family(registry)
    mirror_url = registry.json[f"{MIRROR}/@openai%2Fcodex/0.164.0"]["dist"]["tarball"]
    registry.bytes[mirror_url] = tgz(CODEX, "0.164.0", payload=b"mirror corruption")
    stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64"], no_companions=True)
    assert registry.downloads[0] == mirror_url
    assert registry.downloads[1].startswith(OFFICIAL)


def test_partial_companion_failure_keeps_old_family_and_unrelated_files(tmp_path):
    registry = Registry()
    family(registry)
    for url in registry.bytes:
        if "0.164.0-linux-arm64" in url:
            registry.bytes[url] = b"bad digest"
    initial = {"codex-0.154.0.tgz": b"old main", "codex-linux-x64-0.154.0-linux-x64.tgz": b"old native", "claude-code-2.1.273.tgz": b"other family", "country.mmdb": b"geodata"}
    for filename, body in initial.items():
        (tmp_path / filename).write_bytes(body)
    with pytest.raises(Exception, match="(?i)(integrity|digest|sha512)"):
        stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64", "arm64"])
    assert snapshot(tmp_path) == initial
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(initial)


def test_no_companions_preserves_main_only_ci_semantics(tmp_path):
    registry = Registry()
    family(registry)
    (tmp_path / "codex-linux-x64-0.154.0.tgz").write_bytes(b"old native")
    (tmp_path / "codex-notes.tgz").write_bytes(b"not an owned artifact")
    stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64", "arm64"], no_companions=True)
    assert set(snapshot(tmp_path)) == {"codex-0.164.0.tgz", "codex-notes.tgz"}
    assert len(registry.downloads) == 1
    assert not any("linux-" in url for url in registry.requests)


def test_missing_sha512_or_official_metadata_never_trusts_mirror(tmp_path):
    registry = Registry()
    family(registry)
    del registry.json[f"{OFFICIAL}/@openai%2Fcodex/0.164.0"]["dist"]["integrity"]
    with pytest.raises(Exception, match="(?i)(integrity|sha512)"):
        stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64"])
    assert registry.downloads == []
    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("dependencies", [{"unexpected": "1.0.0"}])
def test_non_optional_dependencies_fail_before_replacing_family(tmp_path, dependencies):
    registry = Registry()
    registry.add(CODEX, "0.164.0", tgz(CODEX, "0.164.0", dependencies=dependencies))
    (tmp_path / "codex-0.154.0.tgz").write_bytes(b"old")
    with pytest.raises(Exception, match="(?i)(closure|dependencies)"):
        stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64"], no_companions=True)
    assert snapshot(tmp_path) == {"codex-0.154.0.tgz": b"old"}


def yazi(registry):
    assets = []
    for arch in ("x86_64", "aarch64"):
        name = f"yazi-{arch}-unknown-linux-musl.zip"
        url = f"https://github.com/sxyazi/yazi/releases/download/v26.9.1/{name}"
        body = f"official yazi {arch}".encode()
        assets.append({"name": name, "browser_download_url": url, "digest": "sha256:" + hashlib.sha256(body).hexdigest()})
        registry.bytes[url] = registry.bytes["https://ghfast.top/" + url] = body
    registry.json["https://api.github.com/repos/sxyazi/yazi/releases/tags/v26.9.1"] = {"tag_name": "v26.9.1", "draft": False, "prerelease": False, "assets": assets}


def test_yazi_all_arches_checks_official_digests_and_clears_old_zip_only(tmp_path):
    registry = Registry()
    yazi(registry)
    (tmp_path / "yazi-x86_64-unknown-linux-musl-v25.2.26.zip").write_bytes(b"old")
    (tmp_path / "codex-0.154.0.tgz").write_bytes(b"other family")
    stager = stage(tmp_path, registry)
    stager.stage_yazi("26.9.1", ["x64", "arm64"])
    assert set(snapshot(tmp_path)) == {"yazi-x86_64-unknown-linux-musl-v26.9.1.zip", "yazi-aarch64-unknown-linux-musl-v26.9.1.zip", "codex-0.154.0.tgz"}
    registry.downloads.clear()
    stager.stage_yazi("26.9.1", ["x64", "arm64"])
    assert registry.downloads == []


def test_yazi_second_arch_bad_digest_keeps_entire_old_family(tmp_path):
    registry = Registry()
    yazi(registry)
    for url in registry.bytes:
        if "aarch64" in url:
            registry.bytes[url] = b"corrupt zip"
    (tmp_path / "yazi-x86_64-unknown-linux-musl-v25.2.26.zip").write_bytes(b"old")
    initial = snapshot(tmp_path)
    with pytest.raises(Exception, match="(?i)(digest|sha256)"):
        stage(tmp_path, registry).stage_yazi("26.9.1", ["x64", "arm64"])
    assert snapshot(tmp_path) == initial


def test_yazi_missing_official_asset_digest_fails_closed(tmp_path):
    registry = Registry()
    yazi(registry)
    del registry.json["https://api.github.com/repos/sxyazi/yazi/releases/tags/v26.9.1"]["assets"][0]["digest"]
    with pytest.raises(Exception, match="(?i)(digest|sha256)"):
        stage(tmp_path, registry).stage_yazi("26.9.1", ["x64"])
    assert snapshot(tmp_path) == {}


def test_cleanup_preserves_non_versioned_same_prefix_files(tmp_path):
    registry = Registry()
    family(registry)
    yazi(registry)
    unrelated = {
        "codex-2026-notes.tgz": b"notes",
        "codex-linux-x64-2026-notes.tgz": b"native notes",
        "yazi-x86_64-unknown-linux-musl-v2026-notes.zip": b"zip notes",
        "claude-code-2.1.273.tgz": b"other family",
    }
    for name, body in unrelated.items():
        (tmp_path / name).write_bytes(body)
    (tmp_path / "codex-0.154.0.tgz").write_bytes(b"obsolete main")
    (tmp_path / "yazi-aarch64-unknown-linux-musl-v25.2.26.zip").write_bytes(b"obsolete zip")
    stager = stage(tmp_path, registry)
    stager.stage_family(CODEX, "0.164.0", ["x64"], no_companions=True)
    stager.stage_yazi("26.9.1", ["x64"])
    remaining = snapshot(tmp_path)
    assert {name: remaining.get(name) for name in unrelated} == unrelated
    assert set(remaining) == set(unrelated) | {"codex-0.164.0.tgz", "yazi-x86_64-unknown-linux-musl-v26.9.1.zip"}


def test_publish_failure_restores_entire_previous_family(tmp_path, monkeypatch):
    registry = Registry()
    family(registry)
    initial = {
        "codex-0.154.0.tgz": b"old main",
        "codex-linux-x64-0.154.0-linux-x64.tgz": b"old native",
        "codex-linux-x64-0.164.0-linux-x64.tgz": b"damaged current native",
        "claude-code-2.1.273.tgz": b"other family",
    }
    for name, body in initial.items():
        (tmp_path / name).write_bytes(body)
    module = helper()
    original_replace = module.os.replace
    failed = False

    def replace(source, destination):
        nonlocal failed
        if Path(destination).parent == tmp_path and Path(destination).name == "codex-linux-x64-0.164.0-linux-x64.tgz" and not failed:
            failed = True
            raise OSError("simulated disk publish failure")
        return original_replace(source, destination)

    monkeypatch.setattr(module.os, "replace", replace)
    with pytest.raises(OSError, match="simulated disk publish failure"):
        module.Stager(tmp_path, registry=MIRROR, get_json=registry.get_json, fetch=registry.fetch).stage_family(CODEX, "0.164.0", ["x64", "arm64"])
    assert failed
    assert snapshot(tmp_path) == initial
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(initial)


@pytest.mark.parametrize("package,version", [(CLAUDE, "0.164.0"), (CODEX, "0.154.0")])
def test_valid_digest_with_wrong_package_identity_keeps_old_family(tmp_path, package, version):
    registry = Registry()
    registry.add(CODEX, "0.164.0", tgz(package, version))
    (tmp_path / "codex-0.154.0.tgz").write_bytes(b"old main")
    with pytest.raises(Exception, match="identity mismatch"):
        stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64"], no_companions=True)
    assert snapshot(tmp_path) == {"codex-0.154.0.tgz": b"old main"}


def test_unavailable_official_metadata_never_downloads_mirror(tmp_path):
    registry = Registry()
    family(registry)
    del registry.json[f"{OFFICIAL}/@openai%2Fcodex/0.164.0"]
    (tmp_path / "codex-0.154.0.tgz").write_bytes(b"old main")
    with pytest.raises(OSError, match="metadata unavailable"):
        stage(tmp_path, registry).stage_family(CODEX, "0.164.0", ["x64"])
    assert registry.downloads == []
    assert snapshot(tmp_path) == {"codex-0.154.0.tgz": b"old main"}


@pytest.mark.parametrize("package,version", [(CODEX, "0.164.0"), (CLAUDE, "2.1.311")])
@pytest.mark.parametrize("arch", ["x64", "arm64"])
@pytest.mark.parametrize("bad", [
    {"dependencies": {"unexpected-runtime": "1.0.0"}},
    {"cpu": ["s390x"]},
    {"os": ["darwin"]},
    {"cpu": None},
    {"os": None},
    {"cpu": "x64"},
])
def test_bad_companion_closure_or_platform_keeps_old_family(tmp_path, package, version, arch, bad):
    registry = Registry()
    family(registry, package, version)
    real = package if package == CODEX else f"{package}-linux-{arch}"
    native_version = f"{version}-linux-{arch}" if package == CODEX else version
    metadata = {"cpu": [arch], "os": ["linux"], **bad}
    registry.add(real, native_version, tgz(real, native_version, **metadata))
    prefix = package.rsplit("/", 1)[-1]
    initial = {f"{prefix}-1.0.0.tgz": b"old main", f"{prefix}-linux-{arch}-1.0.0.tgz": b"old native", "country.mmdb": b"other family"}
    for name, body in initial.items():
        (tmp_path / name).write_bytes(body)
    with pytest.raises(Exception, match="(?i)(dependencies|closure|platform|cpu|os)"):
        stage(tmp_path, registry).stage_family(package, version, [arch])
    assert snapshot(tmp_path) == initial
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(initial)


@pytest.mark.parametrize("secondary", ["unlink", "replace"])
def test_publish_and_rollback_failures_preserve_recoverable_old_bytes(tmp_path, monkeypatch, secondary):
    registry = Registry()
    family(registry)
    initial = {
        "codex-0.154.0.tgz": b"old main",
        "codex-linux-x64-0.154.0-linux-x64.tgz": b"old native",
        "codex-linux-x64-0.164.0-linux-x64.tgz": b"damaged current native",
        "country.mmdb": b"unrelated",
    }
    for name, body in initial.items():
        (tmp_path / name).write_bytes(body)
    module = helper()
    original_replace, original_unlink = module.os.replace, Path.unlink
    forward_failed = False
    rollback_failed = False

    def replace(source, destination):
        nonlocal forward_failed, rollback_failed
        source, destination = Path(source), Path(destination)
        if destination.parent == tmp_path:
            if destination.name == "codex-linux-x64-0.164.0-linux-x64.tgz" and not forward_failed:
                forward_failed = True
                raise OSError("injected publish failure")
            if secondary == "replace" and forward_failed and source.name == "codex-0.154.0.tgz":
                rollback_failed = True
                raise OSError("injected rollback replace failure")
        return original_replace(source, destination)

    def unlink(path, *args, **kwargs):
        nonlocal rollback_failed
        if secondary == "unlink" and forward_failed and path == tmp_path / "codex-0.164.0.tgz":
            rollback_failed = True
            raise OSError("injected rollback unlink failure")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(module.os, "replace", replace)
    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(Exception) as caught:
        module.Stager(tmp_path, registry=MIRROR, get_json=registry.get_json, fetch=registry.fetch).stage_family(CODEX, "0.164.0", ["x64", "arm64"])
    assert forward_failed and rollback_failed
    recovery = list(tmp_path.glob(".stage-recovery-*"))
    assert len(recovery) == 1, "rollback failure must retain backup outside the temporary staging directory"
    assert str(recovery[0].resolve()) in str(caught.value)
    assert "rollback incomplete" in str(caught.value).lower()
    recoverable = {**snapshot(tmp_path), **snapshot(recovery[0])}
    assert {name: recoverable.get(name) for name in initial} == initial
    assert (tmp_path / "codex-linux-x64-0.154.0-linux-x64.tgz").read_bytes() == b"old native", "restore must continue after another file failed"
    assert not list(tmp_path.glob(".stage-codex-*"))
