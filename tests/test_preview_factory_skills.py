from pathlib import Path
import importlib.util
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

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


class FactorySkillRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config_dir = Path(self.temp.name)
        self.db_path = self.config_dir / "cc-switch.db"
        connection = sqlite3.connect(self.db_path)
        connection.execute("""
            CREATE TABLE skills (
                id TEXT PRIMARY KEY, name TEXT, description TEXT, directory TEXT,
                repo_owner TEXT, repo_name TEXT, repo_branch TEXT,
                enabled_claude INTEGER, enabled_codex INTEGER,
                installed_at INTEGER, updated_at INTEGER
            )
        """)
        connection.close()

    def _rows(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        rows = {row["name"]: dict(row) for row in connection.execute("SELECT * FROM skills")}
        connection.close()
        return rows

    def test_all_fresh_rows_have_dual_defaults_identity_metadata_and_timestamps(self):
        with patch.object(A.time, "time", return_value=1234):
            A._register_skills(self.config_dir)
        rows = self._rows()
        self.assertEqual(len(rows), 14)
        for name, description, owner, repo in A.BUNDLED_SKILLS:
            with self.subTest(skill=name):
                self.assertEqual(rows[name], {
                    "id": f"aisc:{name}", "name": name, "description": description,
                    "directory": name, "repo_owner": owner, "repo_name": repo,
                    "repo_branch": "main", "enabled_claude": 1, "enabled_codex": 1,
                    "installed_at": 1234, "updated_at": 1234,
                })

    def test_reregistration_preserves_mixed_choices_install_time_and_unrelated_rows(self):
        with patch.object(A.time, "time", return_value=100):
            A._register_skills(self.config_dir)
        states = {}
        connection = sqlite3.connect(self.db_path)
        for index, (name, *_) in enumerate(A.BUNDLED_SKILLS):
            states[name] = ((1, 0), (0, 1), (0, 0), (1, 1))[index % 4]
            connection.execute(
                "UPDATE skills SET enabled_claude=?, enabled_codex=?, description='old' WHERE name=?",
                (*states[name], name),
            )
        connection.execute("INSERT INTO skills VALUES ('user:custom','custom','untouched','custom','me','repo','branch',0,1,10,20)")
        connection.commit()
        connection.close()
        custom = self._rows()["custom"]
        with patch.object(A.time, "time", return_value=200):
            A._register_skills(self.config_dir)
            A._register_skills(self.config_dir)
        rows = self._rows()
        self.assertEqual(len(rows), 15)
        self.assertEqual(rows["custom"], custom)
        for name, description, *_ in A.BUNDLED_SKILLS:
            with self.subTest(skill=name):
                row = rows[name]
                self.assertEqual((row["enabled_claude"], row["enabled_codex"]), states[name])
                self.assertEqual(row["id"], f"aisc:{name}")
                self.assertEqual(row["directory"], name)
                self.assertEqual(row["installed_at"], 100)
                self.assertEqual(row["updated_at"], 200)
                self.assertEqual(row["description"], description)

    def test_each_deleted_caveman_row_reinstalls_dual_enabled_without_enabling_survivors(self):
        A._register_skills(self.config_dir)
        for name, *_ in A.BUNDLED_SKILLS:
            if name == "grill-me":
                continue
            with self.subTest(skill=name):
                connection = sqlite3.connect(self.db_path)
                connection.execute("UPDATE skills SET enabled_claude=0, enabled_codex=0, installed_at=100")
                connection.execute("UPDATE skills SET enabled_codex=1 WHERE name='grill-me'")
                connection.execute("DELETE FROM skills WHERE name=?", (name,))
                connection.commit()
                connection.close()
                with patch.object(A.time, "time", return_value=300):
                    A._register_skills(self.config_dir)
                rows = self._rows()
                self.assertEqual(len(rows), 14)
                self.assertEqual(rows[name]["id"], f"aisc:{name}")
                self.assertEqual(rows[name]["installed_at"], 300)
                self.assertEqual(rows[name]["updated_at"], 300)
                for other, row in rows.items():
                    expected = (1, 1) if other == name else (0, int(other == "grill-me"))
                    self.assertEqual((row["enabled_claude"], row["enabled_codex"]), expected)
                    if other != name:
                        self.assertEqual(row["installed_at"], 100)


if __name__ == "__main__":
    unittest.main()
