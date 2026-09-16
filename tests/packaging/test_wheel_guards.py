"""Artifact thin-shape guards (0.1.0 A6, guide 3.4.4).

Builds a real wheel in a temp dir and pins BOTH directions: what MUST be
inside (package VERSION, console-script entry point, license file) and
what MUST NOT (packaging/, tests/, vendor/, container/ payloads — the
wheel stays a thin pure-Python artifact; binary ride-alongs are a license
and size regression, see guide 4.2 / D-3).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _build_wheel(outdir: Path) -> Path:
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(outdir)],
        cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-800:]
    wheels = sorted(outdir.glob("*.whl"))
    assert wheels, "no wheel produced"
    return wheels[0]


class WheelShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory(prefix="wheel-guard-")
        cls.wheel = _build_wheel(Path(cls.td.name))
        with zipfile.ZipFile(cls.wheel) as zf:
            cls.names = zf.namelist()

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def test_package_version_file_is_inside(self):
        self.assertTrue(any(n == "aisc/VERSION" for n in self.names),
                        "aisc/VERSION must ship as package data")

    def test_console_script_entry_point_declares_aisc(self):
        with zipfile.ZipFile(self.wheel) as zf:
            ep = [n for n in self.names if n.endswith("entry_points.txt")]
            self.assertTrue(ep, "entry_points.txt missing")
            content = zf.read(ep[0]).decode("utf-8")
        self.assertIn("aisc = aisc.cli.main:main", content)

    def test_license_file_is_inside(self):
        self.assertTrue(
            any("licenses/LICENSE" in n or n == "LICENSE" for n in self.names),
            "license must ride the wheel (SPDF license-files)")

    def test_no_payload_dirs_ride_the_wheel(self):
        forbidden_dirs = ("packaging/", "tests/", "vendor/", "container/", "_bundle/")
        for n in self.names:
            for bad in forbidden_dirs:
                self.assertFalse(
                    n.startswith(bad) or f"/{bad}" in n,
                    f"forbidden payload in wheel: {n}")

    def test_no_binary_assets_ride_the_wheel(self):
        markers = ("mihomo", "geoip.metadb", "geosite.dat", "country.mmdb")
        for n in self.names:
            low = n.lower()
            for m in markers:
                self.assertNotIn(m, low, f"binary payload leaked: {n}")


if __name__ == "__main__":
    unittest.main()
