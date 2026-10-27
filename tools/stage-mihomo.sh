#!/usr/bin/env bash
# Stage pinned Mihomo + one AISC geodata snapshot as a validated group.
# Default: host architecture; --arch amd64|arm64 or --all-arches overrides it.
# The snapshot date is not an upstream release tag: URLs use GEODATA_COMMIT.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DST="$ROOT/container/downloads"
read_pin() {
  awk -v key="$1" '
    index($0, key "=") == 1 { value=substr($0, length(key)+2); sub(/#.*/, "", value); gsub(/^[ \t]+|[ \t\r]+$/, "", value) }
    END { print value }
  ' "$ROOT/config/versions.env"
}
VER="${MIHOMO_VERSION:-$(read_pin MIHOMO_VERSION)}"
GEODATA_VERSION="${GEODATA_VERSION:-$(read_pin GEODATA_VERSION)}"
GEODATA_COMMIT="${GEODATA_COMMIT:-$(read_pin GEODATA_COMMIT)}"
[[ "$VER" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Invalid MIHOMO_VERSION" >&2; exit 2; }
[[ "$GEODATA_VERSION" =~ ^[0-9]{8}$ && "$GEODATA_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]] || {
  echo "Expected an AISC snapshot date and immutable GEODATA_COMMIT" >&2; exit 2;
}

ARCHES=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --all-arches) [ -z "$ARCHES" ] || { echo "Choose one architecture option" >&2; exit 2; }; ARCHES="amd64 arm64" ;;
    --arch)
      [ -z "$ARCHES" ] || { echo "Choose one architecture option" >&2; exit 2; }
      case "${2:?--arch needs amd64 or arm64}" in
        amd64|x86_64|x64) ARCHES=amd64 ;;
        arm64|aarch64) ARCHES=arm64 ;;
        *) echo "Unsupported architecture: $2" >&2; exit 2 ;;
      esac
      shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
if [ -z "$ARCHES" ]; then
  case "$(uname -m)" in
    x86_64|amd64) ARCHES=amd64 ;;
    aarch64|arm64) ARCHES=arm64 ;;
    *) echo "Unsupported host architecture; use --arch" >&2; exit 2 ;;
  esac
fi

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && [ "$("$candidate" -c 'print(1)' 2>/dev/null)" = "1" ]; then
    PY="$candidate"; break
  fi
done
[ -n "$PY" ] || { echo "Python is required to validate official release digests" >&2; exit 1; }

verify_sha256() {
  "$PY" -c '
import hashlib,sys
digest=hashlib.sha256()
with open(sys.argv[2], "rb") as stream:
    for block in iter(lambda: stream.read(1024*1024), b""):
        digest.update(block)
if digest.hexdigest().lower() != sys.argv[1].lower():
    raise SystemExit("SHA256 mismatch: " + sys.argv[2])
' "$1" "$2"
}

if [ -n "${MIHOMO_GH_PROXY:-}" ]; then
  MIRRORS=("$MIHOMO_GH_PROXY")
else
  MIRRORS=("https://ghfast.top/" "https://gh-proxy.com/" "https://github.moeyy.xyz/" "https://ghproxy.net/" "https://mirror.ghproxy.com/")
fi
dl_url() {
  local url="$1" out="$2" mirror=""
  for mirror in "${MIRRORS[@]}" ""; do
    echo "  try: ${mirror}${url}"
    if curl -fSL --http1.1 --retry 2 --retry-delay 1 --retry-all-errors \
            --connect-timeout 8 --max-time 180 "${mirror}${url}" -o "$out"; then
      return 0
    fi
  done
  echo "Download failed: $url" >&2
  return 1
}

mkdir -p "$DST"
CHECKSUMS="$DST/geodata-${GEODATA_VERSION}.sha256"
[ -f "$CHECKSUMS" ] || { echo "Missing snapshot checksums: $CHECKSUMS" >&2; exit 1; }
STAGE="$(mktemp -d "$DST/.stage-mihomo.XXXXXXXX")"
COMMITTING=0
cleanup() {
  local status=$?
  trap - EXIT
  if [ "$COMMITTING" = 1 ] && [ "$status" != 0 ]; then
    echo "Publish failed; restoring previous staging group" >&2
    rm -f "$DST"/mihomo-linux-*.gz "$DST/geoip.metadb" "$DST/geosite.dat" "$DST/country.mmdb"
    for previous in "$STAGE"/backup/*; do
      [ -f "$previous" ] || continue
      cp -p "$previous" "$DST/" || echo "Restore failed: $previous" >&2
    done
  fi
  rm -rf "$STAGE"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# The GitHub release API supplies an upstream SHA256 for each selected asset.
dl_url "https://api.github.com/repos/MetaCubeX/mihomo/releases/tags/${VER}" "$STAGE/release.json"
KEEP=""
for arch in $ARCHES; do
  asset="mihomo-linux-${arch}-${VER}.gz"
  digest="$("$PY" -c '
import json,re,sys
with open(sys.argv[1], encoding="utf-8") as stream:
    release=json.load(stream)
if release.get("tag_name") != sys.argv[2] or release.get("draft") or release.get("prerelease"):
    raise SystemExit("Unexpected Mihomo release identity")
assets=[item for item in release.get("assets", []) if item.get("name") == sys.argv[3]]
if len(assets) != 1 or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", assets[0].get("digest") or ""):
    raise SystemExit("Missing unique official asset SHA256")
print(assets[0]["digest"].split(":", 1)[1])
' "$STAGE/release.json" "$VER" "$asset")"
  dl_url "https://github.com/MetaCubeX/mihomo/releases/download/${VER}/${asset}" "$STAGE/$asset"
  verify_sha256 "$digest" "$STAGE/$asset"
  KEEP="$KEEP $asset"
done
for file in geoip.metadb geosite.dat country.mmdb; do
  digest="$(awk -v file="$file" '$2 == file { n++; digest=$1 } END { if (n != 1 || length(digest) != 64) exit 1; print digest }' "$CHECKSUMS")"
  case "$digest" in *[!0-9a-fA-F]*) echo "Invalid geodata checksum" >&2; exit 1;; esac
  dl_url "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/${GEODATA_COMMIT}/$file" "$STAGE/$file"
  verify_sha256 "$digest" "$STAGE/$file"
done

# No destination payload changes until every requested file has been verified.
# Retain a rollback copy also for filesystem failures during publication.
mkdir "$STAGE/backup"
for previous in "$DST"/mihomo-linux-*.gz "$DST/geoip.metadb" "$DST/geosite.dat" "$DST/country.mmdb"; do
  [ -f "$previous" ] || continue
  cp -p "$previous" "$STAGE/backup/"
done
COMMITTING=1
for file in $KEEP geoip.metadb geosite.dat country.mmdb; do
  mv -f "$STAGE/$file" "$DST/$file"
done
for previous in "$DST"/mihomo-linux-*.gz; do
  [ -f "$previous" ] || continue
  case " $KEEP " in *" $(basename "$previous") "*) ;; *) rm -f "$previous" ;; esac
done
COMMITTING=0
echo "Validated Mihomo $VER ($ARCHES) + geodata snapshot $GEODATA_VERSION ($GEODATA_COMMIT)"
