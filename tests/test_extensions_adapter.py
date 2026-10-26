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
        self.assertEqual(item["directory"], "superpowers")
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

    def test_main_skill_install_group_envelope(self):
        result = {
            "total": 2, "completed": 2,
            "items": [
                {"spec": "obra/superpowers:brainstorming", "status": "installed", "error": ""},
                {"spec": "obra/superpowers:debugging", "status": "installed", "error": ""},
            ],
        }
        with mock.patch.object(A, "skill_install_group", return_value=result) as group_mock, \
             mock.patch("sys.stdout", new_callable=__import__("io").StringIO) as out:
            rc = A.main([
                "skill-install-group",
                "--specs", '["obra/superpowers:brainstorming","obra/superpowers:debugging"]',
            ])
        group_mock.assert_called_once_with([
            "obra/superpowers:brainstorming", "obra/superpowers:debugging",
        ])

        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        self.assertEqual(doc["op"], "skill-install-group")
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["total"], 2)
        self.assertEqual(doc["completed"], 2)
        self.assertEqual(
            [item["spec"] for item in doc["items"]],
            ["obra/superpowers:brainstorming", "obra/superpowers:debugging"],
        )

    def test_main_skill_update_group_envelope(self):
        result = {
            "total": 2, "completed": 2,
            "items": [
                {"spec": "obra/superpowers:brainstorming", "status": "updated", "error": ""},
                {"spec": "obra/superpowers:debugging", "status": "updated", "error": ""},
            ],
        }
        with mock.patch.object(A, "skill_update_group", return_value=result) as group_mock, \
             mock.patch("sys.stdout", new_callable=__import__("io").StringIO) as out:
            rc = A.main([
                "skill-update-group",
                "--specs", '["obra/superpowers:brainstorming","obra/superpowers:debugging"]',
            ])
        group_mock.assert_called_once_with([
            "obra/superpowers:brainstorming", "obra/superpowers:debugging",
        ])

        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        self.assertEqual(doc["op"], "skill-update-group")
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["total"], 2)
        self.assertEqual(doc["completed"], 2)
        self.assertTrue(all(item["status"] == "updated" for item in doc["items"]))

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
    def test_mcp_search_sends_explicit_user_agent(self):
        import urllib.request

        captured = {}

        class Resp:
            def read(self):
                return json.dumps({"servers": []}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def urlopen(req, timeout=None):
            captured["headers"] = dict(req.header_items())
            captured["timeout"] = timeout
            return Resp()

        with mock.patch.object(A.urllib.request, "urlopen", urlopen):
            items = A.mcp_search("pdf")
        self.assertEqual(items, [])
        self.assertEqual(captured["headers"].get("User-agent"), "AISC/2.1.16")
        self.assertLessEqual(captured["timeout"], 20)

    def test_skill_search_builds_market_argv(self):
        import urllib.request
        calls, run = self._fake(stdout="no table")

        class Resp:
            def read(self):
                return json.dumps({"skills": []}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with mock.patch.object(A.subprocess, "run", run), \
             mock.patch.object(A.urllib.request, "urlopen", return_value=Resp()):
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
        self.assertEqual(calls[0]["argv"][:3], ["git", "ls-remote", "https://github.com/anthropics/skills.git"])
        self.assertEqual(calls[1]["argv"], ["cc-switch", "skills", "repos", "add", "https://github.com/anthropics/skills"])

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
        self.assertEqual(calls[0]["argv"][:4], ["git", "ls-remote", "--symref", "https://github.com/mattpocock/skills.git"])
        self.assertEqual(calls[1]["argv"][:2], ["curl", "-fsSIL"])
        self.assertEqual(calls[2]["argv"], ["cc-switch", "skills", "repos", "add", "mattpocock/skills"])
        self.assertEqual(calls[3]["argv"], ["cc-switch", "skills", "install", "mattpocock/skills:grilling"])

    def test_skill_install_plain_dir_skips_repo_add(self):
        calls, run = self._fake()
        with mock.patch.object(A.subprocess, "run", run):
            A.skill_install("caveman")
        self.assertEqual(calls[0]["argv"], ["cc-switch", "skills", "install", "caveman"])

    def test_skill_install_stages_mirror_clone_when_direct_archive_fails(self):
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv), "env": kwargs.get("env"),
                          "timeout": kwargs.get("timeout")})
            if argv[:3] == ["git", "ls-remote", "--symref"]:
                return subprocess.CompletedProcess(
                    argv, 0, "ref: refs/heads/master\tHEAD\nsha HEAD\n", "")
            if argv[:2] == ["curl", "-fsSIL"]:
                if argv[-1].startswith("https://github.com/"):
                    return subprocess.CompletedProcess(argv, 1, "", "direct archive down")
                return subprocess.CompletedProcess(argv, 0, "HTTP/2 200", "")
            if argv[:2] == ["git", "clone"]:
                destination = Path(argv[-1])
                skill = destination / "skills" / "cavecrew"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    "---\nname: cavecrew\n---\n", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(argv, 0, "master\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with mock.patch.object(A.subprocess, "run", run):
            A.skill_install("JuliusBrussee/caveman:cavecrew")

        self.assertEqual(calls[0]["argv"][:3], ["git", "ls-remote", "--symref"])
        self.assertEqual(calls[1]["argv"][-1], "https://github.com/JuliusBrussee/caveman/archive/refs/heads/master.zip")
        self.assertEqual(calls[2]["argv"][-1], "https://ghfast.top/https://github.com/JuliusBrussee/caveman/archive/refs/heads/master.zip")
        self.assertEqual(calls[3]["argv"][:2], ["git", "clone"])
        self.assertIn("ghfast.top", calls[3]["env"]["GIT_CONFIG_KEY_0"])
        self.assertEqual(calls[4]["argv"][:4], ["git", "-C", calls[3]["argv"][-1], "rev-parse"])
        self.assertEqual(calls[5]["argv"], [
            "cc-switch", "skills", "repos", "add", "JuliusBrussee/caveman@master"
        ])
        self.assertEqual(calls[6]["argv"], [
            "cc-switch", "skills", "install", "JuliusBrussee/caveman:cavecrew"
        ])
        staged = self.root / "skills" / "cavecrew" / "SKILL.md"
        self.assertTrue(staged.is_file())
        self.assertEqual(calls[-2]["argv"], ["cc-switch", "skills", "enable", "cavecrew", "-a", "claude"])
        self.assertEqual(calls[-1]["argv"], ["cc-switch", "skills", "enable", "cavecrew", "-a", "codex"])

    def test_skill_install_group_stages_and_installs_all_children(self):
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv), "env": kwargs.get("env")})
            if argv[:3] == ["git", "ls-remote", "--symref"]:
                return subprocess.CompletedProcess(
                    argv, 0, "ref: refs/heads/master\tHEAD\nsha HEAD\n", "")
            if argv[:2] == ["curl", "-fsSIL"]:
                if argv[-1].startswith("https://github.com/"):
                    return subprocess.CompletedProcess(argv, 1, "", "direct archive down")
                return subprocess.CompletedProcess(argv, 0, "HTTP/2 200", "")
            if argv[:2] == ["git", "clone"]:
                destination = Path(argv[-1])
                for name in ("cavecrew", "caveman-commit"):
                    skill = destination / "skills" / name
                    skill.mkdir(parents=True)
                    (skill / "SKILL.md").write_text(
                        f"---\nname: {name}\n---\n", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(argv, 0, "master\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        specs = [
            "JuliusBrussee/caveman:cavecrew",
            "JuliusBrussee/caveman:caveman-commit",
        ]
        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_install_group(specs)

        clone_calls = [call for call in calls if call["argv"][:2] == ["git", "clone"]]
        self.assertEqual(len(clone_calls), 1)
        self.assertTrue(
            (self.root / "skills" / "cavecrew" / "SKILL.md").is_file())
        self.assertTrue(
            (self.root / "skills" / "caveman-commit" / "SKILL.md").is_file())
        self.assertEqual([
            call["argv"] for call in calls
            if call["argv"][:4] == ["cc-switch", "skills", "install", "JuliusBrussee/caveman:cavecrew"]
        ], [["cc-switch", "skills", "install", "JuliusBrussee/caveman:cavecrew"]])
        self.assertEqual([
            call["argv"] for call in calls
            if call["argv"][:4] == ["cc-switch", "skills", "install", "JuliusBrussee/caveman:caveman-commit"]
        ], [["cc-switch", "skills", "install", "JuliusBrussee/caveman:caveman-commit"]])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["completed"], 2)
        self.assertEqual([item["spec"] for item in result["items"]], specs)
        self.assertTrue(all(item["status"] == "installed" for item in result["items"]))
    def test_skill_install_group_stops_before_install_when_child_is_missing(self):
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv)})
            if argv[:3] == ["git", "ls-remote", "--symref"]:
                return subprocess.CompletedProcess(
                    argv, 0, "ref: refs/heads/master\tHEAD\nsha HEAD\n", "")
            if argv[:2] == ["curl", "-fsSIL"]:
                if argv[-1].startswith("https://github.com/"):
                    return subprocess.CompletedProcess(argv, 1, "", "direct archive down")
                return subprocess.CompletedProcess(argv, 0, "HTTP/2 200", "")
            if argv[:2] == ["git", "clone"]:
                destination = Path(argv[-1])
                skill = destination / "skills" / "cavecrew"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    "---\nname: cavecrew\n---\n", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(argv, 0, "master\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        specs = [
            "JuliusBrussee/caveman:cavecrew",
            "JuliusBrussee/caveman:missing-child",
        ]
        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_install_group(specs)

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["completed"], 0)
        self.assertFalse(any(
            call["argv"][:3] == ["cc-switch", "skills", "install"]
            for call in calls
        ))
        self.assertEqual(result["items"][0]["status"], "blocked")
        self.assertEqual(result["items"][1]["status"], "missing")
        self.assertIn("SKILL.md not found", result["items"][1]["error"])
    def test_skill_install_group_preflights_direct_source_before_install(self):
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv), "env": kwargs.get("env")})
            if argv[:3] == ["git", "ls-remote", "--symref"]:
                return subprocess.CompletedProcess(
                    argv, 0, "ref: refs/heads/main\tHEAD\nsha HEAD\n", "")
            if argv[:2] == ["git", "clone"]:
                destination = Path(argv[-1])
                valid = destination / "skills" / "valid"
                valid.mkdir(parents=True)
                (valid / "SKILL.md").write_text("---\nname: valid\n---\n")
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(argv, 0, "main\n", "")
            return subprocess.CompletedProcess(argv, 0, "HTTP/2 200", "")

        specs = ["owner/repo:valid", "owner/repo:missing"]
        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_install_group(specs)

        self.assertEqual(result["completed"], 0)
        self.assertFalse(any(
            call["argv"][:3] == ["cc-switch", "skills", "install"]
            for call in calls
        ))
        self.assertEqual(result["items"][0]["status"], "blocked")
        self.assertEqual(result["items"][1]["status"], "missing")

    def test_skill_install_group_itemizes_unreachable_direct_and_mirror_sources(self):
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv)})
            if argv[:3] == ["git", "ls-remote", "--symref"]:
                return subprocess.CompletedProcess(argv, 1, "", "git direct down")
            if argv[:2] == ["curl", "-fsSIL"]:
                return subprocess.CompletedProcess(argv, 1, "", "curl archive down")
            return subprocess.CompletedProcess(argv, 1, "", "unexpected command")

        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_install_group(["owner/repo:a", "owner/repo:b"])

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["completed"], 0)
        self.assertFalse(any(
            call["argv"][:3] == ["cc-switch", "skills", "install"]
            for call in calls
        ))
        errors = "\n".join(item["error"] for item in result["items"])
        self.assertIn("owner/repo", errors)
        self.assertIn("direct", errors)
        self.assertIn("ghfast.top", errors)
        self.assertIn("gh-proxy.com", errors)
        self.assertEqual(result["items"][0]["status"], "source_failed")
        self.assertEqual(result["items"][1]["status"], "source_failed")

    def test_skill_group_rejects_invalid_directories_before_subprocess(self):
        def run(argv, **kwargs):
            raise AssertionError(f"unexpected subprocess: {argv}")

        for spec in ("owner/repo:", "owner/repo:.", "owner/repo:../x"):
            with self.subTest(spec=spec), \
                 mock.patch.object(A.subprocess, "run", run):
                with self.assertRaises(A.AdapterError):
                    A.skill_install_group([spec])

    def test_skill_install_group_itemizes_official_cli_stderr_tail(self):
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv)})
            if argv[:3] == ["git", "ls-remote", "--symref"]:
                return subprocess.CompletedProcess(
                    argv, 0, "ref: refs/heads/main\tHEAD\nsha HEAD\n", "")
            if argv[:2] == ["git", "clone"]:
                destination = Path(argv[-1])
                for name in ("a", "b"):
                    skill = destination / "skills" / name
                    skill.mkdir(parents=True)
                    (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(argv, 0, "main\n", "")
            if argv[:4] == ["cc-switch", "skills", "install", "owner/repo:b"]:
                return subprocess.CompletedProcess(argv, 1, "", "cc-switch official failure tail")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_install_group(["owner/repo:a", "owner/repo:b"])

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["items"][0]["status"], "installed")
        self.assertEqual(result["items"][1]["status"], "failed")
        self.assertIn("cc-switch official failure tail", result["items"][1]["error"])

    def test_skill_install_group_retries_clone_through_mirror_after_direct_body_fails(self):
        calls = []

        def run(argv, **kwargs):
            env = kwargs.get("env") or {}
            calls.append({"argv": list(argv), "env": env})
            if argv[:3] == ["git", "ls-remote", "--symref"]:
                return subprocess.CompletedProcess(
                    argv, 0, "ref: refs/heads/main\tHEAD\nsha HEAD\n", "")
            if argv[:2] == ["git", "clone"]:
                if "ghfast.top" not in env.get("GIT_CONFIG_KEY_0", ""):
                    return subprocess.CompletedProcess(
                        argv, 1, "", "direct clone body down")
                destination = Path(argv[-1])
                skill = destination / "skills" / "a"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text("---\nname: a\n---\n")
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(argv, 0, "main\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_install_group(["owner/repo:a"])

        clone_attempts = [call for call in calls if call["argv"][:2] == ["git", "clone"]]
        self.assertEqual(len(clone_attempts), 2)
        self.assertIn("ghfast.top", clone_attempts[1]["env"]["GIT_CONFIG_KEY_0"])
        self.assertEqual(result["completed"], 1)

    def test_skill_update_group_supports_local_directory(self):
        connection = sqlite3.connect(self.root / "cc-switch.db")
        connection.execute(
            "INSERT INTO skills (id,name,description,directory,"
            "enabled_claude,enabled_codex,enabled_gemini,enabled_grokbuild,"
            "enabled_opencode,enabled_hermes,installed_at,content_hash,updated_at) "
            "VALUES ('local','local','desc','local',1,0,0,0,0,0,"
            "'2026-01-01','x','2026-01-02')"
        )
        connection.commit()
        connection.close()
        calls, run = self._fake()

        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_update_group(["local"])

        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["items"][0]["status"], "updated")
        argvs = [call["argv"] for call in calls]
        self.assertIn(["cc-switch", "skills", "install", "local"], argvs)
        self.assertIn(["cc-switch", "skills", "enable", "local", "-a", "claude"], argvs)
        self.assertIn(["cc-switch", "skills", "disable", "local", "-a", "codex"], argvs)

    def test_skill_install_group_enables_both_agents_for_local_directory(self):
        calls, run = self._fake()

        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_install_group(["local"])

        self.assertEqual(result["completed"], 1)
        argvs = [call["argv"] for call in calls]
        self.assertIn(["cc-switch", "skills", "install", "local"], argvs)
        self.assertIn(["cc-switch", "skills", "enable", "local", "-a", "claude"], argvs)
        self.assertIn(["cc-switch", "skills", "enable", "local", "-a", "codex"], argvs)

    def test_skill_update_group_uses_preflighted_state_for_local_directory(self):
        connection = sqlite3.connect(self.root / "cc-switch.db")
        connection.execute(
            "INSERT INTO skills (id,name,description,directory,"
            "enabled_claude,enabled_codex,enabled_gemini,enabled_grokbuild,"
            "enabled_opencode,enabled_hermes,installed_at,content_hash,updated_at) "
            "VALUES ('local','local','desc','local',1,0,0,0,0,0,"
            "'2026-01-01','x','2026-01-02')"
        )
        connection.commit()
        connection.close()
        states = iter([
            {"claude": True, "codex": False},
            None,  # The old local fallback reread state here.
        ])
        calls, run = self._fake()

        with mock.patch.object(A, "_skill_enable_states", side_effect=lambda _d: next(states)), \
             mock.patch.object(A.subprocess, "run", run):
            result = A.skill_update_group(["local"])

        self.assertEqual(result["completed"], 1)
        argvs = [call["argv"] for call in calls]
        self.assertIn(["cc-switch", "skills", "install", "local"], argvs)
        self.assertIn(["cc-switch", "skills", "enable", "local", "-a", "claude"], argvs)
        self.assertIn(["cc-switch", "skills", "disable", "local", "-a", "codex"], argvs)

    def test_skill_group_reuses_registered_repo_casing(self):
        connection = sqlite3.connect(self.root / "cc-switch.db")
        connection.execute(
            "INSERT INTO skills (id,name,description,directory,repo_owner,repo_name,"
            "repo_branch,enabled_claude,enabled_codex,enabled_gemini,enabled_grokbuild,"
            "enabled_opencode,enabled_hermes,installed_at,content_hash,updated_at) "
            "VALUES ('JuliusBrussee/caveman:caveman','caveman','desc','caveman',"
            "'JuliusBrussee','caveman','main',1,1,0,0,0,0,"
            "'2026-01-01','x','2026-01-02')"
        )
        connection.commit()
        connection.close()
        calls, run = self._fake()

        with mock.patch.object(A, "_github_repo_identity", return_value=("owner", "repo", None)), \
             mock.patch.object(A, "_github_git_env", return_value={}), \
             mock.patch.object(A, "_stage_skills_from_git_source", return_value=[]), \
             mock.patch.object(A.subprocess, "run", run):
            result = A.skill_install_group([
                "juliusbrussee/caveman:caveman"
            ])

        self.assertEqual(result["completed"], 1)
        self.assertIn(
            ["cc-switch", "skills", "install",
             "JuliusBrussee/caveman:caveman"],
            [call["argv"] for call in calls],
        )

    def test_skill_update_group_requires_every_enable_state_before_install(self):
        states = {
            "superpowers": {"claude": True, "codex": False},
        }
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv)})
            return subprocess.CompletedProcess(argv, 0, "HTTP/2 200", "")

        with mock.patch.object(A, "_skill_enable_states", side_effect=states.get), \
             mock.patch.object(A, "_github_skill_env", return_value={}), \
             mock.patch.object(A.subprocess, "run", run):
            result = A.skill_update_group([
                "obra/superpowers:superpowers",
                "obra/superpowers:missing",
            ])

        self.assertEqual(result["completed"], 0)
        self.assertFalse(any(
            call["argv"][:3] == ["cc-switch", "skills", "install"]
            for call in calls
        ))
        self.assertEqual(result["items"][0]["status"], "blocked")
        self.assertEqual(result["items"][1]["status"], "state_unavailable")

    def test_skill_update_group_preflights_all_and_preserves_enable_state(self):
        connection = sqlite3.connect(self.root / "cc-switch.db")
        connection.execute(
            "INSERT INTO skills VALUES ('JuliusBrussee/caveman:cavecrew','cavecrew',"
            "'desc','cavecrew','JuliusBrussee','caveman','master','',"
            "1,0,0,0,0,0,'2026-01-01','x','2026-01-02')"
        )
        connection.execute(
            "INSERT INTO skills VALUES ('JuliusBrussee/caveman:caveman-commit',"
            "'caveman-commit','desc','caveman-commit','JuliusBrussee','caveman',"
            "'master','',0,1,0,0,0,0,'2026-01-01','x','2026-01-02')"
        )
        connection.commit()
        connection.close()
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv), "env": kwargs.get("env")})
            if argv[:3] == ["git", "ls-remote", "--symref"]:
                return subprocess.CompletedProcess(
                    argv, 0, "ref: refs/heads/master\tHEAD\nsha HEAD\n", "")
            if argv[:2] == ["git", "clone"]:
                destination = Path(argv[-1])
                for name in ("cavecrew", "caveman-commit"):
                    skill = destination / "skills" / name
                    skill.mkdir(parents=True)
                    (skill / "SKILL.md").write_text(
                        f"---\nname: {name}\n---\n", encoding="utf-8")
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:2] == ["git", "-C"]:
                return subprocess.CompletedProcess(argv, 0, "master\n", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        specs = [
            "JuliusBrussee/caveman:cavecrew",
            "JuliusBrussee/caveman:caveman-commit",
        ]
        with mock.patch.object(A.subprocess, "run", run):
            result = A.skill_update_group(specs)

        self.assertEqual(
            len([call for call in calls if call["argv"][:2] == ["git", "clone"]]), 1)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["completed"], 2)
        self.assertTrue(all(item["status"] == "updated" for item in result["items"]))
        argvs = [call["argv"] for call in calls]
        self.assertIn(["cc-switch", "skills", "enable", "cavecrew", "-a", "claude"], argvs)
        self.assertIn(["cc-switch", "skills", "disable", "cavecrew", "-a", "codex"], argvs)
        self.assertIn(["cc-switch", "skills", "disable", "caveman-commit", "-a", "claude"], argvs)
        self.assertIn(["cc-switch", "skills", "enable", "caveman-commit", "-a", "codex"], argvs)

    def test_mcp_market_install_uses_smithery_http_deployment_url(self):
        import urllib.request

        payload = {
            "qualifiedName": "re-port-flow/reportflow-mcp",
            "deploymentUrl": "https://reportflow-mcp--re-port-flow.run.tools",
            "connections": [{"type": "http", "deploymentUrl": "https://reportflow-mcp--re-port-flow.run.tools"}],
        }

        class Resp:
            def read(self):
                return json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with mock.patch.object(A.urllib.request, "urlopen", return_value=Resp()):
            config = A.mcp_market_install("re-port-flow/reportflow-mcp")
        parsed = json.loads(config)["mcpServers"]["reportflow-mcp"]
        self.assertEqual(parsed["url"], "https://reportflow-mcp--re-port-flow.run.tools")

    def test_skill_install_enables_claude_and_codex_by_default(self):
        calls, run = self._fake()
        with mock.patch.object(A.subprocess, "run", run):
            A.skill_install("obra/superpowers:using-superpowers")
        self.assertEqual(calls[-2]["argv"], ["cc-switch", "skills", "enable", "using-superpowers", "-a", "claude"])
        self.assertEqual(calls[-1]["argv"], ["cc-switch", "skills", "enable", "using-superpowers", "-a", "codex"])

    def test_skill_update_preserves_existing_enable_state(self):
        calls, run = self._fake()
        with mock.patch.object(A.subprocess, "run", run):
            A.skill_update("obra/superpowers:superpowers")
        self.assertIn(["cc-switch", "skills", "enable", "superpowers", "-a", "claude"], [call["argv"] for call in calls])
        self.assertIn(["cc-switch", "skills", "disable", "superpowers", "-a", "codex"], [call["argv"] for call in calls])

    def test_github_operations_retry_through_git_mirrors(self):
        calls = []

        def run(argv, **kwargs):
            calls.append({"argv": list(argv), "env": kwargs.get("env")})
            if len(calls) == 1:
                return subprocess.CompletedProcess(argv, 1, "", "network down")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with mock.patch.object(A.subprocess, "run", run):
            A.plugin_install("demo@market")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["env"]["GIT_CONFIG_COUNT"], "1")
        self.assertIn("ghfast.top", calls[1]["env"]["GIT_CONFIG_KEY_0"])
        self.assertEqual(calls[1]["env"]["GIT_CONFIG_VALUE_0"], "https://github.com/")

    def test_skill_search_falls_back_to_skills_api(self):
        import urllib.request

        def failed_run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, "", "network down")

        payload = {
            "skills": [
                {"source": "obra/superpowers", "skillId": "brainstorming", "name": "brainstorming", "installs": 123}
            ]
        }

        class Resp:
            def read(self):
                return json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with mock.patch.object(A.subprocess, "run", failed_run), mock.patch.object(A.urllib.request, "urlopen", return_value=Resp()):
            items = A.skill_search("brainstorming")
        self.assertEqual(items[0]["id"], "obra/superpowers:brainstorming")
        self.assertEqual(items[0]["directory"], "brainstorming")

    def test_parse_plugin_available_filters_and_shapes_items(self):
        raw = json.dumps({
            "installed": [],
            "available": [
                {"pluginId": "chart@official", "name": "chart", "description": "Draw charts",
                 "marketplaceName": "official", "installCount": 12,
                 "source": {"url": "https://example/chart.git"}},
                {"pluginId": "pdf@official", "name": "pdf", "description": "PDF tools",
                 "marketplaceName": "official", "installCount": 20,
                 "source": "./plugins/pdf"},
            ],
        })
        calls, run = self._fake(stdout=raw)
        with mock.patch.object(A.subprocess, "run", run):
            items = A.plugin_search("chart")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["kind"], "market-plugin")
        self.assertEqual(items[0]["id"], "chart@official")
        self.assertEqual(items[0]["repo"], "https://example/chart.git")
        self.assertEqual(items[0]["installs"], "12")

    def test_plugin_search_builds_available_argv(self):
        calls, run = self._fake(stdout='{"installed":[],"available":[]}')
        with mock.patch.object(A.subprocess, "run", run):
            items = A.plugin_search("skill")
        self.assertEqual(calls[0]["argv"], [
            "claude-real", "plugin", "list", "--available", "--json",
        ])
        self.assertEqual(items, [])


    def test_mcp_search_falls_back_to_alternate_smithery_host(self):
        import urllib.request
        attempts = []

        class Resp:
            def read(self):
                return json.dumps({"servers": []}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def urlopen(req, timeout=None):
            attempts.append(req.full_url)
            if len(attempts) == 1:
                raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)
            return Resp()

        with mock.patch.object(A.urllib.request, "urlopen", urlopen):
            items = A.mcp_search("pdf")
        self.assertEqual(items, [])
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[1], "https://api.smithery.ai/servers?q=pdf&pageSize=10")
