"""Agent conversation discovery (v2.1.8 T3).

Read-only JSONL scanning per docs/plans/2.1.8-dev-plans/01-design.md
§1a-1e. Thin read over provider-native session files — no new storage
(方案 A): Claude ``<ws>/claude/projects/**/*.jsonl`` (filename stem =
conversation id), Codex ``<ws>/codex/sessions/**/*.jsonl`` (rollout
filename carries the id).

Oversized files (>10MB) are never fully parsed: a streaming head scan of
the first 200 parseable lines yields title/time, ``message_count`` stays
``null`` and the entry is annotated ``file_too_large``. Malformed JSON
lines are skipped; a file with at least one parseable user message but
some corrupt lines is annotated ``malformed`` and kept, ``resumable:
false``. Entries with zero parseable user messages are excluded.

D-5 (decisions.md): conversation ids are provider-native — Codex uses
time-ordered UUIDv7 in the wild (see the frozen T0 codex fixtures), so id
validation accepts any RFC-4122 version, not only v4. Non-UUID garbage is
still rejected (the check's stated intent).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aisc.application.data_root import DataRootResolver
from aisc.domain.models import CliError

# ---------------------------------------------------------------------------
# Frozen constants (design §1a/1d/1e)
# ---------------------------------------------------------------------------

MAX_JSONL_BYTES = 10 * 1024 * 1024
HEAD_SCAN_PARSEABLE_LINES = 200
TITLE_MAX_CHARS = 80
UNREADABLE_TITLE = "(无法读取)"

ERROR_INVALID_ID = "AISC_ERR_CONVERSATION_INVALID_ID"
ERROR_INVALID_AGENT = "AISC_ERR_CONVERSATION_INVALID_AGENT"
ERROR_UNRESUMABLE = "AISC_ERR_CONVERSATION_UNRESUMABLE"

# D-5: any RFC-4122 version (provider-native ids; Codex ships v7). The
# design's v4-only pattern predated the T0 probe fixtures and would have
# rejected every real Codex session.
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{12}$"
)
_CODEX_FILENAME_RE = re.compile(
    r"^rollout-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{12})\.jsonl$"
)

_AGENTS = ("claude", "codex")


# ---------------------------------------------------------------------------
# Title sanitization (design §1d)
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_REDACT_PATTERNS = (
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+\S+"),
    re.compile(r"api[_-]?key.*['\"]\s*\w{16,}"),
)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")

# Injected-context user messages (手测反馈 #1: providers record setup context
# — AGENTS.md/skills/permissions blocks, command caveats — as user role, so
# the FIRST user line is often not what the user typed). Title selection
# prefers the first message that does not look like injected context and
# falls back to the first message when every candidate does.
_CONTEXT_TITLE_RE = re.compile(
    r"^(?:"
    r"<"                              # XML-ish context blocks (<INSTRUCTIONS>,
                                      # <skills_instructions>, <local-command-
                                      # caveat>, <command-name>, <environment…)
    r"|# AGENTS\.md instructions"     # Codex AGENTS.md injection preamble
    r"|Caveat:"                       # Claude command caveat body
    r")"
)


def sanitize_title(text: str) -> str:
    """Sanitize a raw user message into a display title.

    Order: strip ANSI escapes → apply redaction patterns → drop control
    chars (newlines become spaces) → collapse whitespace → truncate to 80
    Unicode scalar values. Empty results degrade to ``UNREADABLE_TITLE``.
    """
    # 2.1.10 (field report #5): a non-string payload (nested content object
    # from a foreign session schema) must degrade, never render as
    # [object Object] upstream.
    if not isinstance(text, str):
        return UNREADABLE_TITLE
    out = _ANSI_RE.sub("", text)
    for pat in _REDACT_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    out = _CONTROL_CHARS_RE.sub(" ", out)
    out = " ".join(out.split())
    out = out[:TITLE_MAX_CHARS]
    return out or UNREADABLE_TITLE


# ---------------------------------------------------------------------------
# Per-provider user-message extraction (design §1a)
# ---------------------------------------------------------------------------

def _extract_claude_user(obj: Dict[str, Any]) -> Tuple[bool, Optional[str], bool]:
    """Return (is_user_line, extracted_text, title_eligible) for a Claude
    line. ``title_eligible`` excludes SDK-internal prompts ("init" and
    friends — 手测反馈 #1) from title selection."""
    if obj.get("type") != "user":
        return False, None, False
    msg = obj.get("message")
    if not isinstance(msg, dict) or msg.get("role") != "user":
        return False, None, False
    sdk = msg.get("promptSource") == "sdk"
    return True, _text_from_content(msg.get("content"), "text"), not sdk


def _extract_codex_user(obj: Dict[str, Any]) -> Tuple[bool, Optional[str], bool]:
    """Return (is_user_line, extracted_text, title_eligible) for a Codex
    line. Title eligibility is decided later by the context-text heuristic."""
    if obj.get("type") != "response_item":
        return False, None, False
    payload = obj.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "message":
        return False, None, False
    if payload.get("role") != "user":
        return False, None, False
    return True, _text_from_content(payload.get("content"), "input_text"), True


def _text_from_content(content: Any, block_type: str) -> Optional[str]:
    """Content is a string or a list of typed blocks; extract the first
    text block's text (design §1d extraction). Returns None when the line
    is a user line without extractable text (e.g. tool results)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == block_type:
                text = block.get("text")
                if isinstance(text, str):
                    return text
    return None


_EXTRACTORS = {
    "claude": _extract_claude_user,
    "codex": _extract_codex_user,
}


def is_conversation_uuid(value: str) -> bool:
    """True for a well-formed conversation id — any RFC-4122 version (D-5:
    Codex ships UUIDv7). Non-UUID garbage is rejected."""
    return bool(value) and bool(_UUID_RE.match(value))


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

@dataclass
class _FileScan:
    parseable: int = 0
    user_messages: int = 0
    first_ts: Optional[str] = None
    last_ts: Optional[str] = None
    title: Optional[str] = None
    malformed_seen: bool = False
    _first_raw: Optional[str] = None
    _good_raw: Optional[str] = None


def _scan_file(path: Path, agent: str, head_only: bool) -> _FileScan:
    """Stream a JSONL session file. ``head_only`` (oversized files) stops
    after HEAD_SCAN_PARSEABLE_LINES parseable lines — the file is never
    fully parsed (design §1a max_file_size)."""
    state = _FileScan()
    extract = _EXTRACTORS[agent]
    # 2.1.10 (field report #4): one unreadable session file (permissions,
    # owner mismatch on a data-root restored from elsewhere) must not kill
    # the whole conversation list — skip it like a malformed file.
    try:
        fh = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        state.malformed_seen = True
        return state
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (ValueError, TypeError):
                state.malformed_seen = True
                continue
            if not isinstance(obj, dict):
                continue
            state.parseable += 1
            ts = obj.get("timestamp")
            if isinstance(ts, str) and ts:
                if state.first_ts is None:
                    state.first_ts = ts
                state.last_ts = ts
            is_user, text, title_eligible = extract(obj)
            if is_user:
                state.user_messages += 1
                if text:
                    # 手测反馈 #1: prefer the first non-context user message
                    # for the title; fall back to the first message when
                    # every candidate is injected context.
                    if state._first_raw is None:
                        state._first_raw = text
                    if state._good_raw is None and title_eligible \
                            and not _CONTEXT_TITLE_RE.match(text.lstrip()):
                        state._good_raw = text
            if head_only and state.parseable >= HEAD_SCAN_PARSEABLE_LINES:
                break
    chosen = state._good_raw if state._good_raw else state._first_raw
    state.title = sanitize_title(chosen) if chosen else None
    return state


def _conversation_id_for(agent: str, filename: str) -> Optional[str]:
    """Derive the conversation id from the filename (design §1a id_source).

    Claude: filename stem IS the id. Codex: ``rollout-<ts>-<uuid>.jsonl``.
    Returns None for files that do not carry a well-formed id — they are
    not sessions and are skipped.
    """
    if agent == "claude":
        stem = filename[:-len(".jsonl")] if filename.endswith(".jsonl") else filename
        return stem if _UUID_RE.match(stem) else None
    m = _CODEX_FILENAME_RE.match(filename)
    return m.group(1) if m else None


def _summarize(agent: str, conv_id: str, file_size: int,
               scan: _FileScan) -> Optional[Dict[str, Any]]:
    """Apply §1e filtering/annotation. Returns None when the entry is
    excluded from the list (zero parseable user messages)."""
    if scan.user_messages == 0:
        return None
    resumable = True
    reason: Optional[str] = None
    message_count: Optional[int] = scan.user_messages
    if file_size > MAX_JSONL_BYTES:
        resumable = False
        reason = "file_too_large"
        message_count = None  # head scan only — a full count was not taken
    elif scan.malformed_seen:
        resumable = False
        reason = "malformed"
    entry: Dict[str, Any] = {
        "conversation_id": conv_id,
        "agent": agent,
        "title": scan.title if scan.title else UNREADABLE_TITLE,
        "started_at": scan.first_ts,
        "last_at": scan.last_ts,
        "message_count": message_count,
        "file_size": file_size,
        "resumable": resumable,
    }
    if not resumable:
        entry["unavailable_reason"] = reason
    return entry


def _scan_agent_dir(base: Path, agent: str) -> List[Dict[str, Any]]:
    if not base.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(base.rglob("*.jsonl")):
        if not path.is_file():
            continue
        conv_id = _conversation_id_for(agent, path.name)
        if conv_id is None:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        scan = _scan_file(path, agent, head_only=(size > MAX_JSONL_BYTES))
        entry = _summarize(agent, conv_id, size, scan)
        if entry is not None:
            out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def _workspace_dir(workspace: str) -> Path:
    """The workspace's data-root dir (read-only resolve — never creates)."""
    ws = Path(workspace).resolve() if workspace else Path.cwd()
    return DataRootResolver().resolve(ws).workspace_dir


# ---------------------------------------------------------------------------
# Title overrides (v2.1.8 T4 手测反馈 #2: 右键重命名). Providers own session
# titles (first user message); the Workbench label lives in a small override
# map under the workspace runtime dir (设计 3a: that dir is the workspace
# runtime persistence home). <agent>:<id-lowercase> → display title.
# ---------------------------------------------------------------------------

_TITLES_SCHEMA = "aisc.conversation-titles/v1"


def _titles_path(ws_dir: Path) -> Path:
    return ws_dir / "runtime" / "conversation_titles.json"


def _load_titles(ws_dir: Path) -> Dict[str, str]:
    try:
        data = json.loads(_titles_path(ws_dir).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return {}
    if not isinstance(data, dict) or not isinstance(data.get("titles"), dict):
        return {}
    return {
        str(k): str(v)
        for k, v in data["titles"].items()
        if isinstance(v, str) and v
    }


def _save_titles(ws_dir: Path, titles: Dict[str, str]) -> None:
    path = _titles_path(ws_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {"schema": _TITLES_SCHEMA, "titles": titles},
        ensure_ascii=False, indent=2, sort_keys=True,
    ) + "\n"
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)  # atomic — readers never see a partial file


def list_conversations(workspace: str) -> Dict[str, Any]:
    """List agent history conversations for a workspace (design §1b).

    Read-only, no Docker. Sorted most-recent-first for the picker UI
    (``last_at`` descending; entries without timestamps sort last).
    """
    ws_dir = _workspace_dir(workspace)
    entries: List[Dict[str, Any]] = []
    entries.extend(_scan_agent_dir(ws_dir / "claude" / "projects", "claude"))
    entries.extend(_scan_agent_dir(ws_dir / "codex" / "sessions", "codex"))
    entries.sort(
        key=lambda e: (e["last_at"] or "", e["conversation_id"]),
        reverse=True,
    )
    # Title overrides (rename) win over the extracted first-user-message.
    overrides = _load_titles(ws_dir)
    if overrides:
        for entry in entries:
            key = f"{entry['agent']}:{entry['conversation_id'].lower()}"
            if key in overrides:
                entry["title"] = overrides[key]
    return {"schema_version": 1, "conversations": entries}


def _find_conversation_file(ws_dir: Path, agent: str,
                            conversation_id: str) -> Optional[Path]:
    """Exact provider-specific file match for a conversation id (design §2).
    Claude: filename stem == id. Codex: rollout filename's trailing id,
    case-insensitive. Returns None when absent — never a glob substring."""
    if agent == "claude":
        base = ws_dir / "claude" / "projects"
        if not base.is_dir():
            return None
        for p in base.rglob("*.jsonl"):
            if p.is_file() and p.stem == conversation_id:
                return p
        return None
    base = ws_dir / "codex" / "sessions"
    if not base.is_dir():
        return None
    for p in base.rglob("*.jsonl"):
        if not p.is_file():
            continue
        m = _CODEX_FILENAME_RE.match(p.name)
        if m is not None and m.group(1).lower() == conversation_id.lower():
            return p
    return None


def preflight_conversation(workspace: str, conversation_id: str,
                           agent: str) -> Dict[str, Any]:
    """Validate a conversation is resumable BEFORE any PTY spawn (design
    §2: sidecar captured preflight). Exact provider-specific file match —
    never glob substring matching."""
    if not is_conversation_uuid(conversation_id):
        raise CliError(
            message=f"Invalid conversation ID: {conversation_id}",
            exit_code=2,
            error_code=ERROR_INVALID_ID,
        )
    if agent not in _AGENTS:
        raise CliError(
            message=f"Unsupported agent for resume: {agent}",
            exit_code=2,
            error_code=ERROR_INVALID_AGENT,
        )

    ws_dir = _workspace_dir(workspace)
    if _find_conversation_file(ws_dir, agent, conversation_id) is None:
        raise CliError(
            message=f"Conversation {conversation_id} not found for agent {agent}",
            exit_code=3,
            error_code=ERROR_UNRESUMABLE,
        )
    return {
        "preflight_ok": True,
        "conversation_id": conversation_id,
        "agent": agent,
    }


def delete_conversation(workspace: str, conversation_id: str,
                        agent: str) -> Dict[str, Any]:
    """Delete a conversation's session file (v2.1.8 T4 手测反馈 #4: 变更页
    右键删除). Exact match only; the id must be well-formed. Idempotent
    failure mode: an absent conversation raises the same UNRESUMABLE error
    as preflight — the caller has just shown it in a list, so absence is
    an anomaly worth reporting, not a silent success."""
    if not is_conversation_uuid(conversation_id):
        raise CliError(
            message=f"Invalid conversation ID: {conversation_id}",
            exit_code=2,
            error_code=ERROR_INVALID_ID,
        )
    if agent not in _AGENTS:
        raise CliError(
            message=f"Unsupported agent: {agent}",
            exit_code=2,
            error_code=ERROR_INVALID_AGENT,
        )
    ws_dir = _workspace_dir(workspace)
    path = _find_conversation_file(ws_dir, agent, conversation_id)
    if path is None:
        raise CliError(
            message=f"Conversation {conversation_id} not found for agent {agent}",
            exit_code=3,
            error_code=ERROR_UNRESUMABLE,
        )
    try:
        path.unlink()
    except OSError as exc:
        raise CliError(
            message=f"Failed to delete conversation {conversation_id}: {exc}",
            exit_code=1,
            error_code="AISC_ERR_GENERAL",
        ) from exc
    # Drop the rename override with the conversation (best-effort — a stale
    # entry is inert but must not accumulate).
    titles = _load_titles(ws_dir)
    key = f"{agent}:{conversation_id.lower()}"
    if key in titles:
        del titles[key]
        _save_titles(ws_dir, titles)
    return {"deleted": True, "conversation_id": conversation_id, "agent": agent}


def rename_conversation(workspace: str, conversation_id: str, agent: str,
                        title: str) -> Dict[str, Any]:
    """Set a Workbench display title for a conversation (手测反馈 #2). The
    provider's own title is untouched; the override wins in ``list``."""
    if not is_conversation_uuid(conversation_id):
        raise CliError(
            message=f"Invalid conversation ID: {conversation_id}",
            exit_code=2,
            error_code=ERROR_INVALID_ID,
        )
    if agent not in _AGENTS:
        raise CliError(
            message=f"Unsupported agent: {agent}",
            exit_code=2,
            error_code=ERROR_INVALID_AGENT,
        )
    if not isinstance(title, str) or not title.strip():
        raise CliError(
            message="Title must be a non-empty string",
            exit_code=2,
            error_code="AISC_ERR_USAGE",
        )
    ws_dir = _workspace_dir(workspace)
    if _find_conversation_file(ws_dir, agent, conversation_id) is None:
        raise CliError(
            message=f"Conversation {conversation_id} not found for agent {agent}",
            exit_code=3,
            error_code=ERROR_UNRESUMABLE,
        )
    clean = sanitize_title(title.strip())
    titles = _load_titles(ws_dir)
    titles[f"{agent}:{conversation_id.lower()}"] = clean
    _save_titles(ws_dir, titles)
    return {
        "renamed": True,
        "conversation_id": conversation_id,
        "agent": agent,
        "title": clean,
    }


# ---------------------------------------------------------------------------
# Conversation read (批 2 聊天式 UI, 2026-09-21): normalized read-only stream.
# Provider transcripts stay strictly read-only (module-head rule); this layer
# only PROJECTS them into a stable rendering schema — no writes anywhere.
# ---------------------------------------------------------------------------

CONVERSATION_READ_SCHEMA = "aisc.conversation-read/v1"
_READ_TEXT_CAP = 8000     # per user/assistant message (chars)
_READ_REASONING_CAP = 4000
_READ_TOOL_CAP = 4000     # per tool_use input / tool_result output
_READ_MAX_MESSAGES = 4000  # hard bound on the rendered stream


def _read_join_text(content: Any, block_type: str) -> Optional[str]:
    """Join EVERY ``block_type`` text block (unlike _text_from_content, which
    returns the first). A chat bubble must not silently drop the rest of a
    multi-block message."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == block_type:
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text)
        if parts:
            return "\n\n".join(parts)
    return None


def _read_as_text(value: Any) -> Optional[str]:
    """Best-effort text for tool arguments/outputs: strings pass through,
    structured payloads serialize (bounded by the caller's cap)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=1)
    except (TypeError, ValueError):
        return str(value)


def _read_cap(text: Any, cap: int) -> str:
    """Coerce to str and hard-cap, marking the cut in the text itself (the
    chat pane renders plain text — a side flag would be invisible there)."""
    out = text if isinstance(text, str) else ("" if text is None else str(text))
    if len(out) > cap:
        return out[:cap] + f"\n…[截断，共 {len(out)} 字符]"
    return out


def _read_summary_text(summary: Any) -> Optional[str]:
    """Codex reasoning payload: ``summary`` is a list of summary blocks."""
    if isinstance(summary, list):
        parts = []
        for block in summary:
            if isinstance(block, dict) and isinstance(block.get("text"), str) \
                    and block["text"].strip():
                parts.append(block["text"])
        if parts:
            return "\n\n".join(parts)
    if isinstance(summary, str) and summary.strip():
        return summary
    return None


def _read_entries_codex(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One codex rollout line → zero or more rendered entries. Rendered:
    user/assistant messages, reasoning summaries, function calls/results.
    Dropped: session_meta, event_msg, world_state, turn_context, developer
    messages, injected-context user blocks."""
    if obj.get("type") != "response_item":
        return []
    payload = obj.get("payload")
    if not isinstance(payload, dict):
        return []
    ts = obj.get("timestamp") if isinstance(obj.get("timestamp"), str) else None
    kind = payload.get("type")
    if kind == "message":
        role = payload.get("role")
        if role == "user":
            text = _read_join_text(payload.get("content"), "input_text")
            if not text or not text.strip():
                return []
            if _CONTEXT_TITLE_RE.match(text.lstrip()):
                return []
            return [{"role": "user", "kind": "message", "text": text, "ts": ts}]
        if role == "assistant":
            text = _read_join_text(payload.get("content"), "output_text")
            if not text or not text.strip():
                return []
            return [{"role": "assistant", "kind": "message", "text": text, "ts": ts}]
        return []
    if kind == "reasoning":
        text = _read_summary_text(payload.get("summary"))
        if not text:
            return []
        return [{"role": "assistant", "kind": "reasoning", "text": text, "ts": ts}]
    if kind == "function_call":
        name = payload.get("name")
        call_id = payload.get("call_id")
        return [{
            "role": "assistant", "kind": "tool_use",
            "name": name if isinstance(name, str) else "tool",
            "text": _read_as_text(payload.get("arguments")),
            "call_id": call_id if isinstance(call_id, str) else None,
            "ts": ts,
        }]
    if kind == "function_call_output":
        call_id = payload.get("call_id")
        return [{
            "role": "tool", "kind": "tool_result",
            "text": _read_as_text(payload.get("output")),
            "call_id": call_id if isinstance(call_id, str) else None,
            "ts": ts,
        }]
    return []


def _read_entries_claude(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One Claude session line → zero or more rendered entries. Rendered:
    user/assistant text, thinking, tool_use, tool_result. Dropped:
    queue-operation/attachment/last-prompt/atis-latch and sidechain
    (subagent) transcripts — the main thread only."""
    if obj.get("type") not in ("user", "assistant"):
        return []
    if obj.get("isSidechain") is True:
        return []
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return []
    ts = obj.get("timestamp") if isinstance(obj.get("timestamp"), str) else None
    role = "user" if obj.get("type") == "user" else "assistant"
    content = msg.get("content")
    out: List[Dict[str, Any]] = []

    def _push_text(text: Any) -> None:
        if isinstance(text, str) and text.strip():
            if role == "user" and _CONTEXT_TITLE_RE.match(text.lstrip()):
                return
            out.append({"role": role, "kind": "message", "text": text, "ts": ts})

    if isinstance(content, str):
        _push_text(content)
        return out
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            bt = block.get("type")
            if bt == "text":
                _push_text(block.get("text"))
            elif bt == "thinking":
                text = block.get("thinking")
                if isinstance(text, str) and text.strip():
                    out.append({"role": "assistant", "kind": "reasoning",
                                "text": text, "ts": ts})
            elif bt == "tool_use":
                call_id = block.get("id")
                out.append({
                    "role": "assistant", "kind": "tool_use",
                    "name": block.get("name") if isinstance(block.get("name"), str) else "tool",
                    "text": _read_as_text(block.get("input")),
                    "call_id": call_id if isinstance(call_id, str) else None,
                    "ts": ts,
                })
            elif bt == "tool_result":
                inner = block.get("content")
                text = inner if isinstance(inner, str) else _read_join_text(inner, "text")
                call_id = block.get("tool_use_id")
                out.append({
                    "role": "tool", "kind": "tool_result",
                    "text": text,
                    "call_id": call_id if isinstance(call_id, str) else None,
                    "ts": ts,
                })
    return out


_READ_EXTRACTORS = {
    "codex": _read_entries_codex,
    "claude": _read_entries_claude,
}


def read_conversation(workspace: str, conversation_id: str, agent: str,
                      tail: Optional[int] = None,
                      before: Optional[int] = None) -> Dict[str, Any]:
    """Project a provider transcript into the chat rendering stream.

    Pagination walks the RENDERED stream backwards: ``tail`` returns the
    last ``tail`` entries; ``before`` (0-based exclusive ordinal) returns
    the window immediately preceding it. Ordinals are stable per file
    version — the UI pages with ``before=start`` until start reaches 0.
    Malformed lines are skipped and counted, never fatal (list semantics)."""
    if not is_conversation_uuid(conversation_id):
        raise CliError(
            message=f"Invalid conversation ID: {conversation_id}",
            exit_code=2,
            error_code=ERROR_INVALID_ID,
        )
    if agent not in _AGENTS:
        raise CliError(
            message=f"Unsupported agent: {agent}",
            exit_code=2,
            error_code=ERROR_INVALID_AGENT,
        )
    ws_dir = _workspace_dir(workspace)
    path = _find_conversation_file(ws_dir, agent, conversation_id)
    if path is None:
        raise CliError(
            message=f"Conversation {conversation_id} not found for agent {agent}",
            exit_code=3,
            error_code=ERROR_UNRESUMABLE,
        )
    extract = _READ_EXTRACTORS[agent]
    entries: List[Dict[str, Any]] = []
    malformed_lines = 0
    try:
        fh = path.open("r", encoding="utf-8", errors="replace")
    except OSError as e:
        raise CliError(
            message=f"Conversation file unreadable: {e}",
            exit_code=3,
            error_code=ERROR_UNRESUMABLE,
        )
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (ValueError, TypeError):
                malformed_lines += 1
                continue
            if not isinstance(obj, dict):
                continue
            for entry in extract(obj):
                if len(entries) >= _READ_MAX_MESSAGES:
                    break  # stream bound; the tail window still pages correctly
                entries.append(entry)
    # Pair tool results into their calls (nearest preceding unmatched match);
    # unpaired results stay standalone so nothing is silently dropped.
    open_calls: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        if entry["kind"] == "tool_use" and entry.get("call_id"):
            open_calls[entry["call_id"]] = entry
        elif entry["kind"] == "tool_result" and entry.get("call_id"):
            call = open_calls.get(entry["call_id"])
            if call is not None and "result" not in call:
                call["result"] = entry.pop("text")
                entry["consumed"] = True
    rendered = [e for e in entries if not e.get("consumed")]
    for i, entry in enumerate(rendered):
        entry["ordinal"] = i
        cap = _READ_TEXT_CAP
        if entry["kind"] == "reasoning":
            cap = _READ_REASONING_CAP
        elif entry["kind"] == "tool_use":
            entry["text"] = _read_cap(entry.get("text"), _READ_TOOL_CAP)
            if "result" in entry:
                entry["result"] = _read_cap(entry["result"], _READ_TOOL_CAP)
            continue
        elif entry["kind"] == "tool_result":
            cap = _READ_TOOL_CAP
        entry["text"] = _read_cap(entry.get("text"), cap)

    total = len(rendered)
    start = 0
    end = total
    if before is not None:
        end = max(0, min(int(before), total))
    if tail is not None and tail > 0:
        start = max(0, end - int(tail))
    return {
        "schema": CONVERSATION_READ_SCHEMA,
        "conversation_id": conversation_id,
        "agent": agent,
        "file_size": path.stat().st_size,
        "total": total,
        "start": start,
        "messages": rendered[start:end],
        "malformed_lines": malformed_lines,
        "degraded_reason": "malformed" if malformed_lines else None,
    }
