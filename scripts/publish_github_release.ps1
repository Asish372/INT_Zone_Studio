# Publish INT Zone Studio pilot release to GitHub (run after: gh auth login)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$tag = "v0.1.0-pilot.1"
$setup = Join-Path $Root "release\INT Zone Studio Standalone Setup 0.1.0-pilot.1.exe"
$portable = Join-Path $Root "release\INT-Zone-Studio-Pilot-v1.zip"
$notes = Join-Path $Root "RELEASE_NOTES_PILOT_V1.md"

foreach ($f in @($setup, $portable, $notes)) {
    if (-not (Test-Path $f)) { throw "Missing file: $f" }
}

gh release view $tag --repo Asish372/INT_Zone_Studio 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Release $tag already exists. Uploading assets..."
    gh release upload $tag $setup --repo Asish372/INT_Zone_Studio --clobber `
        --name "INT-Zone-Studio-Setup-0.1.0-pilot.1.exe"
    gh release upload $tag $portable --repo Asish372/INT_Zone_Studio --clobber `
        --name "INT-Zone-Studio-Pilot-v1-portable.zip"
} else {
    gh release create $tag `
        --repo Asish372/INT_Zone_Studio `
        --title "INT Zone Studio v0.1.0-pilot.1 — Pilot Evaluation Build" `
        --notes-file $notes `
        "$setup#INT-Zone-Studio-Setup-0.1.0-pilot.1.exe" `
        "$portable#INT-Zone-Studio-Pilot-v1-portable.zip"
}

Write-Host "Done: https://github.com/Asish372/INT_Zone_Studio/releases/tag/$tag"
