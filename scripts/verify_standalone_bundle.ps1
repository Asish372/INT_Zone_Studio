$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$engineExe = Join-Path $repoRoot "desktop\studio\src-tauri\resources\engine\int-zone-engine\int-zone-engine.exe"
$odaExe = Join-Path $repoRoot "desktop\studio\src-tauri\resources\oda\ODAFileConverter.exe"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

if (-not (Test-Path $engineExe)) {
    throw "Engine bundle missing: $engineExe"
}
if (-not (Test-Path $odaExe)) {
    throw "ODA bundle missing: $odaExe (required for DWG on client PCs)"
}

Write-Host "Verifying engine health..."
& $python (Join-Path $repoRoot "scripts\verify_engine_bundle.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Verifying ODA converter launches..."
$p = Start-Process -FilePath $odaExe -WorkingDirectory (Split-Path $odaExe) -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2
if ($p.HasExited -and $p.ExitCode -ne 0) {
    throw "ODAFileConverter exited with code $($p.ExitCode)"
}
if (-not $p.HasExited) {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "OK: standalone bundle ready (engine + DWG converter)"
