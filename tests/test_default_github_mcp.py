"""Default official GitHub MCP registration and ownership rules."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "container" / "lib" / "default_mcp.py"

spec = importlib.util.spec_from_file_location("aisc_default_mcp", MODULE_PATH)
assert spec and spec.loader
DEFAULT_MCP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(DEFAULT_MCP)


class DefaultGithubMcpWiringTests(unittest.TestCase):
    def test_image_contains_default_mcp_helper(self):
        dockerfile = (ROOT / "container" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn(
            "COPY container/lib/default_mcp.py /usr/local/bin/lib/default_mcp.py",
            dockerfile,
        )

    def test_entrypoint_reconciles_default_mcp_after_factory_skills(self):
        entrypoint = (ROOT / "container" / "entrypoint.sh").read_text(encoding="utf-8")
        skills = entrypoint.index("cc_switch_skills.py")
        default_mcp = entrypoint.index("lib/default_mcp.py")
        migrations = entrypoint.index("cc_switch_preset_providers.py")
        self.assertLess(skills, default_mcp)
        self.assertLess(default_mcp, migrations)
        self.assertIn("--project-dir /root/app", entrypoint)
        self.assertIn('--codex-config-dir "$CODEX_CONFIG_DIR"', entrypoint)
        self.assertIn('CC_SWITCH_DEFAULT_MCP_LOG="/tmp/cc-switch-default-mcp.log"', entrypoint)


class DefaultGithubMcpTests(unittest.TestCase):
    def _layout(self, root: Path):
        config_dir = root / "cc-switch"
        project_dir = root / "project"
        codex_dir = root / "codex"
        config_dir.mkdir()
        project_dir.mkdir()
        codex_dir.mkdir()
        db = sqlite3.connect(config_dir / "cc-switch.db")
        db.execute("""
            CREATE TABLE mcp_servers (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, server_config TEXT NOT NULL,
                description TEXT, homepage TEXT, docs TEXT, tags TEXT NOT NULL DEFAULT '[]',
                enabled_claude BOOLEAN NOT NULL DEFAULT 0,
                enabled_codex BOOLEAN NOT NULL DEFAULT 0,
                enabled_gemini BOOLEAN NOT NULL DEFAULT 0,
                enabled_grokbuild BOOLEAN NOT NULL DEFAULT 0,
                enabled_opencode BOOLEAN NOT NULL DEFAULT 0,
                enabled_mcode BOOLEAN NOT NULL DEFAULT 0,
                enabled_agy BOOLEAN NOT NULL DEFAULT 0,
                enabled_kimi BOOLEAN NOT NULL DEFAULT 0,
                enabled_hermes BOOLEAN NOT NULL DEFAULT 0,
                enabled_pi BOOLEAN NOT NULL DEFAULT 0
            )
        """)
        db.commit()
        db.close()
        return config_dir, project_dir, codex_dir

    def _row(self, config_dir: Path):
        db = sqlite3.connect(config_dir / "cc-switch.db")
        row = db.execute(
            "SELECT server_config, enabled_claude, enabled_codex, tags FROM mcp_servers WHERE id='github'"
        ).fetchone()
        db.close()
        return row

    def _sync(self, config_dir, project_dir, codex_dir):
        return DEFAULT_MCP.synchronize(
            config_dir=config_dir,
            project_dir=project_dir,
            codex_config_dir=codex_dir,
        )

    def test_fresh_runtime_installs_official_mcp_and_writes_both_agents(self):
        with tempfile.TemporaryDirectory() as temp:
            config_dir, project_dir, codex_dir = self._layout(Path(temp))
            result = self._sync(config_dir, project_dir, codex_dir)

            self.assertEqual(result, "installed")
            server_config, claude, codex, tags = self._row(config_dir)
            self.assertEqual(json.loads(server_config), {
                "url": "https://api.githubcopilot.com/mcp/",
                "bearer_token_env_var": "GITHUB_PAT_TOKEN",
            })
            self.assertTrue(claude)
            self.assertTrue(codex)
            self.assertIn("aisc-default", tags)
            claude_doc = json.loads((project_dir / ".mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(claude_doc["mcpServers"]["github"], {
                "type": "http", "url": "https://api.githubcopilot.com/mcp/",
            })
            codex_text = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertIn('[mcp_servers.github]', codex_text)
            self.assertIn('url = "https://api.githubcopilot.com/mcp/"', codex_text)
            self.assertIn('bearer_token_env_var = "GITHUB_PAT_TOKEN"', codex_text)

    def test_existing_custom_database_row_is_never_replaced_or_synced(self):
        with tempfile.TemporaryDirectory() as temp:
            config_dir, project_dir, codex_dir = self._layout(Path(temp))
            db = sqlite3.connect(config_dir / "cc-switch.db")
            db.execute(
                "INSERT INTO mcp_servers (id,name,server_config,tags,enabled_claude,enabled_codex) "
                "VALUES ('github','github','{\"url\":\"https://custom.example/mcp\"}','mine',1,0)"
            )
            db.commit(); db.close()
            (project_dir / ".mcp.json").write_text(json.dumps({
                "mcpServers": {"github": {"type": "http", "url": "https://custom.example/mcp"}}
            }), encoding="utf-8")
            (codex_dir / "config.toml").write_text(
                '[mcp_servers.github]\nurl = "https://custom.example/mcp"\n', encoding="utf-8")

            result = self._sync(config_dir, project_dir, codex_dir)

            self.assertEqual(result, "custom")
            self.assertEqual(self._row(config_dir)[0], '{"url":"https://custom.example/mcp"}')
            self.assertIn("custom.example", (project_dir / ".mcp.json").read_text(encoding="utf-8"))
            self.assertIn("custom.example", (codex_dir / "config.toml").read_text(encoding="utf-8"))

    def test_disabled_default_removes_only_its_live_entries_and_preserves_others(self):
        with tempfile.TemporaryDirectory() as temp:
            config_dir, project_dir, codex_dir = self._layout(Path(temp))
            db = sqlite3.connect(config_dir / "cc-switch.db")
            db.execute(
                "INSERT INTO mcp_servers (id,name,server_config,tags,enabled_claude,enabled_codex) "
                "VALUES ('github','github','{\"url\":\"https://api.githubcopilot.com/mcp/\"}',"
                "'aisc-default,github',0,0)"
            )
            db.commit(); db.close()
            (project_dir / ".mcp.json").write_text(json.dumps({
                "keep": 1,
                "mcpServers": {
                    "other": {"type": "http", "url": "https://other"},
                    "github": {"type": "http", "url": "https://api.githubcopilot.com/mcp/"},
                },
            }), encoding="utf-8")
            (codex_dir / "config.toml").write_text(
                'retain = true\n\n[mcp_servers.other]\nurl = "https://other"\n\n'
                '[mcp_servers.github]\nurl = "https://api.githubcopilot.com/mcp/"\n',
                encoding="utf-8")

            result = self._sync(config_dir, project_dir, codex_dir)

            self.assertEqual(result, "synced")
            claude_doc = json.loads((project_dir / ".mcp.json").read_text(encoding="utf-8"))
            self.assertNotIn("github", claude_doc["mcpServers"])
            self.assertIn("other", claude_doc["mcpServers"])
            codex_text = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertNotIn("[mcp_servers.github]", codex_text)
            self.assertIn("retain = true", codex_text)
            self.assertIn("[mcp_servers.other]", codex_text)

    def test_cc_switch_clearing_tags_does_not_lose_aisc_ownership(self):
        with tempfile.TemporaryDirectory() as temp:
            config_dir, project_dir, codex_dir = self._layout(Path(temp))
            self._sync(config_dir, project_dir, codex_dir)
            db = sqlite3.connect(config_dir / "cc-switch.db")
            db.execute("UPDATE mcp_servers SET enabled_claude=0, tags='[]' WHERE id='github'")
            db.commit(); db.close()

            self.assertEqual(self._sync(config_dir, project_dir, codex_dir), "synced")
            self.assertFalse((project_dir / ".mcp.json").exists())
            self.assertIn("[mcp_servers.github]", (codex_dir / "config.toml").read_text(encoding="utf-8"))

    def test_marker_without_row_means_user_deleted_and_is_not_reinstalled(self):
        with tempfile.TemporaryDirectory() as temp:
            config_dir, project_dir, codex_dir = self._layout(Path(temp))
            self._sync(config_dir, project_dir, codex_dir)
            db = sqlite3.connect(config_dir / "cc-switch.db")
            db.execute("DELETE FROM mcp_servers WHERE id='github'")
            db.commit(); db.close()
            (project_dir / ".mcp.json").unlink()

            self.assertEqual(self._sync(config_dir, project_dir, codex_dir), "deleted")
            self.assertIsNone(self._row(config_dir))
            self.assertFalse((project_dir / ".mcp.json").exists())

    def test_existing_default_row_preserves_user_switches_on_resync(self):
        with tempfile.TemporaryDirectory() as temp:
            config_dir, project_dir, codex_dir = self._layout(Path(temp))
            self._sync(config_dir, project_dir, codex_dir)
            db = sqlite3.connect(config_dir / "cc-switch.db")
            db.execute("UPDATE mcp_servers SET enabled_claude=0, enabled_codex=1 WHERE id='github'")
            db.commit(); db.close()

            self.assertEqual(self._sync(config_dir, project_dir, codex_dir), "synced")
            self.assertEqual(self._row(config_dir)[1:3], (0, 1))
            self.assertFalse((project_dir / ".mcp.json").exists())
            codex_text = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertIn("[mcp_servers.github]", codex_text)

    def test_custom_live_github_without_ssot_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as temp:
            config_dir, project_dir, codex_dir = self._layout(Path(temp))
            (project_dir / ".mcp.json").write_text(json.dumps({
                "mcpServers": {"github": {"type": "http", "url": "https://custom.example"}}
            }), encoding="utf-8")

            result = self._sync(config_dir, project_dir, codex_dir)
            self.assertEqual(result, "custom-live")
            self.assertIsNone(self._row(config_dir))
