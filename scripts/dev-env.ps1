# dev-env.ps1 — 项目范围开发环境激活（Windows 裸机开发，2026-09-14 起）
#
# 用法（dot-source，让 PATH/venv 生效在当前会话）：
#   . scripts\dev-env.ps1
#
# 设计约束：不修改宿主机全局配置。
#   - Node 22 是 .tools\node22 便携副本（宿主机 Node 26 保持原样；Node >=26 的原生
#     localStorage 会遮蔽 vitest jsdom 注入，panelLayout 测试必挂——见 docs/win-dev-on-linux.md 1.2）。
#   - rustup 安装用了 --no-modify-path，~\.cargo\bin 由本脚本前置。
#   - Python venv 基于 .tools\python312（nuget 便携版，与 CI 的 3.12 对齐——
#     DEVELOP_WIKI §2.2）。宿主 3.14 跑全测会挂 streaming 超时用例：3.14 Windows
#     子进程启动时复制 std 句柄，子进程 dup2/close 均不再释放管道 EOF（2026-09-14
#     实测，父进程版本无关）。首次恢复：
#     .tools\python312\python.exe -m venv .venv; .venv\Scripts\pip install -e ".[dev]"
# 之后跑全门禁：powershell -File scripts\local-gates.ps1（其内已 dot-source 本文件）。

$root = Split-Path -Parent $PSScriptRoot

$nodeDir = Join-Path $root '.tools\node22'
if (Test-Path (Join-Path $nodeDir 'node.exe')) {
    if (-not (($env:PATH -split ';') -contains $nodeDir)) { $env:PATH = "$nodeDir;$env:PATH" }
} else {
    Write-Warning ".tools\node22 缺失（Node 22 便携副本未恢复）：从 https://nodejs.org/dist/ 下载 node-v22.x-win-x64.zip 解压为 .tools/node22"
}

$cargoBin = Join-Path $env:USERPROFILE '.cargo\bin'
if (Test-Path (Join-Path $cargoBin 'cargo.exe')) {
    if (-not (($env:PATH -split ';') -contains $cargoBin)) { $env:PATH = "$cargoBin;$env:PATH" }
} else {
    Write-Warning "~\.cargo\bin 缺失（rustup 未安装）：rustup-init.exe -y --no-modify-path --profile minimal --default-host x86_64-pc-windows-msvc"
}

$activate = Join-Path $root '.venv\Scripts\Activate.ps1'
if (Test-Path $activate) { & $activate }

Write-Host "dev env: node $(node --version 2>$null) | cargo $(cargo --version 2>$null) | python $(python --version 2>$null)"
