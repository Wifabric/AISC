#!/usr/bin/env python3
"""Version consistency gate (0.1.0 A6, guide 3.4.2).

The three-piece contract, mechanically checked:
  1. src/aisc/VERSION  (single source of truth, CLI track)
  2. docs/releases/v<VERSION>.md exists (release notes ride the tag)
  3. optional --tag: the git tag must equal v<VERSION> (used by the
     publish pipeline's pre-build guard)

The Workbench app version (workbench/src-tauri/tauri.conf.json) left this
contract on 2026-09-18 (dual-track ruling, DEVELOP_WIKI §8.4): it follows
the Workbench 2.1.x stage line, not the CLI version.

Exits 1 with a per-check report on any mismatch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None, help="git tag that must equal v<VERSION>")
    args = ap.parse_args()

    version = (ROOT / "src" / "aisc" / "VERSION").read_text(encoding="utf-8").strip()
    problems: list[str] = []

    notes = ROOT / "docs" / "releases" / f"v{version}.md"
    if not notes.is_file():
        problems.append(f"release notes missing: docs/releases/v{version}.md")

    if args.tag and args.tag != f"v{version}":
        problems.append(f"tag {args.tag!r} != v{version}")

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print(f"OK: VERSION={version} notes=v{version}.md"
          + (f" tag={args.tag}" if args.tag else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
