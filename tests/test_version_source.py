"""Version single-source contract tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import aisc


class VersionSourceTests(unittest.TestCase):
    def test_package_version_matches_version_file(self) -> None:
        expected = (SRC / "aisc" / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(aisc.__version__, expected)

    def test_no_duplicate_project_version_in_versions_env(self) -> None:
        versions_env = (PROJECT_ROOT / "config" / "versions.env").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("AISC_VERSION=", versions_env)

    def test_package_init_has_no_hardcoded_release(self) -> None:
        package_init = (SRC / "aisc" / "__init__.py").read_text(encoding="utf-8")
        current = (SRC / "aisc" / "VERSION").read_text(encoding="utf-8").strip()
        self.assertNotIn(current, package_init)

    def test_wheel_packages_canonical_version_file(self) -> None:
        # A2: VERSION is package data inside src/aisc/ (guide 3.2) — the
        # data-files form landed at <sys.prefix>/aisc/VERSION (outside
        # site-packages; --user installs missed it entirely).
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('[tool.setuptools.package-data]\naisc = ["VERSION"]', pyproject)
        self.assertTrue((SRC / "aisc" / "VERSION").is_file(), "src/aisc/VERSION must exist")
        self.assertFalse((PROJECT_ROOT / "VERSION").exists(), "root VERSION must be gone")


class DistNameFallbackTests(unittest.TestCase):
    """A1 (guide D-1): the metadata fallback must query the DISTRIBUTION
    name (aisc-cli), never the import name — a stale install of the dormant
    third-party ``aisc`` package would otherwise answer with a stranger's
    version, and the pre-rename fallback would return 0+unknown forever."""

    def test_dist_name_constant(self) -> None:
        self.assertEqual(aisc.DIST_NAME, "aisc-cli")

    def test_fallback_queries_distribution_name_and_returns_real_version(self) -> None:
        from unittest import mock

        from importlib import metadata as _metadata

        def fake_version(name: str) -> str:
            queried.append(name)
            if name == "aisc-cli":
                return "9.9.9"
            raise _metadata.PackageNotFoundError(name)

        queried: list[str] = []
        # Force every VERSION-file candidate to miss so the fallback runs.
        real_read_text = Path.read_text

        def missing(self: Path, *args, **kwargs):  # noqa: ANN001, ANN002
            if self.name == "VERSION":
                raise OSError("forced miss")
            return real_read_text(self, *args, **kwargs)

        with mock.patch.object(Path, "read_text", missing), \
                mock.patch.object(_metadata, "version", fake_version):
            self.assertEqual(aisc._read_version(), "9.9.9")
        self.assertEqual(queried, ["aisc-cli"])


class TestWorkbenchCapabilities(unittest.TestCase):
    """Workbench capability negotiation (05-cli-gui-contract.md §四)."""

    def test_version_dict_advertises_implemented_capabilities(self):
        from aisc.domain.models import VersionInfo, WORKBENCH_CAPABILITIES
        info = VersionInfo(cli_version="x", python_version="y")
        caps = info.to_dict()["capabilities"]
        assert caps == WORKBENCH_CAPABILITIES
        # S0.4 ships runtime + session + providerStatus.
        assert caps["runtime"] == "aisc.runtime/v1"
        assert caps["session"] == "aisc.session/v1"
        assert caps["providerStatus"] == "aisc.provider-status/v1"

    def test_version_json_envelope_carries_capabilities(self):
        import contextlib
        import io
        import json
        from aisc.cli.main import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                main(["version", "--format", "json"])
        assert cm.exception.code == 0
        caps = json.loads(buf.getvalue())["data"]["capabilities"]
        assert {"runtime", "session", "providerStatus"} <= set(caps.keys())


if __name__ == "__main__":
    unittest.main()
