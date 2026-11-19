param(
    [Parameter(Mandatory)][string]$CandidateInstaller,
    [Parameter(Mandatory)][string]$ReportDirectory,
    [string]$ExpectedVersion = '2.1.19'
)
$ErrorActionPreference = 'Stop'
# This script installs/uninstalls an application. Never run it on a developer's
# desktop: it is deliberately restricted to disposable GitHub Windows runners.
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'This acceptance test requires a disposable GitHub Actions Windows runner.'
}
$candidate = (Resolve-Path -LiteralPath $CandidateInstaller).Path
New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null
$reportPath = Join-Path $ReportDirectory 'upgrade-result.json'
$result = [ordered]@{ baseline = '2.1.18'; candidateSha256 = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash; steps = @() }
$appDir = Join-Path $env:LOCALAPPDATA 'AISC Workbench'
$dataRoot = Join-Path $env:LOCALAPPDATA 'AISC\data'
$workspace = Join-Path $env:RUNNER_TEMP 'aisc-upgrade-project'
$app = $null

function Record-Step([string]$name) {
    $script:result.steps += [ordered]@{ name = $name; status = 'PASS' }
    Write-Host "PASS: $name"
}
function Install-Package([string]$path) {
    $process = Start-Process -FilePath $path -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installer exited with $($process.ExitCode)" }
}
function Check-Files([hashtable]$expected) {
    foreach ($path in $expected.Keys) {
        if (-not (Test-Path -LiteralPath $path)) { throw "User file missing: $path" }
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $expected[$path]) {
            throw "User file changed: $path"
        }
    }
}

try {
    $baseline = Join-Path $env:RUNNER_TEMP 'AISC-Workbench-2.1.18-setup.exe'
    Invoke-WebRequest -Uri 'https://github.com/Wifabric/AISC/releases/download/v2.1.18/AISC-Workbench-2.1.18-setup.exe' -OutFile $baseline
    # GitHub release asset digest, verified when the upgrade test was added.
    $digest = 'b9a578c34720577182b5fc2088e7bf579dbee93e430bca7b1776faffef479315'
    if ((Get-FileHash -LiteralPath $baseline -Algorithm SHA256).Hash -ine $digest) {
        throw 'Official 2.1.18 installer SHA-256 does not match.'
    }
    Install-Package $baseline
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AISC Workbench'
    if ((Get-ItemProperty -LiteralPath $key).DisplayVersion -ne '2.1.18') {
        throw 'The installed baseline is not official 2.1.18.'
    }
    Record-Step 'Install official 2.1.18'

    $config = Join-Path $dataRoot 'config'
    New-Item -ItemType Directory -Force -Path $config, $workspace | Out-Null
    $settingsFile = Join-Path $config 'settings.json'
    $historyFile = Join-Path $config 'history.json'
    @{ schema_version=1; revision=7; aisc_cli_path=$null; ui=@{language='en-US'; theme='dark'; font_scale=1.1}; upgrade_probe='retain-settings' } |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $settingsFile -Encoding utf8
    @{ schema_version=1; revision=3; workspaces=@(@{path=$workspace; pinned=$true; last_agent='codex'; last_used_at='2026-11-19T00:00:00Z'}) } |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $historyFile -Encoding utf8
    $projectFile = Join-Path $workspace 'keep-project.txt'
    Set-Content -LiteralPath $projectFile -Value 'user project content: keep through upgrade and uninstall' -Encoding utf8
    # Use the CLI resolver to locate the real per-workspace directory.
    $env:AISC_UPGRADE_WORKSPACE = $workspace
    $resolved = python -c 'import os; from aisc.application.data_root import DataRootResolver; print(DataRootResolver().resolve(os.environ["AISC_UPGRADE_WORKSPACE"]).workspace_dir)'
    if ($LASTEXITCODE -ne 0) { throw 'Failed to resolve workspace data location.' }
    $sessionDir = Join-Path $resolved.Trim() 'codex\sessions\2026\11\19'
    New-Item -ItemType Directory -Force -Path $sessionDir | Out-Null
    $sessionId = '11191119-1111-4111-8111-000000000001'
    $sessionFile = Join-Path $sessionDir "rollout-2026-11-19T00-00-00-$sessionId.jsonl"
    $transcript = @(
        @{type='session_meta'; payload=@{id=$sessionId; cwd=$workspace}},
        @{type='response_item'; timestamp='2026-11-19T00:00:00Z'; payload=@{type='message'; role='user'; content=@(@{type='input_text'; text='upgrade retention proof'})}}
    ) | ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 8 }
    [IO.File]::WriteAllLines($sessionFile, [string[]]$transcript, [Text.UTF8Encoding]::new($false))
    $expected = @{}
    foreach ($path in @($settingsFile, $historyFile, $projectFile, $sessionFile)) {
        $expected[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    }
    Install-Package $candidate
    Check-Files $expected
    $version = (Get-ItemProperty -LiteralPath $key).DisplayVersion
    if ($version -ne $ExpectedVersion) { throw "Unexpected installed version: $version (expected $ExpectedVersion)." }
    $result.installedVersion = $version
    Record-Step 'Cross-version upgrade preserves settings, history, native transcript and project bytes'

    $cli = Join-Path $appDir 'aisc.exe'
    & $cli version --format json
    if ($LASTEXITCODE -ne 0) { throw 'Installed CLI cannot start.' }
    $conversation = & $cli conversation read --workspace $workspace --agent codex --conversation-id $sessionId --format json
    if ($LASTEXITCODE -ne 0 -or ($conversation -join '') -notlike '*upgrade retention proof*') {
        throw 'The upgraded CLI could not read the preserved native conversation.'
    }
    Record-Step 'Installed CLI reads preserved native transcript'

    $exe = Get-ChildItem -LiteralPath $appDir -Filter '*.exe' | Where-Object { $_.Name -notin @('aisc.exe','uninstall.exe') } | Select-Object -First 1
    if (-not $exe) { throw 'Installed Workbench executable missing.' }
    $app = Start-Process -FilePath $exe.FullName -ArgumentList @('--aisc-cli', ('"' + $cli + '"')) -WindowStyle Hidden -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    do {
        Start-Sleep -Milliseconds 500
        $app.Refresh()
        if ($app.HasExited) { throw "Installed Workbench exited: $($app.ExitCode)" }
    } until ($app.MainWindowHandle -ne 0 -or [DateTime]::UtcNow -gt $deadline)
    if ($app.MainWindowHandle -eq 0) { throw 'Installed Workbench did not create a native window.' }
    Record-Step 'Installed Workbench creates a native window (launch smoke, not GUI acceptance)'
    $app.CloseMainWindow() | Out-Null
    if (-not $app.WaitForExit(10000)) { Stop-Process -Id $app.Id -Force }
    $app = $null
    # Workbench may legitimately update revision, CLI discovery and history on
    # startup. Check preserved semantics after launch, exact bytes before launch.
    $settings = Get-Content -LiteralPath $settingsFile -Raw | ConvertFrom-Json
    if ($settings.ui.theme -ne 'dark' -or $settings.upgrade_probe -ne 'retain-settings') { throw 'Settings lost after launch.' }
    if (-not ((Get-Content -LiteralPath $historyFile -Raw | ConvertFrom-Json).workspaces | Where-Object { $_.path -eq $workspace })) { throw 'Recent workspace lost after launch.' }
    Check-Files @{ $projectFile=$expected[$projectFile]; $sessionFile=$expected[$sessionFile] }
    Record-Step 'Settings and recent workspace remain usable after launch'

    $uninstaller = Join-Path $appDir 'uninstall.exe'
    $remove = Start-Process -FilePath $uninstaller -ArgumentList '/S' -WindowStyle Hidden -Wait -PassThru
    if ($remove.ExitCode -ne 0) { throw "Uninstall failed: $($remove.ExitCode)" }
    foreach ($path in @($settingsFile,$historyFile,$projectFile,$sessionFile)) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Retained file missing after uninstall: $path" }
    }
    Check-Files @{ $projectFile=$expected[$projectFile]; $sessionFile=$expected[$sessionFile] }
    if (Test-Path -LiteralPath (Join-Path $appDir 'aisc-bundle')) { throw 'Installed bundle remains after uninstall.' }
    Record-Step 'Silent uninstall retains real user-state samples and removes application bundle'
    $result.status = 'PASS'
} catch {
    $result.status = 'FAIL'
    $result.error = $_.Exception.Message
    throw
} finally {
    if ($app -and -not $app.HasExited) { Stop-Process -Id $app.Id -Force }
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
}
