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
                }
                args = SimpleNamespace(**attrs)
                with mock.patch.object(ext_cmd, command_name, return_value={"ok": True}) as cmd:
                    data, code, errors = _cmd_extensions(args, "json")
                self.assertEqual(code, 0)
                self.assertEqual(errors, [])
                self.assertEqual(data, {"ok": True})
                cmd.assert_called_once_with(args)


if __name__ == "__main__":
    unittest.main()
