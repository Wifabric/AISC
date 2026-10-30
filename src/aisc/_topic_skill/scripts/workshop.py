#!/usr/bin/env python3
"""Local topic records. Python 3.9+, standard library; no network or auto-capture."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import uuid

VERSION = "0.3.2"

LOG_MARKER = "<!-- topic-workshop:derived-iteration-log:v1 -->"


def iteration_log(root, known=None):
    """Readable projection of revisions; never invent missing historical facts."""
    known = events(root) if known is None else known
    title = read_json(local(root, "topic.json")).get("topic", root.name)
    def prose(value):
        if isinstance(value, dict):
            labels = {"practical_use": "实际使用", "record_check": "记录检查", "status": "状态", "scope": "检查范围", "warnings": "提示", "errors": "错误", "checked_events": "检查记录数"}
            return "；".join(f"{labels.get(k, k)}：{prose(v)}" for k, v in value.items()) or "无"
        if isinstance(value, list):
            return "；".join(prose(v) for v in value) or "无"
        if isinstance(value, (int, float, bool)):
            return str(value)
        if not isinstance(value, str) or not value.strip():
            return "未记录，需核对原始依据。"
        return value.strip().replace("\n", "\n  ")
    lines = [LOG_MARKER, f"# {prose(title)} — 手册迭代日志", "",
        "> 从修订事件自动整理，最新记录在前；日期按记录时间（UTC）。普通聊天不计为手册修订。",
        "> 请通过追加修订/纠正事件更新，不直接编辑本文件。记录检查通过不代表现实效果成立。", ""]
    revisions = sorted((e for e in known.values() if e.get("type") == "revision"),
        key=lambda e: (e.get("recorded_at", ""), local(root, f"journal/{e['id']}.json").stat().st_mtime_ns, e["id"]), reverse=True)
    if not revisions:
        lines += ["尚无手册修订记录。已有手册不代表其历史修改过程已被记录。", ""]
    for event in revisions:
        identifier = event["id"]
        require(ID.fullmatch(identifier), "invalid revision id")
        data = event["data"]
        lines += [f"## {prose(event.get('summary'))}（{event.get('recorded_at', '时间未记录')}）", "",
            f"- 触发原因：{prose(data.get('trigger') or data.get('reason'))}",
            f"- 原有做法：{prose(data.get('previous'))}",
            f"- 本次修改：{prose(data.get('change'))}",
            f"- 修改理由：{prose(data.get('reason'))}",
            f"- 修订状态：{prose(data.get('status'))}（只描述修订状态）",
            f"- 验证结果说明：{prose(data.get('verification'))}",
            f"- 后续验证/事项：{prose(data.get('next_steps'))}",
            f"- 修订原始记录：[{identifier}](journal/{identifier}.json)"]
        for ref in event.get("related", []):
            require(isinstance(ref, str) and ID.fullmatch(ref), "invalid related event id")
            linked = known.get(ref)
            if linked is None:
                lines.append(f"- 缺失依据：{ref}（需修复关联）")
                continue
            lines.append(f"- 关联依据：[{prose(linked.get('summary'))}](journal/{ref}.json)")
            detail = linked.get("data", {})
            if linked.get("type") == "trial":
                lines.append(f"  - 检查状态：{prose(detail.get('status'))}；证据类别：{prose(detail.get('evidence_kind'))}；结果：{prose(detail.get('outcome'))}")
            elif linked.get("type") == "checkpoint":
                lines.append(f"  - [手册快照](snapshots/{ref}/TOPIC_GUIDE.md) · [状态快照](snapshots/{ref}/STATE.md)")
        lines.append("")
    return "\n".join(lines)


def write_iteration_log(root, known=None):
    """Caller holds topic lock. Unmanaged existing files are never replaced."""
    path = local(root, "ITERATION_LOG.md")
    payload = iteration_log(root, known)
    if path.exists():
        previous = path.read_text(encoding="utf-8")
        require(previous.startswith(LOG_MARKER + "\n"),
                "ITERATION_LOG.md already exists and is not generated; preserved original")
        if previous == payload:
            return
    temporary = local(root, "ITERATION_LOG.md.tmp-" + uuid.uuid4().hex)
    create(temporary, payload)
    os.replace(temporary, path)


def rebuild_log(root):
    with lock(root):
        write_iteration_log(root)
    return {"status": "rebuilt", "path": "ITERATION_LOG.md"}
SCHEMA = "topic-workshop/1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
FIELDS = {
    "interaction": ("speaker", "capture", "coverage", "text"),
    "source": ("locator", "capture", "description"),
    "decision": ("decision", "reason", "scope", "status"),
    "trial": ("setting", "status", "evidence_kind", "success_criteria", "outcome", "evidence"),
    "feedback": ("reporter", "text", "basis"),
    "revision": ("change", "reason", "before", "after", "status"),
    "skill_proposal": ("problem", "hypothesis", "scope", "proposed_change", "validation", "status"),
    "limitation": ("issue", "impact", "next_action"),
    "checkpoint": ("reason", "files"),
}
ENUMS = {
    "interaction": {"speaker": {"user", "assistant"}, "capture": {"verbatim", "summary", "partial"}},
    "source": {"capture": {"file", "url", "summary", "partial"}},
    "decision": {"scope": {"topic"}, "status": {"confirmed", "provisional"}},
    "trial": {
        "setting": {"real", "simulation"},
        "status": {"planned", "passed", "failed", "blocked", "not_run"},
        "evidence_kind": {"artifact_check", "user_report", "observed_use", "external_result", "simulation"},
    },
    "feedback": {"basis": {"user_report", "observed", "artifact_review", "simulation"}},
    "revision": {"status": {"applied"}},
    "skill_proposal": {"status": {"proposed", "tested", "accepted", "rejected"}},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def text(value):
    return isinstance(value, str) and bool(value.strip())


def no_links(path):
    for component in (path, *path.parents):
        require(not component.is_symlink() and not getattr(component, "is_junction", lambda: False)(),
                f"symlink/junction not allowed: {component}")


def local(root, relative):
    require(text(relative) and "\\" not in relative and ":" not in relative,
            "expected a workspace-relative path with / separators")
    parts = PurePosixPath(relative)
    require(not parts.is_absolute() and ".." not in parts.parts and parts.parts,
            "path must stay inside topic root")
    path = root.joinpath(*parts.parts)
    no_links(path)
    require(path.resolve().is_relative_to(root.resolve()), "path escaped topic root")
    return path


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique)


def create(path, payload):
    # Exclusive creation preserves previous records. A partial file after an I/O
    # interruption is detected by check; it is never silently overwritten.
    no_links(path)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def root_path(value, initialized=True):
    root = Path(value).absolute()
    no_links(root)
    if initialized:
        require(root.is_dir(), "topic root does not exist")
        meta = read_json(local(root, "topic.json"))
        require(isinstance(meta, dict) and meta.get("schema") == SCHEMA, "unsupported topic schema")
        for directory in ("journal", "work", "snapshots"):
            require(local(root, directory).is_dir(), f"missing directory: {directory}")
    return root


@contextmanager
def lock(root):
    path = local(root, ".workshop.lock")
    try:
        create(path, json_text({"pid": os.getpid(), "created_at": now()}))
    except FileExistsError as exc:
        raise FileExistsError(
            "topic is locked: .workshop.lock; another writer may be active. "
            "After a crash, follow stale-lock recovery in references/recording.md; do not delete blindly."
        ) from exc
    try:
        yield
    finally:
        path.unlink()


def events(root):
    result = {}
    for path in sorted(local(root, "journal").glob("*.json")):
        no_links(path)
        event = read_json(path)
        require(isinstance(event, dict), f"event must be object: {path.name}")
        require(event.get("id") == path.stem, f"id/filename mismatch: {path.name}")
        result[path.stem] = event
    return result


def validate(event, root, known):
    require(isinstance(event, dict), "event must be a JSON object")
    for field in ("id", "type", "session", "occurred_at", "summary"):
        require(text(event.get(field)), f"missing/non-string field: {field}")
    require(ID.fullmatch(event["id"]), "invalid event id")
    kind = event["type"]
    require(kind in FIELDS, "unknown event type")
    related = event.get("related")
    require(isinstance(related, list) and all(text(v) for v in related), "related must be string array")
    require(event["id"] not in related and len(set(related)) == len(related), "self/duplicate related id")
    require(all(v in known for v in related), "related event missing")
    data = event.get("data")
    require(isinstance(data, dict), "data must be object")
    for field in FIELDS[kind]:
        if field not in ("evidence", "success_criteria", "files"):
            require(text(data.get(field)), f"missing/non-string data.{field}")
    for field, allowed in ENUMS.get(kind, {}).items():
        require(data.get(field) in allowed, f"invalid data.{field}")
    if kind in {"decision", "feedback", "trial", "revision", "skill_proposal"}:
        require(related, f"{kind} needs a related source/interaction/record")
    if kind == "trial":
        criteria = data.get("success_criteria")
        require(isinstance(criteria, list) and criteria and all(text(v) for v in criteria),
                "success_criteria must be a nonempty string array")
        evidence = data.get("evidence")
        require(isinstance(evidence, list), "evidence must be array")
        if data["status"] in {"passed", "failed"}:
            require(evidence, "passed/failed trial needs evidence")
        if data["setting"] == "simulation":
            require(data["evidence_kind"] not in {"observed_use", "external_result"},
                    "simulation cannot claim observed real-world use/results")
        for item in evidence:
            require(isinstance(item, dict) and text(item.get("value")) and text(item.get("note")),
                    "evidence needs kind/value/note")
            if item.get("kind") == "file":
                evidence_path = local(root, item["value"])
                require(evidence_path.is_file(), "evidence file missing")
                if "sha256" in item:
                    require(hashlib.sha256(evidence_path.read_bytes()).hexdigest() == item["sha256"],
                            "evidence file changed; preserve the original and record a new version")
            elif item.get("kind") == "url":
                require(item["value"].startswith(("https://", "http://")), "invalid evidence URL")
            elif item.get("kind") == "event":
                require(item["value"] in known and item["value"] != event["id"], "evidence event missing/self")
            else:
                raise ValueError("unknown evidence kind")
    if kind == "revision":
        require(data["before"] != data["after"], "revision needs distinct before/after snapshots")
        for field in ("before", "after"):
            ref = data[field]
            require(ref in related and known.get(ref, {}).get("type") == "checkpoint",
                    f"revision {field} must reference a related checkpoint")
    if kind == "checkpoint":
        files = data.get("files")
        require(isinstance(files, list) and len(files) == 2, "checkpoint requires guide and state")
        expected = {f"snapshots/{event['id']}/TOPIC_GUIDE.md", f"snapshots/{event['id']}/STATE.md"}
        require(all(isinstance(item, dict) for item in files), "invalid checkpoint files")
        require({item.get("path") for item in files} == expected, "checkpoint paths mismatch")
        for item in files:
            path = local(root, item["path"])
            require(path.is_file(), "checkpoint file missing")
            require(hashlib.sha256(path.read_bytes()).hexdigest() == item.get("sha256"),
                    "checkpoint digest mismatch")


def init(root, topic):
    require(text(topic), "topic is empty")
    require(not root.exists() or (root.is_dir() and not any(root.iterdir())),
            "init refuses a nonempty/existing topic; use resume")
    templates = Path(__file__).resolve().parent.parent / "assets"
    contents = {name: (templates / name).read_text(encoding="utf-8").replace("{{topic}}", topic)
                for name in ("TOPIC_GUIDE.md", "STATE.md")}
    root.mkdir(parents=True, exist_ok=True)
    with lock(root):
        for directory in ("journal", "work", "snapshots"):
            local(root, directory).mkdir()
        for name, content in contents.items():
            create(local(root, name), content)
        create(local(root, "topic.json"), json_text({"schema": SCHEMA, "topic": topic,
               "created_at": now(), "skill": "topic-workshop", "skill_version": VERSION}))
        write_iteration_log(root, {})
    return {"status": "initialized", "root": str(root), "validation": "not_started"}


def append(root, event):
    require(event.get("type") != "checkpoint", "use checkpoint command for snapshots")
    with lock(root):
        known = events(root)
        require(event.get("id") not in known, "event id already exists; append a correction")
        validate(event, root, known)
        event = json.loads(json.dumps(event))
        if event["type"] == "trial":
            for item in event["data"]["evidence"]:
                if item["kind"] == "file":
                    item["sha256"] = hashlib.sha256(local(root, item["value"]).read_bytes()).hexdigest()
        event.update(recorded_at=now(), skill_version=VERSION)
        create(local(root, f"journal/{event['id']}.json"), json_text(event))
        known[event["id"]] = event
        try:
            write_iteration_log(root, known)
        except (OSError, ValueError) as exc:
            return {"status": "recorded", "id": event["id"], "warnings": [f"事件已保存，迭代日志未更新：{exc}"]}
    return {"status": "recorded", "id": event["id"]}


def checkpoint(root, reason):
    require(text(reason), "checkpoint reason is empty")
    with lock(root):
        identifier = "cp-" + uuid.uuid4().hex
        target = local(root, f"snapshots/{identifier}")
        # Read both files before creating a snapshot directory.
        content = {name: local(root, name).read_bytes() for name in ("TOPIC_GUIDE.md", "STATE.md")}
        target.mkdir()
        files = []
        for name, payload in content.items():
            path = local(root, f"snapshots/{identifier}/{name}")
            with path.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            files.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(payload).hexdigest()})
        event = {"id": identifier, "type": "checkpoint", "session": "script", "occurred_at": now(),
                 "recorded_at": now(), "skill_version": VERSION, "summary": reason, "related": [],
                 "data": {"reason": reason, "files": files}}
        validate(event, root, events(root))
        create(local(root, f"journal/{identifier}.json"), json_text(event))
    return {"status": "snapshotted", "id": identifier}


def check(root):
    errors, warnings = [], []
    with lock(root):
        known = events(root)
        for identifier, event in known.items():
            try:
                validate(event, root, known)
                require(text(event.get("recorded_at")) and text(event.get("skill_version")),
                        "missing recording provenance")
                if event.get("type") == "trial":
                    for item in event["data"]["evidence"]:
                        if item.get("kind") == "file" and "sha256" not in item:
                            warnings.append(f"{identifier}: evidence has no fingerprint; historical content unverified")
            except (ValueError, OSError) as exc:
                errors.append(f"{identifier}: {exc}")
        for name in ("TOPIC_GUIDE.md", "STATE.md"):
            path = local(root, name)
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                errors.append(f"missing/empty {name}")
        for path in local(root, "snapshots").iterdir():
            if path.name not in known:
                warnings.append(f"unindexed snapshot (possible interrupted checkpoint): {path.name}")
        if not any(e.get("type") == "trial" for e in known.values()):
            warnings.append("no trial record; practical usefulness remains unverified")
    return {"status": "failed" if errors else "passed", "checked_events": len(known),
            "errors": errors, "warnings": warnings,
            "scope": "structure, local evidence existence/fingerprints and snapshot hashes only; not factual/domain validation"}


def main():
    # Keep JSON usable for Chinese paths even when the Windows host selects a
    # legacy console encoding. File contents are independently UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "record", "checkpoint", "check", "rebuild-log"):
        command = commands.add_parser(name)
        command.add_argument("--root", required=True)
        if name == "init":
            command.add_argument("--topic", required=True)
        elif name == "record":
            command.add_argument("--input", required=True, help="UTF-8 JSON event draft")
        elif name == "checkpoint":
            command.add_argument("--reason", required=True)
    args = parser.parse_args()
    try:
        root = root_path(args.root, args.command != "init")
        if args.command == "init":
            result = init(root, args.topic)
        elif args.command == "record":
            event = read_json(Path(args.input))
            require(isinstance(event, dict), "event must be a JSON object")
            result = append(root, event)
        elif args.command == "checkpoint":
            result = checkpoint(root, args.reason)
        elif args.command == "rebuild-log":
            result = rebuild_log(root)
        else:
            result = check(root)
        print(json_text(result), end="")
        return 1 if result["status"] == "failed" else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json_text({"status": "error", "error": str(exc)}), end="")
        return 1


if __name__ == "__main__":
    sys.exit(main())
