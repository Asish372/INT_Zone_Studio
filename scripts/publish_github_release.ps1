# Publish INT Zone Studio pilot release to GitHub.
# Prerequisites: gh auth login, installer staged in release/
param(
    [string]$Version = "0.1.0-pilot.1",
    [string]$Tag = "v0.1.0-pilot.1"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$releaseDir = Join-Path $repoRoot "release"
$installerName = "INT Zone Studio Standalone Setup $Version.exe"
$installerPath = Join-Path $releaseDir $installerName

if (-not (Test-Path $installerPath)) {
    Write-Host "Installer not found. Staging from Tauri build..."
    & (Join-Path $repoRoot "scripts\stage_release_installer.ps1")
}

if (-not (Test-Path $installerPath)) {
    throw "Missing installer: $installerPath`nRun: cd desktop/studio && npm run tauri:build"
}

$notesFile = Join-Path $repoRoot ".github\release_template.md"
$checksum = (Get-FileHash $installerPath -Algorithm SHA256).Hash
$checksumFile = Join-Path $releaseDir "SHA256SUMS.txt"
@(
    "$checksum  $installerName"
) | Set-Content $checksumFile -Encoding UTF8

Write-Host "Publishing $Tag to GitHub..."
gh release view $Tag 2>$null
if ($LASTEXITCODE -eq 0) {
    gh release upload $Tag $installerPath $checksumFile --clobber
    Write-Host "Updated existing release assets."
} else {
    gh release create $Tag `
        $installerPath `
        $checksumFile `
        --title "INT Zone Studio · Pilot Evaluation Build v1 ($Version)" `
        --notes-file $notesFile `
        --latest
    Write-Host "Created release $Tag"
}

Write-Host "Done: https://github.com/Asish372/INT_Zone_Studio/releases/tag/$Tag"
