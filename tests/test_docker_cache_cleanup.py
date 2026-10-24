"""O7 (opt-batch, D-11): docker cache cleanup — argv invariants + flows."""
from types import SimpleNamespace

import pytest

from aisc.application.docker_lifecycle import (
    _cache_cleanup_argv,
    cache_usage,
    docker_cache_cleanup,
)
from aisc.domain.models import CliError


class FakeExecutor:
    def __init__(self, *, df_ok=True, prune_rc=0, images=""):
        self.df_ok = df_ok
        self.prune_rc = prune_rc
        self.images = images
        self.calls = []

    def run_captured(self, argv, timeout=60.0, input_text=None):
        self.calls.append(list(argv))
        if argv[:2] == ["system", "df"]:
            if not self.df_ok:
                return SimpleNamespace(exit_code=1, stdout="", stderr="docker down")
            return SimpleNamespace(
                exit_code=0,
                stdout=(
                    '{"Type":"Images","TotalCount":"5","Active":"1","Size":"8GB","Reclaimable":"1GB"}\n'
                    '{"Type":"Build Cache","TotalCount":"120","Active":"0","Size":"6.7GB","Reclaimable":"4.1GB"}\n'
                ),
                stderr="",
            )
        if argv[:2] == ["images", "--format"]:
            return SimpleNamespace(exit_code=0, stdout=self.images, stderr="")
        if argv[0] in ("builder", "image"):
            return SimpleNamespace(
                exit_code=self.prune_rc,
                stdout="Total reclaimed space: 4.1GB\n",
                stderr="",
            )
        if argv[:2] == ["rmi", "node:22-slim"]:
            return SimpleNamespace(exit_code=0, stdout="Untagged: node:22-slim\n", stderr="")
        return SimpleNamespace(exit_code=0, stdout="", stderr="")


def test_argv_invariants_never_global_prune_never_all_flag():
    builder = _cache_cleanup_argv("builder", 24)
    dangling = _cache_cleanup_argv("dangling", 48)
    for argv in (builder, dangling):
        assert argv[0] != "system"  # never a global prune
        assert "--force" in argv
    # `builder prune` WITHOUT --all only removes dangling cache (Docker 29
    #实测 1.303GB → 1.246GB)。构建缓存用户裁定为全量，因此 builder 必须 --all。
    assert "--all" in builder
    # image prune 仍绝不能 -a/--all：那只处理悬空镜像，不动正常镜像。
    assert "-a" not in dangling and "--all" not in dangling
    assert builder[0] == "builder" and builder[1] == "prune"
    assert dangling[0] == "image" and dangling[1] == "prune"
    # 2026-10-23 用户裁定：构建缓存全量清（无 until 过滤）；悬空镜像保 24h 窗。
    assert builder == ["builder", "prune", "--force", "--all"]
    assert "until=48h" in dangling


def test_argv_rejects_unknown_kind():
    with pytest.raises(ValueError):
        _cache_cleanup_argv("system", 24)


def test_usage_parses_df_rows():
    ex = FakeExecutor()
    data = cache_usage(ex)
    assert data["docker_available"] is True
    assert data["df"]["Build Cache"]["reclaimable"] == "4.1GB"
    assert data["df"]["Images"]["size"] == "8GB"


def test_usage_docker_down_reported_not_thrown():
    data = cache_usage(FakeExecutor(df_ok=False))
    assert data["docker_available"] is False
    assert data["df"] == {}


def test_cleanup_runs_both_prunes_and_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "aisc.adapters.maintenance_lock.docker_maintenance_lock_at_root",
        lambda root: _NullCtx(),
    )
    ex = FakeExecutor()
    data = docker_cache_cleanup(ex, min_age_hours=24, data_root=tmp_path)
    kinds = [argv[0] for argv in ex.calls if argv[1:2] == ["prune"]]
    assert kinds == ["builder", "image"]
    assert data["prunes"][0]["reclaimed"].startswith("Total reclaimed")
    assert data["df_after"]["Build Cache"]["size"] == "6.7GB"
    assert data["warnings"] == []




def test_cleanup_untags_node_base_image(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "aisc.adapters.maintenance_lock.docker_maintenance_lock_at_root",
        lambda root: _NullCtx(),
    )
    ex = FakeExecutor(images="node\t22-slim\nother/node\t22-slim\n")
    data = docker_cache_cleanup(ex, min_age_hours=24, data_root=tmp_path)
    assert ["rmi", "node:22-slim"] in ex.calls
    assert ["rmi", "other/node:22-slim"] not in ex.calls
    assert data["prunes"][-1]["kind"] == "node-image"
    assert data["warnings"] == []


def test_cleanup_refuses_zero_age(tmp_path):
    with pytest.raises(CliError):
        docker_cache_cleanup(FakeExecutor(), min_age_hours=0, data_root=tmp_path)


def test_cleanup_refuses_when_docker_down(monkeypatch, tmp_path):
    with pytest.raises(CliError):
        docker_cache_cleanup(FakeExecutor(df_ok=False), data_root=tmp_path)


def test_cleanup_prune_failure_is_warning_not_crash(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "aisc.adapters.maintenance_lock.docker_maintenance_lock_at_root",
        lambda root: _NullCtx(),
    )
    data = docker_cache_cleanup(FakeExecutor(prune_rc=1), data_root=tmp_path)
    assert len(data["warnings"]) == 2  # both prunes failed, both surfaced


class _NullCtx:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
