#!/usr/bin/env python3
"""Simulated naive-user flow: open → find → save → reopen → export.

Runs against the live engine API (and optionally the web UI) to verify
no crashes and to record likely human friction points.
"""

from __future__ import annotations

import json
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
ENGINE = "http://127.0.0.1:8765"
UI = "http://localhost:1420"

OBSERVATIONS: list[str] = []
CRASHES: list[str] = []


def observe(step: str, note: str) -> None:
    OBSERVATIONS.append(f"[{step}] {note}")
    print(f"  OBSERVE {step}: {note}")


def step(name: str):
    print(f"\n=== {name} ===")


def main() -> int:
    if not WAREHOUSE_DXF.is_file():
        print(f"Missing test drawing: {WAREHOUSE_DXF}")
        return 1

    client = httpx.Client(timeout=300.0)
    try:
        # Health
        step("0 — Preflight")
        r = client.get(f"{ENGINE}/health")
        r.raise_for_status()
        ui_ok = False
        try:
            ur = client.get(UI, timeout=5.0)
            ui_ok = ur.status_code == 200
        except httpx.HTTPError:
            pass
        print(f"  Engine OK | UI {'OK' if ui_ok else 'DOWN (API-only test)'}")

        # 1 Open drawing
        step("1 — Open drawing")
        r = client.post(f"{ENGINE}/session")
        r.raise_for_status()
        session_id = r.json()["session_id"]
        observe("1", "Naive user likely clicks 'Import Drawing' on welcome (not Open Project)")

        with WAREHOUSE_DXF.open("rb") as fh:
            r = client.post(
                f"{ENGINE}/upload",
                headers={"X-Session-Id": session_id},
                files={"file": (WAREHOUSE_DXF.name, fh, "application/octet-stream")},
            )
        r.raise_for_status()
        upload = r.json()
        polygon_count = upload["counts"]["total"]
        print(f"  Loaded {upload['source_file']} — {polygon_count} polygons")
        assert polygon_count == 618
        observe("1", f"Upload took ~{r.elapsed.total_seconds():.1f}s — user may think app froze on large DWG")

        # 2 Find polygon
        step("2 — Find a polygon")
        observe("2", "Without guidance, user may click canvas (hard at fit zoom) OR scroll polygon table")
        target_id = upload["scene"]["polygons"][0]["id"]
        r = client.post(
            f"{ENGINE}/select",
            headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
            json={"polygon_id": target_id},
        )
        r.raise_for_status()
        selected = r.json()
        print(f"  Selected polygon #{target_id}, area={selected.get('area_m2', '?')} m²")
        observe("2", "Table row click is more reliable than canvas click for first-time users")

        # 3 Save project
        step("3 — Save project")
        observe("3", "First save opens modal asking for FULL PATH — high confusion risk for non-devs")
        with tempfile.TemporaryDirectory() as tmp:
            save_path = Path(tmp) / "pilot_human_test.pjson"
            r = client.post(
                f"{ENGINE}/workspace/save",
                headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                json={"path": str(save_path)},
            )
            r.raise_for_status()
            assert save_path.is_file()
            print(f"  Saved to {save_path}")

            # 4 Close app (new session)
            step("4 — Close app (new session)")
            r = client.post(f"{ENGINE}/session")
            r.raise_for_status()
            new_session = r.json()["session_id"]
            print(f"  New session {new_session}")

            # 5 Reopen project
            step("5 — Reopen project")
            observe("5", "User must choose 'Open Project' not 'Import Drawing' — easy mistake")
            with save_path.open("rb") as fh:
                r = client.post(
                    f"{ENGINE}/workspace/load-project",
                    headers={"X-Session-Id": new_session},
                    files={"file": ("pilot_human_test.pjson", fh, "application/json")},
                )
            r.raise_for_status()
            loaded = r.json()
            assert loaded["counts"]["total"] == polygon_count
            restored_ids = {p["id"] for p in loaded["scene"]["polygons"]}
            assert target_id in restored_ids
            print(f"  Restored {loaded['counts']['total']} polygons, selection #{target_id} present")

            # 6 Export package
            step("6 — Export package")
            observe("6", "Export button top-right; 'Export Project Package' is primary but buried in modal list")
            r = client.post(
                f"{ENGINE}/export",
                headers={"X-Session-Id": new_session, "Content-Type": "application/json"},
                json={"formats": ["package"], "use_timestamp": True},
            )
            r.raise_for_status()
            export = r.json()
            paths = export.get("paths") or {}
            print(f"  Package files: {list(paths.keys())}")
            assert "json" in paths and "dxf" in paths and "pdf" in paths

        step("RESULT")
        print("  PASS — full 6-step flow, no crash")
        return 0

    except Exception as exc:
        CRASHES.append(str(exc))
        print(f"\nFAIL / CRASH: {exc}")
        return 1
    finally:
        client.close()
        report_path = PROJECT_ROOT / "output" / "human_test_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "passed": len(CRASHES) == 0,
                    "crashes": CRASHES,
                    "observations": OBSERVATIONS,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nReport written: {report_path}")


if __name__ == "__main__":
    sys.exit(main())
