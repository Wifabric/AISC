"""v2.1.16 b5: the in-container extensions adapter (aisc.extensions/v1).

Hermetic: cc-switch / claude CLI faked via recorded argv; SQLite is a temp
cc-switch.db; plugin registry is a temp installed_plugins.json. The MCP env
VALUE must never appear in any list envelope (key names only).
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "container" / "aisc-extensions-adapter"

_loader = SourceFileLoader("aisc_extensions_adapter", str(ADAPTER_PATH))
_spec = importlib.util.spec_from_loader("aisc_extensions_adapter", _loader)
assert _spec and _spec.loader
A = importlib.util.module_from_spec(_spec)
_loader.exec_module(A)


def seed_db(dir_path: Path):
    conn = sqlite3.connect(dir_path / "cc-switch.db")
    conn.execute(
        "CREATE TABLE skills (id TEXT, name TEXT, description TEXT, directory TEXT, "
        "repo_owner TEXT, repo_name TEXT, repo_branch TEXT, readme_url TEXT, "
        "enabled_claude INTEGER, enabled_codex INTEGER, enabled_gemini INTEGER, "
        "enabled_grokbuild INTEGER, enabled_opencode INTEGER, enabled_hermes INTEGER, "
        "installed_at TEXT, content_hash TEXT, updated_at TEXT)"
    )
    conn.execute(
        "INSERT INTO skills VALUES ('obra/superpowers:superpowers','superpowers',"
        "'Structured workflows','superpowers','obra','superpowers','main','',"
        "1,0,0,0,0,0,'2026-01-01','x','2026-01-02')"
    )
    conn.execute(
        "CREATE TABLE mcp_servers (id TEXT, name TEXT, server_config TEXT, "
        "description TEXT, homepage TEXT, docs TEXT, tags TEXT, "
        "enabled_claude INTEGER, enabled_codex INTEGER, enabled_gemini INTEGER, "
        "enabled_grokbuild INTEGER, enabled_opencode INTEGER, enabled_hermes INTEGER)"
    )
    conn.execute(
        "INSERT INTO mcp_servers VALUES ('aisc-host','AISC Host',"
        "'{\"url\":\"http://x/mcp\",\"env\":{\"TOKEN\":\"sk-live-secret123\"}}',"
        "'',' ','','host',1,1,0,0,0,0)"
    )
    conn.commit()
    conn.close()


class TempEnv(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        seed_db(self.root)
        self.env = {
            "CC_SWITCH_CONFIG_DIR": str(self.root),
            "CLAUDE_CONFIG_DIR": str(self.root / "claude"),
            "PATH": os.environ.get("PATH", ""),
        }
        self._patcher = mock.patch.dict(os.environ, self.env)
        self._patcher.start()
        self.addCleanup(self._patcher.stop)


class ListTests(TempEnv):
    def test_skills_snapshot_shape(self):
        items = A.list_items("skills")
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["id"], "superpowers")
        self.assertTrue(item["enabled_claude"])
        self.assertFalse(item["enabled_codex"])
        self.assertEqual(item["repo"], "obra/superpowers")

    def test_mcp_snapshot_never_leaks_env_values(self):
        items = A.list_items("mcp")
        item = items[0]
        self.assertEqual(item["transport"], "http")
        self.assertEqual(item["url"], "http://x/mcp")
        self.assertEqual(item["env_keys"], ["TOKEN"])
        rendered = json.dumps(items)
        self.assertNotIn("sk-live-secret123", rendered)

    def test_plugins_snapshot_with_marketplace_freshness(self):
        plugins = self.root / "claude" / "plugins"
        plugins.mkdir(parents=True)
        (plugins / "installed_plugins.json").write_text(json.dumps({
            "version": 2,
            "plugins": {"hud@market": [{"scope": "user", "version": "1.0",
                                        "gitCommitSha": "abc", "installedAt": "t",
                                        "lastUpdated": "u"}]},
        }), encoding="utf-8")
        (plugins / "known_marketplaces.json").write_text(json.dumps({
            "market": {"lastUpdated": "2026-10-01T00:00:00Z"},
        }), encoding="utf-8")
        items = A.list_items("plugins")
        self.assertEqual(items[0]["id"], "hud@market")
        self.assertEqual(items[0]["marketplace_last_updated"], "2026-10-01T00:00:00Z")

    def test_bad_kind_rejected(self):
        with self.assertRaises(A.AdapterError):
            A.list_items("bogus")


class MutationTests(TempEnv):
    def _fake_cli(self):
        calls: list[list[str]] = []
        def run(argv, **kwargs):
            calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, "", "")
        return calls, run

    def test_toggle_uses_official_cli(self):
        calls, run = self._fake_cli()
        with mock.patch.object(A.subprocess, "run", run):
            A.toggle("mcp", "aisc-host", "codex", True)
        self.assertEqual(calls[0], ["cc-switch", "mcp", "enable", "aisc-host", "-a", "codex"])

    def test_delete_dispatches_per_kind(self):
        calls, run = self._fake_cli()
        with mock.patch.object(A.subprocess, "run", run):
            A.delete("skills", "superpowers")
            A.delete("mcp", "aisc-host")
            A.delete("plugins", "hud@market")
        self.assertEqual(calls[0][:4], ["cc-switch", "skills", "uninstall", "superpowers"])
        self.assertEqual(calls[1][:2], ["script", "-qec"])
        self.assertIn("cc-switch mcp delete aisc-host", calls[1][2])
        self.assertEqual(calls[2][:4], ["claude-real", "plugin", "uninstall", "hud"])

    def test_mcp_add_builds_deeplink_and_imports(self):
        calls, run = self._fake_cli()
        with mock.patch.object(A.subprocess, "run", run):
            url = A.mcp_add('{"mcpServers":{"test":{"command":"echo"}}}', ["claude", "codex"])
        self.assertIn("ccswitch://v1/import?resource=mcp", url)
        argv = calls[0]
        self.assertEqual(argv[:2], ["cc-switch", "deeplink"])
        # URL is decodable back to the config
        import base64 as b64, urllib.parse as up
        q = dict(up.parse_qsl(up.urlsplit(argv[2]).query))
        self.assertEqual(
            json.loads(b64.urlsafe_b64decode(q["config"])),
            {"mcpServers": {"test": {"command": "echo"}}},
        )

    def test_mcp_add_rejects_bad_config_and_apps(self):
        for bad in ('{"no":"mcpServers"}', "not-json"):
            with self.assertRaises(A.AdapterError):
                A.mcp_add(bad, ["claude"])
        with self.assertRaises(A.AdapterError):
            A.mcp_add('{"mcpServers":{}}', ["gemini"])

    def test_plugin_install_requires_marketplace_suffix(self):
        with self.assertRaises(A.AdapterError):
            A.plugin_install("hud")


class EnvelopeTests(TempEnv):
    def test_main_list_envelope(self):
        with mock.patch("sys.stdout", new_callable=__import__("io").StringIO) as out:
            rc = A.main(["list", "--kind", "skills"])
        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        self.assertEqual(doc["schema"], "aisc.extensions/v1")
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["items"][0]["id"], "superpowers")

    def test_main_error_envelope(self):
        with mock.patch("sys.stdout", new_callable=__import__("io").StringIO) as out:
            rc = A.main(["list"])
        self.assertEqual(rc, 1)
        doc = json.loads(out.getvalue())
        self.assertFalse(doc["ok"])
        self.assertEqual(doc["error"]["code"], "AISC_ERR_EXTENSIONS_BAD_REQUEST")


if __name__ == "__main__":
    unittest.main()

class MarketTests(TempEnv):
    def _fake(self, stdout="", rc=0):
        calls = []
        def run(argv, **kw):
            calls.append({"argv": list(argv), "input": kw.get("input", "")})
            return subprocess.CompletedProcess(argv, rc, stdout, "" if rc == 0 else "boom")
        return calls, run

    def test_mcp_delete_uses_script_pty_with_y(self):
        calls, run = self._fake()
        with mock.patch.object(A.subprocess, "run", run):
            A.delete("mcp", "cuse-test")
        argv = calls[0]["argv"]
        self.assertEqual(argv[:2], ["script", "-qec"])
        self.assertIn("mcp delete", argv[2])
        self.assertIn("cuse-test", argv[2])
        self.assertEqual(calls[0]["input"], "y\n")

    def test_mcp_delete_failure_maps_to_cli_error(self):
        calls, run = self._fake(rc=1)
        with mock.patch.object(A.subprocess, "run", run):
            with self.assertRaises(A.AdapterError):
                A.delete("mcp", "x")

    def test_parse_market_table(self):
        V, S = chr(0x2502), chr(0x2506)  # │ ┆
        row = V + " anthropics/skills:pdf " + S + " pdf " + S + " pdf " + S + " 214047 " + S + " anthropics/skills " + V
        raw = "\n".join([
            V + " Key " + S + " Directory " + V,
            row,
            "divider without proper cells",
        ])
        items = A._parse_market_table(raw)
        self.assertEqual(items[0]["id"], "anthropics/skills:pdf")
        self.assertEqual(items[0]["installs"], "214047")
    def test_skill_search_builds_market_argv(self):
        calls, run = self._fake(stdout="no table")
        with mock.patch.object(A.subprocess, "run", run):
            items = A.skill_search("pdf")
        self.assertEqual(calls[0]["argv"][:5], ["cc-switch", "skills", "market", "pdf", "--limit"])
        self.assertEqual(items, [])

    def test_deeplink_rejects_non_ccswitch(self):
        with self.assertRaises(A.AdapterError):
            A.deeplink_import("https://x")

    def test_deeplink_argv(self):
        calls, run = self._fake()
        with mock.patch.object(A.subprocess, "run", run):
            A.deeplink_import("ccswitch://v1/import?resource=mcp")
        self.assertEqual(calls[0]["argv"], ["cc-switch", "deeplink", "ccswitch://v1/import?resource=mcp"])

    def test_skill_repo_add(self):
        calls, run = self._fake()
        with mock.patch.object(A.subprocess, "run", run):
            A.skill_repo_add("https://github.com/anthropics/skills")
        self.assertEqual(calls[0]["argv"], ["cc-switch", "skills", "repos", "add", "https://github.com/anthropics/skills"])

    def test_parse_plugin_marketplaces(self):
        raw = "\n".join([
            "Configured marketplaces:",
            "  ❯ claude-plugins-official",
            "    Source: GitHub (anthropics/claude-plugins-official)",
        ])
        items = A._parse_plugin_marketplaces(raw)
        self.assertEqual(items[0]["id"], "claude-plugins-official")
        self.assertEqual(items[0]["source"], "GitHub (anthropics/claude-plugins-official)")

    def test_plugin_market_list(self):
        calls, run = self._fake(stdout="Configured marketplaces:\n")
        with mock.patch.object(A.subprocess, "run", run):
            items = A.plugin_market_list()
        self.assertEqual(calls[0]["argv"][:4], ["claude-real", "plugin", "marketplace", "list"])
        self.assertEqual(items, [])

    def test_skill_install_adds_repo_first(self):
        calls, run = self._fake()
        with mock.patch.object(A.subprocess, "run", run):
            A.skill_install("mattpocock/skills:grilling")
        self.assertEqual(calls[0]["argv"], ["cc-switch", "skills", "repos", "add", "mattpocock/skills"])
        self.assertEqual(calls[1]["argv"], ["cc-switch", "skills", "install", "mattpocock/skills:grilling"])

    def test_skill_install_plain_dir_skips_repo_add(self):
        calls, run = self._fake()
        with mock.patch.object(A.subprocess, "run", run):
            A.skill_install("caveman")
        self.assertEqual(calls[0]["argv"], ["cc-switch", "skills", "install", "caveman"])
