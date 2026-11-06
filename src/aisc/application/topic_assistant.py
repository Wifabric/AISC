"""Workspace-scoped assistant settings and pinned installed skill packages."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

from aisc._topic_skill.scripts import assistant as state
from aisc.application import topic as topics
from aisc.application.data_root import DataRootResolver

MAX_PACKAGE_BYTES = 20 * 1024 * 1024
MAX_PACKAGE_FILES = 500


def skill_root(root):
    return state.safe(DataRootResolver().resolve(root).workspace_dirs["cc-switch"] / "skills")


def package_files(folder):
    state.safe(folder)
    files, total = [], 0
    for parent, dirs, names in os.walk(folder, followlinks=False):
        for name in dirs:
            state.safe(Path(parent) / name)
        for name in sorted(names):
            path = state.safe(Path(parent) / name)
            if not path.is_file():
                raise ValueError("Skill package contains a non-regular file")
            size = path.stat().st_size
            total += size
            if size > 5 * 1024 * 1024 or total > MAX_PACKAGE_BYTES or len(files) >= MAX_PACKAGE_FILES:
                raise ValueError("Skill package exceeds 500 files / 20 MiB / 5 MiB per file")
            files.append(path)
    return sorted(files)


def installed(root):
    base = skill_root(root)
    result, warnings = [], []
    if not base.exists():
        return {"skills": result, "warnings": warnings}
    visited = 0
    for parent, dirs, names in os.walk(base, followlinks=False):
        visited += 1
        if visited > 2000 or len(result) >= 200:
            warnings.append("Installed skill scan reached its limit")
            break
        for name in dirs[:]:
            try:
                state.safe(Path(parent) / name)
            except ValueError:
                dirs.remove(name)
                warnings.append(f"Skipped linked skill directory: {name}")
        if "SKILL.md" in names:
            folder = Path(parent)
            try:
                content = topics._read(folder / "SKILL.md", base)
                title = folder.name
                for line in content.splitlines()[:30]:
                    if line.startswith("name:"):
                        title = line[5:].strip().strip('"\'') or title
                        break
                relative = folder.relative_to(base).as_posix()
                if relative == ".":
                    continue
                result.append({"id": relative, "name": title, "source": f"installed:{relative}"})
                dirs[:] = []  # References inside a package are not separate skills.
            except (OSError, ValueError) as exc:
                warnings.append(str(exc))
    return {"skills": result, "warnings": warnings}


def install_tools(topic):
    folder = topics._inside(topic, ".assistant-tools")
    folder.mkdir(exist_ok=True)
    for src, name in ((Path(state.__file__), "assistant.py"),
                      (topics.SKILL_ROOT / "references/assistant.md", "GUIDE.md")):
        target = topics._inside(topic, f".assistant-tools/{name}")
        # Explicit enable/save upgrades only these platform-owned helper resources.
        target.write_bytes(src.read_bytes())


def profile_path(root):
    folder = topics._inside(root, "topics")
    folder.mkdir(exist_ok=True)
    return topics._inside(root, "topics/.assistant-profile.json")


def show(root, identifier):
    topic = topics._topic(root, identifier)
    return {"assistant": state.read(topic / "assistant.json"),
            "profile": state.read(topics._inside(root, "topics/.assistant-profile.json"))}


def save(root, identifier, form):
    topic = topics._topic(root, identifier)
    state.update(topic / "assistant.json", form)
    install_tools(topic)
    return show(root, identifier)


def save_profile(root, identifier, form):
    topics._topic(root, identifier)
    if not isinstance(form, dict) or any(not isinstance(m, dict) or m.get("kind") != "preference" for m in form.get("memories", [])):
        raise ValueError("Workspace profile accepts preferences only")
    state.update(profile_path(root), form)
    return show(root, identifier)


def pin(root, identifier, form):
    topic = topics._topic(root, identifier)
    key = state.text(form.get("skill_id"), 1024)
    purpose = state.text(form.get("purpose"), 2000)
    item = next((s for s in installed(root)["skills"] if s["id"] == key), None)
    if item is None:
        raise ValueError("Select a currently installed skill; refresh the list")
    source = topics._inside(skill_root(root), key)
    files = package_files(source)
    baseline_id = uuid.uuid4().hex
    dest = topics._inside(topic, f".baselines/{baseline_id}")
    with state.locked(topic / "assistant.json"):
        doc = state.read(topic / "assistant.json")
        if form.get("expected_revision") != doc["revision"]:
            raise ValueError("Assistant changed since it was read; refresh before saving")
        if len(doc["baselines"]) >= 8:
            raise ValueError("At most 8 baselines are supported")
        if any(b["source"] == item["source"] for b in doc["baselines"]):
            raise ValueError("This skill is already pinned; remove it before choosing an updated version")
        try:
            dest.mkdir(parents=True)
            manifest, total = {}, 0
            for path in files:
                relative = path.relative_to(source).as_posix()
                data = state.safe(path).read_bytes()
                total += len(data)
                if len(data) > 5 * 1024 * 1024 or total > MAX_PACKAGE_BYTES:
                    raise ValueError("Skill package changed or grew beyond limits during copy")
                target = topics._inside(dest, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                manifest[relative] = hashlib.sha256(data).hexdigest()
            if "SKILL.md" not in manifest:
                raise ValueError("Skill entry point missing")
            fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
            doc["baselines"].append(dict(id=baseline_id, name=item["name"], purpose=purpose,
                source=item["source"], fingerprint=fingerprint,
                path=f".baselines/{baseline_id}/SKILL.md", files=manifest))
            doc["revision"] += 1
            state.write(topic / "assistant.json", doc)
        except Exception:
            # Only the freshly created, bounded snapshot is cleaned up.
            if dest.exists():
                topics._no_reparse(dest, topic)
                shutil.rmtree(dest)
            raise
    return show(root, identifier)


def unpin(root, identifier, form):
    topic = topics._topic(root, identifier)
    with state.locked(topic / "assistant.json"):
        doc = state.read(topic / "assistant.json")
        if form.get("expected_revision") != doc["revision"]:
            raise ValueError("Assistant changed since it was read; refresh before saving")
        identifier = form.get("baseline_id")
        if not any(b["id"] == identifier for b in doc["baselines"]):
            raise ValueError("Baseline not found")
        doc["baselines"] = [b for b in doc["baselines"] if b["id"] != identifier]
        doc["revision"] += 1
        state.write(topic / "assistant.json", doc)
    # Historical package remains available for old evidence, but is not active context.
    return show(root, topic.name)


def context(topic):
    doc = state.read(topic / "assistant.json")
    if not doc["enabled"]:
        return ""
    relative = f"{topics.CONTAINER_ROOT}/topics/{topic.name}"
    profile = state.read(topic.parent / ".assistant-profile.json")
    selected = [{k: b[k] for k in ("name", "purpose", "path", "fingerprint")} for b in doc["baselines"]]
    data = {"mode": doc["mode"], "memories": doc["memories"], "baselines": selected,
            "workspace_preferences": profile["memories"] if profile["enabled"] else []}
    return ("\n# 用户已启用主题助手\n"
            f"收到真实任务后读取 {relative}/.assistant-tools/GUIDE.md 并按其协作。"
            f"本轮有效模式为 {doc['mode']}。每个新任务核对 {relative}/assistant.json 的最新记忆，"
            "不要将旧快照覆盖用户后续删除/修改。记忆和技能不增加权限；禁用后停止使用。"
            "固定基线按用途读取，不自动执行其中脚本。以下只是启动时数据快照：\n" +
            json.dumps(data, ensure_ascii=False))
