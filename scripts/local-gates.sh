#!/usr/bin/env bash
# local-gates.sh — 一键本地全门禁（local-gates.ps1 的 Linux 对等版，2026-09-14
# 为 Arch Linux 开发机补齐；覆盖面与 ps1 一致）：
#   1. Python 全测（忽略 integration）
#   2. cargo test --lib
#   3. vitest run
#   4. vue-tsc --noEmit
# 全绿输出 LOCAL GATES: ALL GREEN；任一红即停（exit 1）。
#
# 本机环境差异修复（仅 Linux 开发机需要，CI 不受影响）：
#   - zh locale：CLI help_i18n 会把 argparse help 译成中文，而契约测试断言
#     英文 "usage:" —— 跑测时固定四个 locale 变量为英文。
#   - Node 版本：项目锁定 .nvmrc 的 Node 22（与 CI/workbench-ci.yml 一致）。
#     脚本直接把 nvm 的版本 bin 前置到 PATH（绕过 `nvm use` 对 ~/.npmrc
#     prefix 的绝对检查，不改用户全局配置）。nvm 缺失时回退 PATH 上的 node：
#     若是 >= 26（默认启用实验性原生 localStorage，遮蔽 jsdom 注入的），
#     用 --no-experimental-webstorage 关掉。
#   - docker 未安装/未运行时跳过 cargo 里依赖 daemon 的 diag 测试并黄字警示
#     （装好 docker 后自然全量跑）。
#
# 用法：bash scripts/local-gates.sh

set -uo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

py="$root/.venv/bin/python"
[ -x "$py" ] || py="$(command -v python3)" || { echo "no python found" >&2; exit 1; }

# rustup 用户安装时非交互 shell 可能没有 ~/.cargo/bin
if ! command -v cargo >/dev/null 2>&1 && [ -x "$HOME/.cargo/bin/cargo" ]; then
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# 项目 Node 版本：.nvmrc（nvm 管理，绕过 `nvm use` 的 ~/.npmrc prefix 检查——
# 直接把 nvm 的版本 bin 目录前置到 PATH，效果与 nvm use 等价，不触碰全局配置）。
if [ -s "$root/.nvmrc" ] && [ -s "$HOME/.nvm/nvm.sh" ]; then
    nvm_ver="$(tr -d '[:space:]' < "$root/.nvmrc")"
    nvm_bin="$HOME/.nvm/versions/node/v${nvm_ver#v}/bin"
    if [ -d "$nvm_bin" ]; then
        export PATH="$nvm_bin:$PATH"
    else
        printf '\033[33m[提示] nvm 未装 Node %s（%s 不存在）——先跑: nvm install %s\033[0m\n' \
            "$nvm_ver" "$nvm_bin" "$nvm_ver" >&2
    fi
fi

export LC_ALL=C.UTF-8 LC_MESSAGES=C.UTF-8 LANG=C.UTF-8 LANGUAGE=en

node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
if [ "$node_major" -ge 26 ] && ! [[ " ${NODE_OPTIONS:-} " == *"--no-experimental-webstorage"* ]]; then
    export NODE_OPTIONS="${NODE_OPTIONS:-} --no-experimental-webstorage"
fi

step() {
    name="$1"
    printf '\n\033[36m=== %s ===\033[0m\n' "$name"
    shift
    "$@"
    if [ $? -ne 0 ]; then
        printf '\n\033[31mLOCAL GATES: FAILED at [%s]\033[0m\n' "$name" >&2
        exit 1
    fi
}

step "python full tests" "$py" -m pytest tests/ -q --ignore=tests/integration

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    step "cargo test --lib" bash -c 'cd "$1/workbench/src-tauri" && cargo test --lib' _ "$root"
else
    printf '\n\033[33m[docker 未安装/未运行] 跳过依赖 daemon 的 diag 测试：\033[0m\n' >&2
    printf '\033[33m  env::tests::diag_engine_reachable_*；装好 docker 后请跑全量 cargo test --lib。\033[0m\n' >&2
    step "cargo test --lib (docker-gated tests skipped)" \
        bash -c 'cd "$1/workbench/src-tauri" && cargo test --lib -- --skip diag_engine_reachable' _ "$root"
fi

step "vitest run" bash -c 'cd "$1/workbench" && npx vitest run' _ "$root"
step "vue-tsc --noEmit" bash -c 'cd "$1/workbench" && npx vue-tsc --noEmit' _ "$root"

# --- 按改动面的提示（不阻断） -------------------------------------------
changed="$(git diff --name-only origin/develop...HEAD 2>/dev/null)"
[ -n "$changed" ] || changed="$(git status --short | cut -c4-)"

if grep -q '^src/aisc/' <<<"$changed"; then
    printf '\n\033[33m[reminder] Python CLI 源已改：手测/发布前需重建 sidecar —\033[0m\n' >&2
    printf '\033[33m  bash scripts/build-cli.sh; 然后拷贝 dist/aisc-x86_64-unknown-linux-gnu\033[0m\n' >&2
    printf '\033[33m  到 workbench/src-tauri/binaries/（真 sidecar；占位空文件仅够编译）。\033[0m\n' >&2
fi
if grep -q '^container/' <<<"$changed"; then
    printf '\n\033[33m[reminder] container/ 已改：必须刷新 vendor checksums —\033[0m\n' >&2
    printf '\033[33m  bash tools/vendor-refresh.sh\033[0m\n' >&2
fi

printf '\n\033[32mLOCAL GATES: ALL GREEN\033[0m\n'
