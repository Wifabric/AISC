#!/usr/bin/env python3
"""Post-publish installability verification (0.1.0 A6, guide 3.4.3).

Installs the just-published version from a real index (TestPyPI or PyPI)
into an isolated PIPX_HOME and runs the two no-Docker smoke verbs in a
TEMPORARY cwd (the off-checkout contract: a pip install has no repo and
no bundle — version must exit 0 with bundle_version=null, doctor must
degrade, not crash). Tolerates index propagation delay with bounded
retries.

Usage:
    python scripts/verify-pypi-install.py --index-url https://test.pypi.org/simple \\
        [--extra-index-url https://pypi.org/simple/] 0.1.0.dev0
    # a positional argument without dots is treated as --requirement syntax;
    # versions are pinned as aisc-cli==<version>.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RETRIES = 10
RETRY_WAIT_S = 30


def _pipx() -> str:
    import shutil as _sh

    pipx = _sh.which("pipx")
    if pipx is None:
        sys.exit("FAIL: pipx not on PATH (pip install pipx)")
    return pipx


def _run(argv: list, **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(str(a) for a in argv), flush=True)
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, **kw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-url", required=True)
    ap.add_argument("--extra-index-url", default=None)
    ap.add_argument("version", help="exact version to pin (aisc-cli==<version>)")
    args = ap.parse_args()

    pipx = _pipx()
    spec = f"aisc-cli=={args.version}"

    with tempfile.TemporaryDirectory(prefix="aisc-verify-pypi-") as td:
        home = Path(td) / "pipx"
        bin_dir = home / "bin"
        env = dict(os.environ)
        env["PIPX_HOME"] = str(home)
        env["PIPX_BIN_DIR"] = str(bin_dir)
        if args.extra_index_url:
            env["PIP_EXTRA_INDEX_URL"] = args.extra_index_url

        installed = False
        for attempt in range(1, RETRIES + 1):
            # --pip-args VALUE starting with "--" must ride the = form —
            # separate argv tokens make pipx's argparse eat it as its own flag.
            pip_args = f"--extra-index-url={args.extra_index_url}" if args.extra_index_url else "--no-cache-dir"
            proc = _run([pipx, "install", f"--index-url={args.index_url}",
                         f"--pip-args={pip_args}", spec], env=env)
            if proc.returncode == 0 and bin_dir.exists():
                installed = True
                break
            print(f"[{attempt}/{RETRIES}] not propagated yet: "
                  f"{(proc.stderr or proc.stdout).strip()[-200:]}")
            time.sleep(RETRY_WAIT_S)
        if not installed:
            print("FAIL: never became installable from the index")
            return 1

        aisc = str(bin_dir / ("aisc.exe" if os.name == "nt" else "aisc"))
        offco = Path(td) / "offcheckout"
        offco.mkdir()
        env2 = {k: v for k, v in os.environ.items() if k != "AISC_ROOT"}

        ver = subprocess.run([aisc, "version", "--format", "json"],
                             capture_output=True, text=True, cwd=str(offco), env=env2)
        if ver.returncode != 0:
            print("FAIL: version envelope:", ver.stderr[-300:])
            return 1
        data = json.loads(ver.stdout)["data"]
        if data.get("cli_version") != args.version:
            print(f"FAIL: cli_version {data.get('cli_version')} != {args.version}")
            return 1
        if data.get("bundle_version") is not None:
            # Off-checkout with no fetched bundle: null is the CONTRACT. A
            # real value means something leaked a root — investigate.
            print(f"WARN: bundle_version={data.get('bundle_version')!r} off-checkout "
                  f"(expected null unless a bundle store is populated)")

        doc = subprocess.run([aisc, "doctor", "--format", "json"],
                             capture_output=True, text=True, cwd=str(offco), env=env2)
        # Degrade contract: doctor EXITS NON-ZERO when checks fail (no
        # Docker in this off-checkout env — expected). The crash contract
        # is "a valid aisc.cli/v1 envelope still comes out"; exit code is
        # not the criterion.
        try:
            doc_env = json.loads(doc.stdout)
            assert doc_env["meta"]["protocol"] == "aisc.cli/v1"
            assert doc_env["meta"]["command"] == "doctor"
        except Exception:
            print("FAIL: doctor crashed (no valid envelope):", doc.stderr[-300:])
            return 1

        print(f"PASS: {spec} installs from {args.index_url}; off-checkout "
              f"version exit 0 (cli={data['cli_version']}), doctor degrades")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
