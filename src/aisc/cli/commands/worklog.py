"""``aisc worklog`` — per-workspace PTY session ledger (D-12 批 1).

All commands take ``--workspace``; the ledger lives at
``<ws>/runtime/worklogs.json``. Read-only over the provider transcripts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from aisc.cli.output import JsonlEmitter


def _registry(workspace: str) -> Path:
    from aisc.application.data_root import DataRootResolver

    resolved = DataRootResolver().resolve(Path(workspace).resolve())
    return resolved.workspace_dir / "runtime"


def _ws_dir(workspace: str) -> Path:
    from aisc.application.data_root import DataRootResolver

    return DataRootResolver().resolve(Path(workspace).resolve()).workspace_dir


def cmd_worklog_list(workspace: str) -> Dict[str, Any]:
    from aisc.application import worklog

    return {
        "schema_version": worklog.WORKLOG_SCHEMA,
        "workspace": workspace,
        "worklogs": worklog.list_worklogs(_registry(workspace)),
    }


def print_worklog_list(data: Dict[str, Any]) -> None:
    for w in data.get("worklogs", []):
        title = w.get("title") or "(未命名)"
        state = w.get("state", "active")
        sessions = w.get("sessions", [])
        print(f"- {w['worklog_id'][:8]}  {title}  [{state}]  ({len(sessions)} 会话)")
        for s in sessions:
            cid = s.get("conversation_id") or "-"
            closed = "已关闭" if s.get("closed_at") else "进行中"
            print(f"    {s.get('agent', '?'):8s} conv={cid}  {closed}")


def cmd_worklog_rename(workspace: str, worklog_id: str, title: str) -> bool:
    from aisc.application import worklog

    return worklog.rename(_registry(workspace), worklog_id, title)


def cmd_worklog_archive(workspace: str, worklog_id: str, *, restore: bool = False) -> bool:
    from aisc.application import worklog

    return worklog.archive(_registry(workspace), worklog_id, archived=not restore)


def cmd_worklog_delete(workspace: str, worklog_id: str) -> bool:
    from aisc.application import worklog

    return worklog.delete(_registry(workspace), worklog_id)


def cmd_worklog_reconcile(workspace: str) -> Dict[str, Any]:
    from aisc.application import worklog

    return {
        "workspace": workspace,
        **worklog.reconcile(_registry(workspace), _ws_dir(workspace)),
    }
