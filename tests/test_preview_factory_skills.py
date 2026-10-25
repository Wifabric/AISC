from pathlib import Path
import importlib.util
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "container" / "cc_switch_skills.py"
_loader = importlib.util.spec_from_file_location("cc_switch_skills_preview", HELPER)
assert _loader and _loader.loader
A = importlib.util.module_from_spec(_loader)
_loader.loader.exec_module(A)


class PreviewFactorySkillsTests(unittest.TestCase):
    def test_bundled_skills_are_complete_caveman_suite_and_grill_me(self):
        self.assertEqual(
            tuple(row[0] for row in A.BUNDLED_SKILLS),
            (
                "caveman", "caveman-commit", "caveman-compress",
                "caveman-discover", "caveman-evidence-review", "caveman-explore",
                "caveman-help", "caveman-learn", "caveman-manage",
                "caveman-optimize", "caveman-review", "caveman-setup",
                "caveman-stats", "grill-me",
            ),
        )

    def test_vendored_caveman_suite_contains_exactly_thirteen_caveman_skills(self):
        vendored = {
            path.name for path in
            (ROOT / "container" / "_bundle" / "plugins" / "marketplaces" / "caveman" / "skills").iterdir()
            if path.is_dir()
        }
        self.assertEqual(vendored, {
            "caveman", "caveman-commit", "caveman-compress",
            "caveman-discover", "caveman-evidence-review", "caveman-explore",
            "caveman-help", "caveman-learn", "caveman-manage",
            "caveman-optimize", "caveman-review", "caveman-setup",
            "caveman-stats",
        })

    def test_dockerfile_stages_only_the_ruled_skills_offline(self):
        dockerfile = (ROOT / "container" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn(
            "COPY container/cc-switch-skills/grill-me/ /opt/aisc/skills/grill-me/",
            dockerfile,
        )
        self.assertIn(
            "COPY container/_bundle/plugins/marketplaces/caveman/skills/ /opt/aisc/skills/",
            dockerfile,
        )
        self.assertIn(".aisc-bundle.sha256", dockerfile)
        self.assertNotIn(
            "COPY container/cc-switch-skills/ /opt/aisc/skills/", dockerfile
        )
        for skill in (
            "caveman", "caveman-commit", "caveman-compress",
            "caveman-discover", "caveman-evidence-review", "caveman-explore",
            "caveman-help", "caveman-learn", "caveman-manage",
            "caveman-optimize", "caveman-review", "caveman-setup",
            "caveman-stats",
        ):
            self.assertIn(f" {skill} ", dockerfile)

    def test_entrypoint_reports_the_managed_factory_skills(self):
        entrypoint = (ROOT / "container" / "entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("已安装 13 个 caveman 技能与 grill-me", entrypoint)
        self.assertIn("/usr/local/bin/lib/cc_switch_skills.py", entrypoint)
        self.assertIn('--mode "${AISC_SKILLS_SYNC:-auto}"', entrypoint)

    def test_state_query_supports_variable_bundled_skill_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cc-switch.db"
            conn = sqlite3.connect(db)
            conn.execute(
                "CREATE TABLE skills (name TEXT, enabled_claude INTEGER, enabled_codex INTEGER)"
            )
            conn.executemany(
                "INSERT INTO skills VALUES (?, ?, ?)",
                [("caveman", 1, 0), ("grill-me", 0, 1), ("other", 1, 1)],
            )
            conn.commit()
            conn.close()
            states = A._load_skill_states(db)
        self.assertEqual(states["caveman"], (True, False))
        self.assertEqual(states["grill-me"], (False, True))
        self.assertNotIn("other", states)


if __name__ == "__main__":
    unittest.main()
