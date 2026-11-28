"""b3: Windows 升级验收脚本的进程清理竞态回归用例.

The upgrade acceptance script closes the Workbench window and then waits for
the process.  The old code force-stopped the process without waiting and
judged cleanup success from a bare ``$app.HasExited`` state query.  The
process can exit on its own between the graceful timeout and the forced
stop, so cleanup success must be decided by an observed exit, and an actual
termination failure must stay a failure.

Static contract tests, matching the existing Linux-only installer tests:
the unit-test runners have no PowerShell runtime.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "test-windows-upgrade.ps1"
_HELPER = "Stop-TestApplication"


class WindowsUpgradeCleanupRaceTests(unittest.TestCase):
    """The upgrade script must not report cleanup success before exit."""

    @classmethod
    def setUpClass(cls):
        cls.text = _SCRIPT.read_text(encoding="utf-8")

    def _helper_body(self) -> str:
        marker = f"function {_HELPER}"
        self.assertIn(
            marker,
            self.text,
            f"{_HELPER} must own the confirmed-exit cleanup",
        )
        start = self.text.index(marker)
        rest = self.text[start:]
        top_level_try = re.search(r"^try \{", rest, re.MULTILINE)
        return rest[: top_level_try.start()] if top_level_try else rest

    def test_helper_waits_for_exit_after_forced_stop(self):
        body = self._helper_body()
        force = body.index("Stop-Process")
        self.assertGreater(
            body.find("WaitForExit", force),
            force,
            "cleanup must wait for the process after Stop-Process -Force; a "
            "bare Stop-Process races with a process that is already exiting",
        )

    def test_helper_only_succeeds_on_observed_exit(self):
        body = self._helper_body()
        force = body.index("Stop-Process")
        exit_check = body.index("HasExited", force)
        self.assertGreater(
            body.find("throw", exit_check),
            exit_check,
            "cleanup must throw unless the process has actually exited, "
            "preserving an actual termination failure",
        )
        self.assertRegex(
            body,
            r"if \(-not \$target\.HasExited\)\s*\{\s*throw",
            "the helper must gate success on an observed $target.HasExited "
            "exit, not on a state query alone",
        )

    def test_main_path_uses_confirmed_cleanup(self):
        start = self.text.index("Installed Workbench creates a native window")
        end = self.text.index("# Workbench may legitimately update", start)
        block = self.text[start:end]
        self.assertIn(f"{_HELPER} $app", block)
        self.assertNotIn("Stop-Process", block)
        self.assertNotIn("CloseMainWindow", block)

    def test_finally_path_uses_confirmed_cleanup(self):
        block = self.text[self.text.index("} finally {"):]
        self.assertIn(f"{_HELPER} $app", block)
        self.assertNotIn("Stop-Process", block)
        self.assertIn(
            "'FAIL'",
            block,
            "a cleanup failure must be recorded as FAIL, not reported as success",
        )


if __name__ == "__main__":
    unittest.main()
