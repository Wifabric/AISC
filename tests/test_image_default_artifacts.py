"""b2 (2.2.0 D-3): the image ships no default skills/MCP/plugins.

Only the base tools (gh/npm/codex/claude) remain in the image. Every extension
is installed explicitly through the extension market at runtime.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ImageDefaultArtifactsTest(unittest.TestCase):
    def setUp(self):
        self.dockerfile = (ROOT / "container" / "Dockerfile").read_text(encoding="utf-8")
        self.entrypoint = (ROOT / "container" / "entrypoint.sh").read_text(encoding="utf-8")

    def test_no_default_skills_plugins_or_commands_are_copied(self):
        for source in (
            "container/_bundle/skills/",
            "container/_bundle/plugins/cache/",
            "container/cc-switch-skills/",
            "container/commands/",
        ):
            with self.subTest(source=source):
                self.assertNotIn(f"COPY {source}", self.dockerfile)
        self.assertNotIn("prepare-office-hours.sh", self.dockerfile)
        self.assertNotIn("/opt/aisc/skills/", self.dockerfile)

    def test_offline_official_marketplace_catalog_is_bundled(self):
        # b2 review fix: the official marketplace catalog is not a default
        # plugin install — it is the offline search index for the extension
        # market, so it stays in the image while factory installs stay empty.
        self.assertIn(
            "COPY container/_bundle/plugins/marketplaces/claude-plugins-official/ "
            "/opt/aisc/factory/.claude/plugins/marketplaces/claude-plugins-official/",
            self.dockerfile,
        )
        self.assertIn("anthropics/claude-plugins-official", self.dockerfile)
        self.assertIn(
            "/opt/aisc/factory/.claude/plugins/known_marketplaces.json",
            self.dockerfile,
        )

    def test_factory_plugin_registry_starts_empty(self):
        self.assertIn(
            'echo \'{"version":2,"plugins":{}}\' > /opt/aisc/factory/.claude/plugins/installed_plugins.json',
            self.dockerfile,
        )

    def test_tools_are_still_installed(self):
        for token in (" gh ", "@anthropic-ai/claude-code@", "@openai/codex@"):
            with self.subTest(token=token):
                self.assertIn(token, self.dockerfile)

    def test_entrypoint_seeds_no_skills_or_mcp(self):
        self.assertNotIn("cc_switch_skills.py", self.entrypoint)
        self.assertNotIn("default_mcp.py", self.entrypoint)
        self.assertNotIn("已配置 16 个通用技能", self.entrypoint)

    def test_entrypoint_accepts_an_empty_skills_directory(self):
        # b2: empty factory skills is a valid image state, not a failed copy.
        self.assertNotIn("复制后 skills/plugins 目录为空", self.entrypoint)

    def test_settings_enable_no_default_plugins_or_marketplaces(self):
        settings = json.loads(
            (ROOT / "container" / "claude-settings.json").read_text(encoding="utf-8")
        )
        self.assertEqual(settings.get("enabledPlugins"), {})
        self.assertEqual(settings.get("extraKnownMarketplaces"), {})
        self.assertNotIn("statusLine", settings)


if __name__ == "__main__":
    unittest.main()
