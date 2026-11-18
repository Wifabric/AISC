# Build the AISC Workbench Windows installer (NSIS only, skips MSI).
#
#   online  (default): current lightweight setup — Docker installs via winget
#           at first-run onboarding.
#   offline: bundles the latest Docker Desktop installer (scripts/fetch-docker-
#           installer.ps1) into the setup exe; the Workbench installs Docker
#           from the local bundle with no network (like mihomo). The output is
#           suffixed `-offline-setup.exe`.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/build-installer.ps1 -Mode online
#   powershell -ExecutionPolicy Bypass -File scripts/build-installer.ps1 -Mode offline -CopyToDownloads
#   .\scripts\build-installer.ps1 -SigningConfig C:\release\tauri.signing.json
# SigningConfig is a Tauri config overlay with bundle.windows.certificateThumbprint
# or bundle.windows.signCommand for the publisher's signing service.

param(
    [ValidateSet("online", "offline")]
    [string]$Mode = "online",
    [switch]$CopyToDownloads,
    [string]$SigningConfig
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $MyInvocation.MyCommand.Path -Parent | Split-Path -Parent
$Wb = Join-Path $Root "workbench"

$buildArgs = @("run", "tauri", "build", "--", "--bundles", "nsis")
if ($Mode -eq "offline") {
    $buildArgs += @("--config", "src-tauri/tauri.offline.conf.json")
}
if ($PSBoundParameters.ContainsKey("SigningConfig")) {
    $signingFile = Get-Item -LiteralPath $SigningConfig -ErrorAction Stop
    $signing = (Get-Content -Raw -LiteralPath $signingFile.FullName | ConvertFrom-Json).bundle.windows
    if (-not ($signing.certificateThumbprint -or $signing.signCommand)) {
        throw "SigningConfig must specify bundle.windows.certificateThumbprint or signCommand."
    }
    $buildArgs += @("--config", $signingFile.FullName)
}

if ($Mode -eq "offline") {
    Write-Host "== offline mode: fetching Docker Desktop installer =="
    & (Join-Path $Root "scripts\fetch-docker-installer.ps1")
    if ($LASTEXITCODE -ne 0) { throw "fetch-docker-installer failed (exit $LASTEXITCODE)" }
}

Push-Location $Wb
try {
    Write-Host "== tauri build (bundles=nsis, mode=$Mode) =="
    $buildStartedUtc = [DateTime]::UtcNow
    npm @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "tauri build failed (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}

$bundle = Join-Path $Wb "src-tauri\target\release\bundle\nsis"
$setup = Get-ChildItem -Path $bundle -Filter "*-setup.exe" -File |
    Where-Object {
        $_.Name -notlike "*-offline-setup.exe" -and
        (-not $SigningConfig -or $_.LastWriteTimeUtc -ge $buildStartedUtc)
    } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $setup) { throw "No *-setup.exe found under $bundle" }

if ($SigningConfig) {
    $signature = Get-AuthenticodeSignature -LiteralPath $setup.FullName
    if ($signature.Status -ne 'Valid') {
        throw "Installer signature verification failed for $($setup.Name): $($signature.Status)"
    }
    if ($signing.certificateThumbprint -and $signature.SignerCertificate.Thumbprint -ne $signing.certificateThumbprint) {
        throw "Installer was signed by a different certificate than SigningConfig specifies."
    }
}

if ($Mode -eq "offline") {
    $dest = $setup.FullName -replace "-setup\.exe$", "-offline-setup.exe"
    Copy-Item $setup.FullName $dest -Force
    Write-Host "== offline bundle: $dest =="
    $setup = Get-Item $dest
} else {
    Write-Host "== online bundle: $($setup.FullName) =="
}

if ($CopyToDownloads) {
    $dl = Join-Path $env:USERPROFILE "Downloads"
    Copy-Item $setup.FullName $dl -Force
    Write-Host "== copied to $dl\$($setup.Name) =="
}
