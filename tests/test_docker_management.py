"""D-12 docker management (container-action / image-rm / image-tag) tests.

Pins the D-12 boundary: ONLY owned/legacy_owned resources are operable
(unverified refused with AISC_ERR_OWNERSHIP_REFUSED), ownership is
re-verified in-lock at execution time, rm composes stop-then-remove,
and no argv ever touches prune/system/volume/network.
"""

from __future__ import annotations

import os
import unittest

from aisc.application import docker_lifecycle as dl
from aisc.domain.models import CliError, ProcessResult

os.environ.setdefault(
    "AISC_DATA_ROOT",
    os.path.join(os.path.dirname(__file__), "..", ".tmp-test-data"),
)


def _ok(stdout: str = "") -> ProcessResult:
    return ProcessResult(exit_code=0, stdout=stdout, stderr="",
                         command_not_found=False, timed_out=False)


class FakeExec:
    """Routes maintenance-relevant docker argv; records everything."""

    def __init__(self, *, ps="", images="", ancestor="", label_ids="",
                 dangling_ids=""):
        self.ps = ps
        self.images = images
        self.ancestor = ancestor
        self.label_ids = label_ids
        self.dangling_ids = dangling_ids
        self.argvs: list = []

    def run_captured(self, argv, timeout=None):
        self.argvs.append(list(argv))
        head = argv[0]
        if head == "ps":
            if any("ancestor=" in a for a in argv):
                return _ok(self.ancestor)
            return _ok(self.ps)
        if head == "images":
            if "--filter" in argv:
                if any("label=" in a for a in argv):
                    return _ok(self.label_ids)
                if any("dangling=true" in a for a in argv):
                    return _ok(self.dangling_ids)
            return _ok(self.images)
        return _ok()  # start / stop / rm / rmi / tag all succeed

    def asserts_safe(self, testcase):
        forbidden = {"prune", "kill", "volume", "network"}
        for argv in self.argvs:
            testcase.assertFalse(
                set(argv) & forbidden,
                f"management argv touched forbidden verb: {argv}",
            )
        testcase.assertFalse(
            any(argv[:1] == ["system"] for argv in self.argvs),
            "system command leaked into management",
        )


# ps rows (7 tab fields: ID/Names/Image/Status/managed/kind/owner)
PS_OWNED_RUNNING = (
    "c1\twb-x\tsuper-claude:latest\tUp 2 hours\ttrue\t\thost\n"
)
PS_OWNED_STOPPED = (
    "c1\twb-x\tsuper-claude:latest\tExited (0) 1 minute ago\ttrue\t\thost\n"
)
PS_UNVERIFIED = (
    "c9\tsuper-claude-station-x\tsuper-claude:latest\tUp 1 hour\t\t\t\n"
)
# images universe (repo\ttag\tid)
IMAGES = (
    "super-claude\tlatest\td4411a8f1123\n"
    "super-claude\tdev-x\tdev99\n"
)
LABEL_IDS = "d4411a8f1123\n"


class ContainerActionTests(unittest.TestCase):
    def setUp(self):
        self.ex = FakeExec(ps=PS_OWNED_RUNNING)

    def test_start_running_owned_container(self):
        out = dl.container_management_action(
            self.ex, name="wb-x", action="start")
        self.ex.asserts_safe(self)
        self.assertEqual(out["action"], "container-start")
        self.assertIn(["start", "wb-x"], out["argvs"])

    def test_stop_running_owned_container(self):
        out = dl.container_management_action(
            self.ex, name="wb-x", action="stop")
        self.ex.asserts_safe(self)
        self.assertIn(["stop", "wb-x"], out["argvs"])

    def test_stop_already_stopped_is_noop(self):
        self.ex.ps = PS_OWNED_STOPPED
        out = dl.container_management_action(
            self.ex, name="wb-x", action="stop")
        self.ex.asserts_safe(self)
        self.assertEqual(out["argvs"], [])  # idempotent no-op

    def test_rm_composes_stop_then_rm(self):
        out = dl.container_management_action(
            self.ex, name="wb-x", action="rm")
        self.ex.asserts_safe(self)
        self.assertEqual(
            out["argvs"], [["stop", "wb-x"], ["rm", "-f", "wb-x"]])

    def test_unverified_container_refused(self):
        self.ex.ps = PS_UNVERIFIED
        with self.assertRaises(CliError) as ctx:
            dl.container_management_action(self.ex, name="random-box",
                                           action="stop")
        self.assertEqual(ctx.exception.error_code, "AISC_ERR_OWNERSHIP_REFUSED")
        self.assertEqual(ctx.exception.exit_code, 6)
        self.ex.asserts_safe(self)
        # refused = zero docker mutations
        self.assertTrue(all(a[0] not in ("start", "stop", "rm") for a in self.ex.argvs))


class ImageManagementTests(unittest.TestCase):
    def setUp(self):
        self.ex = FakeExec(
            ps=PS_OWNED_RUNNING, images=IMAGES, label_ids=LABEL_IDS,
            ancestor="",
        )

    def test_image_rm_unreferenced_legacy(self):
        out = dl.image_management_rm(self.ex, image_id="d4411a8f1123")
        self.ex.asserts_safe(self)
        self.assertEqual(out["action"], "image-rm")
        self.assertIn(["rmi", "d4411a8f1123"], self.ex.argvs)

    def test_image_rm_in_use_refused(self):
        self.ex.ancestor = "c1\n"
        with self.assertRaises(CliError) as ctx:
            dl.image_management_rm(self.ex, image_id="d4411a8f1123")
        self.assertEqual(ctx.exception.error_code, "AISC_ERR_OWNERSHIP_REFUSED")
        self.assertNotIn(["rmi", "d4411a8f1123"], self.ex.argvs)

    def test_image_rm_unverified_refused(self):
        # super-claude:dev-x = repository-only evidence → unverified
        with self.assertRaises(CliError) as ctx:
            dl.image_management_rm(self.ex, image_id="dev99")
        self.assertEqual(ctx.exception.error_code, "AISC_ERR_OWNERSHIP_REFUSED")

    def test_image_tag_owned_ok(self):
        out = dl.image_management_tag(
            self.ex, image_id="d4411a8f1123",
            repository="myrepo", tag="renamed")
        self.ex.asserts_safe(self)
        self.assertEqual(out["ref"], "myrepo:renamed")
        self.assertIn(["tag", "d4411a8f1123", "myrepo:renamed"], self.ex.argvs)

    def test_image_tag_invalid_ref_refused(self):
        with self.assertRaises(CliError):
            dl.image_management_tag(
                self.ex, image_id="d4411a8f1123",
                repository="my repo", tag="x")

    def test_image_tag_unverified_refused(self):
        with self.assertRaises(CliError) as ctx:
            dl.image_management_tag(
                self.ex, image_id="dev99", repository="r", tag="t")
        self.assertEqual(ctx.exception.error_code, "AISC_ERR_OWNERSHIP_REFUSED")


if __name__ == "__main__":
    unittest.main()
