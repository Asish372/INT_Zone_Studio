#!/usr/bin/env python3
"""Prepare recovery-validation fixture for Pilot Round 2 (gap → recovery E2E).

Uses S111_J.dxf — verified via engine API:
  import ~403 polygons, 2 recoverable suspected gaps, seed recovery succeeds.
Synthetic mini-grid DXFs do not reliably produce recoverable gaps through the
full import pipeline (gap auto-close / layer rules); kept as optional negative case.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "output" / "qa_fixtures"
PRIMARY_SOURCE = PROJECT_ROOT / "output" / ".dxf_cache" / "S111_J.dxf"
FALLBACK_SOURCE = PROJECT_ROOT / "input" / "S111_J.dwg"
OUT_DXF = OUT_DIR / "recovery_validation_S111_J.dxf"
META_JSON = OUT_DIR / "recovery_validation_S111_J.json"

VERIFIED_SEEDS = [
    {"id": "auto-034", "x": 116395.955, "y": 162925.1, "label_hint": "gap-above_threshold_close"},
    {"id": "auto-036", "x": 116495.955, "y": 162925.1, "label_hint": "gap-large_gap_manual_review"},
]


def build_fixture() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = PRIMARY_SOURCE if PRIMARY_SOURCE.is_file() else FALLBACK_SOURCE
    if not source.is_file():
        print(f"Missing S111_J source. Expected {PRIMARY_SOURCE} or {FALLBACK_SOURCE}")
        sys.exit(1)

    if source.suffix.lower() == ".dxf":
        shutil.copy2(source, OUT_DXF)
    else:
        print("Only cached DXF copy supported in this script; convert S111_J.dwg first.")
        sys.exit(1)

    meta = {
        "file": OUT_DXF.name,
        "source_drawing": "S111_J",
        "purpose": "Pilot Round 2 gap → recovery validation (production drawing)",
        "verified_seeds": VERIFIED_SEEDS,
        "expected_import_count_approx": 403,
        "expected_recoverable_gaps_min": 1,
        "validation_notes": (
            "Run Validate after import; click first recoverable gap or use seed auto-034. "
            "Warehouse drawing has 0 recoverable gaps after scoped detection — use this file instead."
        ),
    }
    META_JSON.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_DXF}")
    print(f"Wrote {META_JSON}")


if __name__ == "__main__":
    build_fixture()
    sys.exit(0)
