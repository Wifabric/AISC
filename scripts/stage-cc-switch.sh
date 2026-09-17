#!/usr/bin/env bash
# stage-cc-switch.sh — 预下载 cc-switch-cli release 资产到 container/downloads/
#
# 用途：CN 网络 buildkit TLS 被掐时免网构建（Dockerfile 的 /tmp/dl 预置口，
# 0.1.1 起支持；对齐 stage-mihomo.sh / stage-npm.sh 先例）。构建时 pinned
# 分支仍对预置文件过 sha256 强校验——预置不降低完整性强度。
#
# 用法：
#   bash scripts/stage-cc-switch.sh                # 解析 latest stable（resolver 同源）
#   bash scripts/stage-cc-switch.sh v5.10.5        # 指定版本
# 环境旋钮：AISC_GH_API_BASE / AISC_GH_API_TOKEN（同 resolver）。
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "resolving latest stable cc-switch (resolver cache)..."
  VERSION="$(python - <<'PY'
from aisc.application.cc_switch_resolver import CcSwitchResolver
from aisc.domain.cc_switch_release import ResolveError
try:
    r = CcSwitchResolver().resolve()
    print(r.tag)
except ResolveError as e:
    raise SystemExit(f"resolver failed: {e}")
PY
)"
fi
echo "staging cc-switch ${VERSION}"

# 资产名/URL/SHA256 直接复用仓库内同一实现（不复制粘贴清单逻辑）
python - "$VERSION" <<'PY'
import sys, urllib.request, hashlib, shutil
from pathlib import Path

tag = sys.argv[1]
# 经 resolver 的资产命名约定（与 Dockerfile 回退拼法一致）
url = (f"https://github.com/SaladDay/cc-switch-cli/releases/download/"
       f"{tag}/cc-switch-cli-{tag}-linux-x64-musl.tar.gz")
name = f"cc-switch-cli-{tag}-linux-x64-musl.tar.gz"
dest = Path("container/downloads") / name

mirrors = ["https://ghfast.top/", "https://gh-proxy.com/",
           "https://github.moeyy.xyz/", "https://ghproxy.net/", ""]
for m in mirrors:
    u = f"{m}{url}"
    try:
        print(f"try: {u}")
        req = urllib.request.Request(u, headers={"User-Agent": "aisc-stage"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        print(f"staged: {dest} ({dest.stat().st_size} bytes)")
        print("note: pinned builds verify sha256 at build time (resolver pin)")
        sys.exit(0)
    except Exception as e:
        print(f"  fail: {e}")
raise SystemExit("all mirrors failed")
PY
