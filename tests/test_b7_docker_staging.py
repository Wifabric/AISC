"""Execute dependency selection/staging against local fixtures, without Docker/network."""

from __future__ import annotations

import hashlib
import gzip
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = Path("C:/Program Files/Git/bin/bash.exe") if os.name == "nt" else shutil.which("bash")
NODE = ROOT / ".tools/node22/node.exe" if os.name == "nt" else shutil.which("node")
COMMIT = "02ae05ac06e8c9287916fbabfe61ef5c8591407f"
GEO = ("geoip.metadb", "geosite.dat", "country.mmdb")
PINS = {
    "MIHOMO_VERSION": "v1.19.33", "GEODATA_VERSION": "20261027", "GEODATA_COMMIT": COMMIT,
    "CLAUDE_CODE_VERSION": "2.1.311", "CODEX_VERSION": "0.164.0", "YAZI_VERSION": "26.9.1",
    "CC_SWITCH_VERSION": "v5.11.3", "CC_SWITCH_ASSET_URL": "", "CC_SWITCH_ASSET_NAME": "",
    "CC_SWITCH_ASSET_SHA256": "", "GH_PROXY": "", "GH_MIRRORS": "", "USE_CN_MIRROR": "0",
}


def shell(script: str, root: Path, **env: str) -> subprocess.CompletedProcess[str]:
    assert BASH and Path(BASH).exists(), "bash is required for the shell contract tests"
    process_env = {**os.environ, **PINS, "AISC_TEST_PYTHON": sys.executable,
                   "AISC_TEST_NODE": str(NODE), "AISC_TEST_ROOT": root.as_posix(), **env}
    if os.name == "nt":
        # Native Node invokes Git's GNU tar with C:/ paths, not msys argv conversion.
        process_env["TAR_OPTIONS"] = "--force-local"
    prelude = r'''
python3() { "$AISC_TEST_PYTHON" "$@"; }
python() { "$AISC_TEST_PYTHON" "$@"; }
node() { "$AISC_TEST_NODE" "$@"; }
export -f python3 python node
'''
    return subprocess.run([str(BASH), "--noprofile", "--norc", "-s"], input=prelude + script,
                          cwd=root, env=process_env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=30)


def run_block(marker: str) -> str:
    text = (ROOT / "container/Dockerfile").read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    text = text.replace("\\\n", " ")
    for block in re.findall(r"^RUN (.*)$", text, re.MULTILINE):
        if marker in block:
            return block
    raise AssertionError(f"Docker RUN containing {marker!r} missing")


def remap(block: str, root: Path) -> str:
    for path in ("/tmp", "/opt/aisc", "/usr/local/bin"):
        block = block.replace(path, root.as_posix() + path)
    return block


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    for path in ("tmp/dl", "opt/aisc", "usr/local/bin", "fixtures"):
        (tmp_path / path).mkdir(parents=True)
    return tmp_path


def package(path: Path, metadata: dict) -> None:
    payload = json.dumps(metadata).encode()
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("package/package.json")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))


def npm_family(root: Path, prefix: str, version: str, arch: str = "x64", *, companion: bool = True,
               native_version: str | None = None, native_cpu: str | None = None) -> None:
    dl = root / "tmp/dl"
    name = "@openai/codex" if prefix == "codex" else "@anthropic-ai/claude-code"
    native = native_version or (f"{version}-linux-{arch}" if prefix == "codex" else version)
    key = f"{name}-linux-{arch}"
    spec = f"npm:{name}@{native}" if prefix == "codex" else native
    package(dl / f"{prefix}-{version}.tgz", {"name": name, "version": version,
            "optionalDependencies": {key: spec}})
    if companion:
        package(dl / f"{prefix}-linux-{arch}-{native}.tgz", {
            "name": name if prefix == "codex" else key, "version": native,
            "cpu": [native_cpu or arch], "os": ["linux"],
        })


def npm_install(root: Path, arch: str = "amd64", **overrides: str) -> subprocess.CompletedProcess[str]:
    commands = r'''
dpkg() { echo "$AISC_TEST_ARCH"; }
npm() { printf '%s\n' "$*" >> "$AISC_TEST_ROOT/npm.log"; }
ln() { :; }
claude() { :; }
codex() { :; }
'''
    return shell(commands + remap(run_block("npm config set registry"), root), root,
                 AISC_TEST_ARCH=arch, **overrides)


def test_npm_uses_exact_pin_and_declared_codex_alias_despite_old_archives(sandbox: Path):
    npm_family(sandbox, "claude-code", "2.1.273")
    npm_family(sandbox, "codex", "0.154.0")
    npm_family(sandbox, "claude-code", "2.1.311")
    npm_family(sandbox, "codex", "0.164.0")
    result = npm_install(sandbox)
    assert result.returncode == 0, result.stderr
    deps = json.loads((sandbox / "opt/aisc/npm/package.json").read_text())["dependencies"]
    assert deps["@anthropic-ai/claude-code"].endswith("claude-code-2.1.311.tgz")
    assert deps["@openai/codex"].endswith("codex-0.164.0.tgz")
    assert deps["@openai/codex-linux-x64"].endswith("codex-linux-x64-0.164.0-linux-x64.tgz")
    assert "--offline" in (sandbox / "npm.log").read_text()


@pytest.mark.parametrize("case", ["old_companion", "wrong_arch", "false_identity"])
def test_npm_incomplete_or_wrong_generation_closure_uses_online_pins(sandbox: Path, case: str):
    npm_family(sandbox, "claude-code", "2.1.311")
    npm_family(sandbox, "codex", "0.164.0", companion=False)
    if case == "old_companion":
        npm_family(sandbox, "codex", "0.154.0")
    elif case == "wrong_arch":
        npm_family(sandbox, "codex", "0.164.0", "arm64")
        npm_family(sandbox, "codex", "0.164.0", companion=False)
    else:
        npm_family(sandbox, "codex", "0.164.0", native_cpu="arm64")
    result = npm_install(sandbox)
    assert result.returncode == 0, result.stderr
    log = (sandbox / "npm.log").read_text()
    assert "--offline" not in log
    assert "@anthropic-ai/claude-code@2.1.311" in log
    assert "@openai/codex@0.164.0" in log


def test_npm_respects_user_override_and_alias_version_from_manifest(sandbox: Path):
    npm_family(sandbox, "claude-code", "2.1.300", "arm64")
    npm_family(sandbox, "codex", "0.160.0", "arm64", native_version="0.160.1-linux-arm64")
    result = npm_install(sandbox, "arm64", CLAUDE_CODE_VERSION="2.1.300", CODEX_VERSION="0.160.0")
    assert result.returncode == 0, result.stderr
    deps = json.loads((sandbox / "opt/aisc/npm/package.json").read_text())["dependencies"]
    assert deps["@openai/codex-linux-arm64"].endswith("codex-linux-arm64-0.160.1-linux-arm64.tgz")


def geo_fixture(root: Path, directory: Path) -> Path:
    rows = []
    for name in GEO:
        payload = f"snapshot fixture {name}".encode()
        (root / "fixtures" / name).write_bytes(payload)
        rows.append(f"{hashlib.sha256(payload).hexdigest()}  {name}\n")
    manifest = directory / "geodata-20261027.sha256"
    manifest.write_text("".join(rows), encoding="utf-8")
    return manifest


DOWNLOADS = r'''
curl() {
  local url="" out=""
  while [ "$#" -gt 0 ]; do
    case "$1" in
      -o|--output) out="$2"; shift 2 ;;
      http*) url="$1"; shift ;;
      *) shift ;;
    esac
  done
  printf '%s\n' "$url" >> "$AISC_TEST_ROOT/requests.log"
  local file="${url##*/}"
  case "$url" in
    *api.github.com/repos/MetaCubeX/mihomo/releases/tags/*) file=release.json ;;
  esac
  [ "$file" != "${AISC_FAIL_DOWNLOAD:-none}" ] || return 22
  [ -f "$AISC_TEST_ROOT/fixtures/$file" ] || return 22
  cp "$AISC_TEST_ROOT/fixtures/$file" "$out"
}
export -f curl
'''


@pytest.mark.parametrize("local", [True, False])
def test_geodata_local_and_fallback_are_verified_and_commit_pinned(sandbox: Path, local: bool):
    dl = sandbox / "tmp/dl"
    geo_fixture(sandbox, dl)
    if local:
        for name in GEO:
            shutil.copyfile(sandbox / "fixtures" / name, dl / name)
    result = shell(DOWNLOADS + remap(run_block("mkdir -p /opt/aisc/mihomo"), sandbox), sandbox)
    assert result.returncode == 0, result.stderr
    for name in GEO:
        assert (sandbox / "opt/aisc/mihomo" / name).read_bytes() == (sandbox / "fixtures" / name).read_bytes()
    if not local:
        urls = (sandbox / "requests.log").read_text()
        assert f"raw.githubusercontent.com/MetaCubeX/meta-rules-dat/{COMMIT}/" in urls
        assert "/releases/download/20261027/" not in urls


@pytest.mark.parametrize("local", [True, False])
def test_geodata_checksum_mismatch_fails_instead_of_installing(sandbox: Path, local: bool):
    dl = sandbox / "tmp/dl"
    geo_fixture(sandbox, dl)
    if local:
        for name in GEO:
            shutil.copyfile(sandbox / "fixtures" / name, dl / name)
        (dl / "country.mmdb").write_bytes(b"corrupt")
    else:
        (sandbox / "fixtures/country.mmdb").write_bytes(b"corrupt")
    result = shell(DOWNLOADS + remap(run_block("mkdir -p /opt/aisc/mihomo"), sandbox), sandbox)
    assert result.returncode != 0, "corrupt geodata must fail the build"


def test_geodata_missing_checksum_entry_fails(sandbox: Path):
    manifest = geo_fixture(sandbox, sandbox / "tmp/dl")
    manifest.write_text("".join(manifest.read_text().splitlines(True)[:2]))
    result = shell(DOWNLOADS + remap(run_block("mkdir -p /opt/aisc/mihomo"), sandbox), sandbox)
    assert result.returncode != 0, "all three snapshot checksums are mandatory"


def stage_fixture(root: Path) -> Path:
    (root / "tools").mkdir()
    (root / "config").mkdir()
    dl = root / "container/downloads"
    dl.mkdir(parents=True)
    (root / "tools/stage-mihomo.sh").write_text((ROOT / "tools/stage-mihomo.sh").read_text(), encoding="utf-8", newline="\n")
    (root / "config/versions.env").write_text("".join(f"{key}={value}\n" for key, value in PINS.items()), encoding="utf-8")
    geo_fixture(root, dl)
    assets = []
    for arch in ("amd64", "arm64"):
        name = f"mihomo-linux-{arch}-v1.19.33.gz"
        payload = f"pinned mihomo {arch}".encode()
        (root / "fixtures" / name).write_bytes(payload)
        assets.append({"name": name, "digest": "sha256:" + hashlib.sha256(payload).hexdigest()})
    (root / "fixtures/release.json").write_text(json.dumps({"tag_name": "v1.19.33", "assets": assets}))
    (root / "fixtures/mihomo-linux-amd64-v1.19.27.gz").write_bytes(b"obsolete upstream payload")
    (dl / "mihomo-linux-amd64-v1.19.27.gz").write_bytes(b"previous working archive")
    for name in GEO:
        (dl / name).write_bytes(b"previous " + name.encode())
    (dl / "unrelated.tgz").write_bytes(b"other worker")
    return dl


def stage(root: Path, args: str = "", **env: str) -> subprocess.CompletedProcess[str]:
    prelude = DOWNLOADS + r'''
uname() { echo x86_64; }
export -f uname
unset MIHOMO_VERSION GEODATA_VERSION GEODATA_COMMIT
'''
    return shell(prelude + f'bash "$AISC_TEST_ROOT/tools/stage-mihomo.sh" {args}\n', root, **env)


def test_stage_reads_ssot_verifies_all_arches_then_removes_old_version(sandbox: Path):
    dl = stage_fixture(sandbox)
    result = stage(sandbox, "--all-arches")
    assert result.returncode == 0, result.stderr + result.stdout
    assert not (dl / "mihomo-linux-amd64-v1.19.27.gz").exists()
    for arch in ("amd64", "arm64"):
        name = f"mihomo-linux-{arch}-v1.19.33.gz"
        assert (dl / name).read_bytes() == (sandbox / "fixtures" / name).read_bytes()
    assert (dl / "unrelated.tgz").read_bytes() == b"other worker"
    assert not list(dl.glob(".stage-mihomo*"))


@pytest.mark.parametrize("failure", ["download", "mihomo_digest", "geodata_digest", "missing_digest"])
def test_stage_failed_group_keeps_previous_payloads_unchanged(sandbox: Path, failure: str):
    dl = stage_fixture(sandbox)
    before = {p.name: p.read_bytes() for p in dl.iterdir()}
    if failure == "mihomo_digest":
        (sandbox / "fixtures/mihomo-linux-amd64-v1.19.33.gz").write_bytes(b"corrupt")
    elif failure == "geodata_digest":
        (sandbox / "fixtures/country.mmdb").write_bytes(b"corrupt")
    elif failure == "missing_digest":
        (sandbox / "fixtures/release.json").write_text('{"tag_name":"v1.19.33","assets":[]}')
    result = stage(sandbox, AISC_FAIL_DOWNLOAD="country.mmdb" if failure == "download" else "none")
    assert result.returncode != 0, "failed validation must not publish a partial snapshot"
    assert {p.name: p.read_bytes() for p in dl.iterdir()} == before


def test_docker_defaults_are_release_pins_and_preserve_resolver_receipt():
    text = (ROOT / "container/Dockerfile").read_text()
    expected = {**PINS, "NODE_IMAGE": "node:24.22.1-slim@sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205"}
    for key in ("NODE_IMAGE", "CODEX_VERSION", "CLAUDE_CODE_VERSION", "CC_SWITCH_VERSION",
                "MIHOMO_VERSION", "YAZI_VERSION", "GEODATA_VERSION", "GEODATA_COMMIT"):
        assert f"ARG {key}={expected[key]}\n" in text
    assert 'org.aisc.cc-switch.asset-sha256="${CC_SWITCH_ASSET_SHA256}"' in text


def executable(version: str) -> bytes:
    return f"#!/usr/bin/env bash\necho '{version}'\n".encode()


def native_install(root: Path, marker: str, **env: str) -> subprocess.CompletedProcess[str]:
    commands = DOWNLOADS + '\ndpkg() { echo "$AISC_TEST_ARCH"; }\n'
    return shell(commands + remap(run_block(marker), root), root, AISC_TEST_ARCH="amd64", **env)


def test_mihomo_ignores_stale_local_pin_and_fetches_exact_target_arch(sandbox: Path):
    (sandbox / "tmp/dl/mihomo-linux-amd64-v1.19.27.gz").write_bytes(gzip.compress(executable("stale")))
    (sandbox / "tmp/dl/mihomo-linux-arm64-v1.19.33.gz").write_bytes(gzip.compress(executable("wrong arch")))
    (sandbox / "fixtures/mihomo-linux-amd64-v1.19.33.gz").write_bytes(gzip.compress(executable("v1.19.33")))
    result = native_install(sandbox, "/usr/local/bin/mihomo -v")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("v1.19.33")
    assert "/v1.19.33/mihomo-linux-amd64-v1.19.33.gz" in (sandbox / "requests.log").read_text()


def yazi_package(path: Path, arch: str, version: str):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"yazi-{arch}/yazi", executable(version))


def test_yazi_ignores_wrong_arch_and_old_pin_instead_of_first_zip(sandbox: Path):
    yazi_package(sandbox / "tmp/dl/yazi-aarch64-unknown-linux-musl-v26.9.1.zip", "aarch64-unknown-linux-musl", "wrong arch")
    yazi_package(sandbox / "tmp/dl/yazi-x86_64-unknown-linux-musl-v25.2.26.zip", "x86_64-unknown-linux-musl", "stale")
    yazi_package(sandbox / "fixtures/yazi-x86_64-unknown-linux-musl.zip", "x86_64-unknown-linux-musl", "26.9.1")
    result = native_install(sandbox, "yazi_preset=")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("26.9.1")
    assert "/v26.9.1/yazi-x86_64-unknown-linux-musl.zip" in (sandbox / "requests.log").read_text()


def cc_package(path: Path, version: str):
    payload = executable(version)
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("cc-switch")
        info.size, info.mode = len(payload), 0o755
        archive.addfile(info, io.BytesIO(payload))


def test_cc_manual_build_does_not_let_unrelated_preset_override_pin(sandbox: Path):
    cc_package(sandbox / "tmp/dl/cc-switch-cli-v9.9.9-linux-x64-musl.tar.gz", "wrong generation")
    cc_package(sandbox / "fixtures/cc-switch-cli-v5.11.3-linux-x64-musl.tar.gz", "v5.11.3")
    result = native_install(sandbox, "ccs_preset=")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("v5.11.3")


def test_cc_resolver_receipt_selects_exact_asset_and_verifies_local_digest(sandbox: Path):
    name = "cc-switch-cli-v5.12.0-linux-x64-musl.tar.gz"
    asset = sandbox / "tmp/dl" / name
    cc_package(asset, "resolver-selected-v5.12.0")
    result = native_install(sandbox, "ccs_preset=", CC_SWITCH_ASSET_NAME=name,
                           CC_SWITCH_ASSET_URL=f"https://github.com/SaladDay/cc-switch-cli/releases/download/v5.12.0/{name}",
                           CC_SWITCH_ASSET_SHA256=hashlib.sha256(asset.read_bytes()).hexdigest())
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("resolver-selected-v5.12.0")
    assert not (sandbox / "requests.log").exists()


def test_cc_resolver_rejects_wrong_arch_even_when_preset_exists(sandbox: Path):
    name = "cc-switch-cli-v5.11.3-linux-arm64-musl.tar.gz"
    asset = sandbox / "tmp/dl" / name
    cc_package(asset, "wrong arch")
    result = native_install(sandbox, "ccs_preset=", CC_SWITCH_ASSET_NAME=name,
                           CC_SWITCH_ASSET_URL="https://github.com/asset",
                           CC_SWITCH_ASSET_SHA256=hashlib.sha256(asset.read_bytes()).hexdigest())
    assert result.returncode != 0, "local assets must also match the resolver target architecture"
    assert not (sandbox / "usr/local/bin/cc-switch-real").exists()


@pytest.mark.parametrize("args,arches", [("", ("amd64",)), ("--arch arm64", ("arm64",))])
def test_stage_supports_default_host_and_explicit_arch(sandbox: Path, args: str, arches: tuple[str, ...]):
    dl = stage_fixture(sandbox)
    result = stage(sandbox, args)
    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in dl.glob("mihomo-linux-*.gz")) == [f"mihomo-linux-{arch}-v1.19.33.gz" for arch in arches]


def test_stage_publish_failure_rolls_back_all_previous_payloads(sandbox: Path):
    dl = stage_fixture(sandbox)
    before = {p.name: p.read_bytes() for p in dl.iterdir()}
    prelude = DOWNLOADS + r'''
uname() { echo x86_64; }
mv() {
  case "${*: -1}" in */country.mmdb) return 1;; esac
  command mv "$@"
}
export -f uname mv
unset MIHOMO_VERSION GEODATA_VERSION GEODATA_COMMIT
bash "$AISC_TEST_ROOT/tools/stage-mihomo.sh"
'''
    result = shell(prelude, sandbox)
    assert result.returncode != 0
    assert {p.name: p.read_bytes() for p in dl.iterdir()} == before


def test_stage_verifies_digests_without_gnu_sha256sum_on_host(sandbox: Path):
    dl = stage_fixture(sandbox)
    prelude = DOWNLOADS + r'''
uname() { echo x86_64; }
sha256sum() { return 127; }
export -f uname sha256sum
unset MIHOMO_VERSION GEODATA_VERSION GEODATA_COMMIT
bash "$AISC_TEST_ROOT/tools/stage-mihomo.sh"
'''
    result = shell(prelude, sandbox)
    assert result.returncode == 0, result.stderr
    assert (dl / "country.mmdb").read_bytes() == (sandbox / "fixtures/country.mmdb").read_bytes()
