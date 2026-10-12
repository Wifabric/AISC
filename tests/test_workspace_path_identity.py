r"""b2 (F4) regression: Windows path case variants share one identity.

The data-root hash and workspace_key inputs go through ``resolve()`` /
``canonical_workspace_path``; on Windows that true-cases EXISTING paths, so
`E:\proj` and `e:\proj` must produce identical keys. POSIX is untouched
(case-sensitive). Windows-only: skipped elsewhere (ubuntu CI has no such
filesystem semantics).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from aisc.application.runtime import workspace_key_for
from aisc.domain.data_root import canonical_workspace_path, workspace_hash_v1


@unittest.skipIf(sys.platform != "win32", "Windows-only filesystem semantics")
class WindowsWorkspacePathIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = Path(tempfile.mkdtemp(prefix="aisc-case-")).resolve()

    def _case_variant(self) -> str:
        # Swap the case of every ASCII letter in the real path; the on-disk
        # directory is unchanged, so both spellings name the same directory.
        return str(self.ws).swapcase()

    def test_canonical_workspace_path_converges_case_variants(self) -> None:
        self.assertEqual(
            canonical_workspace_path(self.ws),
            canonical_workspace_path(Path(self._case_variant())),
        )

    def test_workspace_hash_v1_converges_case_variants(self) -> None:
        self.assertEqual(
            workspace_hash_v1(self.ws), workspace_hash_v1(Path(self._case_variant()))
        )

    def test_workspace_key_for_converges_case_variants(self) -> None:
        self.assertEqual(
            workspace_key_for(str(self.ws)), workspace_key_for(self._case_variant())
        )


if __name__ == "__main__":
    unittest.main()
