#!/usr/bin/env python3
"""Full civil-engineer workflow via engine API: Import → Detect refresh → Manual polygon → Save → Reopen."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = (
    PROJECT_ROOT
    / "output"
    / ".dxf_cache"
    / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
ENGINE = os.environ.get("INT_ZONE_ENGINE", "http://127.0.0.1:8765")
ENV_LABEL = os.environ.get("INT_ZONE_ENV", "dev_api")


def _step(name: str) -> None:
    print(f"\n=== {name} ===")


def _polygon_bbox(polygons: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    minx = miny = 1e18
    maxx = maxy = -1e18
    for poly in polygons:
        for pt in poly.get("ring") or []:
            x, y = float(pt[0]), float(pt[1])
            minx, miny = min(minx, x), min(miny, y)
            maxx, maxy = max(maxx, x), max(maxy, y)
    return minx, miny, maxx, maxy


def _empty_manual_ring(polygons: list[dict[str, Any]], size: float = 5000.0) -> list[list[float]]:
    minx, miny, maxx, maxy = _polygon_bbox(polygons)
    x0 = maxx + 10_000.0
    y0 = miny + 10_000.0
    return [
        [x0, y0],
        [x0 + size, y0],
        [x0 + size, y0 + size],
        [x0, y0 + size],
    ]


def run_workflow(client: httpx.Client, environment: str) -> dict[str, Any]:
    results: dict[str, Any] = {
        "environment": environment,
        "steps": {},
        "passed": True,
        "errors": [],
        "counts": {},
    }

    def record(step: str, ok: bool, detail: str, **extra: Any) -> None:
        results["steps"][step] = {"ok": ok, "detail": detail, **extra}
        if not ok:
            results["passed"] = False
            results["errors"].append(f"{step}: {detail}")

    if not WAREHOUSE_DXF.is_file():
        record("preflight", False, f"Missing drawing: {WAREHOUSE_DXF}")
        return results

    try:
        _step(f"{environment} — Preflight")
        r = client.get(f"{ENGINE}/health")
        r.raise_for_status()
        record("preflight", True, "Engine health OK")

        _step(f"{environment} — Import")
        r = client.post(f"{ENGINE}/session")
        r.raise_for_status()
        session_id = r.json()["session_id"]
        with WAREHOUSE_DXF.open("rb") as fh:
            r = client.post(
                f"{ENGINE}/upload",
                headers={"X-Session-Id": session_id},
                files={"file": (WAREHOUSE_DXF.name, fh, "application/octet-stream")},
            )
        r.raise_for_status()
        upload = r.json()
        import_count = int(upload["counts"]["total"])
        results["counts"]["after_import"] = import_count
        record(
            "import",
            import_count > 0,
            f"{upload['source_file']} — {import_count} polygons in {r.elapsed.total_seconds():.1f}s",
        )

        _step(f"{environment} — Detect refresh (Run Detection button behavior)")
        r = client.get(f"{ENGINE}/scene", headers={"X-Session-Id": session_id})
        r.raise_for_status()
        refresh = r.json()
        refresh_count = int(refresh["summary"]["counts"]["total"])
        results["counts"]["after_detect_refresh"] = refresh_count
        record(
            "detect_refresh",
            refresh_count == import_count,
            f"Scene refresh count unchanged: {refresh_count}",
        )

        _step(f"{environment} — Manual polygon")
        ring = _empty_manual_ring(upload["scene"]["polygons"])
        r = client.post(
            f"{ENGINE}/polygon/manual/preview",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"ring": ring},
        )
        if r.status_code != 200:
            record("manual_polygon", False, f"Preview failed: {r.text[:200]}")
            return results
        r = client.post(
            f"{ENGINE}/polygon/manual",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"ring": ring},
        )
        r.raise_for_status()
        manual = r.json()
        after_manual = int(manual["counts"]["total"])
        results["counts"]["after_manual"] = after_manual
        manual_id = manual["polygon"]["id"]
        record(
            "manual_polygon",
            after_manual == import_count + 1 and manual["counts"]["manual_added"] >= 1,
            f"Added manual polygon #{manual_id}; total {after_manual}",
            manual_id=manual_id,
        )

        _step(f"{environment} — Save")
        save_path = Path(tempfile.gettempdir()) / f"int_zone_qa_{environment}.pjson"
        r = client.post(
            f"{ENGINE}/workspace/save",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"path": str(save_path)},
        )
        r.raise_for_status()
        saved_ok = save_path.is_file()
        manual_in_file = False
        if saved_ok:
            payload = json.loads(save_path.read_text(encoding="utf-8"))
            manual_in_file = any(p.get("source") == "manual" for p in payload.get("polygons", []))
        record(
            "save",
            saved_ok and manual_in_file,
            f"Saved to {save_path}; manual polygon in file={manual_in_file}",
            path=str(save_path),
        )

        _step(f"{environment} — Reopen")
        r = client.post(f"{ENGINE}/session")
        r.raise_for_status()
        new_session = r.json()["session_id"]
        with save_path.open("rb") as fh:
            r = client.post(
                f"{ENGINE}/workspace/load-project",
                headers={"X-Session-Id": new_session},
                files={"file": (save_path.name, fh, "application/json")},
            )
        r.raise_for_status()
        loaded = r.json()
        reopen_count = int(loaded["counts"]["total"])
        results["counts"]["after_reopen"] = reopen_count
        cad_ok = bool(loaded.get("cad_available", True))
        restored_manual = any(p.get("source") == "manual" for p in loaded["scene"]["polygons"])
        record(
            "reopen",
            reopen_count == after_manual and restored_manual and cad_ok,
            f"Restored {reopen_count} polygons; manual={restored_manual}; cad_available={cad_ok}",
        )

    except Exception as exc:
        results["passed"] = False
        results["errors"].append(str(exc))
        print(f"  FAIL: {exc}")

    return results


def main() -> int:
    client = httpx.Client(timeout=300.0)
    try:
        result = run_workflow(client, ENV_LABEL)
        report_path = PROJECT_ROOT / "output" / f"civil_engineer_qa_{ENV_LABEL}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    **result,
                    "engine": ENGINE,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nReport: {report_path}")
        print(f"RESULT: {'PASS' if result['passed'] else 'FAIL'}")
        if result["errors"]:
            for err in result["errors"]:
                print(f"  - {err}")
        return 0 if result["passed"] else 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
