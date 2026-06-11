$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$odaDest = Join-Path $repoRoot "desktop\studio\src-tauri\resources\oda"
$odaExe = Join-Path $odaDest "ODAFileConverter.exe"

if (Test-Path $odaExe) {
    Write-Host "ODA File Converter already present at $odaDest"
    exit 0
}

$downloadDir = Join-Path $repoRoot "build\oda_download"
$extractRoot = Join-Path $repoRoot "build\oda_extract"
New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null

$msiPath = Get-ChildItem -Path $downloadDir -Filter "ODAFileConverter*.msi" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $msiPath) {
    Write-Host "Downloading ODA File Converter via winget (required for DWG support)..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "winget not found. Install ODA File Converter manually or place ODAFileConverter*.msi in build/oda_download/"
    }
    & winget download --id OpenDesignAlliance.ODAFileConverter --architecture x64 --download-directory $downloadDir --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "winget download failed with exit code $LASTEXITCODE"
    }
    $msiPath = Get-ChildItem -Path $downloadDir -Filter "ODAFileConverter*.msi" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

if (-not $msiPath) {
    throw "ODAFileConverter MSI not found in $downloadDir"
}

Write-Host "Using MSI: $($msiPath.FullName)"

if (Test-Path $extractRoot) {
    Remove-Item $extractRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null

Write-Host "Extracting ODA File Converter..."
$p = Start-Process -FilePath "msiexec.exe" -ArgumentList @(
    "/a", "`"$($msiPath.FullName)`"", "TARGETDIR=`"$extractRoot`"", "/qn"
) -Wait -PassThru
if ($p.ExitCode -ne 0) {
    throw "msiexec administrative install failed with exit code $($p.ExitCode)"
}

$found = Get-ChildItem -Path $extractRoot -Recurse -Filter "ODAFileConverter.exe" -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $found) {
    throw "ODAFileConverter.exe not found after MSI extract"
}

$sourceDir = $found.Directory.FullName
if (Test-Path $odaDest) {
    Remove-Item $odaDest -Recurse -Force
}
New-Item -ItemType Directory -Path $odaDest -Force | Out-Null
Get-ChildItem -Path $sourceDir -Exclude "*.msi" | Copy-Item -Destination $odaDest -Recurse -Force

if (-not (Test-Path $odaExe)) {
    throw "Failed to stage ODAFileConverter.exe to $odaDest"
}

@"
ODA File Converter is bundled for DWG to DXF conversion.
Copyright Open Design Alliance. https://www.opendesign.com/
"@ | Set-Content -Path (Join-Path $odaDest "ODA_NOTICE.txt") -Encoding UTF8

Write-Host "ODA File Converter ready at $odaDest"
