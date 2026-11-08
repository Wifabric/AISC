"""Execute the entrypoint's real scope initialization against disposable trees."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(not BASH, reason="bash is required")


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def shell_path(path):
    value = path.as_posix()
    if os.name == "nt":
        value = "/" + value[0].lower() + value[2:]
    return shlex.quote(value)


@pytest.fixture
def trees(tmp_path):
    factory, project = tmp_path / "factory", tmp_path / "project"
    for root in (factory, project):
        write(root / ".claude/skills/factory/SKILL.md", "factory skill")
        write(root / ".claude/plugins/installed_plugins.json", '{"version":2,"plugins":{}}')
        write(root / ".claude/plugins/known_marketplaces.json", '{"factory":{}}')
        write(root / ".claude/.factory-version", "new" if root == factory else "old")
        write(root / ".codex/config.toml", "")
        write(root / ".codex/skills/factory/SKILL.md", "factory skill")
    write(factory / ".claude/settings.json", '{"factory":true}')
    write(project / ".claude/settings.json", '{"custom":true}')
    write(factory / ".claude/plugins/cache/factory/content.txt", "new cache")
    write(project / ".claude/plugins/cache/factory/content.txt", "old cache")
    write(factory / ".claude/commands/new.md", "new command")
    for path in project.rglob("*"):
        if path.is_file():
            os.utime(path, (1_000_000_000, 1_000_000_000))
    return factory, project


def initialize(trees, *, force=False):
    factory, project = trees
    text = (ROOT / "container/entrypoint.sh").read_text(encoding="utf-8")
    start = text.index('if [ "$SCOPE" = "global" ]')
    end = text.index("# 插件 bundle 的注册表", start)
    variables = {
        "FACTORY_CLAUDE_DIR": factory / ".claude",
        "FACTORY_CODEX_DIR": factory / ".codex",
        "PROJECT_CLAUDE_DIR": project / ".claude",
        "PROJECT_CODEX_DIR": project / ".codex",
        "PROJECT_CC_SWITCH_DIR": project / ".cc-switch",
    }
    script = "set -e\nSCOPE=project\nFORCE_COPY_CLAUDE=" + str(int(force)) + "\n"
    script += "\n".join(f"{key}={shell_path(value)}" for key, value in variables.items())
    result = subprocess.run([BASH, "--noprofile", "--norc", "-s"],
                            input=script + "\n" + text[start:end],
                            text=True, encoding="utf-8", capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("content", [
    '{"version":2,"plugins":{"custom@private":[{"version":"1.0"}]}}',
    "{}", "", "invalid registry: preserve for diagnosis",
])
def test_upgrade_preserves_workspace_registries_and_updates_factory_assets(trees, content):
    factory, project = trees
    paths = [project / ".claude/plugins" / name for name in
             ("installed_plugins.json", "known_marketplaces.json")]
    for path in paths:
        write(path, content)
        os.utime(path, (1_000_000_000, 1_000_000_000))
    initialize(trees)
    initialize(trees)  # Restart must remain harmless after advancing the factory marker.
    assert all(path.read_text(encoding="utf-8") == content for path in paths)
    assert (project / ".claude/plugins/cache/factory/content.txt").read_text() == "new cache"
    assert (project / ".claude/commands/new.md").read_text() == "new command"
    assert (project / ".claude/.factory-version").read_text() == "new"
    assert (project / ".claude/settings.json").read_text() == '{"custom":true}'


@pytest.mark.parametrize("missing", ["skills", "plugins"])
def test_repair_missing_directory_does_not_reset_existing_configuration(trees, missing):
    _, project = trees
    shutil.rmtree(project / ".claude" / missing)
    registry = project / ".claude/plugins/installed_plugins.json"
    if missing == "skills":
        write(registry, '{"version":2,"plugins":{"user":[]}}')
    initialize(trees)
    assert (project / ".claude/settings.json").read_text() == '{"custom":true}'
    assert registry.read_text() == ('{"version":2,"plugins":{"user":[]}}' if missing == "skills"
                                    else '{"version":2,"plugins":{}}')
    assert (project / ".claude/skills/factory/SKILL.md").is_file()


def test_missing_registry_is_seeded_without_resetting_other_registry(trees):
    _, project = trees
    (project / ".claude/plugins/installed_plugins.json").unlink()
    other = write(project / ".claude/plugins/known_marketplaces.json", '{"user":{}}')
    initialize(trees)
    assert (project / ".claude/plugins/installed_plugins.json").read_text() == '{"version":2,"plugins":{}}'
    assert other.read_text() == '{"user":{}}'


@pytest.mark.parametrize("dangling", [False, True])
def test_upgrade_does_not_replace_registry_symlink_or_write_through_it(trees, dangling):
    _, project = trees
    registry = project / ".claude/plugins/installed_plugins.json"
    target = project / "outside.json"
    if not dangling:
        write(target, "private state")
    registry.unlink()
    try:
        registry.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    initialize(trees)
    assert registry.is_symlink()
    if dangling:
        assert not target.exists()
    else:
        assert target.read_text() == "private state"


def test_fresh_workspace_receives_factory_configuration(trees):
    factory, project = trees
    shutil.rmtree(project)
    initialize(trees)
    for path in factory.rglob("*"):
        if path.is_file():
            assert (project / path.relative_to(factory)).read_bytes() == path.read_bytes()


def test_explicit_force_copy_keeps_existing_reset_semantics(trees):
    _, project = trees
    initialize(trees, force=True)
    assert (project / ".claude/settings.json").read_text() == '{"factory":true}'
