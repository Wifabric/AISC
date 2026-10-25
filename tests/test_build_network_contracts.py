from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildNetworkContracts(unittest.TestCase):
    """preview b3: no-proxy builds must not depend on one direct GitHub path."""

    def test_dockerfile_github_downloads_use_the_shared_mirror_chain(self):
        dockerfile = (ROOT / "container" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn('ARG GH_MIRRORS="https://ghfast.top/ https://gh-proxy.com/', dockerfile)
        # Every online GitHub asset segment consumes the same chain and keeps
        # direct as the final candidate.
        self.assertEqual(dockerfile.count('for m in $mirrors ""; do'), 4)
        self.assertEqual(dockerfile.count('for m in $yazi_mirrors ""; do'), 1)

    def test_staging_scripts_have_mirror_and_direct_candidates(self):
        cc_switch = (ROOT / "scripts" / "stage-cc-switch.sh").read_text(encoding="utf-8")
        self.assertIn('mirrors = ["https://ghfast.top/", "https://gh-proxy.com/"', cc_switch)
        self.assertIn('""]', cc_switch)

        npm = (ROOT / "scripts" / "stage-npm.sh").read_text(encoding="utf-8")
        self.assertIn('for m in "https://ghfast.top/" "https://gh-proxy.com/"', npm)
        self.assertIn('""', npm)

        mihomo = (ROOT / "tools" / "stage-mihomo.sh").read_text(encoding="utf-8")
        self.assertIn('MIRRORS=("https://ghfast.top/" "https://gh-proxy.com/"', mihomo)
        self.assertIn('for m in "${MIRRORS[@]}" ""', mihomo)

    def test_cc_switch_api_resolver_has_tested_mirror_fallback(self):
        resolver = (ROOT / "src" / "aisc" / "application" / "cc_switch_resolver.py").read_text(encoding="utf-8")
        self.assertIn('DEFAULT_API_MIRROR_PREFIX = "https://gh-proxy.com/"', resolver)
        self.assertIn("if self._api_base == DEFAULT_API_BASE:", resolver)


if __name__ == "__main__":
    unittest.main()
