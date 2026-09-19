"""D-2 docker per-resource inspection (``cache_inspect``) tests.

Pins the read-only contract: absolutely no prune/rmi/rm argv anywhere in
the collection pass, machine-format parsing only, per-category degradation
to unknown, and the will_be_cleaned mapping (dangling images / not-in-use
build cache). See docs/plans/2.1.13-dev-plans/docker-scan-fidelity.md.
"""

from __future__ import annotations

import os
import unittest

from aisc.application import docker_lifecycle as dl
from aisc.domain.models import ProcessResult

os.environ.setdefault(
    "AISC_DATA_ROOT",
    os.path.join(os.path.dirname(__file__), "..", ".tmp-test-data"),
)


def _ok(stdout: str = "") -> ProcessResult:
    return ProcessResult(exit_code=0, stdout=stdout, stderr="",
                         command_not_found=False, timed_out=False)


class FakeExec:
    """Routes argv[0] (plus filter flags) to canned stdout, records argv."""

    def __init__(self, *, df_summary="", df_verbose=None, images="",
                 ps="", volume_all="", volume_dangling="", buildx_du=None,
                 network=""):
        self.df_summary = df_summary
        self.df_verbose = df_verbose
        self.images = images
        self.ps = ps
        self.volume_all = volume_all
        self.volume_dangling = volume_dangling
        self.buildx_du = buildx_du
        self.network = network
        self.argvs: list = []

    def run_captured(self, argv, timeout=None):
        self.argvs.append(list(argv))
        head = argv[0]
        if head == "system":
            if "-v" in argv:
                if self.df_verbose is None:
                    return ProcessResult(exit_code=1, stdout="", stderr="unsupported",
                                         command_not_found=False, timed_out=False)
                return _ok(self.df_verbose)
            return _ok(self.df_summary)
        if head == "images":
            return _ok(self.images)
        if head == "ps":
            return _ok(self.ps)
        if head == "volume":
            if "dangling=true" in argv:
                return _ok(self.volume_dangling)
            return _ok(self.volume_all)
        if head == "buildx":
            if self.buildx_du is None:
                return ProcessResult(exit_code=1, stdout="", stderr="no plugin",
                                     command_not_found=False, timed_out=False)
            return _ok(self.buildx_du)
        if head == "network":
            return _ok(self.network)
        return _ok()

    def asserts_readonly(self, testcase):
        forbidden = {"prune", "rmi", "rm", "kill", "stop", "start"}
        for argv in self.argvs:
            testcase.assertFalse(
                set(argv) & forbidden,
                f"read-only contract violated by {argv}",
            )
            # -a/--all are image/system-prune amplifiers — never alongside a
            # destructive verb (ps -a is a read-only list and stays legal).
            if "prune" in argv:
                testcase.assertFalse(
                    set(argv) & {"-a", "--all"},
                    f"unfiltered prune smuggled in: {argv}",
                )
        # never a system prune either
        testcase.assertFalse(
            any(argv[:2] == ["system", "prune"] for argv in self.argvs)
        )


DF_SUMMARY = (
    '{"Type":"Images","TotalCount":"5","Active":"2","Size":"1.2GB","Reclaimable":"800MB (66%)"}\n'
    '{"Type":"Build Cache","TotalCount":"12","Active":"0","Size":"6.7GB","Reclaimable":"4.1GB (61%)"}\n'
)

DF_VERBOSE = (
    '{"Images":['
    '{"Containers":"0","ID":"abc","Repository":"<none>","SharedSize":"10MB",'
    '"Size":"120MB","Tag":"<none>","UniqueSize":"110MB"},'
    '{"Containers":"1","ID":"def","Repository":"super-claude","SharedSize":"40MB",'
    '"Size":"220MB","Tag":"latest","UniqueSize":"180MB"}'
    '],"Containers":[],"Volumes":[],'
    '"BuildCache":['
    '{"CacheType":"exec.cachemount","ID":"cx1","InUse":false,"LastUsedAt":"yesterday",'
    '"Shared":false,"Size":"251MB","UsageCount":2},'
    '{"CacheType":"source.local","ID":"cx2","InUse":true,"LastUsedAt":"now",'
    '"Shared":true,"Size":"12MB","UsageCount":9}'
    ']}'
)

IMAGES_LS = (
    '{"ID":"abc","Repository":"<none>","Tag":"<none>","Size":"120MB","CreatedSince":"3 days ago"}\n'
    '{"ID":"def","Repository":"super-claude","Tag":"latest","Size":"220MB","CreatedSince":"1 hour ago"}\n'
)

PS = (
    '{"ID":"c1","Names":["station-x"],"Image":"super-claude:latest","State":"exited",'
    '"Size":"35.6 kB (virtual 109 MB)"}\n'
    '{"ID":"c2","Names":["live"],"Image":"super-claude:latest","State":"running",'
    '"Size":"0 B (virtual 109 MB)"}\n'
)

VOLUME_ALL = '{"Name":"toolchain-v1"}\n{"Name":"orphan-vol"}\n'
VOLUME_DANGLING = '{"Name":"orphan-vol"}\n'

BUILDX_DU = (
    '{"ID":"bx1","Type":"regular","Mutable":false,"Reclaimable":true,"Shared":false,'
    '"Size":"12MB","UsageCount":1,"LastUsedAt":"yesterday"}\n'
)

NETWORK = '{"Name":"bridge","Driver":"bridge"}\n{"Name":"aisc-net","Driver":"bridge"}\n'


class SizeParsingTests(unittest.TestCase):
    def test_docker_size_strings(self):
        self.assertEqual(dl._size_bytes("35.6 kB"), 35600)
        self.assertEqual(dl._size_bytes("1.2GB"), 1_200_000_000)
        self.assertEqual(dl._size_bytes("120MB"), 120_000_000)
        self.assertIsNone(dl._size_bytes("N/A"))
        self.assertIsNone(dl._size_bytes(None))
        self.assertIsNone(dl._size_bytes("not-a-size"))

    def test_container_rw_size_splits_virtual(self):
        self.assertEqual(dl._container_rw_size("35.6 kB (virtual 109 MB)"), 35600)
        self.assertIsNone(dl._container_rw_size(""))


class CacheInspectTests(unittest.TestCase):
    def setUp(self):
        self.ex = FakeExec(
            df_summary=DF_SUMMARY,
            df_verbose=DF_VERBOSE,
            images=IMAGES_LS,
            ps=PS,
            volume_all=VOLUME_ALL,
            volume_dangling=VOLUME_DANGLING,
            buildx_du=BUILDX_DU,
            network=NETWORK,
        )

    def test_readonly_contract_and_envelope(self):
        out = dl.cache_inspect(self.ex)
        self.ex.asserts_readonly(self)
        self.assertEqual(out["schema_version"], dl.CACHE_INSPECT_SCHEMA)
        self.assertTrue(out["docker_available"])
        self.assertTrue(out["capabilities"]["df_verbose_json"])
        self.assertIn("disclaimer", out)

    def test_images_dangling_vs_inuse_with_unique_sizes(self):
        out = dl.cache_inspect(self.ex)
        rows = out["categories"]["images"]["rows"]
        by_id = {r["id"]: r for r in rows}
        self.assertTrue(by_id["abc"]["dangling"])
        self.assertTrue(by_id["abc"]["will_be_cleaned"])
        self.assertFalse(by_id["abc"]["in_use"])
        self.assertEqual(by_id["abc"]["reclaimable_bytes"], 110_000_000)
        self.assertTrue(by_id["def"]["in_use"])
        self.assertEqual(by_id["def"]["reclaimable_bytes"], 0)
        self.assertFalse(by_id["def"]["will_be_cleaned"])

    def test_containers_rw_only_when_stopped(self):
        out = dl.cache_inspect(self.ex)
        rows = out["categories"]["containers"]["rows"]
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(by_id["c1"]["reclaimable_bytes"], 35600)
        self.assertIsNone(by_id["c2"]["reclaimable_bytes"])  # running → unknown
        self.assertFalse(by_id["c1"]["will_be_cleaned"])

    def test_volume_dangling_flag_but_never_cleanable(self):
        out = dl.cache_inspect(self.ex)
        rows = out["categories"]["volumes"]["rows"]
        by_name = {r["name"]: r for r in rows}
        self.assertTrue(by_name["orphan-vol"]["dangling"])
        self.assertFalse(by_name["orphan-vol"]["will_be_cleaned"])  # invariant 4
        self.assertFalse(by_name["toolchain-v1"]["dangling"])

    def test_build_cache_from_df_verbose(self):
        out = dl.cache_inspect(self.ex)
        rows = out["categories"]["build_cache"]["rows"]
        by_id = {r["id"]: r for r in rows}
        self.assertTrue(by_id["cx1"]["will_be_cleaned"])
        self.assertEqual(by_id["cx1"]["reclaimable_bytes"], 251_000_000)
        self.assertFalse(by_id["cx2"]["will_be_cleaned"])
        self.assertEqual(by_id["cx2"]["reclaimable_bytes"], 0)

    def test_buildx_fallback_when_df_verbose_unavailable(self):
        self.ex.df_verbose = None
        out = dl.cache_inspect(self.ex)
        self.assertFalse(out["capabilities"]["df_verbose_json"])
        self.assertTrue(out["capabilities"]["buildx_du"])
        rows = out["categories"]["build_cache"]["rows"]
        self.assertEqual(rows[0]["id"], "bx1")
        self.assertTrue(rows[0]["will_be_cleaned"])
        self.assertIn("df-verbose-json-unavailable", out["warnings"])

    def test_full_degradation_stays_safe(self):
        ex = FakeExec()  # every docker call fails
        out = dl.cache_inspect(ex)
        self.assertFalse(out["docker_available"])
        for cat in out["categories"].values():
            self.assertEqual(cat["rows"], [])
        ex.asserts_readonly(self)


if __name__ == "__main__":
    unittest.main()
