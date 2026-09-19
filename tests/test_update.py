"""``aisc update`` tests (0.1.0 A4, D-7 acceptance matrix).

Form detection, check-plan (final-only channel), the frozen replace dance
(rename dance on Windows, os.replace elsewhere), rollback leftovers, the
downgrade guard, and the pip/source refusals. Network seams faked via the
bundle_fetch fake transports; archives fabricated to the real layout.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from aisc.application.bundle_fetch import ARCH_TAG, BundleFetcher, _PLAT_TAG
from aisc.application.update import (
    UPDATE_ERROR_USAGE,
    UpdateError,
    build_check_report,
    detect_install_form,
    perform_update,
    sweep_old_files,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_bundle_fetch import FakeApi, _reg_entry, fake_download, releases_page  # noqa: E402

CUR = "1.0.0"


def build_update_zip(version: str, exe_payload: bytes = b"NEW-EXE") -> bytes:
    buf = io.BytesIO()
    top = f"AISC-{version}-{_PLAT_TAG}-{ARCH_TAG}"
    # perform_update looks for aisc.exe on Windows, bare `aisc` elsewhere —
    # the archive must carry the exe under the RUNTIME platform's name, the
    # dir/asset tags must match resolve_asset's runtime _PLAT_TAG/ARCH_TAG
    # defaults, and every member needs the release-shape type bits (_reg_entry).
    exe_name = "aisc.exe" if os.name == "nt" else "aisc"
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(_reg_entry(f"{top}/{exe_name}", 0o755), exe_payload.decode("latin-1"))
        for rel, content in (
            ("VERSION", version + "\n"),
            ("README.md", "# T\n"),
            ("LICENSE", "MIT\n"),
            (".dockerignore", "*\n"),
            ("config/versions.env", "NODE_IMAGE=node:20-slim\n"),
            ("container/Dockerfile", "FROM node:20-slim\nCOPY container/_bundle/ /home/\n"),
            ("container/_bundle/plugins/.keep", ""),
            ("container/downloads/.keep", ""),
            ("vendor/checksums.txt",
             hashlib.sha256(b"").hexdigest() + "  container/_bundle/plugins/.keep\n"),
        ):
            zf.writestr(_reg_entry(f"{top}/aisc-bundle/{rel}"), content)
        manifest = ('{\n  "schema_version": 1,\n  "compatible_cli_versions": '
                    + json.dumps(sorted([version])) + '\n}\n')
        zf.writestr(_reg_entry(f"{top}/aisc-bundle/manifest.json"), manifest)
    return buf.getvalue()


def fake_fetcher_with(data: bytes, version: str, tags=("v0.1.0", "v1.0.0", "v1.2.0")) -> BundleFetcher:
    name = f"AISC-{version}-{_PLAT_TAG}-{ARCH_TAG}.zip"
    pages = [{
        "tag_name": t,
        "assets": ([{"name": name, "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
                     "url": f"https://x/{name}", "browser_download_url": f"https://x/{name}"}]
                   if t == f"v{version}" else []),
    } for t in tags]
    # also list the target's archive under its own tag with the exe asset
    return BundleFetcher(transport=FakeApi(pages), download=fake_download(data))


class FormDetection(unittest.TestCase):
    def test_pip_form_by_site_packages(self):
        form = detect_install_form(frozen=False,
                                   package_file=r"C:\py\Lib\site-packages\aisc\__init__.py")
        self.assertEqual(form["form"], "pip")

    def test_source_form(self):
        form = detect_install_form(frozen=False,
                                   package_file=r"E:\repo\src\aisc\__init__.py")
        self.assertEqual(form["form"], "source")

    def test_frozen_with_adjacent_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "aisc.exe"
            exe.write_bytes(b"old")
            (Path(td) / "aisc-bundle").mkdir()
            form = detect_install_form(frozen=True, executable=str(exe))
            self.assertEqual(form["form"], "frozen")
            self.assertEqual(form["adjacent_bundle"], str(Path(td) / "aisc-bundle"))

    def test_frozen_without_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "aisc.exe"
            form = detect_install_form(frozen=True, executable=str(exe))
            self.assertIsNone(form["adjacent_bundle"])


class CheckPlan(unittest.TestCase):
    def test_latest_final_ignores_prereleases(self):
        data = build_update_zip("1.2.0")
        pages = [
            {"tag_name": "v1.3.0-dev1", "assets": []},
            {"tag_name": "v1.2.0", "assets": [
                {"name": "AISC-1.2.0-windows-x86_64.zip",
                 "digest": "sha256:" + hashlib.sha256(data).hexdigest()}]},
            {"tag_name": "v1.0.0", "assets": []},
        ]
        f = BundleFetcher(transport=FakeApi(pages), download=fake_download(data))
        self.assertEqual(f.latest_final_version(), "1.2.0")

    def test_check_frozen_names_replace_plan(self):
        data = build_update_zip("1.2.0")
        f = fake_fetcher_with(data, "1.2.0")
        with tempfile.TemporaryDirectory() as td:
            form = detect_install_form(frozen=True, executable=str(Path(td) / "aisc.exe"))
            report = build_check_report(cli_version=CUR, form=form, fetcher=f)
        self.assertEqual(report["latest_final"], "1.2.0")
        self.assertTrue(report["update_available"])
        self.assertIn("replace exe", report["action"])

    def test_check_up_to_date_when_latest_equals_current(self):
        data = build_update_zip(CUR)
        f = fake_fetcher_with(data, CUR, tags=("v0.1.0", "v1.0.0"))
        with tempfile.TemporaryDirectory() as td:
            form = detect_install_form(frozen=True, executable=str(Path(td) / "aisc.exe"))
            report = build_check_report(cli_version=CUR, form=form, fetcher=f)
        self.assertFalse(report["update_available"])

    def test_check_pip_and_source_never_touch_network(self):
        class ExplodingFetcher(BundleFetcher):
            def latest_final_version(self):
                raise AssertionError("network touched for a local-form check")

        for pkg in (r"C:\py\Lib\site-packages\aisc\__init__.py", r"E:\repo\src\aisc\__init__.py"):
            form = detect_install_form(frozen=False, package_file=pkg)
            report = build_check_report(cli_version=CUR, form=form, fetcher=ExplodingFetcher())
            self.assertIn(form["form"], ("pip", "source"))


class PerformUpdate(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="upd-"))
        self.exe = self.td / "aisc.exe"
        self.exe.write_bytes(b"OLD-EXE")
        (self.td / "aisc-bundle").mkdir()
        (self.td / "aisc-bundle" / "VERSION").write_text(CUR + "\n")

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def _form(self):
        return detect_install_form(frozen=True, executable=str(self.exe))

    def test_from_file_replaces_exe_and_bundle_with_rollback_copy(self):
        data = build_update_zip("1.2.0")
        arch = self.td / f"AISC-1.2.0-{_PLAT_TAG}-{ARCH_TAG}.zip"
        arch.write_bytes(data)
        f = BundleFetcher()
        r = perform_update(cli_version=CUR, form=self._form(), fetcher=f,
                           version="1.2.0", from_file=arch,
                           sha256=hashlib.sha256(data).hexdigest(), workdir=self.td)
        self.assertEqual(r["status"], "updated")
        self.assertEqual(r["to_version"], "1.2.0")
        self.assertEqual(self.exe.read_bytes(), b"NEW-EXE")
        if os.name == "nt":
            old = Path(r["preserved_old_exe"])
            self.assertTrue(old.is_file())
            self.assertEqual(old.read_bytes(), b"OLD-EXE")
            self.assertIn(".old-", old.name)

    def test_online_path_retired_points_to_new_channels(self):
        """D-8 (2026-09-19): releases ship the Workbench installer only —
        the online sidecar-swap is retired with a redirective error; the
        exe is never touched."""
        f = fake_fetcher_with(build_update_zip("1.2.0"), "1.2.0")
        with self.assertRaises(UpdateError) as cm:
            perform_update(cli_version=CUR, form=self._form(), fetcher=f, workdir=self.td)
        self.assertEqual(cm.exception.code, UPDATE_ERROR_USAGE)
        self.assertIn("pip install -U", str(cm.exception))
        self.assertEqual(self.exe.read_bytes(), b"OLD-EXE")

    def test_up_to_date_is_a_no_op(self):
        data = build_update_zip(CUR)
        f = fake_fetcher_with(data, CUR, tags=("v0.1.0", "v1.0.0"))
        r = perform_update(cli_version=CUR, form=self._form(), fetcher=f, workdir=self.td)
        self.assertEqual(r["status"], "up-to-date")
        self.assertEqual(self.exe.read_bytes(), b"OLD-EXE")

    def test_from_file_without_sha_rejected(self):
        data = build_update_zip("1.2.0")
        arch = self.td / f"AISC-1.2.0-{_PLAT_TAG}-{ARCH_TAG}.zip"
        arch.write_bytes(data)
        with self.assertRaises(UpdateError) as cm:
            perform_update(cli_version=CUR, form=self._form(), fetcher=BundleFetcher(),
                           version="1.2.0", from_file=arch, workdir=self.td)
        self.assertEqual(cm.exception.code, UPDATE_ERROR_USAGE)
        self.assertEqual(self.exe.read_bytes(), b"OLD-EXE")

    def test_bad_digest_rejected_nothing_replaced(self):
        data = build_update_zip("1.2.0")
        arch = self.td / f"AISC-1.2.0-{_PLAT_TAG}-{ARCH_TAG}.zip"
        arch.write_bytes(data)
        with self.assertRaises(UpdateError):
            perform_update(cli_version=CUR, form=self._form(), fetcher=BundleFetcher(),
                           version="1.2.0", from_file=arch, sha256="0" * 64, workdir=self.td)
        self.assertEqual(self.exe.read_bytes(), b"OLD-EXE")

    def test_pip_form_refused_with_guidance(self):
        with self.assertRaises(UpdateError) as cm:
            perform_update(cli_version=CUR, form={"form": "pip"},
                           fetcher=BundleFetcher())
        self.assertIn("pipx upgrade aisc-cli", cm.exception.message)

    def test_source_form_refused(self):
        with self.assertRaises(UpdateError) as cm:
            perform_update(cli_version=CUR, form={"form": "source"},
                           fetcher=BundleFetcher())
        self.assertIn("git", cm.exception.message)

    def test_sweep_removes_stale_old_files(self):
        stale = self.td / "aisc.old-111.exe"
        stale.write_bytes(b"x")
        stale_dir = self.td / "aisc-bundle.old-111"
        stale_dir.mkdir()
        removed = sweep_old_files(self.td)
        self.assertIn("aisc.old-111.exe", removed)
        self.assertFalse(stale.exists())
        self.assertFalse(stale_dir.exists())


if __name__ == "__main__":
    unittest.main()
