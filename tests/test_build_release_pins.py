"""Pinned build inputs must survive mirror fallback and local image reuse."""
import json

import pytest

from aisc.cli.commands.build import _base_image_candidates, _ensure_base_image, plan_build, run_build
from aisc.domain.models import BuildPlan, CliError, DockerPreflightResult, ImageInspectResult, ImageInspectStatus, ProcessResult


DIGEST = "sha256:55fb5f5a527ea2c5c4a95f963e48ef90aa38c7b346054fdc8ee9957a2b55d205"
IMAGE_ID = "sha256:" + "a" * 64
OTHER_ID = "sha256:" + "b" * 64
SELECTED = "mirror.example/library/node:24.22.1-slim@" + DIGEST
FALLBACK = "fallback.example/library/node:24.22.1-slim@" + DIGEST
LOCAL = "aisc-node-base:" + DIGEST.replace(":", "-")


def image_doc(digest=DIGEST, image_id=IMAGE_ID):
    # The engine may record the upstream repository instead of the pull alias.
    return {"Id": image_id, "RepoDigests": ["docker.io/library/node@" + digest]}


class PinnedDocker:
    def __init__(self, *, cached=None, pulls=None, tag_ok=True, driver="docker"):
        self.images = dict(cached or {})
        self.pulls = dict(pulls or {})
        self.tag_ok = tag_ok
        self.driver = driver
        self.calls = []

    def preflight(self):
        return DockerPreflightResult(available=True)

    def inspect_image(self, ref):
        self.calls.append(["inspect_image", ref])
        doc = self.images.get(ref)
        return ImageInspectResult(
            status=ImageInspectStatus.EXISTS if doc else ImageInspectStatus.MISSING,
            image=ref, image_id=doc.get("Id", "") if doc else "",
        )

    def run_captured(self, argv, **kwargs):
        self.calls.append(list(argv))
        if argv == ["context", "show"]:
            return ProcessResult(exit_code=0, stdout="desktop-linux\n")
        if argv == ["buildx", "inspect", "desktop-linux"]:
            return ProcessResult(exit_code=0, stdout=f"Name: desktop-linux\nDriver: {self.driver}\n\nNodes:\nEndpoint: desktop-linux\n")
        if argv[:2] == ["buildx", "inspect"]:
            return ProcessResult(exit_code=125, stderr="unknown flag: --format")
        if argv[:2] == ["image", "inspect"]:
            doc = self.images.get(argv[2])
            return ProcessResult(exit_code=0 if doc else 1, stdout=json.dumps([doc]) if doc else "[]")
        if argv[0] == "pull":
            doc = self.pulls.get(argv[1])
            if doc is None:
                return ProcessResult(exit_code=1, stderr="unreachable")
            self.images[argv[1]] = doc
            return ProcessResult(exit_code=0)
        if argv[0] == "tag":
            if not self.tag_ok or "@" in argv[2]:
                return ProcessResult(exit_code=1, stderr="invalid tag")
            doc = next((doc for ref, doc in self.images.items() if ref == argv[1] or doc.get("Id") == argv[1]), None)
            if doc is None:
                return ProcessResult(exit_code=1)
            self.images[argv[2]] = doc
        return ProcessResult(exit_code=0)


def pinned_plan(**kwargs):
    return BuildPlan(build_arg_node_image=SELECTED, node_image_mirrors=("fallback.example/library",), **kwargs)


def build_root(tmp_path, extra=""):
    (tmp_path / "container").mkdir()
    (tmp_path / "container" / "Dockerfile").write_text("ARG NODE_IMAGE\nFROM ${NODE_IMAGE}\n", encoding="utf-8")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "versions.env").write_text(
        "NODE_IMAGE=node:24.22.1-slim\nNODE_IMAGE_CN=mirror.example/library/node:24.22.1-slim\n" + extra,
        encoding="utf-8",
    )
    return tmp_path


@pytest.mark.parametrize("value", [DIGEST, DIGEST.removeprefix("sha256:")])
def test_separate_digest_pin_reaches_selected_image_and_every_pull_candidate(tmp_path, value):
    root = build_root(tmp_path, "NODE_IMAGE_DIGEST=" + value + "\nNODE_IMAGE_MIRRORS=fallback.example/library\n")
    plan = plan_build(root, data_root=tmp_path / "user")
    assert plan.build_arg_node_image == SELECTED
    assert _base_image_candidates(plan) == [SELECTED, FALLBACK]
    assert "NODE_IMAGE=" + SELECTED in plan.docker_argv


@pytest.mark.parametrize("digest", ["sha256:abcd", "deadbeef", "sha512:" + "a" * 64, "sha256:" + "g" * 64])
def test_malformed_pin_fails_before_any_docker_call(tmp_path, digest):
    root = build_root(tmp_path, "NODE_IMAGE_DIGEST=" + digest + "\n")
    with pytest.raises(CliError) as error:
        plan_build(root, data_root=tmp_path / "user")
    assert error.value.exit_code == 1


def test_conflicting_embedded_digest_fails_instead_of_silently_replacing_it(tmp_path):
    root = build_root(tmp_path, "NODE_IMAGE_DIGEST=" + DIGEST + "\n")
    env = root / "config" / "versions.env"
    env.write_text(env.read_text(encoding="utf-8").replace("NODE_IMAGE=node:24.22.1-slim", "NODE_IMAGE=node:24.22.1-slim@" + OTHER_ID), encoding="utf-8")
    with pytest.raises(CliError):
        plan_build(root, data_root=tmp_path / "user")


def test_all_non_npm_factory_pins_reach_build_argv(tmp_path):
    # Deliberately differ from defaults to catch hardcoded argv values.
    root = build_root(tmp_path, "MIHOMO_VERSION=v1.19.34\nGEODATA_VERSION=20261028\nGEODATA_COMMIT=" + "c" * 40 + "\nYAZI_VERSION=26.9.2\n")
    argv = plan_build(root, data_root=tmp_path / "user").docker_argv
    for value in ("MIHOMO_VERSION=v1.19.34", "GEODATA_VERSION=20261028", "GEODATA_COMMIT=" + "c" * 40, "YAZI_VERSION=26.9.2"):
        assert value in argv


def test_model_and_missing_env_defaults_agree(tmp_path):
    root = build_root(tmp_path)
    planned = plan_build(root, data_root=tmp_path / "user")
    default = BuildPlan()
    assert default.build_arg_node_image == "node:24.22.1-slim"
    for prefix in ("MIHOMO_VERSION=", "GEODATA_VERSION=", "GEODATA_COMMIT=", "YAZI_VERSION="):
        expected = next(arg for arg in default.docker_argv if arg.startswith(prefix))
        assert expected in planned.docker_argv


def test_unverified_same_name_tag_cannot_bypass_pinned_pull():
    docker = PinnedDocker(cached={"node:24.22.1-slim": image_doc(image_id=OTHER_ID)}, pulls={SELECTED: image_doc()})
    assert _ensure_base_image(docker, pinned_plan(), None, False) == LOCAL
    assert ["pull", SELECTED] in docker.calls
    assert ["tag", IMAGE_ID, LOCAL] in docker.calls
    assert all("@" not in call[2] for call in docker.calls if call[0] == "tag")


def test_verified_digest_cache_accepts_upstream_repo_mapping_and_skips_pull():
    docker = PinnedDocker(cached={SELECTED: image_doc(), LOCAL: image_doc(image_id=OTHER_ID)})
    assert _ensure_base_image(docker, pinned_plan(), None, False) == LOCAL
    assert not any(call[0] == "pull" for call in docker.calls)
    assert docker.images[LOCAL]["Id"] == IMAGE_ID
    assert not any(call[0] == "rmi" for call in docker.calls)


def test_verified_cache_on_later_mirror_avoids_network_to_earlier_sources():
    docker = PinnedDocker(cached={FALLBACK: image_doc()})
    assert _ensure_base_image(docker, pinned_plan(), None, False) == LOCAL
    assert not any(call[0] == "pull" for call in docker.calls)


@pytest.mark.parametrize("doc", [
    {"Id": IMAGE_ID, "RepoDigests": []},
    {"Id": IMAGE_ID, "RepoDigests": ["mirror.example/node@" + OTHER_ID]},
    {"Id": IMAGE_ID, "RepoDigests": "repo@" + DIGEST},
    {"Id": "", "RepoDigests": ["repo@" + DIGEST]},
])
def test_unverifiable_successful_pull_fails_closed(doc):
    docker = PinnedDocker(pulls={SELECTED: doc})
    with pytest.raises(CliError) as error:
        _ensure_base_image(docker, pinned_plan(), None, False)
    assert error.value.exit_code == 4
    assert not any(call[0] == "tag" for call in docker.calls)


def test_digest_failure_rotates_to_next_mirror_without_losing_pin():
    docker = PinnedDocker(pulls={FALLBACK: image_doc()})
    assert _ensure_base_image(docker, pinned_plan(), None, False) == LOCAL
    assert [call for call in docker.calls if call[0] == "pull"] == [["pull", SELECTED], ["pull", FALLBACK]]


def test_failed_local_tag_does_not_fall_back_to_builder_resolving_remote_ref():
    docker = PinnedDocker(pulls={SELECTED: image_doc()}, tag_ok=False)
    with pytest.raises(CliError):
        _ensure_base_image(docker, pinned_plan(), None, False)


def test_pull_refreshes_pinned_source_then_build_uses_verified_local_ref_without_pull():
    docker = PinnedDocker(cached={SELECTED: image_doc()}, pulls={SELECTED: image_doc()})
    result = run_build(pinned_plan(pull=True), executor=docker)
    assert result.executed
    assert ["pull", SELECTED] in docker.calls
    assert "NODE_IMAGE=" + LOCAL in result.docker_argv
    assert "--pull" not in result.docker_argv
    assert result.docker_argv[1:3] == ["--builder", "desktop-linux"]


@pytest.mark.parametrize("driver", ["docker-container", "remote", ""])
def test_builder_without_verified_local_store_access_fails_closed(driver):
    docker = PinnedDocker(cached={SELECTED: image_doc()}, driver=driver)
    with pytest.raises(CliError) as error:
        run_build(pinned_plan(), executor=docker)
    assert error.value.exit_code == 4
    assert not any(call[0] == "build" for call in docker.calls)


def test_failed_digest_preparation_never_runs_build():
    docker = PinnedDocker(cached={LOCAL: image_doc()})
    with pytest.raises(CliError):
        run_build(pinned_plan(), executor=docker)
    assert not any(call[0] == "build" for call in docker.calls)
