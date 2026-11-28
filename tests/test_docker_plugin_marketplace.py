from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FactoryPluginMarketTests(unittest.TestCase):
    def test_factory_plugins_start_empty_without_marketplace_cache(self):
        dockerfile = (ROOT / "container" / "Dockerfile").read_text(encoding="utf-8")
        self.assertNotIn("COPY container/_bundle/plugins/", dockerfile)
        self.assertNotIn("known_marketplaces.json", dockerfile)
        self.assertIn(
            "echo '{\"version\":2,\"plugins\":{}}' > /opt/aisc/factory/.claude/plugins/installed_plugins.json",
            dockerfile,
        )


if __name__ == "__main__":
    unittest.main()
