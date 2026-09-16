"""Bundle fetch machinery tests (0.1.0 A3, guide 3.3.3 acceptance matrix).

Every network seam is faked: the API transport serves crafted release JSON,
the download transport streams in-memory archive bytes. Archives are built
IN-TEST via zipfile to the real release layout (single top dir + aisc/ +
aisc-bundle/), so safe-extraction + bundle verification run for real.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from aisc.application.bundle_fetch import (
    BUNDLE_FETCH_ERROR_CONFLICT,
    BUNDLE_FETCH_ERROR_INTEGRITY,
    BUNDLE_FETCH_ERROR_INVALID,
    BUNDLE_FETCH_ERROR_NETWORK,
    BUNDLE_FETCH_ERROR_NOT_FOUND,
    BundleFetchError,
    BundleFetcher,
    _write_manifest,
    bundle_compatible,
)
from aisc.application.resources import find_data_root_bundles

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "packaging"))
import artifact as _art  # noqa: E402  (re-export shim proves the thin wrapper)

CLI_VERSION = "9.9.9"


def build_bundle_files(base: Path, version: str) -> None:
    """Minimal staged bundle passing verify_staged_bundle."""
    b = base / "aisc-bundle"
    (b / "container" / "_bundle" / "plugins").mkdir(parents=True)
    (b / "container" / "downloads").mkdir(parents=True)
    (b / "config").mkdir()
    (b / "vendor").mkdir()
    (b / "VERSION").write_text(version + "\n", encoding="utf-8")
    (b / "README.md").write_text("# T\n", encoding="utf-8")
    (b / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (b / ".dockerignore").write_text("*\n", encoding="utf-8")
    (b / "config" / "versions.env").write_text("NODE_IMAGE=node:20-slim\n", encoding="utf-8")
    (b / "container" / "Dockerfile").write_text(
        "FROM node:20-slim\nCOPY container/_bundle/ /home/\n", encoding="utf-8")
    (b / "container" / "_bundle" / "plugins" / ".keep").write_text("", encoding="utf-8")
    (b / "vendor" / "checksums.txt").write_text(
        hashlib.sha256(b"").hexdigest() + "  container/_bundle/plugins/.keep\n",
        encoding="utf-8")
    _write_manifest(b / "manifest.json", {"schema_version": 1, "compatible_cli_versions": [version]})


def build_release_zip(version: str, plat: str = "windows", arch: str = "x86_64",
                      bundle_version: str | None = None) -> bytes:
    buf = io.BytesIO()
    top = f"AISC-{version}-{plat}-{arch}"
    bv = bundle_version or version
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{top}/aisc", "#!/bin/sh\n")
        for rel, content in (
            ("VERSION", bv + "\n"),
            ("README.md", "# T\n"),
            ("LICENSE", "MIT\n"),
            (".dockerignore", "*\n"),
            ("config/versions.env", "NODE_IMAGE=node:20-slim\n"),
            ("container/Dockerfile", "FROM node:20-slim\nCOPY container/_bundle/ /home/\n"),
            ("container/_bundle/plugins/.keep", ""),
            ("vendor/checksums.txt",
             hashlib.sha256(b"").hexdigest() + "  container/_bundle/plugins/.keep\n"),
        ):
            zf.writestr(f"{top}/aisc-bundle/{rel}", content)
        manifest = '{\n  "schema_version": 1,\n  "compatible_cli_versions": '
        manifest += json.dumps(sorted([bv])) + '\n}\n'
        zf.writestr(f"{top}/aisc-bundle/manifest.json", manifest)
        zf.writestr(f"{top}/aisc-bundle/container/downloads/.keep", "")
    return buf.getvalue()


class FakeApi:
    """JSON transport serving one crafted releases page."""

    def __init__(self, pages: list, *, fail: str | None = None, rate_limited: bool = False):
        self.pages = pages
        self.fail = fail
        self.rate_limited = rate_limited

    def __call__(self, url, headers, timeout):
        if self.fail:
            raise BundleFetchError(BUNDLE_FETCH_ERROR_NETWORK, self.fail)
        if self.rate_limited:
            return 403, {"x-ratelimit-remaining": "0"}, {"message": "rate limit exceeded"}
        return 200, {}, self.pages


def fake_download(data: bytes):
    def dl(url, headers, timeout, sink):
        sink(data)
        return 200
    return dl


def releases_page(assets: dict) -> list:
    return [{
        "tag_name": "v0",
        "assets": [
            {"name": name, "digest": meta["digest"], "size": meta.get("size", 1),
             "url": f"https://x/{name}", "browser_download_url": f"https://x/{name}"}
            for name, meta in assets.items()
        ],
    }]


class FetchMatrix(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="bf-"))
        self.data_root = self.td / "data"
        self.data_root.mkdir()

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def fetcher(self, api: FakeApi, data: bytes) -> BundleFetcher:
        return BundleFetcher(transport=api, download=fake_download(data))

    def page_for(self, version: str, data: bytes, plat="windows", arch="x86_64"):
        name = f"AISC-{version}-{plat}-{arch}.zip"
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        return releases_page({name: {"digest": digest}})

    def test_happy_path_installs_and_is_idempotent(self):
        data = build_release_zip(CLI_VERSION)
        f = self.fetcher(FakeApi(self.page_for(CLI_VERSION, data)), data)
        r = f.fetch(self.data_root, CLI_VERSION)
        self.assertEqual(r["status"], "installed")
        self.assertTrue((self.data_root / "bundles" / CLI_VERSION / "aisc-bundle" / "VERSION").is_file())
        r2 = f.fetch(self.data_root, CLI_VERSION)
        self.assertEqual(r2["status"], "already-installed")

    def test_digest_mismatch_fails_closed_installs_nothing(self):
        data = build_release_zip(CLI_VERSION)
        bad = self.page_for(CLI_VERSION, data)
        bad[0]["assets"][0]["digest"] = "sha256:" + "0" * 64
        f = self.fetcher(FakeApi(bad), data)
        with self.assertRaises(BundleFetchError) as cm:
            f.fetch(self.data_root, CLI_VERSION)
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_INTEGRITY)
        self.assertFalse((self.data_root / "bundles" / CLI_VERSION).exists())
        self.assertEqual(f.installed_versions(self.data_root), [])

    def test_version_not_found_lists_recent(self):
        data = build_release_zip("1.0.0")
        f = self.fetcher(FakeApi(self.page_for("1.0.0", data)), data)
        with self.assertRaises(BundleFetchError) as cm:
            f.fetch(self.data_root, "2.0.0")
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_NOT_FOUND)
        self.assertIn("1.0.0", cm.exception.message)

    def test_network_error_is_fail_closed(self):
        # Fake transports raise RAW failures; the enrichment (three escape
        # hatches) is the default_transport's job — pinned separately below.
        data = build_release_zip(CLI_VERSION)
        f = self.fetcher(FakeApi(None, fail="boom"), data)
        with self.assertRaises(BundleFetchError) as cm:
            f.fetch(self.data_root, CLI_VERSION)
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_NETWORK)
        self.assertEqual(f.installed_versions(self.data_root), [])

    def test_default_transport_copy_carries_three_escape_hatches(self):
        from aisc.application.bundle_fetch import _network_error_copy

        copy = _network_error_copy("boom")
        for needle in ("--from-file", "--aisc-root", "AISC_GH_API_TOKEN"):
            self.assertIn(needle, copy)

    def test_rate_limit_is_network_failure(self):
        data = build_release_zip(CLI_VERSION)
        f = self.fetcher(FakeApi(self.page_for(CLI_VERSION, data), rate_limited=True), data)
        with self.assertRaises(BundleFetchError) as cm:
            f.fetch(self.data_root, CLI_VERSION)
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_NETWORK)
        self.assertIn("rate limited", cm.exception.message)

    def test_asset_without_api_digest_refused(self):
        data = build_release_zip(CLI_VERSION)
        page = self.page_for(CLI_VERSION, data)
        page[0]["assets"][0]["digest"] = ""
        f = self.fetcher(FakeApi(page), data)
        with self.assertRaises(BundleFetchError) as cm:
            f.fetch(self.data_root, CLI_VERSION)
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_INTEGRITY)

    def test_corrupt_archive_is_invalid(self):
        f = self.fetcher(FakeApi(self.page_for(CLI_VERSION, b"junk")), b"junk")
        with self.assertRaises(BundleFetchError) as cm:
            f.fetch(self.data_root, CLI_VERSION)
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_INVALID)

    def test_manifest_gate_rejects_foreign_cli_unless_allow_mismatch(self):
        data = build_release_zip("1.2.3")  # asset+bundle are 1.2.3; running CLI is 9.9.9
        f = self.fetcher(FakeApi(self.page_for("1.2.3", data)), data)
        with self.assertRaises(BundleFetchError) as cm:
            f.fetch(self.data_root, CLI_VERSION, version="1.2.3")
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_CONFLICT)
        self.assertIn("manifest", cm.exception.message)
        r = f.fetch(self.data_root, CLI_VERSION, version="1.2.3", allow_mismatch=True)
        self.assertEqual(r["status"], "installed")

    def test_from_file_requires_sha_and_verifies_it(self):
        data = build_release_zip(CLI_VERSION)
        arch = self.td / "AISC-9.9.9-windows-x86_64.zip"
        arch.write_bytes(data)
        f = BundleFetcher()  # no transport needed for the offline path
        with self.assertRaises(BundleFetchError) as cm:
            f.fetch(self.data_root, CLI_VERSION, from_file=arch)
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_INTEGRITY)
        with self.assertRaises(BundleFetchError):
            f.fetch(self.data_root, CLI_VERSION, from_file=arch, sha256="0" * 64)
        good = hashlib.sha256(data).hexdigest()
        r = f.fetch(self.data_root, CLI_VERSION, from_file=arch, sha256=good)
        self.assertEqual(r["status"], "installed")

    def test_sweep_tmp_removes_crashed_leftovers(self):
        stray = self.data_root / "bundles" / ".tmp-crashed"
        (stray / "junk").mkdir(parents=True)
        removed = BundleFetcher().sweep_tmp(self.data_root)
        self.assertIn(".tmp-crashed", removed)
        self.assertFalse(stray.exists())

    def test_remove_refuses_active_root(self):
        data = build_release_zip(CLI_VERSION)
        f = self.fetcher(FakeApi(self.page_for(CLI_VERSION, data)), data)
        f.fetch(self.data_root, CLI_VERSION)
        active = self.data_root / "bundles" / CLI_VERSION / "aisc-bundle"
        with self.assertRaises(BundleFetchError) as cm:
            f.remove(self.data_root, CLI_VERSION, active)
        self.assertEqual(cm.exception.code, BUNDLE_FETCH_ERROR_CONFLICT)
        r = f.remove(self.data_root, CLI_VERSION, active_root=None)
        self.assertEqual(r["status"], "removed")


class CompatGate(unittest.TestCase):
    def test_missing_manifest_incompatible(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(bundle_compatible(Path(td), "1.0")[0], False)

    def test_version_must_be_exact_member(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            _write_manifest(b / "manifest.json", {"schema_version": 1, "compatible_cli_versions": ["1.0"]})
            ok, _ = bundle_compatible(b, "1.0")
            self.assertTrue(ok)
            ok, reason = bundle_compatible(b, "1.1")
            self.assertFalse(ok)
            self.assertIn("1.1", reason)


class DataRootLayer(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="bl-"))

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def _install(self, ver: str, allow: list | None = None) -> Path:
        target = self.td / "data" / "bundles" / ver / "aisc-bundle"
        build_bundle_files(target.parent, ver)
        if allow is not None:
            _write_manifest(target / "manifest.json",
                            {"schema_version": 1, "compatible_cli_versions": allow})
        return target

    def test_compatible_bundle_found_incompatible_skipped_with_note(self):
        from aisc import __version__ as cli
        good = self._install("1.0", allow=["1.0", cli])
        bad = self._install("0.1", allow=["0.1"])
        roots, skipped = find_data_root_bundles(self.td / "data")
        self.assertEqual([r.name for r in roots], [good.name])
        self.assertEqual(len(skipped), 1)
        self.assertIn(str(bad), skipped[0])
        self.assertIn("manifest", skipped[0])

    def test_find_returns_compatible_first(self):
        self._install("1.0", allow=["1.0", "9.9.9", "0.1.0.dev0"])
        roots, skipped = find_data_root_bundles(self.td / "data")
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0].parent.name, "1.0")
        self.assertEqual(skipped, [])


class PackagingReexport(unittest.TestCase):
    def test_thin_wrapper_symbols_resolve(self):
        for name in ("_write_manifest", "verify_staged_bundle", "safe_extract_archive",
                     "validate_tar_members", "validate_zip_members", "_sha256_file"):
            self.assertTrue(hasattr(_art, name), name)
        self.assertEqual(_art.verify_staged_bundle.__module__, "aisc.application.bundle_fetch")


if __name__ == "__main__":
    unittest.main()
