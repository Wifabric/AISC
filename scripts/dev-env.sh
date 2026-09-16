# dev-env.sh — 项目范围开发环境激活（git-bash / MSYS，与 dev-env.ps1 对等）
#
# 用法：source scripts/dev-env.sh
# 设计约束同 dev-env.ps1：不动宿主机全局配置 —— Node 22 走 .tools 便携副本，
# rustup 是 --no-modify-path 安装，Python venv 基于 .tools/python312（CI 对齐，
# 宿主 3.14 会挂 streaming 超时用例，见 dev-env.ps1 注释）。
# 注意：msys 环境拉起的同步 daemon 曾有连不上远端的坑（仅诊断脚本场景，见 devlog），
# 产品/门禁不受影响。

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

_node="$ROOT/.tools/node22"
if [ -x "$_node/node.exe" ] || [ -x "$_node/bin/node" ]; then
  case ":$PATH:" in *":$_node:"*) ;; *) export PATH="$_node:$PATH";; esac
else
  echo "warning: .tools/node22 缺失（Node 22 便携副本未恢复）" >&2
fi

_cargo="${USERPROFILE:-$HOME}/.cargo/bin"
if [ -x "$_cargo/cargo.exe" ] || [ -x "$_cargo/cargo" ]; then
  case ":$PATH:" in *":$_cargo:"*) ;; *) export PATH="$_cargo:$PATH";; esac
else
  echo "warning: ~/.cargo/bin 缺失（rustup 未安装）" >&2
fi

if [ -f "$ROOT/.venv/Scripts/activate" ]; then
  . "$ROOT/.venv/Scripts/activate"
fi

echo "dev env: node $(node --version 2>/dev/null) | cargo $(cargo --version 2>/dev/null) | python $(python --version 2>/dev/null)"
