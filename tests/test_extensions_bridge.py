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
        self.assertEqual(argv[i + 3], "owner/repo:a,owner/repo:b")
        self.assertEqual(data["kind"], "skills")
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["completed"], 1)
        self.assertEqual(data["items"], payload)
        self.assertEqual(data["operation_id"], "group-op")
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


if __name__ == "__main__":
    unittest.main()
