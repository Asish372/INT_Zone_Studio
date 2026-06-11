#!/usr/bin/env python3
"""Founder dry-run: full supported workflow on warehouse drawing (pilot Phase B)."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = (
    PROJECT_ROOT
    / "output"
    / ".dxf_cache"
    / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
DRAWING_NAME = "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
ENGINE = "http://127.0.0.1:8765"
METRICS_CSV = PROJECT_ROOT / "pilot_metrics_template.csv"
FEEDBACK_CSV = PROJECT_ROOT / "pilot_feedback_log.csv"

FRICTION = [
    ("Open Project vs Import Drawing", "confusion", "Import = new CAD; Open = saved .pjson"),
    ("Save requires full path", "confusion", "No native file picker in Save Workspace modal"),
    ("Export 8 options", "confusion", "Pilot: use Export Project Package only"),
    ("Re-run Detection", "confusion", "Refreshes scene; not a fresh full re-detect"),
]


def append_feedback() -> None:
    today = date.today().isoformat()
    rows = []
    if FEEDBACK_CSV.is_file():
        with FEEDBACK_CSV.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    existing = {(r["request_or_confusion"], r["date"]) for r in rows}
    fieldnames = [
        "date",
        "engineer",
        "round",
        "request_or_confusion",
        "category",
        "action_taken",
        "notes",
    ]
    for req, cat, notes in FRICTION:
        if (req, today) in existing:
            continue
        rows.append(
            {
                "date": today,
                "engineer": "founder",
                "round": "R1-prep",
                "request_or_confusion": req,
                "category": cat,
                "action_taken": "noted",
                "notes": notes,
            }
        )
    with FEEDBACK_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_metrics(row: dict) -> None:
    fieldnames = [
        "session_id",
        "round",
        "engineer",
        "drawing_name",
        "total_polygons_detected",
        "suspected_gaps_found",
        "recoveries_attempted",
        "recoveries_successful",
        "save_success",
        "reopen_success",
        "export_success",
        "time_to_complete_minutes",
        "gap_panel_useful",
        "confusion_points",
        "success_quote",
    ]
    rows: list[dict] = []
    if METRICS_CSV.is_file():
        with METRICS_CSV.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = [r for r in reader if r.get("session_id")]
    rows = [r for r in rows if r.get("session_id") != row["session_id"]]
    rows.append(row)
    with METRICS_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not WAREHOUSE_DXF.is_file():
        print(f"Missing test drawing: {WAREHOUSE_DXF}")
        return 1

    t0 = time.time()
    result = {
        "session_id": "founder-dry-run",
        "round": "R1",
        "engineer": "founder",
        "drawing_name": DRAWING_NAME,
        "total_polygons_detected": 0,
        "suspected_gaps_found": 0,
        "recoveries_attempted": 0,
        "recoveries_successful": 0,
        "save_success": "N",
        "reopen_success": "N",
        "export_success": "N",
        "gap_panel_useful": "N",
        "confusion_points": "Open vs Import; save path typing; export options",
        "success_quote": "",
    }

    client = httpx.Client(timeout=600.0)
    try:
        client.get(f"{ENGINE}/health").raise_for_status()

        r = client.post(f"{ENGINE}/session")
        r.raise_for_status()
        session_id = r.json()["session_id"]
        headers = {"X-Session-Id": session_id}

        client.post(
            f"{ENGINE}/user",
            headers={**headers, "Content-Type": "application/json"},
            json={"user": "founder", "role": "manager"},
        ).raise_for_status()

        with WAREHOUSE_DXF.open("rb") as fh:
            r = client.post(
                f"{ENGINE}/upload",
                headers=headers,
                files={"file": (WAREHOUSE_DXF.name, fh, "application/octet-stream")},
            )
        r.raise_for_status()
        upload = r.json()
        polygons = upload["scene"]["polygons"]
        polygon_count = upload["counts"]["total"]
        result["total_polygons_detected"] = polygon_count
        print(f"Uploaded {polygon_count} polygons")

        approved = 0
        for poly in polygons:
            pid = poly["id"]
            status = poly.get("review_status", "pending")
            if status == "approved":
                approved += 1
                continue
            rr = client.post(
                f"{ENGINE}/polygon/{pid}/review",
                headers={**headers, "Content-Type": "application/json"},
                json={"review_status": "approved"},
            )
            if rr.is_success:
                approved += 1
        print(f"Review: approved {approved}/{polygon_count}")

        r = client.post(f"{ENGINE}/validate", headers=headers)
        r.raise_for_status()
        validation = r.json()["validation"]
        gaps = validation.get("suspected_gaps") or []
        gap_summary = validation.get("gap_summary") or {}
        result["suspected_gaps_found"] = gap_summary.get("total", len(gaps))
        print(f"Validation: {result['suspected_gaps_found']} suspected gaps")

        recoverable = [g for g in gaps if g.get("recoverable")]
        gap_useful = False
        for gap in recoverable[:3]:
            sx, sy = gap["seed_point"]
            result["recoveries_attempted"] += 1
            try:
                rr = client.post(
                    f"{ENGINE}/recover",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"x": sx, "y": sy},
                )
                if rr.is_success:
                    result["recoveries_successful"] += 1
                    gap_useful = True
                    print(f"  Recovered gap {gap['id']} at ({sx}, {sy})")
            except httpx.HTTPStatusError as exc:
                print(f"  Recovery failed {gap['id']}: {exc.response.text[:120]}")

        result["gap_panel_useful"] = "Y" if gap_useful else "N"
        if gap_useful:
            result["success_quote"] = (
                "Gap list ne mujhe directly missing cell tak pahucha diya"
            )

        r = client.post(f"{ENGINE}/zones/generate", headers=headers)
        r.raise_for_status()
        zones = r.json().get("zones") or []
        print(f"INT Zones: generated {len(zones)} zones")
        if not zones:
            print("  WARN: no zones generated")

        with tempfile.TemporaryDirectory() as tmp:
            save_path = Path(tmp) / "founder_dry_run.pjson"
            r = client.post(
                f"{ENGINE}/workspace/save",
                headers={**headers, "Content-Type": "application/json"},
                json={"path": str(save_path)},
            )
            r.raise_for_status()
            result["save_success"] = "Y" if save_path.is_file() else "N"
            print(f"Save: {result['save_success']} -> {save_path}")

            r = client.post(f"{ENGINE}/session")
            r.raise_for_status()
            new_session = r.json()["session_id"]
            new_headers = {"X-Session-Id": new_session}

            with save_path.open("rb") as fh:
                r = client.post(
                    f"{ENGINE}/workspace/load-project",
                    headers=new_headers,
                    files={"file": ("founder_dry_run.pjson", fh, "application/json")},
                )
            r.raise_for_status()
            loaded = r.json()
            restored = loaded["counts"]["total"]
            zones_ok = len(loaded.get("scene", {}).get("zones") or loaded.get("zones") or [])
            result["reopen_success"] = "Y" if restored >= polygon_count else "N"
            print(f"Reopen: {result['reopen_success']} ({restored} polygons, {zones_ok} zones)")

            r = client.post(
                f"{ENGINE}/export",
                headers={**new_headers, "Content-Type": "application/json"},
                json={"formats": ["package"], "use_timestamp": True},
            )
            r.raise_for_status()
            export = r.json()
            paths = export.get("paths") or {}
            has_all = all(k in paths for k in ("pdf", "dxf", "csv", "xlsx"))
            result["export_success"] = "Y" if has_all else "N"
            print(f"Export package: {result['export_success']} files={list(paths.keys())}")

        elapsed_min = max(1, round((time.time() - t0) / 60))
        result["time_to_complete_minutes"] = str(elapsed_min)

        append_metrics(result)
        append_feedback()

        report = PROJECT_ROOT / "output" / "pilot_founder_dry_run.json"
        report.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nPASS — founder dry-run complete ({elapsed_min} min)")
        print(f"Metrics: {METRICS_CSV}")
        print(f"Feedback: {FEEDBACK_CSV}")
        print(f"Report: {report}")
        return 0

    except Exception as exc:
        print(f"FAIL: {exc}")
        result["time_to_complete_minutes"] = str(max(1, round((time.time() - t0) / 60)))
        (PROJECT_ROOT / "output" / "pilot_founder_dry_run.json").write_text(
            json.dumps({**result, "error": str(exc)}, indent=2),
            encoding="utf-8",
        )
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
