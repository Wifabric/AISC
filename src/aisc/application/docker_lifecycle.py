"""Docker resource lifecycle service (docker-resource-lifecycle A1/B).

Centralized scan / classification / cleanup / rebuild over AISC-owned
containers and workstation images. Every installer calls THIS through the
``aisc maintenance`` CLI — platform scripts never reimplement the filter
rules (02 §1/§2/§3/§4).

Ownership tiers (frozen):
- ``owned``         — labels prove it (io.aisc.managed / org.aisc.managed);
- ``legacy_owned``  — no labels but legacy evidence: registry record, the
                      ``aisc-wb-`` name pattern, or the historical
                      ``super-claude-station-`` name + super-claude repo
                      (containers); the exact default tag
                      ``super-claude:latest`` in an upgrade/uninstall
                      context (images);
- ``unverified``    — merely looks AISC-ish (name/repository similar).
                      Reported, NEVER deleted.

Safety invariants (02 §5): no global prune; never delete by repository
name alone; containers before images; volumes/networks untouched; Docker
unavailable never concludes "not_found"; re-scan before deleting; argv
and logs never carry secrets.

All Docker I/O rides machine formats (ps/images templates, inspect
``{{.Id}}``) — never human-text parsing. Cleanup/rebuild hold the shared
docker-maintenance lock (cross-plan order: maintenance -> workspace ->
registry). The runtime-create critical section (02 §4.1) attaches when
Stage C wires the installers' rebuild flow.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from aisc.domain.models import CliError, RuntimeErrorCode, RuntimeExitCode

#: Exact default workstation tag (legacy evidence in upgrade/uninstall).
DEFAULT_IMAGE_TAG = "super-claude:latest"

SCAN_SCHEMA = "aisc.docker-scan/v1"
CLEANUP_SCHEMA = "aisc.docker-cleanup/v1"
REBUILD_SCHEMA = "aisc.docker-rebuild/v1"

#: docker ps template: id, name, image ref, status + the AISC labels.
_PS_FORMAT = (
    "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t"
    '{{.Label "io.aisc.managed"}}\t{{.Label "io.aisc.kind"}}\t'
    '{{.Label "io.aisc.owner"}}'
)
#: docker images template (no .Labels placeholder exists on `docker
#: images` — ownership comes from the server-side label filter below).
_IMAGES_FORMAT = "{{.Repository}}	{{.Tag}}	{{.ID}}"


def _ps_rows(executor: Any) -> List[Dict[str, str]]:
    try:
        result = executor.run_captured(
            ["ps", "-a", "--format", _PS_FORMAT], timeout=15.0
        )
    except Exception:
        return []
    if getattr(result, "exit_code", 1) != 0:
        return []
    rows: List[Dict[str, str]] = []
    for line in (result.stdout or "").splitlines():
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) < 4:
            continue
        rows.append({
            "id": parts[0], "name": parts[1], "image": parts[2],
            "status": parts[3],
            "managed": parts[4] if len(parts) > 4 else "",
            "kind": parts[5] if len(parts) > 5 else "",
            "owner": parts[6] if len(parts) > 6 else "",
        })
    return rows


def _image_universe(executor: Any) -> List[Dict[str, Any]]:
    """All images as {repository, tag, id, ref} rows (no labels)."""
    try:
        result = executor.run_captured(
            ["images", "--format", _IMAGES_FORMAT], timeout=15.0
        )
    except Exception:
        return []
    if getattr(result, "exit_code", 1) != 0:
        return []
    rows: List[Dict[str, Any]] = []
    for line in (result.stdout or "").splitlines():
        parts = [p.strip() for p in line.split("	")]
        if len(parts) < 3:
            continue
        rows.append({
            "repository": parts[0], "tag": parts[1], "id": parts[2],
            "ref": f"{parts[0]}:{parts[1]}" if parts[1] != "<none>" else "",
        })
    return rows


def _filtered_image_ids(executor: Any, flag: str) -> List[str]:
    """Image IDs passing a server-side ``docker images --filter``."""
    try:
        result = executor.run_captured(
            ["images", "--filter", flag, "--format", "{{.ID}}"], timeout=15.0
        )
    except Exception:
        return []
    if getattr(result, "exit_code", 1) != 0:
        return []
    return [ln.strip() for ln in (result.stdout or "").splitlines() if ln.strip()]


def _registry_evidence(data_root: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    """All registry records across workspaces (legacy container evidence)."""
    from aisc.adapters.container_registry import list_containers_readonly
    from aisc.application.data_root import shared_root

    root = Path(data_root) if data_root else shared_root()
    evidence: Dict[str, Dict[str, Any]] = {}
    ws_root = root / "workspaces"
    if not ws_root.is_dir():
        return evidence
    for ws_dir in ws_root.iterdir():
        reg = ws_dir / "runtime"
        if not reg.is_dir():
            continue
        try:
            for name, meta in list_containers_readonly(reg).items():
                if isinstance(meta, dict):
                    evidence[name] = meta
        except Exception:
            continue  # one unreadable workspace registry never breaks the scan
    return evidence


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_containers(
    rows: Iterable[Dict[str, str]], registry: Dict[str, Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "owned": [], "legacy_owned": [], "unverified": [],
    }
    for row in rows:
        name = row["name"]
        image_repo = row["image"].split(":")[0]
        if row["managed"] == "true":
            ownership, reason = "owned", "label"
        elif name in registry:
            ownership, reason = "legacy_owned", "registry"
        elif name.startswith("aisc-wb-"):
            ownership, reason = "legacy_owned", "legacy-name"
        elif name.startswith("super-claude-station-") and image_repo == "super-claude":
            ownership, reason = "legacy_owned", "legacy-name"
        elif image_repo == "super-claude" or "aisc" in name.lower():
            ownership, reason = "unverified", "repository-only"
        else:
            continue  # not AISC-adjacent — none of our business
        buckets[ownership].append({
            "id": row["id"], "name": name, "image": row["image"],
            "ownership": ownership,
            "state": "running" if row["status"].startswith("Up") else "stopped",
            "reason": reason,
        })
    return buckets


def classify_images(
    rows: Iterable[Dict[str, Any]],
    *,
    context: str,
    owned_ids: Iterable[str] = (),
    dangling_ids: Iterable[str] = (),
    old_image_ids: Iterable[str] = (),
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    """Three-tier image classification + evidence-backed dangling set.

    ``owned_ids`` come from the server-side ``label=org.aisc.managed=true``
    filter (docker images has no label template — the filter is the only
    reliable source); ``dangling_ids`` from ``dangling=true``.
    """
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "owned": [], "legacy_owned": [], "unverified": [],
    }
    dangling: List[Dict[str, Any]] = []
    owned = {i for i in owned_ids if i}
    dangling_set = {i for i in dangling_ids if i}
    old_ids = {i for i in old_image_ids if i}
    for row in rows:
        entry = {
            "id": row["id"], "name": row["ref"] or row["id"],
            "image": row["ref"] or row["id"],
        }
        if row["repository"] == "<none>":
            # Dangling FIRST (no ref to untag — deletable by ID only).
            # Evidence: org.aisc label (survives on the image config) or the
            # upgrade's captured old_image_id (temporary proof).
            if row["id"] in owned or row["id"] in old_ids:
                dangling.append({
                    "id": row["id"], "name": row["id"], "image": row["id"],
                    "ownership": "owned", "state": "dangling",
                    "reason": "label" if row["id"] in owned else "upgrade-old-id",
                })
        elif row["id"] in owned:
            entry.update({"ownership": "owned", "state": "present", "reason": "label"})
            buckets["owned"].append(entry)
        elif row["ref"] == DEFAULT_IMAGE_TAG and context != "first_install":
            entry.update({"ownership": "legacy_owned", "state": "present",
                          "reason": "default-tag"})
            buckets["legacy_owned"].append(entry)
        elif row["repository"] == "super-claude":
            entry.update({"ownership": "unverified", "state": "present",
                          "reason": "repository-only"})
            buckets["unverified"].append(entry)
        else:
            continue  # not AISC-adjacent — none of our business
    return buckets, dangling


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def docker_scan(
    executor: Any,
    *,
    context: str = "upgrade",
    old_image_ids: Iterable[str] = (),
    data_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """One read-only classification pass (02 §2 envelope)."""
    from aisc.application.runtime import _check_docker

    available = _check_docker(executor)
    payload: Dict[str, Any] = {
        "schema_version": SCAN_SCHEMA,
        "docker": {"available": available, "reason": "ok" if available else "unavailable"},
        "containers": {"owned": [], "legacy_owned": [], "unverified": []},
        "images": {"owned": [], "legacy_owned": [], "unverified": []},
        "dangling_owned": [],
        "warnings": [],
    }
    if not available:
        return payload
    registry = _registry_evidence(data_root)
    payload["containers"] = classify_containers(_ps_rows(executor), registry)
    payload["images"], payload["dangling_owned"] = classify_images(
        _image_universe(executor),
        context=context,
        owned_ids=_filtered_image_ids(executor, "label=org.aisc.managed=true"),
        dangling_ids=_filtered_image_ids(executor, "dangling=true"),
        old_image_ids=old_image_ids,
    )
    return payload


def render_scan_text(payload: Dict[str, Any]) -> str:
    """Space-separated one-line-per-resource text for installers and shell
    scripts (NSIS/Inno/POSIX sh cannot parse JSON cheaply; this format is
    stable: ``<kind> <ownership> <id> <name>``).

    Example lines::

        docker available
        container owned cid123 aisc-wb-1
        image owned sha256:abc super-claude:latest
    """
    lines = [
        "docker available" if payload.get("docker", {}).get("available")
        else "docker unavailable"
    ]
    for kind in ("containers", "images"):
        buckets = payload.get(kind, {})
        for ownership in ("owned", "legacy_owned", "unverified"):
            for entry in buckets.get(ownership, []):
                lines.append(
                    f"{kind.rstrip('s')} {ownership} {entry.get('id', '')} "
                    f"{entry.get('name', '')}"
                )
    for entry in payload.get("dangling_owned", []):
        lines.append(f"image dangling-owned {entry.get('id', '')} {entry.get('id', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cleanup (02 §3 order; per-resource failure never aborts the rest)
# ---------------------------------------------------------------------------

def _is_no_such(stderr: str) -> bool:
    low = (stderr or "").lower()
    return "no such" in low or "not found" in low


def docker_cleanup(
    executor: Any,
    *,
    context: str = "upgrade",
    old_image_ids: Iterable[str] = (),
    data_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Upgrade context cleans CONTAINERS ONLY (01 §3 upgrade ordering):
    the tagged image must survive until docker-rebuild succeeds, or a
    failed rebuild would leave the user with no workstation image at all;
    the old image is then removed by ID via rebuild's old-ID handoff."""
    result: Dict[str, Any] = {
        "schema_version": CLEANUP_SCHEMA,
        "action": "cleanup",
        "containers": {"removed": [], "not_found": [], "failed": []},
        "images": {"removed": [], "not_found": [], "failed": []},
        "skipped_unverified": [],
        "warnings": [],
    }

    def _run(argv: List[str], timeout: float = 60.0):
        return executor.run_captured(argv, timeout=timeout)

    # Re-scan + re-verify (invariant 6: never trust a stale list).
    scan = docker_scan(executor, context=context, old_image_ids=old_image_ids,
                       data_root=data_root)
    if not scan["docker"]["available"]:
        raise CliError(
            message="Docker unavailable; cleanup refused (nothing concluded)",
            exit_code=RuntimeExitCode.DOCKER_UNAVAILABLE,
            error_code=RuntimeErrorCode.DOCKER_UNAVAILABLE,
        )
    for entry in scan["containers"]["unverified"] + scan["images"]["unverified"]:
        result["skipped_unverified"].append(entry["name"])

    from aisc.adapters.maintenance_lock import docker_maintenance_lock_at_root
    from aisc.application.data_root import shared_root

    root = Path(data_root) if data_root else shared_root()

    with docker_maintenance_lock_at_root(root):
        # 1-3. containers first (order: stop orderly, then force remove).
        for entry in scan["containers"]["owned"] + scan["containers"]["legacy_owned"]:
            name = entry["name"]
            if entry["state"] == "running":
                stop = _run(["stop", "-t", "10", name], timeout=30.0)
                if stop.exit_code != 0 and not _is_no_such(stop.stderr):
                    result["containers"]["failed"].append(name)
                    continue
            rm = _run(["rm", "-f", name], timeout=60.0)
            if rm.exit_code == 0 or _is_no_such(rm.stderr):
                bucket = "removed" if rm.exit_code == 0 else "not_found"
                result["containers"][bucket].append(name)
            else:
                result["containers"]["failed"].append(name)

        # 4-6. re-scan image references, then untag/delete by evidence.
        # Upgrade: images ride the rebuild handoff — skip entirely.
        removed_ids = set()
        if context == "upgrade":
            scan2 = {"images": {"owned": [], "legacy_owned": [], "unverified": []},
                     "dangling_owned": []}
        else:
            scan2 = docker_scan(executor, context=context, old_image_ids=old_image_ids,
                                data_root=data_root)
        for entry in scan2["images"]["owned"] + scan2["images"]["legacy_owned"]:
            ref = entry["image"]
            if entry["id"] in removed_ids:
                continue
            rm = _run(["rmi", ref], timeout=120.0)
            if rm.exit_code == 0:
                result["images"]["removed"].append(ref)
                removed_ids.add(entry["id"])
            elif _is_no_such(rm.stderr):
                result["images"]["not_found"].append(ref)
            else:
                # referenced by another tag/container or refused — kept.
                result["images"]["failed"].append(ref)
                result["warnings"].append(
                    f"image kept (still referenced or refused): {ref}"
                )
        # 7. dangling with evidence.
        for entry in scan2["dangling_owned"]:
            if entry["id"] in removed_ids:
                continue
            rm = _run(["rmi", entry["id"]], timeout=120.0)
            if rm.exit_code == 0:
                result["images"]["removed"].append(entry["id"])
                removed_ids.add(entry["id"])
            elif not _is_no_such(rm.stderr):
                result["images"]["failed"].append(entry["id"])
        # Volumes/networks: deliberately nothing (invariant 4).
    return result


# ---------------------------------------------------------------------------
# Rebuild (02 §4)
# ---------------------------------------------------------------------------

def _cc_switch_for_rebuild() -> Any:
    """Deterministic-offline cc-switch pin for installer rebuilds.

    Priority: explicit cached version (any age — a pinned digest is stable
    content, and installers must not depend on reaching the GitHub API) →
    live ``latest`` → None (Dockerfile ARG fallback, documented
    non-reproducible; the result carries a warning).
    """
    import json as _json
    from aisc.application.cc_switch_resolver import CcSwitchResolver
    from aisc.application.data_root import shared_root

    resolver = CcSwitchResolver()
    cache = shared_root() / "cache" / "cc-switch" / "last-resolved.json"
    version = ""
    try:
        version = str(_json.loads(cache.read_text(encoding="utf-8")).get("version") or "")
    except (OSError, ValueError):
        version = ""
    for candidate in ([version] if version else []) + ["latest"]:
        try:
            return resolver.resolve(version=candidate)
        except Exception:
            continue
    return None


_CC_UNSET = object()


def docker_rebuild(
    executor: Any,
    *,
    root: str,
    tag: str = DEFAULT_IMAGE_TAG,
    old_image_id: str = "",
    no_cache: bool = True,
    pull: bool = False,
    cc_switch: Any = _CC_UNSET,
) -> Dict[str, Any]:
    """No-cache rebuild of the workstation image with old-ID handoff.

    ``root`` is the BUNDLE ROOT (aisc-root shaped: ``container/Dockerfile``
    + ``config/versions.env`` — validated like ``aisc build``), matching
    the installed ``$INSTDIR/aisc-bundle``. cc-switch is pinned from the
    resolver cache when available (offline-deterministic; installers must
    not require the GitHub API), falling back to the Dockerfile ARG path
    with a warning.

    Returns the 02 §4 result: old/new image ids, image_changed,
    old_image_action (removed | untagged | kept_referenced | not_found),
    reconcile_hint. Build failure PRESERVES the old image and reports
    failed=true (the caller decides the UX; nothing is deleted on failure).
    """
    from aisc.adapters.maintenance_lock import docker_maintenance_lock_at_root
    from aisc.application.data_root import shared_root
    from aisc.cli.commands.build import plan_build

    if cc_switch is _CC_UNSET:
        cc_switch = _cc_switch_for_rebuild()
    warnings: List[str] = []
    if cc_switch is None:
        warnings.append(
            "cc-switch not pinned (no resolver cache, live resolve failed); "
            "built via Dockerfile ARG fallback"
        )
    try:
        plan = plan_build(
            Path(root), tag=tag, no_cache=no_cache, pull=pull,
            dry_run=False, cc_switch=cc_switch,
        )
    except CliError as exc:
        raise CliError(
            message=f"bundle validation failed: {exc.message}",
            exit_code=RuntimeExitCode.USAGE_ERROR,
            error_code=RuntimeErrorCode.WORKSPACE_INVALID,
        ) from exc

    with docker_maintenance_lock_at_root(shared_root()):
        build = executor.run_captured(plan.docker_argv, timeout=1800.0)
        new_id = _image_id_by_ref(executor, tag)
        if build.exit_code != 0 or not new_id:
            return {
                "schema_version": REBUILD_SCHEMA,
                "tag": tag,
                "old_image_id": old_image_id,
                "new_image_id": "",
                "image_changed": False,
                "old_image_action": "not_found" if not old_image_id else "kept_referenced",
                "reconcile_hint": "unchanged",
                "failed": True,
                "warnings": warnings,
                "build_log_tail": _log_tail(build.stdout or ""),
            }
        changed = bool(old_image_id) and old_image_id != new_id
        action = "not_found"
        if old_image_id and changed:
            rm = executor.run_captured(["rmi", old_image_id], timeout=120.0)
            if rm.exit_code == 0:
                action = "removed"
            elif _is_no_such(rm.stderr):
                action = "not_found"
            else:
                action = "kept_referenced"  # still tagged elsewhere / in use
        return {
            "schema_version": REBUILD_SCHEMA,
            "tag": tag,
            "old_image_id": old_image_id,
            "new_image_id": new_id,
            "image_changed": changed,
            "old_image_action": action,
            "reconcile_hint": "image_changed" if changed else "unchanged",
            "failed": False,
            "warnings": warnings,
            "build_log_tail": _log_tail(build.stdout or ""),
        }


def _image_id_by_ref(executor: Any, ref: str) -> str:
    try:
        result = executor.run_captured(
            ["image", "inspect", ref, "--format", "{{.Id}}"], timeout=15.0
        )
    except Exception:
        return ""
    if getattr(result, "exit_code", 1) != 0:
        return ""
    return (result.stdout or "").strip()


def _log_tail(stdout: str, lines: int = 20) -> str:
    tail = "\n".join(stdout.strip().splitlines()[-lines:])
    # Redaction-by-construction: build output contains no secrets; cap the
    # size so the envelope stays bounded either way.
    return tail[-4000:]


# ---------------------------------------------------------------------------
# O7 (opt-batch, D-11): build-cache cleanup — builder prune + dangling images
# with filters. Extends the module's safety invariants: NEVER a global
# `docker system prune`, NEVER `-a` (non-dangling images stay), and the
# `until=` filter keeps caches/entries younger than the window untouched.
# ---------------------------------------------------------------------------

CACHE_USAGE_SCHEMA = "aisc.docker-cache-usage/v1"
CACHE_CLEANUP_SCHEMA = "aisc.docker-cache-cleanup/v1"
CACHE_INSPECT_SCHEMA = "aisc.docker-cache-inspect/v1"
MANAGEMENT_SCHEMA = "aisc.docker-management/v1"


# --- v2.1.13 (docker-scan-fidelity): read-only per-resource inspection -----
#
# D-2 (2026-09-19): detect FINER and report ACCURATELY; never clean anything
# automatically, never add new prune paths. Primary size/detail source is
# `docker system df -v --format json` (Docker 29.x returns structured
# per-item JSON there — verified on 29.8.0; officially undocumented, so
# callers must tolerate absence). Fallbacks degrade per-category and mark
# rows unknown; nothing here blocks anything else.
#
# Accuracy notes (the "更准确" half):
# - Image RECLAIMABLE aggregates over-count shared layers; the accurate
#   per-image figure is UNIQUE SIZE, summed over images with Containers==0.
# - `image prune` (no -a) only ever removes DANGLING images, so rows also
#   carry will_be_cleaned to show what the CURRENT manual cleanup would hit.
# - Build cache has no Reclaimable boolean in df -v; it is derived from
#   InUse. buildx du (fallback) carries it natively.

_SIZE_UNITS: Dict[str, int] = {
    "": 1, "B": 1,
    "K": 10**3, "KI": 2**10,
    "M": 10**6, "MI": 2**20,
    "G": 10**9, "GI": 2**30,
    "T": 10**12, "TI": 2**40,
}


def _size_bytes(value: Any) -> Optional[int]:
    """Best-effort docker size strings (`35.6 kB`, `1.2GB`, ints) → bytes.
    None for N/A / unparseable — the row is reported as unknown."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s or s.upper() in ("N/A", "UNKNOWN"):
        return None
    m = re.match(r"^([\d.]+)\s*([A-Za-z]*)$", s)
    if not m:
        return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    unit = m.group(2).upper().rstrip("B") if m.group(2) else ""
    if unit not in _SIZE_UNITS:
        return None
    return int(num * _SIZE_UNITS[unit])


def _container_rw_size(value: Any) -> Optional[int]:
    """`ps -s` size strings: `35.6 kB (virtual 109 MB)` → writable layer."""
    if value is None:
        return None
    head = str(value).split("(virtual")[0].strip()
    return _size_bytes(head)


def _json_lines(stdout: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _df_verbose(executor: Any) -> Optional[Dict[str, Any]]:
    """`docker system df -v --format json` → {Images, Containers, Volumes,
    BuildCache} (no Networks section). None when unavailable."""
    try:
        result = executor.run_captured(
            ["system", "df", "-v", "--format", "json"], timeout=60.0
        )
    except Exception:
        return None
    if getattr(result, "exit_code", 1) != 0:
        return None
    text = (result.stdout or "").strip()
    if not text:
        return None
    try:
        doc = json.loads(text)
        if isinstance(doc, dict):
            return doc
    except ValueError:
        pass
    merged: Dict[str, Any] = {}
    for row in _json_lines(text):
        merged.update(row)
    return merged or None


def _buildx_du(executor: Any) -> Optional[List[Dict[str, Any]]]:
    """`docker buildx du --format json` (NDJSON records). None when the
    buildx plugin is absent/old (Docker Desktop's `docker builder` aliases
    to buildx; classic CLIs lack du entirely)."""
    try:
        result = executor.run_captured(
            ["buildx", "du", "--format", "json"], timeout=60.0
        )
    except Exception:
        return None
    if getattr(result, "exit_code", 1) != 0:
        return None
    rows = _json_lines(result.stdout or "")
    return rows or None


def _images_rows(executor: Any, df_v: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Image rows. df -v Images is the ONLY real Unique/Shared source on
    Docker 29 (image ls --format json reports N/A placeholders there); the
    ls pass adds dangling classification for older daemons. Reclaimable =
    Σ UniqueSize over images with no containers; dangling is the subset the
    current manual cleanup would remove (its 24h age filter is NOT applied
    per-row — the disclaimer says so)."""
    rows: List[Dict[str, Any]] = []
    ls = executor.run_captured(["images", "--format", "{{json .}}"], timeout=30.0)
    fallback: List[Dict[str, Any]] = []
    if getattr(ls, "exit_code", 1) == 0:
        for row in _json_lines(ls.stdout or ""):
            repo = str(row.get("Repository") or "")
            fallback.append({
                "id": str(row.get("ID") or ""),
                "name": f"{repo}:{row.get('Tag')}",
                "in_use": None,
                "dangling": repo == "<none>",
                "size": row.get("Size"),
                "size_bytes": _size_bytes(row.get("Size")),
                "unique_size": None,
                "shared": None,
                "reclaimable_bytes": None,
                "will_be_cleaned": repo == "<none>",
            })
    dv = (df_v or {}).get("Images")
    if not isinstance(dv, list) or not dv:
        return fallback
    for row in dv:
        if not isinstance(row, dict):
            continue
        containers = str(row.get("Containers") or "").strip()
        in_use = containers not in ("", "0", "N/A")
        repo = str(row.get("Repository") or "")
        dangling = repo == "<none>"
        unique = _size_bytes(row.get("UniqueSize"))
        rows.append({
            "id": str(row.get("ID") or ""),
            "name": f"{repo}:{row.get('Tag')}",
            "in_use": in_use,
            "dangling": dangling,
            "size": row.get("Size"),
            "size_bytes": _size_bytes(row.get("Size")),
            "unique_size": row.get("UniqueSize"),
            # SharedSize is a display STRING (e.g. "326.5MB") - it must never
            # ride the boolean shared field (2.1.13 hand-test: the string
            # made the Rust serde drop the whole images category).
            "shared": None,
            "reclaimable_bytes": (0 if in_use else unique),
            "will_be_cleaned": dangling,
        })
    return rows


def _container_rows(executor: Any) -> List[Dict[str, Any]]:
    """Stopped containers' writable layers are the reclaimable part; running
    ones report unknown (they cannot be reclaimed without stopping)."""
    ps = executor.run_captured(
        ["ps", "-a", "--size", "--format", "{{json .}}"], timeout=30.0
    )
    rows: List[Dict[str, Any]] = []
    if getattr(ps, "exit_code", 1) != 0:
        return rows
    for row in _json_lines(ps.stdout or ""):
        names = row.get("Names") or row.get("Name") or ""
        name = ", ".join(str(n) for n in names) if isinstance(names, list) else str(names)
        state = str(row.get("State") or "")
        running = state == "running"
        rw = _container_rw_size(row.get("Size"))
        rows.append({
            "id": str(row.get("ID") or ""),
            "name": name,
            "image": str(row.get("Image") or ""),
            "state": state,
            "size": row.get("Size"),
            "size_bytes": None if running else _container_rw_size(row.get("Size")),
            "in_use": running,
            "reclaimable_bytes": (None if running else rw),
            "will_be_cleaned": False,  # AISC never removes user containers here
        })
    return rows


def _volume_rows(executor: Any) -> List[Dict[str, Any]]:
    """Named/anonymous × in-use/dangling. Sizes stay unknown by default
    (per-volume du can take minutes); AISC NEVER deletes volumes (02 §5) —
    every row is will_be_cleaned=False and the UI says so."""
    ls = executor.run_captured(["volume", "ls", "--format", "{{json .}}"], timeout=30.0)
    if getattr(ls, "exit_code", 1) != 0:
        return []
    dang = executor.run_captured(
        ["volume", "ls", "--filter", "dangling=true", "--format", "{{json .}}"],
        timeout=30.0,
    )
    dangling: set = set()
    if getattr(dang, "exit_code", 1) == 0:
        for row in _json_lines(dang.stdout or ""):
            name = str(row.get("Name") or "")
            if name:
                dangling.add(name)
    rows: List[Dict[str, Any]] = []
    for row in _json_lines(ls.stdout or ""):
        name = str(row.get("Name") or "")
        if not name:
            continue
        rows.append({
            "id": name,
            "name": name,
            "dangling": name in dangling,
            "in_use": name not in dangling,
            "size": row.get("Size"),
            "size_bytes": _size_bytes(row.get("Size")),
            "reclaimable_bytes": None,  # volumes are never reclaimed by AISC
            "will_be_cleaned": False,
        })
    return rows


def _cache_rows(executor: Any, df_v: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """Build-cache rows + whether the buildx fallback ran. Primary: df -v
    BuildCache (daemon-wide, deduped; Reclaimable derived from InUse).
    Fallback: buildx du (Reclaimable natively; single builder)."""
    rows: List[Dict[str, Any]] = []
    dv = (df_v or {}).get("BuildCache")
    if isinstance(dv, list) and dv:
        for row in dv:
            if not isinstance(row, dict):
                continue
            in_use = bool(row.get("InUse"))
            size_bytes = _size_bytes(row.get("Size"))
            rows.append({
                "id": str(row.get("ID") or ""),
                "kind": str(row.get("CacheType") or row.get("Type") or ""),
                "in_use": in_use,
                "shared": bool(row.get("Shared")),
                "size": row.get("Size"),
                "size_bytes": size_bytes,
                "reclaimable_bytes": (0 if in_use else (size_bytes or 0)),
                "will_be_cleaned": not in_use,
                "last_used_at": row.get("LastUsedAt"),
                "usage_count": row.get("UsageCount"),
            })
        return rows, False
    bx = _buildx_du(executor)
    if bx is not None:
        for row in bx:
            reclaimable = bool(row.get("Reclaimable"))
            size_bytes = _size_bytes(row.get("Size"))
            rows.append({
                "id": str(row.get("ID") or ""),
                "kind": str(row.get("Type") or row.get("CacheType") or ""),
                "in_use": not reclaimable,
                "shared": bool(row.get("Shared")),
                "size": row.get("Size"),
                "size_bytes": size_bytes,
                "reclaimable_bytes": ((size_bytes or 0) if reclaimable else 0),
                "will_be_cleaned": reclaimable,
                "last_used_at": row.get("LastUsedAt"),
                "usage_count": row.get("UsageCount"),
            })
        return rows, True
    return rows, False


def _network_rows(executor: Any) -> List[Dict[str, Any]]:
    """Networks are 0-byte; only the count/reference picture matters."""
    ls = executor.run_captured(["network", "ls", "--format", "{{json .}}"], timeout=30.0)
    rows: List[Dict[str, Any]] = []
    if getattr(ls, "exit_code", 1) != 0:
        return rows
    for row in _json_lines(ls.stdout or ""):
        name = str(row.get("Name") or "")
        if not name:
            continue
        rows.append({
            "id": name,
            "name": name,
            "kind": str(row.get("Driver") or ""),
            "in_use": None,  # reference counting rides the containers pass
            "size_bytes": 0,
            "reclaimable_bytes": 0,
            "will_be_cleaned": False,
        })
    return rows


def _category_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    reclaimable = 0
    unknown = 0
    for row in rows:
        value = row.get("reclaimable_bytes")
        if value is None:
            unknown += 1
        else:
            reclaimable += int(value)
    return {
        "count": len(rows),
        "reclaimable_bytes": reclaimable,
        "unknown_count": unknown,
    }


def cache_inspect(executor: Any, *, cleanup_min_age_hours: int = 24) -> Dict[str, Any]:
    """Read-only per-resource inspection (D-2). Detects images / containers /
    volumes / build cache / networks item-by-item, reports the deduped
    (UNIQUE-size) reclaimable picture, and flags what the CURRENT manual
    cleanup would hit. Absolutely no prune/rmi/rm anywhere in here, and no
    caller ever chains this into cleanup."""
    df = _system_df(executor)
    docker_available = bool(df)
    warnings: List[str] = []
    df_v: Optional[Dict[str, Any]] = None
    buildx_used = False
    if docker_available:
        df_v = _df_verbose(executor)
        if df_v is None:
            warnings.append("df-verbose-json-unavailable")
        buildx_used = _buildx_du(executor) is None
    images = _images_rows(executor, df_v)
    containers = _container_rows(executor)
    volumes = _volume_rows(executor)
    cache_rows, buildx_used = _cache_rows(executor, df_v)
    networks = _network_rows(executor)

    def cat(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"rows": rows, "summary": _category_summary(rows)}

    return {
        "schema_version": CACHE_INSPECT_SCHEMA,
        "action": "cache-inspect",
        "docker_available": docker_available,
        "categories": {
            "images": cat(images),
            "containers": cat(containers),
            "volumes": cat(volumes),
            "build_cache": cat(cache_rows),
            "networks": cat(networks),
        },
        "capabilities": {
            "df_verbose_json": df_v is not None,
            "buildx_du": buildx_used,
        },
        "cleanup_min_age_hours": cleanup_min_age_hours,
        "warnings": warnings,
        "disclaimer": (
            "Reclaimable figures are estimates (UNIQUE-size based, deduped); "
            "actual freed space can be lower. will_be_cleaned approximates "
            "the current manual cleanup (dangling images / not-in-use build "
            "cache) without its age filter."
        ),
    }


def _cache_cleanup_argv(kind: str, min_age_hours: int) -> List[str]:
    """Pure argv builder for the two prune kinds (test-pinned invariants).

    builder → `docker builder prune --force --filter until=<h>h`
    dangling → `docker image prune --force --filter until=<h>h` (NO -a)
    """
    if kind == "builder":
        return ["builder", "prune", "--force",
                "--filter", f"until={min_age_hours}h"]
    if kind == "dangling":
        # image prune WITHOUT -a removes DANGLING (<none>) images only.
        return ["image", "prune", "--force",
                "--filter", f"until={min_age_hours}h"]
    raise ValueError(f"unknown cache-cleanup kind: {kind}")


def _system_df(executor: Any) -> Dict[str, Dict[str, str]]:
    """`docker system df` rows keyed by type (Images/Containers/Local Volumes/
    Build Cache). Unavailable docker → empty dict (caller surfaces it)."""
    result = executor.run_captured(
        ["system", "df", "--format", "{{json .}}"], timeout=30.0
    )
    import json as _json

    rows: Dict[str, Dict[str, str]] = {}
    if getattr(result, "exit_code", 1) != 0:
        return rows
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = _json.loads(line)
        except ValueError:
            continue
        kind = str(row.get("Type") or "")
        if kind:
            rows[kind] = {
                "total_count": str(row.get("TotalCount") or ""),
                "active": str(row.get("Active") or ""),
                "size": str(row.get("Size") or ""),
                "reclaimable": str(row.get("Reclaimable") or ""),
            }
    return rows


def cache_usage(executor: Any) -> Dict[str, Any]:
    """Read-only df summary for the settings card."""
    df = _system_df(executor)
    return {
        "schema_version": CACHE_USAGE_SCHEMA,
        "docker_available": bool(df),
        "df": df,
    }


def docker_cache_cleanup(
    executor: Any,
    *,
    min_age_hours: int = 24,
    data_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Prune the build cache and dangling images (both until-filtered).

    Never a global prune; never `-a`; running containers' layers are never
    candidates (docker enforces this for both prune kinds). Reports the df
    before/after deltas plus each prune's own reclaimed line.
    """
    if min_age_hours < 1:
        raise CliError(
            message="min_age_hours must be >= 1 (refusing unfiltered prune)",
            exit_code=RuntimeExitCode.USAGE_ERROR,
            error_code="AISC_ERR_USAGE",
        )

    from aisc.adapters.maintenance_lock import docker_maintenance_lock_at_root
    from aisc.application.data_root import shared_root

    root = Path(data_root) if data_root else shared_root()
    before = _system_df(executor)
    if not before:
        raise CliError(
            message="Docker unavailable; cache cleanup refused",
            exit_code=RuntimeExitCode.DOCKER_UNAVAILABLE,
            error_code=RuntimeErrorCode.DOCKER_UNAVAILABLE,
        )

    result: Dict[str, Any] = {
        "schema_version": CACHE_CLEANUP_SCHEMA,
        "action": "cache-cleanup",
        "min_age_hours": min_age_hours,
        "prunes": [],
        "df_before": before,
        "df_after": {},
        "warnings": [],
    }
    with docker_maintenance_lock_at_root(root):
        for kind in ("builder", "dangling"):
            argv = _cache_cleanup_argv(kind, min_age_hours)
            pr = executor.run_captured(argv, timeout=300.0)
            reclaimed = ""
            for line in (pr.stdout or "").splitlines():
                if "reclaimed" in line.lower():
                    reclaimed = line.strip()
                    break
            entry = {"kind": kind, "argv": argv,
                     "exit_code": pr.exit_code, "reclaimed": reclaimed}
            if pr.exit_code != 0:
                entry["error"] = (pr.stderr or pr.stdout or "").strip()[:200]
                result["warnings"].append(f"{kind} prune failed")
            result["prunes"].append(entry)

    result["df_after"] = _system_df(executor)
    return result


# --- v2.1.13 (docker-management, D-12): owned-resource operations -----------
#
# Boundary (user ruling 2026-09-20): start/stop/rm for AISC-owned containers,
# rm/retag for AISC-owned images - NOTHING else, and ONLY owned/legacy_owned
# resources are operable (unverified is report-only, forever). Every action
# re-classifies IN-LOCK at execution time: a stale UI snapshot never authorizes
# a delete. Volumes/networks: never touched. Target-following comes free -
# the CLI subcommand runs on whatever machine the drive target points at.

MANAGEMENT_SCHEMA = "aisc.docker-management/v1"

_MANAGEMENT_ACTIONS = ("start", "stop", "rm")


def _assert_container_owned(
    executor: Any, *, name: str, data_root: Optional[Path]
) -> Dict[str, Any]:
    """Re-scan and assert `name` is an owned/legacy_owned container (D-12)."""
    rows = _ps_rows(executor)
    registry = _registry_evidence(data_root)
    buckets = classify_containers(rows, registry)
    for bucket in ("owned", "legacy_owned"):
        for row in buckets[bucket]:
            if row["name"] == name:
                return row
    raise CliError(
        message=(
            f"container {name!r} is not an AISC-owned resource "
            "(unverified or unknown) - action refused"
        ),
        exit_code=6,
        error_code="AISC_ERR_OWNERSHIP_REFUSED",
    )


def _assert_image_operable(
    executor: Any, *, image_id: str, data_root: Optional[Path],
    allow_in_use: bool,
) -> Dict[str, Any]:
    """Re-scan and assert the image is owned/legacy_owned (D-12). When
    allow_in_use=False an ancestor-container check is also enforced
    (retag works on in-use images; rmi does not)."""
    rows = _image_universe(executor)
    owned_ids = _filtered_image_ids(executor, "label=org.aisc.managed=true")
    buckets, dangling = classify_images(
        rows, context="management", owned_ids=owned_ids
    )
    target: Optional[Dict[str, Any]] = None

    def matches(row: Dict[str, Any]) -> bool:
        rid = str(row.get("id") or "")
        return rid == image_id or rid.endswith(image_id)

    for bucket in ("owned", "legacy_owned"):
        for row in buckets[bucket]:
            if matches(row):
                target = dict(row)
                break
        if target:
            break
    if target is None:
        for row in dangling:
            if matches(row):
                target = {"id": row["id"], "name": row["id"]}
                break
    if target is None:
        raise CliError(
            message=(
                f"image {image_id!r} is not an AISC-owned resource "
                "(unverified or unknown) - action refused"
            ),
            exit_code=6,
            error_code="AISC_ERR_OWNERSHIP_REFUSED",
        )
    if not allow_in_use:
        ps = executor.run_captured(
            ["ps", "-a", "--filter", f"ancestor={target['id']}",
             "--format", "{{.ID}}"],
            timeout=15.0,
        )
        if getattr(ps, "exit_code", 1) == 0 and (ps.stdout or "").strip():
            raise CliError(
                message=(
                    "image is referenced by a container - "
                    "remove the container(s) first"
                ),
                exit_code=6,
                error_code="AISC_ERR_OWNERSHIP_REFUSED",
            )
    return target


def container_management_action(
    executor: Any, *, name: str, action: str, data_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Start/stop/remove ONE aisc-owned container (D-12).

    rm = stop + rm -f composed (same order as docker_cleanup). The
    ownership re-scan runs inside the maintenance lock; a refused action
    never touches docker."""
    if action not in _MANAGEMENT_ACTIONS:
        raise CliError(
            message=f"unknown container action: {action}",
            exit_code=RuntimeExitCode.USAGE_ERROR,
            error_code="AISC_ERR_USAGE",
        )
    from aisc.adapters.maintenance_lock import docker_maintenance_lock_at_root
    from aisc.application.data_root import shared_root

    root = Path(data_root) if data_root else shared_root()
    argvs: List[List[str]] = []
    with docker_maintenance_lock_at_root(root):
        row = _assert_container_owned(executor, name=name, data_root=root)
        running = row["state"] == "running"
        if action == "start":
            argvs.append(["start", name])
        elif action == "stop":
            if running:
                argvs.append(["stop", name])
        else:  # rm: stop (if needed) then remove
            if running:
                argvs.append(["stop", name])
            argvs.append(["rm", "-f", name])
        for argv in argvs:
            pr = executor.run_captured(argv, timeout=60.0)
            if pr.exit_code != 0:
                raise CliError(
                    message=(
                        f"container {action} failed: "
                        f"{(pr.stderr or pr.stdout or '').strip()[:200]}"
                    ),
                    exit_code=10,
                    error_code="AISC_ERR_CONTAINER_FAILED",
                )
    return {
        "schema_version": MANAGEMENT_SCHEMA,
        "action": f"container-{action}",
        "name": name,
        "ownership": row["ownership"],
        "argvs": argvs,
        "warnings": [],
    }


def image_management_rm(
    executor: Any, *, image_id: str, data_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Remove ONE unreferenced aisc-owned image (D-12)."""
    from aisc.adapters.maintenance_lock import docker_maintenance_lock_at_root
    from aisc.application.data_root import shared_root

    root = Path(data_root) if data_root else shared_root()
    with docker_maintenance_lock_at_root(root):
        target = _assert_image_operable(
            executor, image_id=image_id, data_root=root, allow_in_use=False
        )
        argv = ["rmi", target["id"]]
        pr = executor.run_captured(argv, timeout=120.0)
        if pr.exit_code != 0:
            raise CliError(
                message=(
                    f"image rmi failed: "
                    f"{(pr.stderr or pr.stdout or '').strip()[:200]}"
                ),
                exit_code=10,
                error_code="AISC_ERR_IMAGE_NOT_FOUND",
            )
    return {
        "schema_version": MANAGEMENT_SCHEMA,
        "action": "image-rm",
        "id": target["id"],
        "argv": argv,
        "warnings": [],
    }


def image_management_tag(
    executor: Any, *, image_id: str, repository: str, tag: str,
    data_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retag ONE aisc-owned image (D-12 'rename'): adds repository:tag.
    The old tag is preserved (retag semantics); in-use images allowed."""
    if not repository or not tag or any(
        ch.isspace() or ch == "'" or ch == '"' for ch in repository + tag
    ):
        raise CliError(
            message="invalid repository/tag",
            exit_code=RuntimeExitCode.USAGE_ERROR,
            error_code="AISC_ERR_USAGE",
        )
    from aisc.adapters.maintenance_lock import docker_maintenance_lock_at_root
    from aisc.application.data_root import shared_root

    root = Path(data_root) if data_root else shared_root()
    ref = f"{repository}:{tag}"
    with docker_maintenance_lock_at_root(root):
        target = _assert_image_operable(
            executor, image_id=image_id, data_root=root, allow_in_use=True
        )
        argv = ["tag", target["id"], ref]
        pr = executor.run_captured(argv, timeout=60.0)
        if pr.exit_code != 0:
            raise CliError(
                message=(
                    f"image tag failed: "
                    f"{(pr.stderr or pr.stdout or '').strip()[:200]}"
                ),
                exit_code=10,
                error_code="AISC_ERR_GENERAL",
            )
    return {
        "schema_version": MANAGEMENT_SCHEMA,
        "action": "image-tag",
        "id": target["id"],
        "ref": ref,
        "argv": argv,
        "warnings": [],
    }
