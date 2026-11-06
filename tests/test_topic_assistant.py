import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from aisc.application import topic, topic_assistant as app
from aisc._topic_skill.scripts import assistant as state


@pytest.fixture
def setup_topic(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("AISC_DATA_ROOT", str(data))
    item = topic.create_topic(workspace, "Practice", "Make a usable result", [])["topic"]
    return workspace, item["id"], workspace / item["relative_path"]


def memory(text="Prefer examples", kind="preference", status="confirmed", evidence=""):
    return dict(id="memory-1", text=text, kind=kind, status=status, evidence=evidence)


def skill(workspace):
    folder = app.skill_root(workspace) / "story"
    (folder / "references").mkdir(parents=True)
    (folder / "SKILL.md").write_text("---\nname: story\n---\nUse references/example.md", encoding="utf-8")
    (folder / "references/example.md").write_text("original method", encoding="utf-8")
    return folder


def test_new_topic_enabled_and_old_topic_opt_in(setup_topic):
    workspace, identifier, folder = setup_topic
    assert app.show(workspace, identifier)["assistant"]["enabled"]
    (folder / "assistant.json").unlink()
    (folder / ".skill/references/assistant.md").unlink()
    (folder / ".skill/scripts/assistant.py").unlink()
    original = (folder / ".skill/SKILL.md").read_bytes()
    assert not app.show(workspace, identifier)["assistant"]["enabled"]
    assert app.context(folder) == ""
    topic.prepare(workspace, identifier, "continue", "Continue")
    app.save(workspace, identifier, {"expected_revision": 0, "enabled": True})
    assert (folder / ".skill/SKILL.md").read_bytes() == original
    assert (folder / ".assistant-tools/assistant.py").is_file()


def test_memory_save_delete_and_disabled_context(setup_topic):
    workspace, identifier, folder = setup_topic
    app.save(workspace, identifier, {"expected_revision": 1, "memories": [memory()]})
    assert "Prefer examples" in app.context(folder)
    app.save(workspace, identifier, {"expected_revision": 2, "memories": []})
    assert "Prefer examples" not in app.context(folder)
    app.save(workspace, identifier, {"expected_revision": 3, "enabled": False})
    assert app.context(folder) == ""


def test_stale_update_cannot_overwrite_or_drop_baselines(setup_topic):
    workspace, identifier, folder = setup_topic
    app.save(workspace, identifier, {"expected_revision": 1, "mode": "coach"})
    with pytest.raises(ValueError, match="changed"):
        app.save(workspace, identifier, {"expected_revision": 1, "mode": "deliver"})
    assert state.read(folder / "assistant.json")["mode"] == "coach"


@pytest.mark.parametrize("change", [
    {"memories": [memory(kind="experience")]},
    {"memories": [memory(), memory()]},
    {"mode": "unknown"}, {"enabled": "yes"},
    {"memories": [memory(text="")]}])
def test_invalid_state_does_not_replace_existing(setup_topic, change):
    workspace, identifier, folder = setup_topic
    original = (folder / "assistant.json").read_bytes()
    with pytest.raises(ValueError):
        app.save(workspace, identifier, {"expected_revision": 1, **change})
    assert (folder / "assistant.json").read_bytes() == original


def test_profile_is_explicit_and_scoped_to_workspace(setup_topic, tmp_path):
    workspace, identifier, folder = setup_topic
    app.save_profile(workspace, identifier, {"expected_revision": 0, "enabled": True, "memories": [memory("Use concise explanations")]})
    second = topic.create_topic(workspace, "Second", "Practice", [])["topic"]
    assert "Use concise explanations" in app.context(workspace / second["relative_path"])
    other = tmp_path / "other"
    other.mkdir()
    third = topic.create_topic(other, "Other", "Practice", [])["topic"]
    assert "Use concise explanations" not in app.context(other / third["relative_path"])
    app.save_profile(workspace, identifier, {"expected_revision": 1, "enabled": False})
    assert "Use concise explanations" not in app.context(folder)
    with pytest.raises(ValueError, match="preferences only"):
        app.save_profile(workspace, identifier, {"expected_revision": 2, "memories": [memory(kind="rule")]})


def test_pin_complete_snapshot_survives_upstream_changes(setup_topic):
    workspace, identifier, folder = setup_topic
    source = skill(workspace)
    assert app.installed(workspace)["skills"][0]["id"] == "story"
    doc = app.pin(workspace, identifier, {"expected_revision": 1, "skill_id": "story", "purpose": "Story structure"})["assistant"]
    baseline = doc["baselines"][0]
    snapshot = folder / baseline["path"]
    assert (snapshot.parent / "references/example.md").read_text() == "original method"
    (source / "references/example.md").write_text("changed upstream")
    assert (snapshot.parent / "references/example.md").read_text() == "original method"
    assert baseline["files"]["references/example.md"] == hashlib.sha256(b"original method").hexdigest()
    with pytest.raises(ValueError, match="already pinned"):
        app.pin(workspace, identifier, {"expected_revision": 2, "skill_id": "story", "purpose": "Duplicate"})
    app.unpin(workspace, identifier, {"expected_revision": 2, "baseline_id": baseline["id"]})
    assert "Story structure" not in app.context(folder)
    assert snapshot.exists()  # Historical evidence still has its original resource.


def test_baseline_id_is_not_a_file_path(setup_topic):
    workspace, identifier, folder = setup_topic
    skill(workspace)
    for value in ("../secret", "C:/secret", "/etc", "story/../../secret"):
        with pytest.raises(ValueError):
            app.pin(workspace, identifier, {"expected_revision": 1, "skill_id": value, "purpose": "Test"})
    assert not (folder / ".baselines").exists()


def test_failed_copy_does_not_create_binding(setup_topic, monkeypatch):
    workspace, identifier, folder = setup_topic
    skill(workspace)
    monkeypatch.setattr(state, "write", lambda *args: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        app.pin(workspace, identifier, {"expected_revision": 1, "skill_id": "story", "purpose": "Test"})
    assert state.read(folder / "assistant.json")["baselines"] == []
    assert list((folder / ".baselines").iterdir()) == []


def test_package_limits_reject_before_copy(setup_topic, monkeypatch):
    workspace, identifier, folder = setup_topic
    skill(workspace)
    monkeypatch.setattr(app, "MAX_PACKAGE_FILES", 1)
    with pytest.raises(ValueError, match="exceeds"):
        app.pin(workspace, identifier, {"expected_revision": 1, "skill_id": "story", "purpose": "Test"})
    assert state.read(folder / "assistant.json")["baselines"] == []


def test_portable_agent_helper_updates_same_state(setup_topic):
    workspace, identifier, folder = setup_topic
    script = folder / ".assistant-tools/assistant.py"
    result = subprocess.run([sys.executable, str(script), "save", "--root", str(folder)],
        input=json.dumps({"expected_revision": 1, "mode": "coach", "memories": [memory()]}),
        text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert app.show(workspace, identifier)["assistant"]["mode"] == "coach"
    assert "Prefer examples" in app.context(folder)


def test_cli_dispatch_accepts_form_and_rejects_conflict(setup_topic):
    workspace, identifier, folder = setup_topic
    result = topic.execute("assistant-save", str(workspace), id=identifier,
                           form={"expected_revision": 1, "mode": "deliver"})
    assert result["assistant"]["mode"] == "deliver"
    from aisc.domain.models import CliError
    with pytest.raises(CliError) as error:
        topic.execute("assistant-save", str(workspace), id=identifier, form={"expected_revision": 1})
    assert "changed" in error.value.message
