"""Work Record / Collection ledger (v2.1.15 b6).

A per-workspace aggregate layer above provider-native conversations.  The
ledger stores only weak references and metadata; provider JSONL files remain
the source of truth and are never written here.  ``bash`` and ``cc-switch``
are intentionally outside this model.

Storage: ``<workspace data root>/runtime/work-collections.json``.
Fail-open applies to incidental readers (missing/corrupt ledger becomes an
empty document); explicit CRUD failures are surfaced to the caller.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from aisc.application import conversation as conversation
from aisc.domain.models import CliError

# Module-level alias also lets reconcile tests substitute the provider scanner
# without changing transcript discovery semantics.
list_conversations = conversation.list_conversations

WORK_COLLECTION_SCHEMA = "aisc.work-collections/v1"
COLLECTIONS_FILENAME = "work-collections.json"
_AGENTS = ("claude", "codex")
_MEMBER_SOURCES = ("manual", "active_auto")
_LOCK_TIMEOUT_SECONDS = 2.0
# One process-wide lock serializes in-process callers.  The lock file below
# adds best-effort cross-process serialization on top of it.
_PROCESS_LOCK = threading.RLock()

# Convenience re-export: Work Record membership uses the exact same provider
# UUID definition as the conversation layer.
is_conversation_uuid = conversation.is_conversation_uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id() -> str:
    return str(uuid.uuid4())


def collections_path(registry_root: Any) -> Path:
    """Return the ledger path inside a workspace runtime directory."""
    return Path(registry_root) / COLLECTIONS_FILENAME


def empty_document() -> Dict[str, Any]:
    return {
        "schema_version": WORK_COLLECTION_SCHEMA,
        "active_collection_id": None,
        "observed_provider_keys": [],
        "collections": [],
    }


def _quarantine_path(path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return path.with_name(f"work-collections.corrupt-{stamp}.json")


def _valid_document(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("schema_version") == WORK_COLLECTION_SCHEMA
        and isinstance(value.get("active_collection_id"), (str, type(None)))
        and isinstance(value.get("observed_provider_keys"), list)
        and isinstance(value.get("collections"), list)
    )


def load(registry_root: Any) -> Dict[str, Any]:
    """Load a ledger; isolate invalid/corrupt files and return an empty one."""
    path = collections_path(registry_root)
    if not path.is_file():
        return empty_document()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        value = None
    if not _valid_document(value):
        try:
            os.replace(path, _quarantine_path(path))
        except OSError:
            # Quarantine is best-effort; the empty in-memory document still
            # prevents provider conversation flows from being blocked.
            pass
        return empty_document()
    return value


def _write(registry_root: Any, doc: Dict[str, Any]) -> None:
    if not _valid_document(doc):
        raise CliError(
            message="Invalid work collection document",
            exit_code=1,
            error_code="AISC_ERR_WORK_COLLECTION_INVALID_DOCUMENT",
        )
    path = collections_path(registry_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f".{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    try:
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)  # atomic on POSIX and Windows
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def _ledger_lock(registry_root: Any):
    """Serialize ledger mutation within and, best-effort, across processes."""
    acquired_process = False
    lock_path = Path(registry_root) / f".{COLLECTIONS_FILENAME}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    lock_created = False
    try:
        if not _PROCESS_LOCK.acquire(timeout=_LOCK_TIMEOUT_SECONDS):
            raise CliError(
                message="Timed out waiting for work collection lock",
                exit_code=1,
                error_code="AISC_ERR_WORK_COLLECTION_LOCK_TIMEOUT",
            )
        acquired_process = True
        while time.monotonic() < deadline:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("ascii"))
                os.close(fd)
                lock_created = True
                break
            except FileExistsError:
                time.sleep(0.02)
            except OSError:
                # Locking must not make a local read-only data root unusable.
                break
        if not lock_created and time.monotonic() >= deadline:
            raise CliError(
                message="Timed out waiting for work collection lock",
                exit_code=1,
                error_code="AISC_ERR_WORK_COLLECTION_LOCK_TIMEOUT",
            )
        yield
    finally:
        if lock_created:
            try:
                lock_path.unlink()
            except OSError:
                pass
        if acquired_process:
            _PROCESS_LOCK.release()


def save(registry_root: Any, doc: Dict[str, Any]) -> None:
    """Atomically save a complete ledger document."""
    with _ledger_lock(registry_root):
        _write(registry_root, doc)


def _find(doc: Dict[str, Any], collection_id: str) -> Dict[str, Any]:
    if not isinstance(collection_id, str) or not collection_id:
        raise CliError(
            message="Collection ID is required",
            exit_code=2,
            error_code="AISC_ERR_USAGE",
        )
    for item in doc["collections"]:
        if item.get("id") == collection_id:
            return item
    raise CliError(
        message=f"Work collection not found: {collection_id}",
        exit_code=3,
        error_code="AISC_ERR_WORK_COLLECTION_NOT_FOUND",
    )


def _clean_title(title: str) -> str:
    if not isinstance(title, str) or not title.strip():
        raise CliError(
            message="Title must be a non-empty string",
            exit_code=2,
            error_code="AISC_ERR_USAGE",
        )
    return " ".join(title.split())[:80]


def _member_key(agent: str, conversation_id: str) -> str:
    return f"{agent}:{conversation_id.lower()}"


def _require_exact_order(requested: List[str], current: List[str], *, noun: str) -> None:
    if len(requested) != len(set(requested)):
        raise CliError(
            message=f"Duplicate {noun} key in reorder request",
            exit_code=2,
            error_code="AISC_ERR_USAGE",
        )
    if set(requested) != set(current):
        raise CliError(
            message=f"{noun} reorder request does not match current items",
            exit_code=1,
            error_code="AISC_ERR_WORK_COLLECTION_ORDER_CONFLICT",
        )


def _ordered_unfiled(doc: Dict[str, Any], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_key = {
        _member_key(item["agent"], item["conversation_id"]): item
        for item in items
    }
    ordered: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for key in doc.get("unfiled_order", []):
        item = by_key.get(key)
        if item is None:
            continue
        ordered.append(item)
        seen.add(key)
    ordered.extend(item for key, item in by_key.items() if key not in seen)
    return ordered


def _existing_member_keys(doc: Dict[str, Any]) -> set[str]:
    return {
        member.get("member_key")
        for collection in doc["collections"]
        for member in collection.get("members", [])
        if isinstance(member, dict)
    }


def create(registry_root: Any, *, title: str, now: Optional[str] = None) -> Dict[str, Any]:
    """Create an active (but not globally activated) Collection."""
    with _ledger_lock(registry_root):
        doc = load(registry_root)
        timestamp = now or _now_iso()
        item = {
            "id": _new_id(),
            "title": _clean_title(title),
            "status": "active",
            "created_at": timestamp,
            "updated_at": timestamp,
            "archived_at": None,
            "members": [],
        }
        doc["collections"].append(item)
        _write(registry_root, doc)
        return copy.deepcopy(item)


def list_collections(registry_root: Any) -> List[Dict[str, Any]]:
    return copy.deepcopy(load(registry_root)["collections"])


def _mutate(
    registry_root: Any,
    collection_id: str,
    function: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    with _ledger_lock(registry_root):
        doc = load(registry_root)
        collection = _find(doc, collection_id)
        result = function(doc, collection)
        _write(registry_root, doc)
        return copy.deepcopy(result)


def rename(registry_root: Any, collection_id: str, title: str) -> Dict[str, Any]:
    clean = _clean_title(title)

    def apply(_doc: Dict[str, Any], collection: Dict[str, Any]) -> Dict[str, Any]:
        collection["title"] = clean
        collection["updated_at"] = _now_iso()
        return collection

    return _mutate(registry_root, collection_id, apply)


def _baseline(workspace: Optional[str]) -> List[str]:
    if not workspace:
        return []
    data = list_conversations(str(workspace))
    return [
        _member_key(item["agent"], item["conversation_id"])
        for item in data.get("conversations", [])
        if item.get("agent") in _AGENTS
    ]


def set_active(
    registry_root: Any,
    collection_id: str,
    *,
    workspace: Optional[str] = None,
) -> Dict[str, Any]:
    """Select the one active Collection and establish its adoption baseline."""
    with _ledger_lock(registry_root):
        doc = load(registry_root)
        collection = _find(doc, collection_id)
        if collection.get("status") != "active":
            raise CliError(
                message="An archived collection cannot be activated",
                exit_code=1,
                error_code="AISC_ERR_WORK_COLLECTION_ARCHIVED",
            )
        doc["active_collection_id"] = collection_id
        if workspace is not None:
            doc["observed_provider_keys"] = _baseline(workspace)
        _write(registry_root, doc)
        return copy.deepcopy(collection)


def deactivate(registry_root: Any) -> Dict[str, Any]:
    with _ledger_lock(registry_root):
        doc = load(registry_root)
        previous = doc["active_collection_id"]
        doc["active_collection_id"] = None
        _write(registry_root, doc)
        return {"active_collection_id": None, "previous_collection_id": previous}


def archive(registry_root: Any, collection_id: str) -> Dict[str, Any]:
    def apply(doc: Dict[str, Any], collection: Dict[str, Any]) -> Dict[str, Any]:
        collection["status"] = "archived"
        collection["archived_at"] = _now_iso()
        collection["updated_at"] = collection["archived_at"]
        if doc["active_collection_id"] == collection["id"]:
            doc["active_collection_id"] = None
        return collection

    return _mutate(registry_root, collection_id, apply)


def restore(registry_root: Any, collection_id: str) -> Dict[str, Any]:
    def apply(_doc: Dict[str, Any], collection: Dict[str, Any]) -> Dict[str, Any]:
        collection["status"] = "active"
        collection["archived_at"] = None
        collection["updated_at"] = _now_iso()
        return collection

    return _mutate(registry_root, collection_id, apply)


def add_member(
    registry_root: Any,
    collection_id: str,
    *,
    agent: str,
    conversation_id: str,
    runtime_id: Optional[str] = None,
    source: str = "manual",
) -> Dict[str, Any]:
    if agent not in _AGENTS:
        raise CliError(
            message=f"Unsupported agent: {agent}",
            exit_code=2,
            error_code=conversation.ERROR_INVALID_AGENT,
        )
    if not conversation.is_conversation_uuid(conversation_id):
        raise CliError(
            message=f"Invalid conversation ID: {conversation_id}",
            exit_code=2,
            error_code=conversation.ERROR_INVALID_ID,
        )
    if source not in _MEMBER_SOURCES:
        raise CliError(
            message=f"Invalid member source: {source}",
            exit_code=2,
            error_code="AISC_ERR_WORK_COLLECTION_INVALID_SOURCE",
        )
    normalized_id = conversation_id.lower()
    key = _member_key(agent, normalized_id)

    def apply(doc: Dict[str, Any], collection: Dict[str, Any]) -> Dict[str, Any]:
        own = any(m.get("member_key") == key for m in collection["members"])
        if own:
            return next(m for m in collection["members"] if m["member_key"] == key)
        if key in _existing_member_keys(doc):
            raise CliError(
                message=f"Conversation is already in another work collection: {key}",
                exit_code=1,
                error_code="AISC_ERR_WORK_COLLECTION_MEMBER_EXISTS",
            )
        member = {
            "member_key": key,
            "agent": agent,
            "conversation_id": normalized_id,
            "runtime_id": runtime_id,
            "source": source,
            "added_at": _now_iso(),
        }
        collection["members"].append(member)
        collection["updated_at"] = member["added_at"]
        return member

    return _mutate(registry_root, collection_id, apply)


def remove_member(
    registry_root: Any,
    collection_id: str,
    *,
    agent: str,
    conversation_id: str,
) -> Dict[str, Any]:
    if agent not in _AGENTS:
        raise CliError(
            message=f"Unsupported agent: {agent}",
            exit_code=2,
            error_code=conversation.ERROR_INVALID_AGENT,
        )
    if not conversation.is_conversation_uuid(conversation_id):
        raise CliError(
            message=f"Invalid conversation ID: {conversation_id}",
            exit_code=2,
            error_code=conversation.ERROR_INVALID_ID,
        )
    key = _member_key(agent, conversation_id)

    def apply(doc: Dict[str, Any], collection: Dict[str, Any]) -> Dict[str, Any]:
        before = len(collection["members"])
        collection["members"] = [
            member
            for member in collection["members"]
            if member.get("member_key") != key
        ]
        if len(collection["members"]) == before:
            raise CliError(
                message=f"Conversation is not a member: {key}",
                exit_code=3,
                error_code="AISC_ERR_WORK_COLLECTION_MEMBER_NOT_FOUND",
            )
        collection["updated_at"] = _now_iso()
        return {"removed": True, "member_key": key}

    return _mutate(registry_root, collection_id, apply)


def _supported_conversations(workspace: str) -> List[Dict[str, Any]]:
    data = list_conversations(workspace)
    return [
        item
        for item in data.get("conversations", [])
        if item.get("agent") in _AGENTS
    ]


def reconcile(registry_root: Any, workspace: str) -> Dict[str, Any]:
    """Adopt only new provider conversations into the active Collection."""
    with _ledger_lock(registry_root):
        providers = _supported_conversations(workspace)
        provider_keys = [
            _member_key(item["agent"], item["conversation_id"])
            for item in providers
        ]
        provider_key_set = set(provider_keys)
        doc = load(registry_root)
        member_keys = _existing_member_keys(doc)
        active_id = doc["active_collection_id"]
        active = None
        if active_id:
            try:
                active = _find(doc, active_id)
            except CliError:
                active = None
            if active is not None and active.get("status") != "active":
                active = None

        added: List[str] = []
        if active is not None:
            observed = set(doc["observed_provider_keys"])
            timestamp = _now_iso()
            for item in providers:
                key = _member_key(item["agent"], item["conversation_id"])
                if key in observed or key in member_keys:
                    continue
                member = {
                    "member_key": key,
                    "agent": item["agent"],
                    "conversation_id": str(item["conversation_id"]).lower(),
                    "runtime_id": None,
                    "source": "active_auto",
                    "added_at": timestamp,
                }
                active["members"].append(member)
                member_keys.add(key)
                added.append(key)
                active["updated_at"] = timestamp
        # The observed set is a scan baseline, not user-facing data.  It is
        # refreshed to exactly this reconcile's supported provider scan.
        doc["observed_provider_keys"] = [
            key for key in provider_keys if key in provider_key_set
        ]
        _write(registry_root, doc)
        return {
            "schema_version": WORK_COLLECTION_SCHEMA,
            "added": added,
            "active_collection_id": doc["active_collection_id"],
            "collections": copy.deepcopy(doc["collections"]),
            "observed_provider_keys": doc["observed_provider_keys"],
        }


def unfiled(registry_root: Any, workspace: str) -> List[Dict[str, Any]]:
    """Compute supported provider conversations not belonging to any Collection."""
    doc = load(registry_root)
    member_keys = _existing_member_keys(doc)
    items = [
        item
        for item in _supported_conversations(workspace)
        if _member_key(item["agent"], item["conversation_id"]) not in member_keys
    ]
    return _ordered_unfiled(doc, items)


def reorder_collections(registry_root: Any, collection_ids: List[str]) -> Dict[str, Any]:
    with _ledger_lock(registry_root):
        doc = load(registry_root)
        current = [item["id"] for item in doc["collections"]]
        _require_exact_order(collection_ids, current, noun="collection")
        by_id = {item["id"]: item for item in doc["collections"]}
        doc["collections"] = [by_id[item_id] for item_id in collection_ids]
        _write(registry_root, doc)
        return {"collections": copy.deepcopy(doc["collections"])}


def reorder_members(
    registry_root: Any,
    collection_id: str,
    member_keys: List[str],
) -> Dict[str, Any]:
    with _ledger_lock(registry_root):
        doc = load(registry_root)
        collection = _find(doc, collection_id)
        current = [item["member_key"] for item in collection["members"]]
        _require_exact_order(member_keys, current, noun="member")
        by_key = {item["member_key"]: item for item in collection["members"]}
        collection["members"] = [by_key[key] for key in member_keys]
        collection["updated_at"] = _now_iso()
        _write(registry_root, doc)
        return copy.deepcopy(collection)


def reorder_unfiled(
    registry_root: Any,
    workspace: str,
    member_keys: List[str],
) -> Dict[str, Any]:
    with _ledger_lock(registry_root):
        doc = load(registry_root)
        existing = _existing_member_keys(doc)
        items = [
            item
            for item in _supported_conversations(workspace)
            if _member_key(item["agent"], item["conversation_id"]) not in existing
        ]
        current = [_member_key(item["agent"], item["conversation_id"]) for item in items]
        _require_exact_order(member_keys, current, noun="unfiled member")
        doc["unfiled_order"] = member_keys
        _write(registry_root, doc)
        return {"unfiled": _ordered_unfiled(doc, items)}


def move_member(
    registry_root: Any,
    from_collection_id: str,
    to_collection_id: Optional[str],
    member_key: str,
    *,
    destination_order: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Atomically move one member to another Collection, or out to unfiled."""
    with _ledger_lock(registry_root):
        doc = load(registry_root)
        source = _find(doc, from_collection_id)
        member = next(
            (item for item in source["members"] if item.get("member_key") == member_key),
            None,
        )
        if member is None:
            raise CliError(
                message=f"Conversation is not a member: {member_key}",
                exit_code=3,
                error_code="AISC_ERR_WORK_COLLECTION_MEMBER_NOT_FOUND",
            )
        source["members"] = [
            item for item in source["members"] if item.get("member_key") != member_key
        ]
        source["updated_at"] = _now_iso()
        if to_collection_id is None:
            order = list(destination_order or [member_key])
            if member_key not in order:
                raise CliError(
                    message="Moved member missing from unfiled destination order",
                    exit_code=2,
                    error_code="AISC_ERR_USAGE",
                )
            doc["unfiled_order"] = order
            _write(registry_root, doc)
            return {"member": copy.deepcopy(member), "member_key": member_key, "collection_id": None}

        target = _find(doc, to_collection_id)
        if target["id"] != source["id"] and member_key in _existing_member_keys(doc):
            raise CliError(
                message=f"Conversation is already in another work collection: {member_key}",
                exit_code=1,
                error_code="AISC_ERR_WORK_COLLECTION_MEMBER_EXISTS",
            )
        target["members"].append(member)
        target["updated_at"] = _now_iso()
        if destination_order is not None:
            current = [item["member_key"] for item in target["members"]]
            _require_exact_order(destination_order, current, noun="member")
            by_key = {item["member_key"]: item for item in target["members"]}
            target["members"] = [by_key[key] for key in destination_order]
        _write(registry_root, doc)
        return {
            "member": copy.deepcopy(member),
            "member_key": member_key,
            "collection_id": target["id"],
        }


def _runtime_root(workspace: str) -> Path:
    return conversation._workspace_dir(workspace) / "runtime"


def _failure(member: Dict[str, Any], stage: str, exc: Exception) -> Dict[str, Any]:
    reason = (
        exc.message if isinstance(exc, CliError) else str(exc).strip()
    ) or exc.__class__.__name__
    return {
        "member_key": member["member_key"],
        "agent": member["agent"],
        "conversation_id": member["conversation_id"],
        "stage": stage,
        "reason": reason,
    }


def delete_collection(
    workspace: str,
    collection_id: str,
    *,
    terminator: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None,
    deleter: Optional[Callable[[str, str, str], Any]] = None,
) -> Dict[str, Any]:
    """Cascade-delete a Collection while keeping one bad member isolated.

    A missing transcript is treated as already deleted.  Other provider
    deletion errors are collected and do not stop later members or metadata
    cleanup, matching b6's partial-failure ruling.
    """
    runtime = _runtime_root(workspace)
    delete_provider = deleter or conversation.delete_conversation
    with _ledger_lock(runtime):
        doc = load(runtime)
        collection = _find(doc, collection_id)
        terminated: List[str] = []
        deleted: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []
        failed_keys: set[str] = set()

        for member in list(collection.get("members", [])):
            key = member["member_key"]
            if terminator is not None:
                try:
                    session_id = terminator(member)
                    if session_id:
                        terminated.append(str(session_id))
                except Exception as exc:
                    failures.append(_failure(member, "terminate", exc))
                    failed_keys.add(key)
                    continue
            try:
                delete_provider(
                    str(workspace),
                    member["conversation_id"],
                    member["agent"],
                )
                deleted.append(copy.deepcopy(member))
            except CliError as exc:
                if exc.error_code == conversation.ERROR_UNRESUMABLE:
                    deleted.append(copy.deepcopy(member))
                else:
                    failures.append(_failure(member, "delete", exc))
                    failed_keys.add(key)
            except Exception as exc:
                failures.append(_failure(member, "delete", exc))
                failed_keys.add(key)

        doc["collections"] = [
            item for item in doc["collections"] if item.get("id") != collection_id
        ]
        if doc["active_collection_id"] == collection_id:
            doc["active_collection_id"] = None
        _write(runtime, doc)
        return {
            "deleted": True,
            "collection_id": collection_id,
            "terminated_session_ids": terminated,
            "deleted_members": deleted,
            "failed_members": failures,
        }


