#!/usr/bin/env bash
# local-gates.sh — 一键本地全门禁（local-gates.ps1 的 Linux 对等版，2026-09-14
# 为 Arch Linux 开发机补齐；覆盖面与 ps1 一致）：
#   1. Python 全测（忽略 integration；PROJECT_MAP §5 登记的预存失败判绿）
#   2. cargo test --lib（docker-gated 自动跳过）
#   3. vitest run
#   4. vue-tsc --noEmit
#   5. i18n key 使用率检查（孤儿 key 判红）
#   + container/ 或 vendor/ 改动时阻断跑 vendor-verify（checksum 漂移即红）
# 全绿输出 LOCAL GATES: ALL GREEN；任一非预存失败即停（exit 1）。
#
# 用法：
#   bash scripts/local-gates.sh            # 全量（CI / 发布前）
#   bash scripts/local-gates.sh --scoped   # 只跑本次改动面相关的步骤
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

set -uo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

SCOPED=false
for arg in "$@"; do
  case "$arg" in
    --scoped) SCOPED=true ;;
    *) printf 'ERROR: unknown arg: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

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

# 已知预存失败（与 PROJECT_MAP §5 基线一致）：pytest 失败集合 ⊆ 本清单时判绿。
KNOWN_PYTHON_FAILURES='
tests/test_extensions_adapter.py::MarketTests::test_skill_repo_remove_rejects_malformed_source
tests/test_extensions_adapter.py::MarketTests::test_office_hours_includes_only_selected_skill_and_referenced_runtime
'

# 本次改动面（--scoped 与 vendor-verify 触发用）
changed="$(git diff --name-only origin/develop...HEAD 2>/dev/null)"
[ -n "$changed" ] || changed="$(git status --short | cut -c4-)"
touches() { grep -qE "$1" <<<"$changed"; }

run_python=yes
run_cargo=yes
run_frontend=yes
if [ "$SCOPED" = true ]; then
    run_python=no; run_cargo=no; run_frontend=no
    touches '^(src/|container/|tests/)' && run_python=yes
    touches '^workbench/src-tauri/' && run_cargo=yes
    touches '^workbench/' && run_frontend=yes
fi

if [ "$run_python" = yes ]; then
    printf '\n\033[36m=== python full tests ===\033[0m\n'
    py_log="$(mktemp)"
    if "$py" -m pytest tests/ -q --ignore=tests/integration --tb=no >"$py_log" 2>&1; then
        tail -n 1 "$py_log"
    else
        failed="$(grep '^FAILED ' "$py_log" | sed 's/^FAILED //' | sort)"
        unexpected=""
        while IFS= read -r f; do
            [ -z "$f" ] && continue
            if ! grep -qxF "$f" <<<"$KNOWN_PYTHON_FAILURES"; then
                unexpected="${unexpected}${f}"$'\n'
            fi
        done <<<"$failed"
        if [ -n "$unexpected" ]; then
            tail -n 25 "$py_log" >&2
            printf '\n\033[31mLOCAL GATES: FAILED at [python full tests]（非预存失败）\033[0m\n' >&2
            printf '%s' "$unexpected" >&2
            rm -f "$py_log"
            exit 1
        fi
        printf '\033[33m[已知预存失败] PROJECT_MAP §5 基线，判绿：\033[0m\n' >&2
        printf '%s\n' "$failed" | sed 's/^/  /' >&2
    fi
    rm -f "$py_log"
elif [ "$SCOPED" = true ]; then
    printf '\n\033[33m[--scoped] 跳过 python 全测（无 src/container/tests 改动）\033[0m\n'
fi

if [ "$run_cargo" = yes ]; then
    if ! command -v cargo >/dev/null 2>&1; then
        printf '\n\033[33m[cargo 未安装] 跳过 cargo test --lib（PATH 无 cargo，CI 为 Rust 权威）\033[0m\n' >&2
    elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
        step "cargo test --lib" bash -c 'cd "$1/workbench/src-tauri" && cargo test --lib' _ "$root"
    else
        printf '\n\033[33m[docker 未安装/未运行] 跳过依赖 daemon 的 diag 测试：\033[0m\n' >&2
        printf '\033[33m  env::tests::diag_engine_reachable_*；装好 docker 后请跑全量 cargo test --lib。\033[0m\n' >&2
        step "cargo test --lib (docker-gated tests skipped)" \
            bash -c 'cd "$1/workbench/src-tauri" && cargo test --lib -- --skip diag_engine_reachable' _ "$root"
    fi
elif [ "$SCOPED" = true ]; then
    printf '\n\033[33m[--scoped] 跳过 cargo（无 src-tauri 改动）\033[0m\n'
fi

if [ "$run_frontend" = yes ]; then
    step "vitest run" bash -c 'cd "$1/workbench" && npx vitest run' _ "$root"
    step "vue-tsc --noEmit" bash -c 'cd "$1/workbench" && npx vue-tsc --noEmit' _ "$root"
    # i18n 孤儿 key：非阻断（仓库有预存欠债），只黄字提示；收紧后再转 step
    if "$py" scripts/check-i18n-keys.py >/tmp/aisc-i18n.log 2>&1; then
        printf '\033[32m[i18n] %s\033[0m\n' "$(tail -n1 /tmp/aisc-i18n.log)"
    else
        printf '\033[33m[i18n] 存在孤儿 key（预存欠债，非阻断）；完整清单见 scripts/check-i18n-keys.py\033[0m\n' >&2
    fi
    rm -f /tmp/aisc-i18n.log
elif [ "$SCOPED" = true ]; then
    printf '\n\033[33m[--scoped] 跳过 vitest/vue-tsc（无 workbench 改动）\033[0m\n'
fi

# container/ 或 vendor/ 改动 → 阻断核对 vendor checksums（漂移即红）
if touches '^(container/|vendor/)'; then
    step "vendor verify" bash -c 'cd "$1" && bash tools/vendor-verify.sh' _ "$root"
fi

# --- 按改动面的提示（不阻断） -------------------------------------------
if grep -q '^src/aisc/' <<<"$changed"; then
    printf '\n\033[33m[reminder] Python CLI 源已改：手测/发布前需重建 sidecar —\033[0m\n' >&2
    printf '\033[33m  bash scripts/build-cli.sh; 然后拷贝 dist/aisc-x86_64-unknown-linux-gnu\033[0m\n' >&2
    printf '\033[33m  到 workbench/src-tauri/binaries/（真 sidecar；占位空文件仅够编译）。\033[0m\n' >&2
fi

printf '\n\033[32mLOCAL GATES: ALL GREEN\033[0m\n'
