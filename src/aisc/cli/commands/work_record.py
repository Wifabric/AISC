"""``aisc work-record`` — Work Record / Collection CLI surface (v2.1.15 b6).

This module is deliberately thin: provider transcript scanning, ledger
durability, and cascade deletion live in
``aisc.application.work_collection``.  Commands normalize JSON-envelope data
and human-readable failure summaries only.

Deleting a live PTY remains a Workbench-side orchestration step because the
ledger intentionally does not use ``runtime_id`` for identity or termination
(D-3); a local Workbench can safely close the matching tab before invoking
``work-record delete``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def _registry(workspace: str) -> Path:
    from aisc.application.data_root import DataRootResolver

    resolved = DataRootResolver().resolve(Path(workspace).resolve())
    return resolved.workspace_dir / "runtime"


def _collection_module():
    from aisc.application import work_collection

    return work_collection


def cmd_work_record_list(workspace: str) -> Dict[str, Any]:
    """Reconcile, then return Collections plus the computed unfiled view."""
    wc = _collection_module()
    runtime = _registry(workspace)
    reconciled = wc.reconcile(runtime, workspace)
    return {
        "schema_version": wc.WORK_COLLECTION_SCHEMA,
        "workspace": workspace,
        "active_collection_id": reconciled["active_collection_id"],
        "collections": reconciled["collections"],
        "unfiled": wc.unfiled(runtime, workspace),
    }


def cmd_work_record_create(workspace: str, title: str) -> Dict[str, Any]:
    wc = _collection_module()
    return {"collection": wc.create(_registry(workspace), title=title)}


def cmd_work_record_rename(workspace: str, collection_id: str, title: str) -> Dict[str, Any]:
    wc = _collection_module()
    return {"collection": wc.rename(_registry(workspace), collection_id, title)}


def cmd_work_record_activate(workspace: str, collection_id: str) -> Dict[str, Any]:
    wc = _collection_module()
    collection = wc.set_active(_registry(workspace), collection_id, workspace=workspace)
    return {"active_collection_id": collection["id"]}


def cmd_work_record_deactivate(workspace: str) -> Dict[str, Any]:
    wc = _collection_module()
    return wc.deactivate(_registry(workspace))


def cmd_work_record_archive(workspace: str, collection_id: str) -> Dict[str, Any]:
    wc = _collection_module()
    return {"collection": wc.archive(_registry(workspace), collection_id)}


def cmd_work_record_restore(workspace: str, collection_id: str) -> Dict[str, Any]:
    wc = _collection_module()
    return {"collection": wc.restore(_registry(workspace), collection_id)}


def cmd_work_record_add(
    workspace: str,
    collection_id: str,
    agent: str,
    conversation_id: str,
    runtime_id: str | None = None,
) -> Dict[str, Any]:
    wc = _collection_module()
    member = wc.add_member(
        _registry(workspace),
        collection_id,
        agent=agent,
        conversation_id=conversation_id,
        runtime_id=runtime_id,
    )
    return {"member": member}


def cmd_work_record_remove(
    workspace: str,
    collection_id: str,
    agent: str,
    conversation_id: str,
) -> Dict[str, Any]:
    wc = _collection_module()
    return wc.remove_member(
        _registry(workspace),
        collection_id,
        agent=agent,
        conversation_id=conversation_id,
    )


def cmd_work_record_reorder_collections(workspace: str, collection_ids: list[str]) -> Dict[str, Any]:
    wc = _collection_module()
    return wc.reorder_collections(_registry(workspace), collection_ids)


def cmd_work_record_reorder_members(
    workspace: str,
    collection_id: str,
    member_keys: list[str],
) -> Dict[str, Any]:
    wc = _collection_module()
    return {
        "collection": wc.reorder_members(
            _registry(workspace), collection_id, member_keys
        )
    }


def cmd_work_record_reorder_unfiled(
    workspace: str,
    member_keys: list[str],
) -> Dict[str, Any]:
    wc = _collection_module()
    return wc.reorder_unfiled(_registry(workspace), workspace, member_keys)


def cmd_work_record_move(
    workspace: str,
    from_collection_id: str,
    member_key: str,
    to_collection_id: str | None = None,
    destination_order: list[str] | None = None,
) -> Dict[str, Any]:
    wc = _collection_module()
    return wc.move_member(
        _registry(workspace),
        from_collection_id,
        to_collection_id,
        member_key,
        destination_order=destination_order,
    )


def cmd_work_record_delete(workspace: str, collection_id: str) -> Dict[str, Any]:
    wc = _collection_module()
    return wc.delete_collection(workspace, collection_id)


def cmd_work_record_reconcile(workspace: str) -> Dict[str, Any]:
    wc = _collection_module()
    return wc.reconcile(_registry(workspace), workspace)


def print_work_record_list(data: Dict[str, Any]) -> None:
    active_id = data.get("active_collection_id")
    print(f"Active: {active_id or '(none)'}")
    for collection in data.get("collections", []):
        marker = "*" if collection.get("id") == active_id else "-"
        status = collection.get("status", "active")
        members = collection.get("members", [])
        print(
            f"{marker} {collection.get('id', '')[:8]}  "
            f"{collection.get('title', '')}  [{status}]  ({len(members)} 成员)"
        )
        for member in members:
            print(
                f"    {member.get('agent', '?'):7s} "
                f"conv={member.get('conversation_id', '-')}  "
                f"source={member.get('source', '-')}"
            )
    unfiled = data.get("unfiled", [])
    print(f"未归档会话: {len(unfiled)}")
    for item in unfiled:
        print(
            f"    {item.get('agent', '?'):7s} "
            f"conv={item.get('conversation_id', '-')}  "
            f"{item.get('title', '')}"
        )


def print_work_record_delete(data: Dict[str, Any]) -> None:
    print(
        f"已删除工作记录 {data.get('collection_id', '')[:8]}；"
        f"成员 {len(data.get('deleted_members', []))} 个成功"
    )
    terminated = data.get("terminated_session_ids", [])
    if terminated:
        print("已终止 session:")
        for session_id in terminated:
            print(f"    {session_id}")
    failed = data.get("failed_members", [])
    if failed:
        print("删除失败成员:")
        for item in failed:
            print(
                f"    {item.get('agent', '?')}:{item.get('conversation_id', '')} "
                f"[{item.get('stage', 'delete')}] {item.get('reason', '')}"
            )

