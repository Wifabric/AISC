import unittest
from types import SimpleNamespace
from unittest import mock

from aisc.cli.commands import extensions as ext_cmd
from aisc.cli.main import _cmd_extensions


class ExtensionsDispatchTests(unittest.TestCase):
    def test_market_ops_are_dispatched(self):
        cases = [
            ("mcp-search", "cmd_extensions_mcp_search"),
            ("mcp-market-install", "cmd_extensions_mcp_market_install"),
            ("plugin-update", "cmd_extensions_plugin_update"),
            ("skill-update", "cmd_extensions_skill_update"),
            ("skill-install-group", "cmd_extensions_skill_install_group"),
            ("skill-update-group", "cmd_extensions_skill_update_group"),
            ("plugin-search", "cmd_extensions_plugin_search"),
        ]
        for sub, command_name in cases:
            with self.subTest(sub=sub):
                attrs = {
                    "extensions_command": sub,
                    "runtime_id": "00000000-0000-4000-8000-000000000000",
                    "workspace": ".",
                    "query": "pdf",
                    "id": "example",
                    "spec": "owner/repo:skill",
                    "specs": '["owner/repo:skill"]',
                }
                args = SimpleNamespace(**attrs)
                with mock.patch.object(ext_cmd, command_name, return_value={"ok": True}) as cmd:
                    data, code, errors = _cmd_extensions(args, "json")
                self.assertEqual(code, 0)
                self.assertEqual(errors, [])
                self.assertEqual(data, {"ok": True})
                cmd.assert_called_once_with(args)


    def test_group_result_text_output_is_readable(self):
        import contextlib
        import io

        data = {
            "kind": "skills", "total": 2, "completed": 1,
            "items": [
                {"spec": "owner/repo:a", "status": "installed", "error": ""},
                {"spec": "owner/repo:b", "status": "failed", "error": "cli exit 1"},
            ],
        }
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ext_cmd.print_extensions_text(data)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], "1/2")
        self.assertEqual(lines[1], "owner/repo:a\tinstalled")
        self.assertEqual(lines[2], "owner/repo:b\tfailed | cli exit 1")

if __name__ == "__main__":
    unittest.main()
