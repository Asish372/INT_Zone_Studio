#!/usr/bin/env python3
"""Pilot release workflow test (import → detect refresh → save → reopen).

Pilot-v1 package predates manual polygon API; manual step is skipped with note.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = (
    PROJECT_ROOT
    / "output"
    / ".dxf_cache"
    / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
ENGINE = os.environ.get("INT_ZONE_ENGINE", "http://127.0.0.1:8765")


def main() -> int:
    result: dict = {"environment": "pilot_release", "passed": True, "steps": {}, "errors": []}

    def record(step: str, ok: bool, detail: str, **extra: object) -> None:
        result["steps"][step] = {"ok": ok, "detail": detail, **extra}
        print(f"  {'PASS' if ok else 'FAIL'} — {detail}")
        if not ok:
            result["passed"] = False
            result["errors"].append(f"{step}: {detail}")

    if not WAREHOUSE_DXF.is_file():
        record("preflight", False, f"Missing {WAREHOUSE_DXF}")
        return 1

    client = httpx.Client(timeout=300.0)
    try:
        print("\n=== pilot_release — Preflight ===")
        r = client.get(f"{ENGINE}/health")
        record("preflight", r.status_code == 200, f"Engine health {r.status_code}")

        print("\n=== pilot_release — Import ===")
        sid = client.post(f"{ENGINE}/session").json()["session_id"]
        with WAREHOUSE_DXF.open("rb") as fh:
            r = client.post(
                f"{ENGINE}/upload",
                headers={"X-Session-Id": sid},
                files={"file": (WAREHOUSE_DXF.name, fh, "application/octet-stream")},
            )
        r.raise_for_status()
        upload = r.json()
        count = int(upload["counts"]["total"])
        result["counts"] = {"after_import": count}
        record("import", count > 0, f"{count} polygons")

        print("\n=== pilot_release — Detect refresh ===")
        r = client.get(f"{ENGINE}/scene", headers={"X-Session-Id": sid})
        refresh = int(r.json()["summary"]["counts"]["total"])
        record("detect_refresh", refresh == count, f"Count unchanged at {refresh}")

        print("\n=== pilot_release — Manual polygon (expected unsupported) ===")
        r = client.post(
            f"{ENGINE}/polygon/manual",
            headers={"X-Session-Id": sid, "Content-Type": "application/json"},
            json={"ring": [[0, 0], [100, 0], [100, 100], [0, 100]]},
        )
        manual_supported = r.status_code == 200
        if manual_supported:
            count = int(r.json()["counts"]["total"])
            record("manual_polygon", True, f"Unexpectedly supported — total {count}")
        else:
            record(
                "manual_polygon",
                True,
                f"Not in pilot-v1 package (HTTP {r.status_code}) — use current dev build for manual draw",
                skipped=True,
            )

        print("\n=== pilot_release — Save ===")
        save_path = Path(tempfile.gettempdir()) / "int_zone_qa_pilot.pjson"
        r = client.post(
            f"{ENGINE}/workspace/save",
            headers={"X-Session-Id": sid, "Content-Type": "application/json"},
            json={"path": str(save_path)},
        )
        r.raise_for_status()
        record("save", save_path.is_file(), f"Saved {save_path}")

        print("\n=== pilot_release — Reopen ===")
        sid2 = client.post(f"{ENGINE}/session").json()["session_id"]
        with save_path.open("rb") as fh:
            r = client.post(
                f"{ENGINE}/workspace/load-project",
                headers={"X-Session-Id": sid2},
                files={"file": (save_path.name, fh, "application/json")},
            )
        r.raise_for_status()
        loaded = r.json()
        reopen = int(loaded["counts"]["total"])
        result["counts"]["after_reopen"] = reopen
        record(
            "reopen",
            reopen == count,
            f"Restored {reopen} polygons; cad_available={loaded.get('cad_available', True)}",
        )

    except Exception as exc:
        result["passed"] = False
        result["errors"].append(str(exc))
        print(f"  FAIL: {exc}")
    finally:
        client.close()

    report = PROJECT_ROOT / "output" / "civil_engineer_qa_pilot_release.json"
    report.write_text(
        json.dumps({**result, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=2),
        encoding="utf-8",
    )
    print(f"\nReport: {report}")
    print(f"RESULT: {'PASS' if result['passed'] else 'FAIL'}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
