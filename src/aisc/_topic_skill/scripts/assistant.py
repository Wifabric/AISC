"""Portable topic assistant state. Same validation for UI and Agent writes.

No model calls, global profile, background inference, or execution of skill files.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sys
import uuid

SCHEMA = "aisc.topic-assistant/v1"
MAX_BYTES = 128 * 1024
MODES = ("collaborate", "coach", "deliver")
KINDS = ("preference", "constraint", "experience", "rule")


def safe(path: Path) -> Path:
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Assistant paths cannot contain links or reparse points")
    return path


def text(value, limit=2000, empty=False):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        raise ValueError(f"Expected text up to {limit} characters")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise ValueError("Control characters are not allowed")
    return value


def defaults():
    return dict(schema=SCHEMA, revision=0, enabled=False, mode="collaborate", memories=[], baselines=[])


def validate(doc):
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError("Unsupported assistant schema")
    if type(doc.get("revision")) is not int or doc["revision"] < 0:
        raise ValueError("Invalid revision")
    if type(doc.get("enabled")) is not bool or doc.get("mode") not in MODES:
        raise ValueError("Invalid enabled flag or mode")
    memories = doc.get("memories")
    if not isinstance(memories, list) or len(memories) > 40:
        raise ValueError("At most 40 memories are supported")
    ids = set()
    budget = 0
    for item in memories:
        if not isinstance(item, dict) or item.get("kind") not in KINDS or item.get("status") not in ("confirmed", "provisional"):
            raise ValueError("Invalid memory kind or status")
        identifier = item.get("id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identifier) or identifier in ids:
            raise ValueError("Invalid or duplicate memory id")
        ids.add(identifier)
        text(item.get("text"))
        text(item.get("evidence", ""), 1000, empty=True)
        budget += len((item["text"] + item.get("evidence", "")).encode("utf-8"))
        if budget > 16000:
            raise ValueError("Memory content exceeds the 16000-byte context budget")
        if item["kind"] == "experience" and item["status"] == "confirmed" and not item.get("evidence", "").strip():
            raise ValueError("Confirmed experience needs evidence and applicable conditions")
    baselines = doc.get("baselines")
    if not isinstance(baselines, list) or len(baselines) > 8:
        raise ValueError("At most 8 baselines are supported")
    ids = set()
    for item in baselines:
        if not isinstance(item, dict) or not re.fullmatch(r"[a-f0-9]{32}", item.get("id", "")) or item["id"] in ids:
            raise ValueError("Invalid or duplicate baseline id")
        ids.add(item["id"])
        for field in ("name", "purpose", "source", "fingerprint"):
            text(item.get(field), 2000)
        if not re.fullmatch(r"[a-f0-9]{64}", item["fingerprint"]):
            raise ValueError("Invalid baseline fingerprint")
        if item.get("path") != f".baselines/{item['id']}/SKILL.md":
            raise ValueError("Invalid baseline path")
    return doc


def read(path: Path):
    safe(path)
    if not path.exists():
        return defaults()
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Assistant state exceeds size limit")
    return validate(json.loads(raw.decode("utf-8-sig")))


@contextmanager
def locked(path):
    safe(path)
    lock = safe(path.with_name(path.name + ".lock"))
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError("Assistant is being saved; refresh and retry") from exc
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def write(path, doc):
    validate(doc)
    raw = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("Assistant state exceeds size limit")
    temp = safe(path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp"))
    try:
        with temp.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def update(path, form):
    if not isinstance(form, dict):
        raise ValueError("Assistant update must be an object")
    with locked(path):
        doc = read(path)
        if type(form.get("expected_revision")) is not int or form["expected_revision"] != doc["revision"]:
            raise ValueError("Assistant changed since it was read; refresh before saving")
        for field in ("enabled", "mode", "memories"):
            if field in form:
                doc[field] = form[field]
        doc["revision"] += 1
        write(path, doc)
    return doc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=("show", "save", "profile-show", "profile-save"))
    p.add_argument("--root", required=True, help="Existing topic directory")
    args = p.parse_args()
    root = safe(Path(args.root).absolute())
    if not (root / "topic.json").is_file() or root.parent.name != "topics":
        raise ValueError("Expected an existing workspace/topics/<topic> directory")
    profile = args.operation.startswith("profile-")
    path = root.parent / ".assistant-profile.json" if profile else root / "assistant.json"
    if args.operation.endswith("save"):
        raw = sys.stdin.read(MAX_BYTES + 1)
        if len(raw.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Input too large")
        form = json.loads(raw)
        if profile and any(not isinstance(m, dict) or m.get("kind") != "preference" for m in form.get("memories", [])):
            raise ValueError("Workspace profile accepts preferences only")
        result = update(path, form)
    else:
        result = read(path)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
