"""Package the selected office-hours skill with its upstream runtime references."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil


_ROOT = re.compile(r"(?:~|\$HOME)/\.claude/skills/gstack/(office-hours/)?")
_ASSET = re.compile(r"(?:~|\$HOME)/\.claude/skills/gstack/((?:bin|lib|scripts|docs)/[\w./-]+|ETHOS\.md)")
_SHELL_HELPER = re.compile(
    r'(?:\$(?:_?BIN|SCRIPT_DIR|_SCRIPT_DIR|SELF_DIR)|\$\(dirname "\$0"\)|/bin)/'
    r'(gstack-[\w.-]+)'
)
_IMPORT = re.compile(r"""(?:\bfrom\s+|\b(?:import|require)\(\s*)["'](\.[\w./-]+)["']""")
_SHARED_DIRS = {"bin", "lib", "scripts", "docs"}


def package(checkout: Path, skill: Path, destination: Path) -> None:
    """Prepare in the disposable checkout, before replacing an installed skill."""
    checkout = checkout.resolve()
    installed = destination.as_posix()
    if not re.fullmatch(r"[\w:/.-]+", installed):
        raise ValueError("Unsupported container skill path")
    runtime = skill / ".aisc-gstack"
    runtime.mkdir()  # Never merge with an entry supplied by the repository.
    required = {"bin/gstack-skill-load", "bin/gstack-skill-start", "LICENSE",
                "VERSION", "scripts/one-way-doors.ts", "scripts/psychographic-signals.ts"}
    for document in skill.rglob("*.md"):
        original = document.read_text(encoding="utf-8")
        required.update(match.rstrip(".") for match in _ASSET.findall(original))
        relocated = _ROOT.sub(lambda match: installed + ("/" if match[1] else "/.aisc-gstack/"), original)
        document.write_text(relocated, encoding="utf-8")

    copied: set[str] = set()
    while required:
        name = required.pop()
        if name in copied:
            continue
        relative = Path(name)
        if (relative.is_absolute() or ".." in relative.parts
                or not (relative.parts[0] in _SHARED_DIRS or name in {"LICENSE", "VERSION", "ETHOS.md"})):
            raise ValueError(f"Unsupported gstack dependency: {name}")
        file = checkout / relative
        if not file.is_file() or file.resolve() != file:
            raise ValueError(f"Missing or linked gstack dependency: {name}")
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        copied.add(name)
        if relative.parts[0] not in {"bin", "lib", "scripts"}:
            continue
        source = file.read_text(encoding="utf-8")
        code = "\n".join(line for line in source.splitlines()
                         if not line.lstrip().startswith(("#", "//", "*")))
        for helper in _SHELL_HELPER.findall(code):
            candidate = "bin/" + helper.rstrip(".")
            if (checkout / candidate).is_file():
                required.add(candidate)
        for module in _IMPORT.findall(code):
            path = Path(os.path.normpath(file.parent / module))
            for candidate in (path, Path(str(path) + ".ts")):
                if candidate.is_relative_to(checkout) and candidate.is_file():
                    required.add(candidate.relative_to(checkout).as_posix())
                    break
