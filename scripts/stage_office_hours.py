"""Refresh the pinned gstack source subset included for first-time market installs."""
import argparse
import gzip
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "container/lib"))
from gstack_office_hours import package

REVISION = "8143a91809b2305da6ffa7486923008b72d337e6"


def stage(checkout: Path, output: Path) -> None:
    # Keep original Git file modes and bytes, including the upstream MIT license.
    tree = subprocess.check_output([
        "git", "-C", str(checkout), "archive", REVISION, "office-hours", "bin",
        "scripts", "lib", "docs", "LICENSE", "VERSION", "ETHOS.md",
    ])
    with tempfile.TemporaryDirectory() as temporary, tarfile.open(fileobj=io.BytesIO(tree)) as archive:
        root = Path(temporary).resolve()
        for member in archive:
            if member.isfile():
                target = root / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
        skill = root / "office-hours"
        package(root, skill, Path("/opt/aisc/test"))
        dependencies = skill / ".aisc-gstack"
        paths = {p.relative_to(root).as_posix() for p in skill.rglob("*")
                 if p.is_file() and not p.is_relative_to(dependencies)}
        paths.update(p.relative_to(dependencies).as_posix() for p in dependencies.rglob("*") if p.is_file())
        with output.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", mtime=0, fileobj=raw) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as result:
                for path in sorted(paths):
                    member = archive.getmember(path)
                    result.addfile(member, archive.extractfile(member))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="local garrytan/gstack checkout containing the pinned revision")
    parser.add_argument("--output", type=Path, default=ROOT / "container/downloads" / f"gstack-office-hours-{REVISION[:12]}.tar.gz")
    args = parser.parse_args()
    stage(args.checkout, args.output)
