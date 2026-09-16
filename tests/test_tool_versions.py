"""Tool pin overlay tests (0.1.0 A5, D-9/D-27).

Factory layer from the root's config/versions.env, user layer at
<data-root>/config/versions.env overriding KEY-WISE; the writer preserves
comments and lands atomically; the check section is network-tolerant.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from aisc.application.tool_versions import (
    effective_tool_versions,
    tools_check_section,
    user_pin_path,
    write_user_pins,
)

FACTORY = """# factory defaults
NODE_IMAGE=node:22-slim
CLAUDE_CODE_VERSION=2.1.273
CODEX_VERSION=0.154.0
CC_SWITCH_VERSION=v5.10.4
"""


def make_root(td: Path) -> Path:
    cfg = td / "root" / "config"
    cfg.mkdir(parents=True)
    (cfg / "versions.env").write_text(FACTORY, encoding="utf-8")
    return td / "root"


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="tv-"))
        self.root = make_root(self.td)
        self.data_root = self.td / "data"

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_no_user_layer_is_factory_everywhere(self):
        eff = effective_tool_versions(self.root, self.data_root)
        self.assertEqual(eff["CLAUDE_CODE_VERSION"], ("2.1.273", "default"))
        self.assertEqual(eff["NODE_IMAGE"], ("node:22-slim", "default"))

    def test_user_layer_overrides_keywise_only(self):
        write_user_pins(self.data_root, {"CLAUDE_CODE_VERSION": "2.0.0"})
        eff = effective_tool_versions(self.root, self.data_root)
        self.assertEqual(eff["CLAUDE_CODE_VERSION"], ("2.0.0", "user"))
        self.assertEqual(eff["CODEX_VERSION"], ("0.154.0", "default"))

    def test_user_layer_cannot_invent_keys(self):
        write_user_pins(self.data_root, {"CLAUDE_CODE_VERSION": "2.0.0"})
        (user_pin_path(self.data_root)).write_text(
            "TOTALLY_NEW=9\n", encoding="utf-8")
        eff = effective_tool_versions(self.root, self.data_root)
        self.assertNotIn("TOTALLY_NEW", eff)

    def test_writer_rejects_unknown_keys(self):
        with self.assertRaises(ValueError) as cm:
            write_user_pins(self.data_root, {"NODE_IMAGE": "node:99"})
        self.assertIn("not pinnable", str(cm.exception))

    def test_writer_roundtrip_preserves_comments_and_updates_in_place(self):
        write_user_pins(self.data_root, {"CLAUDE_CODE_VERSION": "2.0.0",
                                         "CODEX_VERSION": "0.1.0"})
        # second write updates one key in place, keeps the other + comments
        write_user_pins(self.data_root, {"CLAUDE_CODE_VERSION": "2.1.100"})
        text = user_pin_path(self.data_root).read_text(encoding="utf-8")
        self.assertIn("AISC user tool pins", text)
        self.assertIn("CLAUDE_CODE_VERSION=2.1.100", text)
        self.assertIn("CODEX_VERSION=0.1.0", text)
        self.assertNotIn("2.0.0", text)
        eff = effective_tool_versions(self.root, self.data_root)
        self.assertEqual(eff["CLAUDE_CODE_VERSION"], ("2.1.100", "user"))
        self.assertEqual(eff["CODEX_VERSION"], ("0.1.0", "user"))
        self.assertEqual(eff["CC_SWITCH_VERSION"], ("v5.10.4", "default"))


class CheckSectionTests(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="tvc-"))
        self.root = make_root(self.td)
        self.data_root = self.td / "data"

    def tearDown(self):
        shutil.rmtree(self.td, ignore_errors=True)

    def test_registry_failure_degrades_to_unknown_not_error(self):
        def exploding(url):
            raise OSError("offline")

        section = tools_check_section(self.root, self.data_root, opener=exploding)
        by_tool = {t["tool"]: t for t in section}
        self.assertIsNone(by_tool["CLAUDE_CODE_VERSION"]["latest"])
        self.assertEqual(by_tool["CLAUDE_CODE_VERSION"]["source"], "default")

    def test_registry_success_populates_latest_and_node_req(self):
        def opener(url):
            pkg = url.rsplit("/", 1)[-1]
            latest = "2.1.273" if "claude-code" in pkg else "0.154.0"
            return {
                "dist-tags": {"latest": latest},
                "versions": {latest: {"engines": {"node": ">=22.0.0"}}},
            }

        section = tools_check_section(self.root, self.data_root, opener=opener)
        by_tool = {t["tool"]: t for t in section}
        self.assertEqual(by_tool["CLAUDE_CODE_VERSION"]["latest"], "2.1.273")
        self.assertEqual(by_tool["CLAUDE_CODE_VERSION"]["node_requirement"], ">=22.0.0")

    def test_user_pin_marks_source(self):
        write_user_pins(self.data_root, {"CODEX_VERSION": "0.99.0"})
        section = tools_check_section(self.root, self.data_root,
                                      opener=lambda u: (_ for _ in ()).throw(OSError()))
        by_tool = {t["tool"]: t for t in section}
        self.assertEqual(by_tool["CODEX_VERSION"]["source"], "user")
        self.assertEqual(by_tool["CODEX_VERSION"]["current"], "0.99.0")


class BuildArgForwarding(unittest.TestCase):
    def test_user_pin_reaches_docker_argv(self):
        from aisc.cli.commands.build import plan_build

        td = Path(tempfile.mkdtemp(prefix="tvb-"))
        try:
            root = make_root(td)
            (root / "container").mkdir()
            (root / "container" / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
            data_root = td / "data"
            write_user_pins(data_root, {"CLAUDE_CODE_VERSION": "2.1.300"})
            plan = plan_build(root, dry_run=True, data_root=data_root)
            argv = plan.docker_argv
            self.assertIn("CLAUDE_CODE_VERSION=2.1.300", argv)
            self.assertIn("CODEX_VERSION=0.154.0", argv)  # factory default rides
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_factory_pin_reaches_docker_argv_without_user_layer(self):
        from aisc.cli.commands.build import plan_build

        td = Path(tempfile.mkdtemp(prefix="tvb2-"))
        try:
            root = make_root(td)
            (root / "container").mkdir()
            (root / "container" / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
            data_root = td / "data"  # absent -> no overlay
            plan = plan_build(root, dry_run=True, data_root=data_root)
            self.assertIn("CLAUDE_CODE_VERSION=2.1.273", argv_of(plan))
        finally:
            shutil.rmtree(td, ignore_errors=True)


def argv_of(plan):
    return plan.docker_argv


if __name__ == "__main__":
    unittest.main()
