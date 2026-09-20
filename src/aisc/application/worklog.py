"""Worklog ledger (v2.1.13 history-worklog 批 1, D-7).

The per-workspace account of PTY sessions: every session opened through
``build_session_exec`` (CLI open_session AND serve PTY ops share it) appends
one entry; ``terminate_session`` closes it. Stored at
``<ws_dir>/runtime/worklogs.json`` (``aisc.worklog/v1``) — the same home as
conversation_titles.json, on the host data root, surviving container removal.

Fail-open everywhere: a missing/corrupt ledger never blocks opening or
closing a session (批 1 ruling). Provider transcript files are NEVER written
by this module (方案 A 铁律) — the ledger only references them.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKLOG_SCHEMA = "aisc.worklog/v1"
UNFILED_TITLE = "未归档会话"
_TITLE_MAX = 80


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return str(uuid.uuid4())


def ledger_path(registry_root: Any) -> Path:
    """worklogs.json lives beside containers.json in the runtime state dir."""
    return Path(registry_root) / "worklogs.json"


def _sanitize_title(title: str) -> str:
    cleaned = " ".join(title.split())
    return cleaned[:_TITLE_MAX]


def _empty_doc() -> Dict[str, Any]:
    return {"schema_version": WORKLOG_SCHEMA, "worklogs": []}


def load(registry_root: Any) -> Dict[str, Any]:
    """Tolerant load: missing → empty ledger; corrupt → quarantined aside
    (`.corrupt-<ts>`) and an empty ledger returned (fail-open, 批 1 ruling)."""
    path = ledger_path(registry_root)
    if not path.is_file():
        return _empty_doc()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        try:
            path.rename(path.with_name(
                f"worklogs.corrupt-{_now_iso().replace(':', '')}.json"
            ))
        except OSError:
            pass
        return _empty_doc()
    if not isinstance(doc, dict) or not isinstance(doc.get("worklogs"), list):
        return _empty_doc()
    return doc


def save(registry_root: Any, doc: Dict[str, Any]) -> None:
    """Atomic write (tmp + os.replace), Windows-safe."""
    path = ledger_path(registry_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    os.replace(tmp, path)


def record_open(
    registry_root: Any,
    *,
    session_id: str,
    agent: str,
    resume_conversation_id: Optional[str] = None,
    now: Optional[str] = None,
) -> Optional[str]:
    """Append one PTY-session-open entry as a NEW worklog (auto-title
    placeholder; rename later). Fail-open: returns the worklog_id or None."""
    try:
        doc = load(registry_root)
        now = now or _now_iso()
        worklog = {
            "worklog_id": _new_id(),
            "title": "",  # empty = auto placeholder (agent + time at render)
            "created_at": now,
            "last_opened_at": now,
            "state": "active",
            "sessions": [
                {
                    "terminal_session_id": session_id,
                    "agent": agent,
                    "conversation_id": None,  # filled by reconcile
                    "resume_of_conversation_id": resume_conversation_id,
                    "opened_at": now,
                    "closed_at": None,
                    "exit_code": None,
                }
            ],
        }
        doc["worklogs"].append(worklog)
        save(registry_root, doc)
        return worklog["worklog_id"]
    except Exception:
        return None  # fail-open: ledger problems never block opening


def record_close(
    registry_root: Any,
    *,
    session_id: str,
    exit_code: Optional[int] = None,
    closed_at: Optional[str] = None,
) -> bool:
    """Mark the matching open entry closed. Fail-open; returns whether an
    entry was updated."""
    try:
        doc = load(registry_root)
        closed_at = closed_at or _now_iso()
        for worklog in doc.get("worklogs", []):
            for entry in worklog.get("sessions", []):
                if (entry.get("terminal_session_id") == session_id
                        and entry.get("closed_at") is None):
                    entry["closed_at"] = closed_at
                    entry["exit_code"] = exit_code
                    save(registry_root, doc)
                    return True
        return False
    except Exception:
        return False


def rename(registry_root: Any, worklog_id: str, title: str) -> bool:
    doc = load(registry_root)
    for worklog in doc.get("worklogs", []):
        if worklog.get("worklog_id") == worklog_id:
            worklog["title"] = _sanitize_title(title)
            save(registry_root, doc)
            return True
    return False


def archive(registry_root: Any, worklog_id: str, *, archived: bool = True) -> bool:
    doc = load(registry_root)
    for worklog in doc.get("worklogs", []):
        if worklog.get("worklog_id") == worklog_id:
            worklog["state"] = "archived" if archived else "active"
            save(registry_root, doc)
            return True
    return False


def delete(registry_root: Any, worklog_id: str) -> bool:
    doc = load(registry_root)
    before = len(doc.get("worklogs", []))
    doc["worklogs"] = [
        w for w in doc.get("worklogs", []) if w.get("worklog_id") != worklog_id
    ]
    if len(doc["worklogs"]) != before:
        save(registry_root, doc)
        return True
    return False


def list_worklogs(registry_root: Any) -> List[Dict[str, Any]]:
    """Newest-first worklog list (by last_opened_at)."""
    doc = load(registry_root)
    return sorted(
        doc.get("worklogs", []),
        key=lambda w: w.get("last_opened_at") or "",
        reverse=True,
    )


def _provider_session_ids(ws_dir: Path) -> Dict[str, set]:
    """Known provider conversation IDs per agent, from the transcript files
    (filename-derived, same source conversation.py uses). Read-only."""
    out: Dict[str, set] = {"claude": set(), "codex": set()}
    claude_root = ws_dir / "claude" / "projects"
    if claude_root.is_dir():
        for p in claude_root.rglob("*.jsonl"):
            out["claude"].add(p.stem)
    codex_root = ws_dir / "codex" / "sessions"
    if codex_root.is_dir():
        for p in codex_root.rglob("rollout-*.jsonl"):
            # rollout-<ts>-<uuid>.jsonl → tail segment is the session id
            stem = p.stem
            tail = stem.rsplit("-", 1)[-1]
            if tail:
                out["codex"].add(tail)
    return out


def reconcile(registry_root: Any, ws_dir: Any) -> Dict[str, int]:
    """Attach provider sessions not present in any worklog entry to a
    synthetic 「未归档会话」 worklog (reused across runs). Returns counts."""
    ws_dir = Path(ws_dir)
    doc = load(registry_root)
    known: Dict[str, set] = {"claude": set(), "codex": set()}
    for worklog in doc.get("worklogs", []):
        for entry in worklog.get("sessions", []):
            cid = entry.get("conversation_id")
            agent = entry.get("agent")
            if cid and agent in known:
                known[agent].add(cid)
    provider = _provider_session_ids(ws_dir)

    unattached: List[Dict[str, str]] = []
    for agent, ids in provider.items():
        for cid in sorted(ids):
            if cid not in known[agent]:
                unattached.append({"agent": agent, "conversation_id": cid})

    added = 0
    if unattached:
        unfiled = None
        for worklog in doc.get("worklogs", []):
            if worklog.get("title") == UNFILED_TITLE and worklog.get("state") == "active":
                unfiled = worklog
                break
        now = _now_iso()
        if unfiled is None:
            unfiled = {
                "worklog_id": _new_id(),
                "title": UNFILED_TITLE,
                "created_at": now,
                "last_opened_at": now,
                "state": "active",
                "sessions": [],
            }
            doc["worklogs"].append(unfiled)
        for item in unattached:
            unfiled["sessions"].append({
                "terminal_session_id": None,
                "agent": item["agent"],
                "conversation_id": item["conversation_id"],
                "resume_of_conversation_id": None,
                "opened_at": None,
                "closed_at": None,
                "exit_code": None,
                "inferred": True,
            })
            added += 1
        unfiled["last_opened_at"] = now
        save(registry_root, doc)
    return {"attached": added, "worklogs": len(doc.get("worklogs", []))}
