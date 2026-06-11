#!/usr/bin/env python3
"""Verify release package is ready for Round 1 engineers."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE = PROJECT_ROOT / "release" / "INT-Zone-Studio-Pilot-v1"

REQUIRED = [
    "TESTER_SETUP.txt",
    "PILOT_V1.md",
    "PILOT_FEEDBACK.md",
    "pilot_metrics_template.csv",
    "requirements.txt",
    "scripts/run_polygon_workspace.py",
    "Setup-Dependencies.bat",
]

OPTIONAL_EXE = "INT Zone Studio.exe"


def sync_pilot_assets() -> None:
    for name in ("pilot_metrics_template.csv", "PILOT_FEEDBACK.md"):
        src = PROJECT_ROOT / name
        dst = RELEASE / name
        if src.is_file():
            shutil.copy2(src, dst)


def main() -> int:
    print("=== Pilot Phase C — Release package prep ===\n")
    missing = [p for p in REQUIRED if not (RELEASE / p).is_file()]
    if missing:
        for m in missing:
            print(f"  MISSING: {m}")
        return 1

    sync_pilot_assets()

    has_exe = (RELEASE / OPTIONAL_EXE).is_file()
    print(f"  Release folder: {RELEASE}")
    print(f"  Required files: {len(REQUIRED)}/{len(REQUIRED)} OK")
    print(f"  Executable: {'OK' if has_exe else 'MISSING (dev testers use npm run dev + sidecar)'}")

    checklist = RELEASE / "PILOT_HANDOFF_CHECKLIST.txt"
    checklist.write_text(
        """INT Zone Studio — Round 1 Engineer Handoff
==========================================

Give engineers the ENTIRE folder:
  release/INT-Zone-Studio-Pilot-v1/

Before first session:
  1. Run Setup-Dependencies.bat OR: python -m pip install -r requirements.txt
  2. Double-click INT Zone Studio.exe (or dev: sidecar + npm run dev)
  3. Copy pilot_metrics_template.csv — one row per drawing

Briefing (15 min):
  - Workflow: Import → Detect → Review → Gaps → Zones → Save → Reopen → Export Project Package
  - Open Project ≠ Import Drawing
  - Save = type full path
  - Primary signal: gap list → recover → useful?

Per drawing:
  - Fill one metrics row
  - Log confusion in pilot_feedback_log.csv (copy to engineer folder)

Round 1 target: 3–5 drawings, 1–2 engineers
""",
        encoding="utf-8",
    )
    print(f"  Handoff checklist: {checklist}")

    report = PROJECT_ROOT / "output" / "pilot_release_prep.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "release_path": str(RELEASE),
                "required_ok": True,
                "has_exe": has_exe,
                "handoff_checklist": str(checklist),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nPASS — release package ready\nReport: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
