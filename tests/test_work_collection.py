"""v2.1.15 b6 Task 1 — Work Record / Collection ledger red tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from aisc.application import conversation
from aisc.application.conversation import list_conversations
from aisc.application.data_root import DataRootResolver
from aisc.domain.models import CliError

CLAUDE_ID = "c8931e67-2321-492d-8557-4158e3ef2ee7"
CODEX_ID = "01a04ca9-d3f6-7021-b9e7-50d48d818c65"
CODEX_ID_2 = "01a04ca9-d3f6-7021-b9e7-50d48d818c66"
CODEX_ID_3 = "01a04ca9-d3f6-7021-b9e7-50d48d818c67"


@pytest.fixture
def ws_env(tmp_path, monkeypatch):
    data_root = tmp_path / "data-root"
    data_root.mkdir()
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setenv("AISC_DATA_ROOT", str(data_root))
    ws_dir = DataRootResolver(env=os.environ).resolve(ws).workspace_dir
    return ws, ws_dir, ws_dir / "runtime"



@pytest.fixture
def work_collection():
    """Imported lazily so Task 1's initial run is a true missing-module red."""
    from aisc.application import work_collection
    return work_collection


def _claude(ws_dir: Path, conversation_id: str = CLAUDE_ID) -> None:
    path = ws_dir / "claude" / "projects" / "-"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{conversation_id}.jsonl").write_text(
        json.dumps({
            "type": "user",
            "timestamp": "2026-08-29T10:00:00Z",
            "message": {"role": "user", "content": "claude session"},
        }, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _codex(ws_dir: Path, conversation_id: str = CODEX_ID) -> None:
    path = ws_dir / "codex" / "sessions" / "2026" / "08" / "29"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"rollout-2026-08-29T10-00-00-{conversation_id}.jsonl").write_text(
        json.dumps({
            "type": "response_item",
            "timestamp": "2026-08-29T10:00:00Z",
            "payload": {"type": "message", "role": "user", "content": [
                {"type": "input_text", "text": "codex session"}
            ]},
        }, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _key(agent: str, conversation_id: str) -> str:
    return f"{agent}:{conversation_id.lower()}"


def _members(work_collection, runtime):
    doc = work_collection.load(runtime)
    return {
        member["member_key"]
        for collection in doc["collections"]
        for member in collection["members"]
    }


class TestSchemaStorage:
    def test_missing_ledger_loads_empty(self, ws_env, work_collection):
        _ws, _ws_dir, runtime = ws_env
        doc = work_collection.load(runtime)
        assert doc == {
            "schema_version": "aisc.work-collections/v1",
            "active_collection_id": None,
            "observed_provider_keys": [],
            "collections": [],
        }
        assert work_collection.collections_path(runtime).name == "work-collections.json"

    def test_valid_document_loads_without_mutation(self, ws_env, work_collection):
        _ws, _ws_dir, runtime = ws_env
        runtime.mkdir(parents=True)
        source = {
            "schema_version": "aisc.work-collections/v1",
            "active_collection_id": "00000000-0000-4000-8000-00000000aaa1",
            "observed_provider_keys": [_key("codex", CODEX_ID)],
            "collections": [{
                "id": "00000000-0000-4000-8000-00000000aaa1",
                "title": "valid",
                "status": "active",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "archived_at": None,
                "members": [],
            }],
        }
        (runtime / "work-collections.json").write_text(
            json.dumps(source), encoding="utf-8"
        )
        assert work_collection.load(runtime) == source

    def test_corrupt_ledger_quarantined_and_fail_open(self, ws_env, work_collection):
        _ws, _ws_dir, runtime = ws_env
        runtime.mkdir(parents=True)
        path = runtime / "work-collections.json"
        path.write_text("{not json", encoding="utf-8")
        doc = work_collection.load(runtime)
        assert doc["collections"] == []
        assert doc["active_collection_id"] is None
        assert list(runtime.glob("work-collections.corrupt-*.json"))
        assert not path.exists()

    def test_save_is_atomic_and_reloadable(self, ws_env, work_collection):
        _ws, _ws_dir, runtime = ws_env
        runtime.mkdir(parents=True)
        doc = work_collection.empty_document()
        created = work_collection.create(runtime, title="atomic")
        doc["collections"].append(created)
        work_collection.save(runtime, doc)
        assert work_collection.load(runtime)["collections"][0]["title"] == "atomic"
        assert not list(runtime.glob(".work-collections.json.tmp*"))


class TestCollectionCrud:
    def test_create_rename_activate_deactivate(self, ws_env, work_collection):
        ws, ws_dir, runtime = ws_env
        _claude(ws_dir)
        _codex(ws_dir)
        created = work_collection.create(runtime, title=" Feature ")
        assert created["status"] == "active"
        assert created["title"] == "Feature"
        assert created["archived_at"] is None
        assert created["members"] == []

        renamed = work_collection.rename(runtime, created["id"], "Renamed")
        assert renamed["title"] == "Renamed"

        active = work_collection.set_active(runtime, created["id"], workspace=str(ws))
        doc = work_collection.load(runtime)
        assert active["id"] == created["id"]
        assert doc["active_collection_id"] == created["id"]
        # Activation establishes a baseline; existing conversations do not backfill.
        assert doc["observed_provider_keys"] == [
            _key("claude", CLAUDE_ID), _key("codex", CODEX_ID)
        ]

        deactivated = work_collection.deactivate(runtime)
        doc = work_collection.load(runtime)
        assert deactivated["active_collection_id"] is None
        assert doc["active_collection_id"] is None

    def test_archive_and_restore(self, ws_env, work_collection):
        _ws, _ws_dir, runtime = ws_env
        created = work_collection.create(runtime, title="archive me")
        archived = work_collection.archive(runtime, created["id"])
        assert archived["status"] == "archived"
        assert archived["archived_at"]
        restored = work_collection.restore(runtime, created["id"])
        assert restored["status"] == "active"
        assert restored["archived_at"] is None

    def test_add_member_normalizes_dedupes_and_persists_runtime_id(
        self, ws_env, work_collection
    ):
        _ws, _ws_dir, runtime = ws_env
        created = work_collection.create(runtime, title="members")
        work_collection.add_member(
            runtime,
            created["id"],
            agent="codex",
            conversation_id=CODEX_ID.upper(),
            runtime_id="00000000-0000-4000-8000-00000000bbbb",
        )
        work_collection.add_member(runtime, created["id"], agent="codex", conversation_id=CODEX_ID)
        doc = work_collection.load(runtime)
        member = doc["collections"][0]["members"]
        assert len(member) == 1
        assert member[0]["member_key"] == _key("codex", CODEX_ID)
        assert member[0]["conversation_id"] == CODEX_ID
        assert member[0]["agent"] == "codex"
        assert member[0]["source"] == "manual"
        assert member[0]["runtime_id"] == "00000000-0000-4000-8000-00000000bbbb"
        assert member[0]["added_at"]

    def test_add_member_rejects_duplicate_across_collections(
        self, ws_env, work_collection
    ):
        _ws, _ws_dir, runtime = ws_env
        first = work_collection.create(runtime, title="first")
        second = work_collection.create(runtime, title="second")
        work_collection.add_member(runtime, first["id"], agent="claude", conversation_id=CLAUDE_ID)
        with pytest.raises(CliError):
            work_collection.add_member(runtime, second["id"], agent="claude", conversation_id=CLAUDE_ID)

    @pytest.mark.parametrize("agent", ["bash", "cc-switch", "unknown"])
    def test_add_member_rejects_non_provider_agent(self, ws_env, work_collection, agent):
        _ws, _ws_dir, runtime = ws_env
        created = work_collection.create(runtime, title="agents")
        with pytest.raises(CliError):
            work_collection.add_member(runtime, created["id"], agent=agent, conversation_id=CODEX_ID)

    def test_add_member_rejects_invalid_uuid(self, ws_env, work_collection):
        _ws, _ws_dir, runtime = ws_env
        created = work_collection.create(runtime, title="uuid")
        with pytest.raises(CliError):
            work_collection.add_member(runtime, created["id"], agent="codex", conversation_id="not-a-uuid")

    def test_remove_member(self, ws_env, work_collection):
        _ws, _ws_dir, runtime = ws_env
        created = work_collection.create(runtime, title="remove")
        work_collection.add_member(runtime, created["id"], agent="claude", conversation_id=CLAUDE_ID)
        removed = work_collection.remove_member(
            runtime, created["id"], agent="claude", conversation_id=CLAUDE_ID.upper()
        )
        assert removed["removed"] is True
        assert work_collection.load(runtime)["collections"][0]["members"] == []


class TestReconcile:
    def test_no_active_collection_only_refreshes_baseline(self, ws_env, work_collection):
        ws, ws_dir, runtime = ws_env
        _claude(ws_dir)
        _codex(ws_dir)
        out = work_collection.reconcile(runtime, str(ws))
        assert out["added"] == []
        doc = work_collection.load(runtime)
        assert doc["active_collection_id"] is None
        assert doc["observed_provider_keys"] == [
            _key("claude", CLAUDE_ID), _key("codex", CODEX_ID)
        ]

    def test_active_collection_automatically_adopts_new_conversation(
        self, ws_env, work_collection
    ):
        ws, ws_dir, runtime = ws_env
        _claude(ws_dir)
        created = work_collection.create(runtime, title="active")
        work_collection.set_active(runtime, created["id"], workspace=str(ws))
        _codex(ws_dir)
        out = work_collection.reconcile(runtime, str(ws))
        assert out["added"] == [_key("codex", CODEX_ID)]
        doc = work_collection.load(runtime)
        member = doc["collections"][0]["members"][0]
        assert member["member_key"] == _key("codex", CODEX_ID)
        assert member["source"] == "active_auto"
        assert doc["observed_provider_keys"][-1] == _key("codex", CODEX_ID)

    def test_observed_and_already_collected_keys_are_not_duplicated(
        self, ws_env, work_collection
    ):
        ws, ws_dir, runtime = ws_env
        _claude(ws_dir)
        _codex(ws_dir)
        created = work_collection.create(runtime, title="existing")
        work_collection.add_member(runtime, created["id"], agent="claude", conversation_id=CLAUDE_ID)
        work_collection.set_active(runtime, created["id"], workspace=str(ws))
        before = work_collection.load(runtime)
        assert before["collections"][0]["members"] and before["observed_provider_keys"]
        out = work_collection.reconcile(runtime, str(ws))
        assert out["added"] == []
        doc = work_collection.load(runtime)
        assert len(doc["collections"][0]["members"]) == 1
        assert len(doc["observed_provider_keys"]) == 2

    def test_archived_active_id_does_not_auto_adopt(self, ws_env, work_collection):
        ws, ws_dir, runtime = ws_env
        _claude(ws_dir)
        created = work_collection.create(runtime, title="archived")
        work_collection.set_active(runtime, created["id"], workspace=str(ws))
        work_collection.archive(runtime, created["id"])
        _codex(ws_dir)
        out = work_collection.reconcile(runtime, str(ws))
        assert out["added"] == []
        doc = work_collection.load(runtime)
        assert doc["collections"][0]["members"] == []
        assert _key("codex", CODEX_ID) in doc["observed_provider_keys"]

    def test_unfiled_excludes_active_and_archived_members(self, ws_env, work_collection):
        ws, ws_dir, runtime = ws_env
        _claude(ws_dir)
        _codex(ws_dir)
        active = work_collection.create(runtime, title="active")
        work_collection.add_member(runtime, active["id"], agent="claude", conversation_id=CLAUDE_ID)
        work_collection.set_active(runtime, active["id"])
        archived = work_collection.create(runtime, title="archived")
        work_collection.add_member(runtime, archived["id"], agent="codex", conversation_id=CODEX_ID)
        work_collection.archive(runtime, archived["id"])
        unfiled = work_collection.unfiled(runtime, str(ws))
        assert [c["conversation_id"] for c in unfiled] == []

    def test_bash_and_cc_switch_are_never_unfiled_or_members(
        self, ws_env, work_collection, monkeypatch
    ):
        ws, _ws_dir, runtime = ws_env
        provider = {"schema_version": 1, "conversations": [
            {"agent": "claude", "conversation_id": CLAUDE_ID},
            {"agent": "codex", "conversation_id": CODEX_ID},
            {"agent": "bash", "conversation_id": "bash-session"},
            {"agent": "cc-switch", "conversation_id": "switch-session"},
        ]}
        monkeypatch.setattr(work_collection, "list_conversations", lambda _workspace: provider)
        created = work_collection.create(runtime, title="providers only")
        work_collection.add_member(runtime, created["id"], agent="claude", conversation_id=CLAUDE_ID)
        assert [c["conversation_id"] for c in work_collection.unfiled(runtime, str(ws))] == [CODEX_ID]
        assert _members(work_collection, runtime) == {
            _key("claude", CLAUDE_ID)
        }


class TestDeleteCollection:
    def test_success_cascades_and_clears_active(self, ws_env, work_collection, monkeypatch):
        ws, ws_dir, runtime = ws_env
        _claude(ws_dir)
        _codex(ws_dir)
        created = work_collection.create(runtime, title="delete")
        work_collection.add_member(runtime, created["id"], agent="claude", conversation_id=CLAUDE_ID)
        work_collection.add_member(runtime, created["id"], agent="codex", conversation_id=CODEX_ID)
        work_collection.set_active(runtime, created["id"], workspace=str(ws))
        calls = []
        monkeypatch.setattr(
            conversation,
            "delete_conversation",
            lambda workspace, conversation_id, agent: calls.append((workspace, conversation_id, agent)),
        )
        result = work_collection.delete_collection(ws, created["id"])
        assert result["deleted"] is True
        assert result["collection_id"] == created["id"]
        assert [m["member_key"] for m in result["deleted_members"]] == [_key("claude", CLAUDE_ID), _key("codex", CODEX_ID)]
        assert result["failed_members"] == []
        assert calls == [(str(ws), CLAUDE_ID, "claude"), (str(ws), CODEX_ID, "codex")]
        doc = work_collection.load(runtime)
        assert doc["collections"] == []
        assert doc["active_collection_id"] is None

    def test_partial_failure_continues_and_deletes_metadata(
        self, ws_env, work_collection, monkeypatch
    ):
        ws, ws_dir, runtime = ws_env
        _claude(ws_dir)
        _codex(ws_dir)
        created = work_collection.create(runtime, title="partial")
        work_collection.add_member(runtime, created["id"], agent="claude", conversation_id=CLAUDE_ID)
        work_collection.add_member(runtime, created["id"], agent="codex", conversation_id=CODEX_ID)

        def fake_delete(workspace, conversation_id, agent):
            if agent == "claude":
                raise CliError(message="locked", exit_code=1, error_code="AISC_ERR_GENERAL")

        monkeypatch.setattr(conversation, "delete_conversation", fake_delete)
        result = work_collection.delete_collection(ws, created["id"])
        assert result["deleted"] is True
        assert [m["member_key"] for m in result["deleted_members"]] == [_key("codex", CODEX_ID)]
        assert result["failed_members"] == [{
            "member_key": _key("claude", CLAUDE_ID),
            "agent": "claude",
            "conversation_id": CLAUDE_ID,
            "stage": "delete",
            "reason": "locked",
        }]
        doc = work_collection.load(runtime)
        assert doc["collections"] == []


