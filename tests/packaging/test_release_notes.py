import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ReleaseNotesContractTests(unittest.TestCase):
    def test_release_workflow_reads_tag_scoped_markdown(self) -> None:
        """D-8: releases are published by nsis-installer.yml's preview job
        (a v* tag → prerelease carrying the Workbench NSIS). The notes file
        is tag-scoped markdown, same contract as the old artifact flow."""
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "nsis-installer.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("- uses: actions/checkout@v4", workflow)
        self.assertIn("docs/releases/${GITHUB_REF_NAME}.md", workflow)
        # Prerelease channel (D-8.8): previews are the default publish form.
        self.assertIn("--prerelease", workflow)

    def test_current_version_has_release_notes(self) -> None:
        version = (PROJECT_ROOT / "src" / "aisc" / "VERSION").read_text(encoding="utf-8").strip()
        release_notes = PROJECT_ROOT / "docs" / "releases" / f"v{version}.md"

        self.assertTrue(
            release_notes.is_file(),
            f"missing GitHub Release Notes: {release_notes.relative_to(PROJECT_ROOT)}",
        )
        self.assertIn(
            f"# AISC v{version}",
            release_notes.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
