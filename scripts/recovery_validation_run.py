#!/usr/bin/env python3
"""Validate gap → recovery on recovery_validation_grid.dxf."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DXF = PROJECT_ROOT / "output" / "qa_fixtures" / "recovery_validation_S111_J.dxf"
META = PROJECT_ROOT / "output" / "qa_fixtures" / "recovery_validation_S111_J.json"
ENGINE = "http://127.0.0.1:8765"


def main() -> int:
    if not DXF.is_file():
        print(f"Missing {DXF} — run scripts/generate_recovery_validation_drawing.py first")
        return 1

    result = {
        "drawing": DXF.name,
        "passed": False,
        "import_count": 0,
        "recoverable_gaps": 0,
        "recovery_attempted": False,
        "recovery_success": False,
        "errors": [],
    }

    client = httpx.Client(timeout=120.0, base_url=ENGINE)
    try:
        client.get("/health").raise_for_status()
        sid = client.post("/session").json()["session_id"]
        headers = {"X-Session-Id": sid}

        with DXF.open("rb") as fh:
            r = client.post(
                "/upload",
                headers=headers,
                files={"file": (DXF.name, fh, "application/octet-stream")},
            )
        r.raise_for_status()
        upload = r.json()
        result["import_count"] = int(upload["counts"]["total"])

        r = client.post("/validate", headers=headers)
        r.raise_for_status()
        validation = r.json()["validation"]
        gaps = validation.get("suspected_gaps") or []
        gap_summary = validation.get("gap_summary") or {}
        result["suspected_gaps"] = gap_summary.get("total", len(gaps))
        recoverable = [g for g in gaps if g.get("recoverable")]
        result["recoverable_gaps"] = len(recoverable)

        if not recoverable:
            meta = json.loads(META.read_text(encoding="utf-8")) if META.is_file() else {}
            seeds = meta.get("verified_seeds") or []
            if seeds:
                sx, sy = seeds[0]["x"], seeds[0]["y"]
                result["recovery_attempted"] = True
                rr = client.post(
                    "/recover",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"x": sx, "y": sy},
                )
                if rr.status_code == 200:
                    result["recovery_success"] = True
                    result["after_recovery_count"] = int(rr.json()["counts"]["total"])
                    result["recovered_via"] = seeds[0].get("id", "verified_seed")
                else:
                    result["errors"].append(f"Verified seed recovery failed: {rr.text[:200]}")
            else:
                result["errors"].append("No recoverable gaps and no verified seeds in meta")
        else:
            gap = recoverable[0]
            sx, sy = gap["seed_point"]
            result["recovery_attempted"] = True
            rr = client.post(
                "/recover",
                headers={**headers, "Content-Type": "application/json"},
                json={"x": sx, "y": sy},
            )
            if rr.status_code == 200:
                result["recovery_success"] = True
                result["recovered_polygon_id"] = rr.json().get("polygon", {}).get("id")
                result["after_recovery_count"] = int(rr.json()["counts"]["total"])
            else:
                result["errors"].append(f"Gap recovery failed: {rr.text[:200]}")

        result["passed"] = (
            result["import_count"] >= 1
            and result["recovery_success"]
            and result.get("after_recovery_count", 0) > result["import_count"]
        )

        out = PROJECT_ROOT / "output" / "recovery_validation_run.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        print(f"\nReport: {out}")
        return 0 if result["passed"] else 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
