# local-gates.ps1 — 一键本地全门禁（2026-08-20 用户决策：能本地跑的全部本地跑，
# 远程 CI 只作环境差异兜底；安装包产物改为本地构建）。
#
# 覆盖 Workbench CI + CLI sidecar 两条远程 CI 的全部可本地检查项：
#   1. Python 全测（忽略 integration）
#   2. cargo test --lib
#   3. vitest run
#   4. vue-tsc --noEmit
# 并按改动面提示两条人工后续（sidecar 重建 / vendor 刷新）。
#
# 用法：powershell -File scripts\local-gates.ps1
# 全绿输出 LOCAL GATES: ALL GREEN；任一红即停（exit 1）。

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# 拉起项目范围工具链（.tools Node 22、--no-modify-path 安装的 cargo、.venv），
# 门禁自含激活，不要求调用方先手工 source dev-env。
. "$PSScriptRoot\dev-env.ps1"

function Step($name, $script) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    & $script
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nLOCAL GATES: FAILED at [$name]" -ForegroundColor Red
        exit 1
    }
}

Step "python full tests" {
    # Windows MAX_PATH(260)：长测试夹具路径实测 ~275 字符（tmp\data-root\
    # workspaces\sha256-v1-<64hex>\codex\sessions\<date>\<73-char file>），
    # 超 260 即 FileNotFoundError。不改宿主机注册表（LongPathsEnabled 属
    # 系统配置），按 local-gates.sh 修 Linux 坑的同一先例把 pytest 临时根
    # 指到短路径（C:\ 根建目录标准用户可写、无需管理员）。
    $shortTmp = 'C:\pt'
    try {
        New-Item -ItemType Directory -Force -Path $shortTmp | Out-Null
        # pytest basetemp 目录逐次递增（pytest-1、pytest-2…），位数变长后
        # 最深的 conversation 夹具恰好越过 MAX_PATH 260（2026-09-16 实测
        # pytest-10 起红）。清掉旧目录让每次都从 pytest-0 起，路径恒定。
        Get-ChildItem -Path $shortTmp -Directory -Filter 'pytest-*' -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        $env:TMP = $shortTmp; $env:TEMP = $shortTmp
    } catch {
        Write-Warning "无法创建短临时目录 $shortTmp，沿用默认 TEMP（长路径用例将失败）"
    }
    python -m pytest tests/ -q --ignore=tests/integration --basetemp="$shortTmp\pytest"
}

Step "cargo test --lib" {
    Set-Location "$root\workbench\src-tauri"
    # PS 5.1：native stderr 经 2>&1 会包成 ErrorRecord，叠加 $ErrorAction
    # =Stop 即致命——cargo 重编译的 "Compiling…" 行会假失败。直接放行输出。
    cargo test --lib
    Set-Location $root
}

Step "vitest run" {
    Set-Location "$root\workbench"
    npx vitest run
    Set-Location $root
}

Step "vue-tsc --noEmit" {
    Set-Location "$root\workbench"
    npx vue-tsc --noEmit
    Set-Location $root
}

# --- 按改动面的提示（不阻断） -------------------------------------------
$changed = @()
try { $changed = git diff --name-only origin/develop...HEAD 2>$null } catch {}
if (-not $changed) { try { $changed = git status --short | ForEach-Object { $_.Substring(3) } } catch {} }

if ($changed -match "^src/aisc/") {
    Write-Host "`n[reminder] Python CLI 源已改：手测/发布前需重建 sidecar —" -ForegroundColor Yellow
    Write-Host "  powershell -File scripts\build-cli.ps1; 然后拷贝 dist\aisc-x86_64-pc-windows-msvc.exe" -ForegroundColor Yellow
    Write-Host "  到 workbench\src-tauri\binaries\ 与 target\debug\aisc.exe" -ForegroundColor Yellow
}
if ($changed -match "^container/") {
    Write-Host "`n[reminder] container/ 已改：必须刷新 vendor checksums —" -ForegroundColor Yellow
    Write-Host '  PATH="/tmp/py3shim:$PATH" bash tools/vendor-refresh.sh' -ForegroundColor Yellow
}

Write-Host "`nLOCAL GATES: ALL GREEN" -ForegroundColor Green
