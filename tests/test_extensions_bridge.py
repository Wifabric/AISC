"""v2.1.16 b5: host-side extensions data plane (docker exec bridge)."""

from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest import mock

from aisc.application import extensions as ext


def fake_executor(container="ct-1"):
    calls = []
    def run_captured(argv, timeout=0.0, input_text=""):
        calls.append({"argv": list(argv), "input": input_text, "timeout": timeout})
        return SimpleNamespace(exit_code=0, stdout=json.dumps({
            "schema": ext.PROTOCOL, "operation_id": "op", "op": argv_root(argv),
            "ok": True, "items": [],
        }) + "\n", stderr="")
    def argv_root(argv):
        return argv[argv.index("--") + 1] if "--" in argv else "list"
    return calls, SimpleNamespace(run_captured=run_captured)


class ValidationTests(unittest.TestCase):
    def test_rejects_bad_op_kind_agent(self):
        for fn, kwargs in [
            (lambda: ext._validate("bogus", None, None), {}),
        ]:
            from aisc.domain.models import CliError
            with self.assertRaises(CliError):
                fn()
        from aisc.domain.models import CliError
        with self.assertRaises(CliError):
            ext._validate("list", "bogus", None)
        with self.assertRaises(CliError):
            ext._validate("toggle", "skills", "gemini")


class BridgeTests(unittest.TestCase):
    def test_list_builds_scope_exec_and_parses_envelope(self):
        calls, executor = fake_executor()
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            data = ext.extensions_list("rid", "skills", "/ws", executor)
        argv = calls[0]["argv"]
        self.assertEqual(argv[:3], ["exec", "-i", "ct-1"])
        self.assertIn("aisc-scope", argv)
        self.assertIn("/usr/local/bin/aisc-extensions-adapter", argv)
        i = argv.index("/usr/local/bin/aisc-extensions-adapter")
        self.assertEqual(argv[i + 1: i + 5], ["list", "--kind", "skills"])
        self.assertEqual(data["kind"], "skills")
        self.assertEqual(calls[0]["timeout"], 600.0)

    def test_mcp_add_rides_stdin_not_argv(self):
        calls, executor = fake_executor()
        config = {"mcpServers": {"x": {"command": "echo"}}}
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            ext.extensions_mcp_add("rid", config, "claude,codex", "/ws", executor)
        argv = calls[0]["argv"]
        self.assertIn("--apps", argv)
        rendered = " ".join(argv)
        self.assertNotIn("mcpServers", rendered)
        self.assertEqual(json.loads(calls[0]["input"]), config)

    def test_skill_install_group_builds_exec_and_parses_itemized_envelope(self):
        calls = []
        payload = [
            {"spec": "owner/repo:a", "status": "installed", "error": ""},
            {"spec": "owner/repo:b", "status": "failed", "error": "cli exit 1"},
        ]

        def run_captured(argv, timeout=0.0, input_text=""):
            calls.append({"argv": list(argv), "input": input_text, "timeout": timeout})
            return SimpleNamespace(
                exit_code=0,
                stdout=json.dumps({
                    "schema": ext.PROTOCOL, "operation_id": "group-op",
                    "op": "skill-install-group", "ok": True,
                    "total": 2, "completed": 1, "items": payload,
                }) + "\n",
                stderr="",
            )

        executor = SimpleNamespace(run_captured=run_captured)
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            data = ext.extensions_skill_install_group(
                "rid", ["owner/repo:a", "owner/repo:b"], "/ws", executor)

        argv = calls[0]["argv"]
        i = argv.index("/usr/local/bin/aisc-extensions-adapter")
        self.assertEqual(argv[i + 1:i + 3], ["skill-install-group", "--specs"])
        self.assertEqual(argv[i + 3], '["owner/repo:a","owner/repo:b"]')
        self.assertEqual(data["kind"], "skills")
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["completed"], 1)
        self.assertEqual(data["items"], payload)
        self.assertEqual(data["operation_id"], "group-op")
    def test_skill_update_group_builds_exec_and_parses_itemized_envelope(self):
        calls = []

        def run_captured(argv, timeout=0.0, input_text=""):
            calls.append({"argv": list(argv), "input": input_text, "timeout": timeout})
            return SimpleNamespace(
                exit_code=0,
                stdout=json.dumps({
                    "schema": ext.PROTOCOL, "operation_id": "group-update",
                    "op": "skill-update-group", "ok": True,
                    "total": 2, "completed": 2,
                    "items": [
                        {"spec": "owner/repo:a", "status": "updated", "error": ""},
                        {"spec": "owner/repo:b", "status": "updated", "error": ""},
                    ],
                }) + "\n",
                stderr="",
            )

        executor = SimpleNamespace(run_captured=run_captured)
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            data = ext.extensions_skill_update_group(
                "rid", ["owner/repo:a", "owner/repo:b"], "/ws", executor)

        argv = calls[0]["argv"]
        i = argv.index("/usr/local/bin/aisc-extensions-adapter")
        self.assertEqual(argv[i + 1:i + 3], ["skill-update-group", "--specs"])
        self.assertEqual(argv[i + 3], '["owner/repo:a","owner/repo:b"]')
        self.assertEqual(data["kind"], "skills")
        self.assertEqual(data["completed"], 2)
        self.assertEqual(data["operation_id"], "group-update")

    def test_skill_group_timeout_derives_from_repos_and_children(self):
        calls = []

        def run_captured(argv, timeout=0.0, input_text=""):
            calls.append({"timeout": timeout})
            return SimpleNamespace(
                exit_code=0,
                stdout=json.dumps({
                    "schema": ext.PROTOCOL, "operation_id": "op",
                    "op": "skill-install-group", "ok": True,
                    "total": 2, "completed": 2, "items": [],
                }) + "\n",
                stderr="",
            )

        executor = SimpleNamespace(run_captured=run_captured)
        specs = ["owner/repo:a", "owner/repo:b"]
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            ext.extensions_skill_install_group("rid", specs, "/ws", executor)

        self.assertEqual(calls[0]["timeout"], 960.0)

    def test_skill_search_cache_and_updates_check_are_transported(self):
        calls = []

        def run_captured(argv, timeout=0.0, input_text=""):
            calls.append({"argv": list(argv), "op": argv[argv.index("--") + 1]
                          if "--" in argv else argv[0]})
            return SimpleNamespace(
                exit_code=0,
                stdout=json.dumps({
                    "schema": ext.PROTOCOL, "operation_id": "op",
                    "op": "skill-search", "ok": True,
                    "items": [{"id": "owner/repo:skill"}],
                    "cache": {"source": "cache", "cached": True,
                              "query": "skill", "error": "network down"},
                }) + "\n",
                stderr="",
            )

        executor = SimpleNamespace(run_captured=run_captured)
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            search = ext.extensions_call_raw("rid", "skill-search", "/ws", executor,
                                             query="skill")
            updates = ext.extensions_call_raw("rid", "updates-check", "/ws", executor)

        self.assertTrue(search["cache"]["cached"])
        self.assertIn("network down", search["cache"]["error"])
        self.assertEqual(updates["op"], "updates-check")
        self.assertEqual(calls[-1]["argv"][-1], "updates-check")

    def test_group_specs_json_transport_preserves_commas(self):
        calls = []

        def run_captured(argv, timeout=0.0, input_text=""):
            calls.append({"argv": list(argv), "input": input_text})
            return SimpleNamespace(
                exit_code=0,
                stdout=json.dumps({
                    "schema": ext.PROTOCOL, "operation_id": "op",
                    "op": "skill-install-group", "ok": True,
                    "total": 1, "completed": 1,
                    "items": [{"spec": "owner/repo:a,b", "status": "installed", "error": ""}],
                }) + "\n",
                stderr="",
            )

        executor = SimpleNamespace(run_captured=run_captured)
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            ext.extensions_skill_install_group(
                "rid", ["owner/repo:a,b"], "/ws", executor)

        argv = calls[0]["argv"]
        i = argv.index("/usr/local/bin/aisc-extensions-adapter")
        self.assertEqual(argv[i + 3], '["owner/repo:a,b"]')

    def test_adapter_error_maps_to_cli_error(self):
        def run_captured(argv, timeout=0.0, input_text=""):
            return SimpleNamespace(
                exit_code=1,
                stdout=json.dumps({
                    "schema": ext.PROTOCOL, "operation_id": "op", "op": "delete",
                    "ok": False,
                    "error": {"code": "AISC_ERR_EXTENSIONS_CLI_ERROR",
                              "message": "boom"},
                }),
                stderr="",
            )
        executor = SimpleNamespace(run_captured=run_captured)
        from aisc.domain.models import CliError
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            with self.assertRaises(CliError) as ctx:
                ext.extensions_delete("rid", "skills", "x", "/ws", executor)
        self.assertEqual(ctx.exception.error_code, "AISC_ERR_EXTENSIONS_CLI_ERROR")


    def test_r2_source_maintenance_ops_are_transportable(self):
        calls = []

        def run_captured(argv, timeout=0.0, input_text=""):
            calls.append({"argv": list(argv), "timeout": timeout})
            return SimpleNamespace(
                exit_code=0,
                stdout=json.dumps({
                    "schema": ext.PROTOCOL, "operation_id": "op", "op": "ok",
                    "ok": True, "items": [],
                }) + "\n",
                stderr="",
            )

        executor = SimpleNamespace(run_captured=run_captured)
        with mock.patch.object(ext, "resolve_running_container", return_value="ct-1"):
            listed = ext.extensions_call_raw("rid", "skill-repos-list", "/ws", executor)
            ext.extensions_call_raw("rid", "skill-repo-remove", "/ws", executor,
                                    item_id="owner/repo")
            ext.extensions_call_raw("rid", "plugin-market-remove", "/ws", executor,
                                    item_id="market")

        self.assertEqual(listed["op"], "skill-repos-list")
        adapter_args = [argv[argv.index("/usr/local/bin/aisc-extensions-adapter") + 1:]
                        for argv in [call["argv"] for call in calls]]
        self.assertIn(["skill-repos-list"], adapter_args)
        self.assertIn(["skill-repo-remove", "--id", "owner/repo"], adapter_args)
        self.assertIn(["plugin-market-remove", "--id", "market"], adapter_args)


if __name__ == "__main__":
    unittest.main()
