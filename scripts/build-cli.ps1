# Build the AISC CLI as a Tauri sidecar binary (Windows).
#
# Produces dist\<name>-<target-triple>.exe (Tauri externalBin convention;
# the .exe extension is handled by Tauri's bundler on Windows).
# Requires: python with PyInstaller (pip install -e ".[dev]" or uv).
#
# 2.1.11 r8 (field lesson): Python-side CLI changes (e.g. serve.py gate) do
# NOT reach the running app until this script rebuilds the sidecar AND the
# Workbench restarts its resident serve pool. ALSO: while Workbench runs, its
# pooled `aisc serve` children hold target\debug\aisc.exe locked — the copy
# below fails mid-script (half-synced state). The preflight below refuses to
# build until they are gone.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $MyInvocation.MyCommand.Path | Join-Path -ChildPath "..")

# --- preflight: refuse while a running aisc would lock the destinations ---
$Running = @(Get-Process aisc -ErrorAction SilentlyContinue)
if ($Running.Count -gt 0) {
    Write-Host "== PREFLIGHT FAILED: aisc.exe is running (pid(s): $((($Running | ForEach-Object Id) -join ', '))) ==" -ForegroundColor Red
    Write-Host "   A running Workbench pools resident `aisc serve` children that lock"
    Write-Host "   workbench\src-tauri\target\debug\aisc.exe; the copy step would fail"
    Write-Host "   mid-script. Close Workbench (or stop those processes) and re-run."
    exit 1
}

$TargetTriple = $env:TARGET_TRIPLE
if (-not $TargetTriple) {
    $Arch = $env:PROCESSOR_ARCHITECTURE
    if ($Arch -eq "ARM64") { $TargetTriple = "aarch64-pc-windows-msvc" }
    else { $TargetTriple = "x86_64-pc-windows-msvc" }
}

Write-Host "== building aisc sidecar ($TargetTriple) =="
python -m PyInstaller --noconfirm --clean packaging/aisc.spec

New-Item -ItemType Directory -Force -Path dist | Out-Null
Move-Item -Force dist\aisc.exe "dist\aisc-$TargetTriple.exe"
Write-Host "== artifact: dist\aisc-$TargetTriple.exe =="
& "dist\aisc-$TargetTriple.exe" version --format json | Select-Object -First 1

# v2.1.7 S5: sync the fresh sidecar to BOTH places that actually run it.
# workbench/src-tauri/binaries/ feeds tauri build/dev externalBin, and the
# dev Workbench's CLI pin resolves workbench/src-tauri/target/debug/aisc.exe.
# Leaving either stale cost a full debugging round on 2026-08-27 (the app
# ran a two-day-old sidecar and failed with a capability mismatch).
$Dst1 = "workbench\src-tauri\binaries\aisc-$TargetTriple.exe"
$Dst2 = "workbench\src-tauri\target\debug\aisc.exe"
New-Item -ItemType Directory -Force -Path (Split-Path $Dst1) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $Dst2) | Out-Null
Copy-Item -Force "dist\aisc-$TargetTriple.exe" $Dst1
Copy-Item -Force "dist\aisc-$TargetTriple.exe" $Dst2
Write-Host "== synced: $Dst1"
Write-Host "== synced: $Dst2"

# 2026-08-29 incident: the bundle chain is repo container/ → nsis/bundle/aisc-bundle/
# → (cargo build copies to) target/debug/aisc-bundle/ → (aisc build) → docker image.
# The nsis/ directory is the SOURCE that cargo re-copies on every tauri dev restart —
# leaving it stale means every dev restart reverts the debug bundle to old code.
# Sync BOTH the source (nsis) and the current copy (target/debug).
#
# 2026-09-16 (2.1.12 B0 infra): PS 5.1 Remove-Item/Copy-Item die past
# MAX_PATH(260) — the C:→E: repo move lengthened the root by 8 chars and the
# vendored agent-skills office schemas now cross it inside the bundle copy.
# robocopy is long-path native in both directions; /MIR onto an empty dir is
# the canonical long-path delete. Exit codes 0-7 are success, >=8 is failure.
$RoboQuiet = "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP"
$EmptyDir = Join-Path $env:TEMP "aisc-bundle-sync-empty"
New-Item -ItemType Directory -Force -Path $EmptyDir | Out-Null
foreach ($Bundle in @(
    "workbench\src-tauri\nsis\bundle\aisc-bundle",
    "workbench\src-tauri\target\debug\aisc-bundle"
)) {
    if (Test-Path $Bundle) {
        foreach ($Dir in @("container", "config", "vendor")) {
            $DstDir = Join-Path $Bundle $Dir
            if (Test-Path $DstDir) {
                robocopy $EmptyDir $DstDir /MIR $RoboQuiet | Out-Null
                if ($LASTEXITCODE -ge 8) { throw "robocopy clear failed for $DstDir (exit $LASTEXITCODE)" }
                Remove-Item -Force -Recurse -ErrorAction SilentlyContinue $DstDir
                if (Test-Path $DstDir) { throw "failed to clear $DstDir" }
            }
            robocopy $Dir $DstDir /E $RoboQuiet | Out-Null
            if ($LASTEXITCODE -ge 8) { throw "robocopy copy failed for $Dir -> $DstDir (exit $LASTEXITCODE)" }
        }
        # A2: VERSION moved into the package; the BUNDLE layout keeps it at the bundle root.
        Copy-Item -Force src\aisc\VERSION (Join-Path $Bundle "VERSION")
        Write-Host "== synced: $Bundle"
    }
}
