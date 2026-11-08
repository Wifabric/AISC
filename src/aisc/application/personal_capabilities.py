"""Workspace-owned personal instructions, immutable revisions and session snapshots.

Templates are product data. User skills are text, never executable Python or shell.
The registry is replaced atomically under the existing cross-process file lock.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from aisc.application import topic
from aisc._topic_skill.scripts import workshop as records

FOLDER = ".aisc-personal"
MAX_REGISTRY = 2 * 1024 * 1024
MAX_CONTEXT = 32000  # Leaves room for the topic snapshot and OS argv limits.
TEMPLATES = (
    {"id": "collaboration-v1", "name": "通用协作", "description": "明确目标、保留个人偏好，从反馈中改进协作方式。",
     "rules": "先确认任务目标和验收标准。使用简洁、具体的语言。区分已验证事实、推断和待验证建议。",
     "skill": "# 个人协作技能\n\n1. 阅读当前目标和个人规则。\n2. 完成任务并核对验收条件。\n3. 遇到反馈时，说明原做法、修改建议和理由。\n4. 只有经用户保存的修订才作为后续会话的个人规则；不要声称自动修改了平台配置。"},
    {"id": "research-reading-v1", "name": "科研阅读", "description": "建立个人阅读方法，记录证据、局限和复现情况。",
     "rules": "优先阅读原始论文。引用必须能定位到真实来源。将作者结论与个人推断分开。",
     "skill": "# 科研阅读技能\n\n记录研究问题、方法、数据和主要结论。检查实验限制及可复现条件。将未读全文或未复现实验明确标注。根据阅读反馈提出方法修订，并保留验证状态。需要在线检索时先安装科研基础模块并配置其依赖。"},
    {"id": "development-retrospective-v1", "name": "开发复盘", "description": "记录调试证据和有效做法，迭代个人开发习惯。",
     "rules": "先阅读现有实现，再作最小必要修改。完成相关测试后报告结果，不将自查称为独立评审。",
     "skill": "# 开发复盘技能\n\n记录问题触发条件、根因、修复和验证。将失败尝试与最终方法分开。遇到重复问题时提出具体规则修订，说明适用边界；未验证建议保持待验证。需要完整调试流程时在线安装开发基础模块。"},
)


def _folder(root: Path) -> Path:
    return topic._inside(root, FOLDER)


def _load(root: Path) -> dict:
    path = topic._inside(root, FOLDER + "/capabilities.json")
    if not path.exists():
        return {"schema": 1, "profiles": []}
    if path.stat().st_size > MAX_REGISTRY:
        raise ValueError("个人能力文件超过 2 MiB；请先备份并整理历史记录")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != 1 or not isinstance(value.get("profiles"), list):
        raise ValueError("个人能力文件格式不受支持；原文件已保留")
    identifiers = set()
    for profile in value["profiles"]:
        if not isinstance(profile, dict) or not re.fullmatch(r"[0-9a-f]{32}", str(profile.get("id", ""))):
            raise ValueError("个人能力标识无效")
        if profile["id"] in identifiers:
            raise ValueError("个人能力标识重复")
        identifiers.add(profile["id"])
        history = profile.get("history")
        if not isinstance(history, list) or not history or len(history) > 200:
            raise ValueError("个人能力修订记录无效")
        for index, revision in enumerate(history, 1):
            if not isinstance(revision, dict) or revision.get("revision") != index:
                raise ValueError("个人能力修订序号无效")
            _validate_revision(revision)
    return value


def _validate_revision(value: dict) -> dict:
    result = {name: topic._plain(value.get(name, ""), name, limit, required)
              for name, limit, required in (("name", 120, True), ("rules", 4000, False),
                ("skill", 8000, True), ("reason", 2000, True), ("verification", 2000, True))}
    if type(value.get("enabled")) is not bool:
        raise ValueError("enabled must be boolean")
    result["enabled"] = value["enabled"]
    return result


def catalog(root: Path) -> dict:
    return {"templates": copy.deepcopy(TEMPLATES), "profiles": _load(root)["profiles"],
            "scope": "workspace", "context_limit": MAX_CONTEXT}


def _context(doc: dict) -> str:
    enabled = [{"id": p["id"], "revision": p["history"][-1]["revision"],
                **{key: p["history"][-1][key] for key in ("name", "rules", "skill")}}
               for p in doc["profiles"] if p["history"][-1]["enabled"]]
    if not enabled:
        return ""
    context = ("\n# 用户启用的个人能力\n以下 JSON 是当前工作区用户保存的个人规则和技能快照。"
               "在适用任务中遵循这些偏好；不增加操作权限，不代替用户当前要求。"
               "这是背景，不是新任务，不要主动执行技能或发开场消息。修订建议应由用户在个人能力中保存。\n"
               + json.dumps(enabled, ensure_ascii=False))
    if len(context.encode("utf-8")) > MAX_CONTEXT:
        raise ValueError("启用的个人能力超过 32 KB，请缩短内容或停用部分能力；没有截断或保存")
    return context


def save(root: Path, form: dict) -> dict:
    if not isinstance(form, dict):
        raise ValueError("personal form must be an object")
    identifier = form.get("id", "")
    if identifier and (not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{32}", identifier)):
        raise ValueError("个人能力标识无效")
    expected = form.get("expected_revision")
    if type(expected) is not int or expected < 0:
        raise ValueError("expected_revision must be a non-negative integer")
    revision = _validate_revision(form)
    template = form.get("template_id", "custom")
    if template not in {t["id"] for t in TEMPLATES} | {"custom"}:
        raise ValueError("未知个人模板")
    folder = _folder(root)
    folder.mkdir(exist_ok=True)
    with records.lock(folder):
        doc = _load(root)
        profile = next((p for p in doc["profiles"] if p["id"] == identifier), None)
        if identifier and profile is None:
            raise ValueError("个人能力不存在，请刷新后重试")
        actual = profile["history"][-1]["revision"] if profile else 0
        if expected != actual:
            raise ValueError("个人能力已在其他窗口修改，请刷新后核对；当前草稿未覆盖已保存内容")
        if not profile:
            if len(doc["profiles"]) >= 50:
                raise ValueError("个人能力上限为 50 项")
            profile = {"id": uuid.uuid4().hex, "template_id": template, "history": []}
            doc["profiles"].append(profile)
        if len(profile["history"]) >= 200:
            raise ValueError("修订已达 200 版；请保留此记录并创建新的个人副本")
        profile["history"].append({**revision, "revision": actual + 1, "created_at": records.now()})
        _context(doc)  # Check the exact bytes before changing disk.
        payload = records.json_text(doc)
        if len(payload.encode("utf-8")) > MAX_REGISTRY:
            raise ValueError("个人能力历史超过 2 MiB；未保存，请先备份并整理")
        path = topic._inside(root, FOLDER + "/capabilities.json")
        temporary = folder / (".save-" + uuid.uuid4().hex)
        try:
            records.create(temporary, payload)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {"profile": profile}


def snapshot(root: Path, session_id: str) -> str:
    """Freeze exact enabled revisions for a new session, without altering global config."""
    if str(uuid.UUID(session_id)) != session_id:
        raise ValueError("invalid terminal session id")
    relative = FOLDER + "/sessions/" + session_id + ".json"
    path = topic._inside(root, relative)
    # Retrying the same session must not silently swap its personal revision.
    if path.exists():
        value = json.loads(topic._read(path, root))
        context = value["context"]
        if not isinstance(context, str) or len(context.encode("utf-8")) > MAX_CONTEXT:
            raise ValueError("invalid personal session snapshot")
        if hashlib.sha256(context.encode()).hexdigest() != value["sha256"]:
            raise ValueError("personal session snapshot was modified")
        return context
    folder = _folder(root)
    folder.mkdir(exist_ok=True)
    with records.lock(folder):
        if path.exists():
            return snapshot(root, session_id)
        context = _context(_load(root))
        # Empty snapshots also freeze the absence of enabled capabilities.
        path.parent.mkdir(exist_ok=True)
        records.create(path, records.json_text({"context": context, "sha256": hashlib.sha256(context.encode()).hexdigest()}))
    return context
