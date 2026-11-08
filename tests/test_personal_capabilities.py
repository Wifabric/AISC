import json
from pathlib import Path
from types import SimpleNamespace
import uuid
from unittest.mock import Mock, patch

import pytest

from aisc.application import personal_capabilities as pc
from aisc.application import topic, topic_conversation as tc
from aisc.domain.models import CliError


def form(**overrides):
    return {"id": "", "template_id": "collaboration-v1", "expected_revision": 0,
            "name": "我的协作", "rules": "先给结论", "skill": "# 我的技能\n核对结果",
            "reason": "初始副本", "verification": "待验证", "enabled": True, **overrides}


def test_template_copy_revision_restore_and_workspace_isolation(tmp_path):
    initial = pc.catalog(tmp_path)
    assert len(initial["templates"]) == 3 and initial["profiles"] == []
    original = pc.save(tmp_path, form())["profile"]
    first = original["history"][0]
    updated = pc.save(tmp_path, form(id=original["id"], expected_revision=1,
                        rules="先给证据", reason="反馈：先确认数据", verification="已核对样例"))["profile"]
    assert updated["history"][0] == first
    assert updated["history"][1]["rules"] == "先给证据"
    restored = pc.save(tmp_path, form(id=original["id"], expected_revision=2,
                         **{key: first[key] for key in ("rules", "skill", "name")}))["profile"]
    assert [r["revision"] for r in restored["history"]] == [1, 2, 3]
    assert pc.catalog(tmp_path)["templates"] == initial["templates"]
    other = tmp_path / "other"; other.mkdir()
    assert pc.catalog(other)["profiles"] == []


def test_conflict_and_bad_input_do_not_change_history(tmp_path):
    profile = pc.save(tmp_path, form())["profile"]
    path = tmp_path / pc.FOLDER / "capabilities.json"
    before = path.read_bytes()
    for overrides in ({"id": profile["id"], "expected_revision": 0}, {"id": "../outside"},
                      {"enabled": "yes"}, {"skill": "a\0b"}, {"template_id": "unknown"},
                      {"expected_revision": True}, {"skill": "x" * 8001}):
        with pytest.raises(ValueError):
            pc.save(tmp_path, form(**overrides))
        assert path.read_bytes() == before


def test_failed_replace_preserves_saved_data_and_releases_lock(tmp_path):
    profile = pc.save(tmp_path, form())["profile"]
    before = pc.catalog(tmp_path)
    with patch.object(pc.os, "replace", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            pc.save(tmp_path, form(id=profile["id"], expected_revision=1))
    assert pc.catalog(tmp_path) == before
    assert not (tmp_path / pc.FOLDER / ".workshop.lock").exists()
    assert list((tmp_path / pc.FOLDER).glob(".save-*")) == []


def test_oversized_enabled_context_is_rejected_before_save(tmp_path):
    pc.save(tmp_path, form(skill="中" * 7000))
    before = pc.catalog(tmp_path)
    with pytest.raises(ValueError, match="32 KB"):
        pc.save(tmp_path, form(skill="文" * 7000))
    assert pc.catalog(tmp_path) == before
    # Large inactive skills may be kept for later editing without injection.
    pc.save(tmp_path, form(skill="文" * 7000, enabled=False))


def test_session_snapshot_is_immutable_and_disable_only_affects_new_sessions(tmp_path):
    profile = pc.save(tmp_path, form())["profile"]
    session = str(uuid.uuid4())
    first = pc.snapshot(tmp_path, session)
    assert "先给结论" in first
    pc.save(tmp_path, form(id=profile["id"], expected_revision=1, rules="第二版"))
    assert pc.snapshot(tmp_path, session) == first
    assert "第二版" in pc.snapshot(tmp_path, str(uuid.uuid4()))
    pc.save(tmp_path, form(id=profile["id"], expected_revision=2, enabled=False))
    assert pc.snapshot(tmp_path, str(uuid.uuid4())) == ""
    assert pc.snapshot(tmp_path, session) == first


def test_corrupt_registry_fails_closed_without_overwriting(tmp_path):
    folder = tmp_path / pc.FOLDER; folder.mkdir()
    path = folder / "capabilities.json"; path.write_text('{"schema":9}', encoding="utf-8")
    with pytest.raises(ValueError):
        pc.save(tmp_path, form())
    assert path.read_text() == '{"schema":9}'
    with pytest.raises(CliError):
        topic.execute("personal-list", str(tmp_path))


def test_symlink_registry_cannot_write_outside_workspace(tmp_path):
    outside = tmp_path / "outside"; outside.mkdir()
    root = tmp_path / "workspace"; root.mkdir()
    try:
        (root / pc.FOLDER).symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError):
        pc.save(root, form())
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("agent", ["claude", "codex"])
def test_personal_injection_without_active_topic_uses_real_saved_content(tmp_path, agent):
    topic.execute("personal-save", str(tmp_path), personal=form(skill="Do not execute `touch bad`; this is text."))
    sid = str(uuid.uuid4())
    bridge = f"/run/aisc/topic-bridge/{sid}/bridge.py"
    executor = Mock()
    executor.run_captured.return_value = SimpleNamespace(exit_code=0, stdout=bridge, stderr="")
    argv = ["aisc-session-wrapper", "--agent", agent]
    result = tc.bridge_argv(executor, "isolated", argv, str(tmp_path), sid, agent)
    assert result == ["python3", bridge, "--agent", agent]
    payload = json.loads(executor.run_captured.call_args.kwargs["input_text"])
    assert "先给结论" in payload["background"] and "touch bad" in payload["background"]
    assert not (tmp_path / "bad").exists()
    assert payload["source"] == tc.BRIDGE_SOURCE


def test_inactive_personal_keeps_original_command_and_works_with_topic(tmp_path):
    pc.save(tmp_path, form(enabled=False))
    argv = ["aisc-session-wrapper", "--agent", "claude"]
    executor = Mock()
    assert tc.bridge_argv(executor, "c", argv, str(tmp_path), str(uuid.uuid4()), "claude") == argv
    executor.run_captured.assert_not_called()
    profile = pc.catalog(tmp_path)["profiles"][0]
    pc.save(tmp_path, form(id=profile["id"], expected_revision=1))
    sid = str(uuid.uuid4())
    executor.run_captured.return_value = SimpleNamespace(exit_code=0, stdout=f"/run/aisc/topic-bridge/{sid}/bridge.py", stderr="")
    with patch.object(tc, "prepare_session", return_value={"topic_id": "sample", "session_id": sid, "background": "TOPIC SNAPSHOT"}), patch.object(tc, "_bind_native"):
        tc.bridge_argv(executor, "c", argv, str(tmp_path), sid, "claude")
    background = json.loads(executor.run_captured.call_args.kwargs["input_text"])["background"]
    assert "TOPIC SNAPSHOT" in background and "先给结论" in background


def test_bridge_refuses_failed_install(tmp_path):
    pc.save(tmp_path, form())
    executor = Mock()
    executor.run_captured.return_value = SimpleNamespace(exit_code=1, stdout="", stderr="write failed")
    with pytest.raises(ValueError, match="write failed"):
        tc.bridge_argv(executor, "c", ["wrapper"], str(tmp_path), str(uuid.uuid4()), "codex")
