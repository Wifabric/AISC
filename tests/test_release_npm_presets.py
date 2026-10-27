"""Release bundles must not quietly ship stale ignored native companions."""
import io
import json
import tarfile

import pytest

from aisc.application import bundle_fetch
from aisc.application.tool_versions import _npm_latest


def package(path, name, version, optional=None):
    body = json.dumps({"name": name, "version": version,
                       "optionalDependencies": optional or {}}).encode()
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("package/package.json")
        member.size = len(body)
        archive.addfile(member, io.BytesIO(body))


@pytest.fixture
def preset(tmp_path):
    dl = tmp_path / "container" / "downloads"
    dl.mkdir(parents=True)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "versions.env").write_text("CODEX_VERSION=1.2.3\n")
    package(dl / "codex-1.2.3.tgz", "@openai/codex", "1.2.3",
            {"@openai/codex-linux-x64": "npm:@openai/codex@1.2.3-linux-x64"})
    package(dl / "codex-linux-x64-1.2.3-linux-x64.tgz", "@openai/codex", "1.2.3-linux-x64")
    return tmp_path, dl


def test_alias_companion_and_optional_online_fallback(preset):
    root, dl = preset
    assert bundle_fetch._verify_npm_presets(root) == []
    (dl / "codex-linux-x64-1.2.3-linux-x64.tgz").unlink()
    assert bundle_fetch._verify_npm_presets(root) == []


def test_rejects_ignored_old_companion_even_alongside_correct_one(preset):
    root, dl = preset
    package(dl / "codex-linux-x64-1.1.0-linux-x64.tgz", "@openai/codex", "1.1.0-linux-x64")
    assert any("stale" in e for e in bundle_fetch._verify_npm_presets(root))


def test_rejects_renamed_or_damaged_companion(preset):
    root, dl = preset
    path = dl / "codex-linux-x64-1.2.3-linux-x64.tgz"
    package(path, "@openai/codex", "1.1.0-linux-x64")
    assert any("metadata" in e for e in bundle_fetch._verify_npm_presets(root))
    path.write_bytes(b"broken gzip")
    assert bundle_fetch._verify_npm_presets(root)


@pytest.mark.parametrize("damage", ["crc", "truncate8", "truncate32", "deflate"])
def test_rejects_companion_with_intact_metadata_but_damaged_gzip_tail(preset, damage):
    root, dl = preset
    path = dl / "codex-linux-x64-1.2.3-linux-x64.tgz"
    data = bytearray(path.read_bytes())
    if damage == "crc":
        data[-8] ^= 1
    elif damage == "deflate":
        # Skip the optional gzip filename and select reserved DEFLATE BTYPE=3.
        offset = 10
        if data[3] & 8:
            offset = data.index(0, offset) + 1
        data[offset] = (data[offset] & ~6) | 6
    else:
        del data[-int(damage.removeprefix("truncate")):]
    path.write_bytes(data)
    assert bundle_fetch._verify_npm_presets(root)


def test_factory_pin_mismatch_and_missing_main(preset):
    root, dl = preset
    (root / "config" / "versions.env").write_text("CODEX_VERSION=2.0.0\n")
    assert bundle_fetch._verify_npm_presets(root)
    (dl / "codex-1.2.3.tgz").unlink()
    assert bundle_fetch._verify_npm_presets(root)


@pytest.mark.parametrize("latest", ["2.0.0-beta.1", "2.0.0+canary", "latest", None, 123])
def test_latest_tag_does_not_promote_nonstable_version(latest):
    assert _npm_latest("pkg", lambda _: {"dist-tags": {"latest": latest}}) is None


def test_latest_tag_wins_over_higher_beta():
    metadata = {"dist-tags": {"latest": "1.2.3", "beta": "99.0.0-beta.1"},
                "versions": {"1.2.3": {"engines": {"node": ">=22"}}}}
    assert _npm_latest("pkg", lambda _: metadata) == {"latest": "1.2.3", "node": ">=22"}
