from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FactoryPluginMarketTests(unittest.TestCase):
    def test_official_market_is_builtin_without_factory_installs(self):
        dockerfile = (ROOT / "container" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn(
            "COPY container/_bundle/plugins/marketplaces/claude-plugins-official/ "
            "/opt/aisc/factory/.claude/plugins/marketplaces/claude-plugins-official/",
            dockerfile,
        )
        self.assertIn('"claude-plugins-official"', dockerfile)
        self.assertIn("anthropics/claude-plugins-official", dockerfile)
        self.assertIn(
            "echo '{}' > /opt/aisc/factory/.claude/plugins/installed_plugins.json",
            dockerfile,
        )
        self.assertNotIn(
            "COPY container/_bundle/plugins/cache/",
            dockerfile,
        )
        marketplace = (ROOT / "container" / "_bundle" / "plugins" / "marketplaces"
                       / "claude-plugins-official" / ".claude-plugin" / "marketplace.json")
        self.assertTrue(marketplace.is_file())


if __name__ == "__main__":
    unittest.main()
