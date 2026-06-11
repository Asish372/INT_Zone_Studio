$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Write-Host "Fetching ODA File Converter for bundled DWG support..."
& (Join-Path $PSScriptRoot "fetch_oda_converter.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "ODA File Converter fetch failed"
}

Write-Host "Building bundled detection engine with PyInstaller..."
Push-Location $repoRoot
try {
    & $python -m pip install pyinstaller --quiet
    & $python -m PyInstaller `
        (Join-Path $repoRoot "desktop\engine_sidecar\int_zone_engine.spec") `
        --noconfirm `
        --distpath (Join-Path $repoRoot "desktop\studio\src-tauri\resources\dist") `
        --workpath (Join-Path $repoRoot "build\pyinstaller-engine")

    $engineSrc = Join-Path $repoRoot "desktop\studio\src-tauri\resources\dist\int-zone-engine"
    $engineDst = Join-Path $repoRoot "desktop\studio\src-tauri\resources\engine\int-zone-engine"
    if (Test-Path $engineDst) { Remove-Item $engineDst -Recurse -Force }
    New-Item -ItemType Directory -Path (Split-Path $engineDst) -Force | Out-Null
    Move-Item $engineSrc $engineDst

    $pilotFiles = @("PILOT_FEEDBACK.md", "pilot_metrics_template.csv", "config.yaml")
    foreach ($name in $pilotFiles) {
        $src = Join-Path $repoRoot $name
        if (Test-Path $src) {
            Copy-Item $src (Join-Path $repoRoot "desktop\studio\src-tauri\resources\$name") -Force
        }
    }

    Write-Host "Verifying standalone bundle (engine + ODA)..."
    & (Join-Path $PSScriptRoot "verify_standalone_bundle.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Standalone bundle verification failed"
    }

    Write-Host "Engine bundle ready at desktop/studio/src-tauri/resources/engine/int-zone-engine"
}
finally {
    Pop-Location
}
