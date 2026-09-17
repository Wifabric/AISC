#!/usr/bin/env python3
"""Version consistency gate (0.1.0 A6, guide 3.4.2).

The four-piece contract, mechanically checked:
  1. src/aisc/VERSION  (single source of truth)
  2. workbench/src-tauri/tauri.conf.json version — PEP 440-normalized
     equality (the dash form `0.1.0-dev` stays legal there: it is the
     Workbench app version, semantically distinct; only the NORMALIZED
     values must agree)
  3. docs/releases/v<VERSION>.md exists (release notes ride the tag)
  4. optional --tag: the git tag must equal v<VERSION> (used by the
     publish pipeline's pre-build guard)

Exits 1 with a per-check report on any mismatch.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def pep440_normalized(v: str) -> str:
    """dash form -> dot form: 0.1.0-dev == 0.1.0.dev0"""
    m = re.match(r"^(\d+(?:\.\d+)*)(?:-dev(\d+)?)$", v.strip())
    if m:
        return f"{m.group(1)}.dev{m.group(2) or 0}"
    return v.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None, help="git tag that must equal v<VERSION>")
    args = ap.parse_args()

    version = (ROOT / "src" / "aisc" / "VERSION").read_text(encoding="utf-8").strip()
    problems: list[str] = []

    tauri = json.loads(
        (ROOT / "workbench" / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    tauri_v = pep440_normalized(str(tauri.get("version", "")))
    if tauri_v != version:
        problems.append(f"tauri.conf version {tauri.get('version')!r} (normalized "
                        f"{tauri_v!r}) != VERSION {version!r}")

    notes = ROOT / "docs" / "releases" / f"v{version}.md"
    if not notes.is_file():
        problems.append(f"release notes missing: docs/releases/v{version}.md")

    if args.tag and args.tag != f"v{version}":
        problems.append(f"tag {args.tag!r} != v{version}")

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print(f"OK: VERSION={version} tauri(normalized)={tauri_v} notes=v{version}.md"
          + (f" tag={args.tag}" if args.tag else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
