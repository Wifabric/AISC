"""Tool pin resolution + user-layer overlay (0.1.0 A5, D-9/D-27).

Two-layer truth for the container tool versions:

- FACTORY layer: ``config/versions.env`` inside the resolved root (repo
  checkout / installed aisc-bundle / pip ``bundles/<ver>/``). Read-only —
  it is part of the shipped bundle and every update path replaces it.
- USER layer: ``<data-root>/config/versions.env`` — the ONE place
  ``aisc update --pin-tool`` writes. Survives CLI updates, NSIS upgrades
  and bundle fetches by construction (none of them touch the data root's
  config/). ``AISC_DATA_ROOT`` knob applies via ``shared_root()``.

Resolution: factory values as the base, user layer overrides KEY-WISE
(only keys the user bumped). The r4 incident (pins silently downgraded by
a bundle refresh) is structurally impossible under this split.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

#: Keys a user may pin (claude/codex are npm-driven; cc-switch's resolver
#: pin is the manual-fallback value only; NODE_IMAGE stays factory — the CN
#: mirror chain pairs with it and a bare image override would desync them).
PINNABLE_TOOL_KEYS = ("CLAUDE_CODE_VERSION", "CODEX_VERSION", "CC_SWITCH_VERSION")


def _parse_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        v = v.split("#", 1)[0].strip()  # strip trailing comments
        if k.strip() and v:
            out[k.strip()] = v
    return out


def user_pin_path(data_root: Path) -> Path:
    return data_root / "config" / "versions.env"


def effective_tool_versions(
    root: Path,
    data_root: Optional[Path] = None,
) -> Dict[str, Tuple[str, str]]:
    """Resolve each factory key with its source: key -> (value, source).

    source is ``"user"`` (user-layer override won) or ``"default"``
    (factory value). Only keys present in the FACTORY file participate —
    the user layer cannot invent keys the image build never reads.
    """
    factory = _parse_env_file(root / "config" / "versions.env")
    user: Dict[str, str] = {}
    if data_root is None:
        try:
            from aisc.application.data_root import shared_root

            data_root = shared_root()
        except Exception:
            data_root = None
    if data_root is not None:
        user = _parse_env_file(user_pin_path(data_root))
    out: Dict[str, Tuple[str, str]] = {}
    for key, value in factory.items():
        if key in user:
            out[key] = (user[key], "user")
        else:
            out[key] = (value, "default")
    return out


def write_user_pins(
    data_root: Path,
    pins: Dict[str, str],
) -> Path:
    """Merge *pins* into the user-layer versions.env (comment-preserving,
    atomic tmp+rename). Returns the written path. Validates keys against
    PINNABLE_TOOL_KEYS (raises ValueError listing the offenders)."""
    unknown = sorted(k for k in pins if k not in PINNABLE_TOOL_KEYS)
    if unknown:
        raise ValueError(
            f"not pinnable: {', '.join(unknown)} "
            f"(pinnable: {', '.join(PINNABLE_TOOL_KEYS)})")
    path = user_pin_path(data_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    # Update in place when the key exists on its own line; collect misses.
    seen = set()
    updated: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in pins:
                updated.append(f"{k}={pins[k]}")
                seen.add(k)
                continue
        updated.append(line)
    header_needed = not updated or updated[0].strip() != "# AISC user tool pins (aisc update --pin-tool; overrides the bundle's factory defaults)"
    if header_needed and not any("AISC user tool pins" in l for l in updated):
        updated.insert(0, "# AISC user tool pins (aisc update --pin-tool; overrides the bundle's factory defaults)")
    for k, v in pins.items():
        if k not in seen:
            updated.append(f"{k}={v}")
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".versions-", suffix=".env")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text("\n".join(updated) + "\n", encoding="utf-8", newline="")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return path


# ---------------------------------------------------------------------------
# Latest-available lookups (network-tolerant; injectable for tests)
# ---------------------------------------------------------------------------

NPM_MIRROR = "https://registry.npmmirror.com"
NPM_PACKAGES = {
    "CLAUDE_CODE_VERSION": "@anthropic-ai/claude-code",
    "CODEX_VERSION": "@openai/codex",
}


def _npm_latest(pkg: str, opener: Callable[[str], dict]) -> Optional[dict]:
    """One registry metadata read via *opener*(url) -> parsed json dict."""
    try:
        d = opener(f"{NPM_MIRROR}/{pkg}")
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    latest = d.get("dist-tags", {}).get("latest")
    if not latest:
        return None
    engines = (d.get("versions", {}) or {}).get(latest, {}).get("engines") or {}
    return {"latest": latest, "node": engines.get("node") or ""}


def default_opener(url: str) -> dict:
    import json
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "aisc-update-check"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tools_check_section(
    root: Path,
    data_root: Optional[Path] = None,
    opener: Callable[[str], dict] = default_opener,
) -> List[dict]:
    """The `--check` tools block: effective pin (value + source) and the
    latest available version per tool. Registry failures degrade to
    ``latest: null`` — a check must never fail because the network did."""
    eff = effective_tool_versions(root, data_root)
    out: List[dict] = []
    for key, pkg in NPM_PACKAGES.items():
        value, source = eff.get(key, ("latest", "default"))
        info = _npm_latest(pkg, opener)
        out.append({
            "tool": key,
            "current": value,
            "source": source,
            "latest": info["latest"] if info else None,
            "node_requirement": info["node"] if info else None,
        })
    cc_value, cc_source = eff.get("CC_SWITCH_VERSION", ("latest", "default"))
    cc_latest = _cached_cc_switch_latest()
    out.append({
        "tool": "CC_SWITCH_VERSION",
        "current": cc_value,
        "source": cc_source,
        "latest": cc_latest,
        "node_requirement": "",
    })
    return out


def _cached_cc_switch_latest() -> Optional[str]:
    """Latest stable cc-switch from the resolver cache (offline-tolerant;
    a cache-less machine reports null — the build-time resolver remains
    the authoritative live source)."""
    try:
        import json

        from aisc.application.data_root import shared_root

        f = shared_root() / "cache" / "cc-switch" / "last-resolved.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        return str(d.get("version") or "") or None
    except Exception:
        return None
