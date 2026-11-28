#!/usr/bin/env bash
# 安装 git pre-commit 钩子到 .git/hooks/
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$here/git-hooks/pre-commit"
dest="$here/../.git/hooks/pre-commit"
mkdir -p "$(dirname "$dest")"
cp "$src" "$dest"
chmod +x "$dest"
printf 'installed: %s\n' "$dest"
