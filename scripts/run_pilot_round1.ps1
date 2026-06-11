# INT Zone Studio — Round 1 pilot automation (founder prep + evaluation)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "Phase A: Layout verification"
python scripts/pilot_verify_layout.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nPhase B: Founder dry-run (API)"
python scripts/pilot_founder_dry_run.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nPhase C: Release package prep"
python scripts/pilot_prep_release.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nPhase D: Exit criteria tally"
python scripts/pilot_evaluate_round1.py
exit $LASTEXITCODE
