"""history-worklog 批 1 data-layer tests: record_open/close, list/rename/
archive/delete, reconcile, corrupt-tolerance, and the fail-open contract
(a ledger problem never blocks build_session_exec / terminate_session).
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aisc.application import worklog
from aisc.domain.models import ProcessResult

os.environ.setdefault(
    "AISC_DATA_ROOT",
    os.path.join(os.path.dirname(__file__), "..", ".tmp-test-data"),
)

S1 = "00000000-0000-4000-8000-000000000001"
S2 = "00000000-0000-4000-8000-000000000002"


class WorklogOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reg = Path(self.tmp.name) / "runtime"
        self.reg.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_open_creates_worklog_with_one_session(self):
        wid = worklog.record_open(self.reg, session_id=S1, agent="codex")
        self.assertIsNotNone(wid)
        items = worklog.list_worklogs(self.reg)
        self.assertEqual(len(items), 1)
        entry = items[0]["sessions"][0]
        self.assertEqual(entry["terminal_session_id"], S1)
        self.assertIsNone(entry["closed_at"])
        self.assertIsNone(entry["resume_of_conversation_id"])

    def test_resume_id_is_recorded(self):
        worklog.record_open(self.reg, session_id=S1, agent="codex",
                            resume_conversation_id="conv-9")
        items = worklog.list_worklogs(self.reg)
        self.assertEqual(items[0]["sessions"][0]["resume_of_conversation_id"],
                         "conv-9")

    def test_close_marks_entry(self):
        worklog.record_open(self.reg, session_id=S1, agent="codex")
        self.assertTrue(worklog.record_close(self.reg, session_id=S1,
                                             exit_code=0))
        item = worklog.list_worklogs(self.reg)[0]
        self.assertEqual(item["sessions"][0]["exit_code"], 0)
        self.assertIsNotNone(item["sessions"][0]["closed_at"])

    def test_close_unknown_session_is_false(self):
        worklog.record_open(self.reg, session_id=S1, agent="codex")
        self.assertFalse(worklog.record_close(self.reg, session_id=S2))

    def test_rename_archive_delete(self):
        wid = worklog.record_open(self.reg, session_id=S1, agent="codex")
        self.assertTrue(worklog.rename(self.reg, wid, "我的任务"))
        self.assertEqual(worklog.list_worklogs(self.reg)[0]["title"], "我的任务")
        self.assertTrue(worklog.archive(self.reg, wid))
        self.assertEqual(worklog.list_worklogs(self.reg)[0]["state"], "archived")
        self.assertTrue(worklog.archive(self.reg, wid, archived=False))
        self.assertTrue(worklog.delete(self.reg, wid))
        self.assertEqual(worklog.list_worklogs(self.reg), [])

    def test_corrupt_ledger_quarantined_and_fail_open(self):
        worklog.record_open(self.reg, session_id=S1, agent="codex")
        (self.reg / "worklogs.json").write_text("{not json", encoding="utf-8")
        items = worklog.list_worklogs(self.reg)
        self.assertEqual(items, [])  # fail-open empty, no exception
        quarantine = list(self.reg.glob("worklogs.corrupt-*.json"))
        self.assertEqual(len(quarantine), 1)

    def test_reconcile_files_unattached_sessions(self):
        ws = Path(self.tmp.name) / "ws"
        (ws / "claude" / "projects" / "p").mkdir(parents=True)
        (ws / "claude" / "projects" / "p" / "conv-a.jsonl").write_text(
            "{}", encoding="utf-8")
        (ws / "codex" / "sessions" / "2026" / "09" / "20").mkdir(parents=True)
        (ws / "codex" / "sessions" / "2026" / "09" / "20" /
         "rollout-2026-09-20T10-00-00-conv-b.jsonl").write_text(
            "{}", encoding="utf-8")
        out = worklog.reconcile(self.reg, ws)
        self.assertEqual(out["attached"], 2)
        unfiled = [w for w in worklog.list_worklogs(self.reg)
                   if w["title"] == worklog.UNFILED_TITLE]
        self.assertEqual(len(unfiled), 1)
        self.assertEqual(len(unfiled[0]["sessions"]), 2)
        # second run: nothing new to attach
        out2 = worklog.reconcile(self.reg, ws)
        self.assertEqual(out2["attached"], 0)


class SessionHookTests(unittest.TestCase):
    """build_session_exec records the open; terminate_session closes it.
    Both fail-open: a broken ledger never raises."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reg = Path(self.tmp.name) / "runtime"
        self.reg.mkdir(parents=True)

    def _executor(self, container="ct"):
        ex = MagicMock()
        ex.run_captured.return_value = ProcessResult(
            exit_code=0, stdout=container, stderr="",
            command_not_found=False, timed_out=False)
        return ex

    def test_build_session_exec_records_open_fail_open(self):
        from aisc.application.session import build_session_exec

        ex = self._executor("ct")
        broken = self.reg / "nonexistent-dir"  # ledger path unwritable root
        with patch("aisc.application.session._resolve_running_container",
                   return_value="ct"):
            # no exception even if the ledger write fails internally
            container, argv, env = build_session_exec(
                runtime_id="00000000-0000-4000-8000-00000000aaaa",
                session_id=S1,
                agent="codex",
                executor=ex,
                registry_root=broken,
            )
        self.assertEqual(container, "ct")

    def test_terminate_records_close(self):
        from aisc.application.session import terminate_session

        worklog.record_open(self.reg, session_id=S1, agent="codex")
        ex = MagicMock()

        def routed(argv, timeout=None):
            return ProcessResult(
                exit_code=0,
                stdout=json.dumps({"session_id": S1, "state": "exited",
                                   "exit_code": 0}),
                stderr="", command_not_found=False, timed_out=False)

        ex.run_captured.side_effect = routed
        with patch("aisc.application.session._resolve_running_container",
                   return_value="ct"):
            out = terminate_session("00000000-0000-4000-8000-00000000bbbb",
                                    S1, ex, self.reg)
        self.assertEqual(out["exit_code"], 0)
        items = worklog.list_worklogs(self.reg)
        entry = items[0]["sessions"][0]
        self.assertIsNotNone(entry["closed_at"])


if __name__ == "__main__":
    unittest.main()
