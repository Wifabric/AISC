#!/usr/bin/env bash
# Stage pinned npm main/native families and optionally yazi into container/downloads.
# The Python helper verifies official SHA512 / release SHA256 before replacing
# any member of a family. Defaults come from config/versions.env.
#
#   bash scripts/stage-npm.sh --yazi --all-arches
#   bash scripts/stage-npm.sh --registry https://registry.npmjs.org
#   bash scripts/stage-npm.sh --no-companions  # main-only Git/CI presets
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Windows python3 can be a Microsoft Store stub; use a working interpreter.
PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && [ "$("$cand" -c 'print(1)' 2>/dev/null)" = "1" ]; then
    PY="$cand"
    break
  fi
done
[ -n "$PY" ] || { echo "ERROR: Python 3 is required" >&2; exit 1; }

# Keep the existing GitHub mirror/direct candidates, shared by both yazi arches.
mirrors=()
for m in "https://ghfast.top/" "https://gh-proxy.com/" "https://github.moeyy.xyz/" ""; do
  mirrors+=(--github-mirror "$m")
done
exec "$PY" "$ROOT/scripts/stage_npm.py" --root "$ROOT" "${mirrors[@]}" "$@"
