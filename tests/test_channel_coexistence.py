"""A8 channel-coexistence tests (guide 3.5.5)."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from aisc.application.doctor import _check_channel_confusion, _check_platform_support
from aisc.application.version import _install_channel
from aisc.domain.models import VersionInfo


class InstallChannelTests(unittest.TestCase):
    def test_text_carries_channel_but_json_dict_does_not(self):
        info = VersionInfo(cli_version="1", python_version="2", install_channel="pip/pipx (site-packages)")
        text = info.to_text()
        self.assertIn("Install channel", text)
        self.assertIn("pip/pipx", text)
        # JSON contract: 6 fixed keys + capabilities, NO channel key
        self.assertNotIn("install_channel", info.to_dict())

    def test_channel_frozen_source_bundlefetch(self):
        with mock.patch("sys.frozen", True, create=True):
            self.assertIn("frozen", _install_channel(None))
        self.assertIn("source", _install_channel(Path("/repo/checkout")))
        self.assertIn(
            "bundle fetch",
            _install_channel(Path("/data/bundles/0.1.0/aisc-bundle")))


class ChannelConfusionTests(unittest.TestCase):
    def test_multiple_hits_warn_with_paths(self):
        with mock.patch.dict(os.environ, {"PATH": "/a" + os.pathsep + "/b"}),              mock.patch.object(Path, "is_file", lambda self: self.name == "aisc"),              mock.patch.object(Path, "stat", lambda self: mock.Mock(st_size=1024)):
            r = _check_channel_confusion()
        self.assertEqual(r.name, "channel-confusion")
        self.assertIn("2 aisc executables", r.message)
        self.assertIn("warn", str(r.status))

    def test_single_hit_passes(self):
        with mock.patch.dict(os.environ, {"PATH": "/only"}),              mock.patch.object(Path, "is_file", lambda self: self.name == "aisc"),              mock.patch.object(Path, "stat", lambda self: mock.Mock(st_size=1024)):
            r = _check_channel_confusion()
        self.assertEqual(str(r.status), "pass")


class PlatformSupportTests(unittest.TestCase):
    def test_supported_combo_passes(self):
        with mock.patch("platform.system", return_value="Windows"),              mock.patch("platform.machine", return_value="AMD64"):
            self.assertEqual(str(_check_platform_support().status), "pass")

    def test_unsupported_combo_warns(self):
        with mock.patch("platform.system", return_value="Linux"),              mock.patch("platform.machine", return_value="aarch64"):
            r = _check_platform_support()
        self.assertEqual(str(r.status), "warn")
        self.assertIn("unsupported", r.message)


class ScriptGuards(unittest.TestCase):
    """The pipx-shim ownership guards are shell; pin their presence and
    shape (the behavior matrix lives in the scripts' own comments)."""

    def test_install_sh_guards_foreign_symlink(self):
        s = (Path(__file__).resolve().parents[1] / "packaging" / "install.sh").read_text(encoding="utf-8")
        self.assertIn("never rm a link we don't own", s)
        self.assertIn("Keeping foreign", s)

    def test_uninstall_sh_guards_foreign_symlink(self):
        s = (Path(__file__).resolve().parents[1] / "packaging" / "uninstall.sh").read_text(encoding="utf-8")
        self.assertIn("pipx shims are symlinks too", s)
        self.assertIn("not our install", s)


import os  # noqa: E402  (used inside mocked-env tests)

if __name__ == "__main__":
    unittest.main()
