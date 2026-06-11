#!/usr/bin/env python3
"""Test Import → Detect → Manual polygon → Save → Reopen for every canonical DXF/DWG file."""

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
ENGINE = os.environ.get("INT_ZONE_ENGINE", "http://127.0.0.1:8765")
ENV_LABEL = os.environ.get("INT_ZONE_ENV", "dev_api")
MANUAL_SUPPORTED = os.environ.get("INT_ZONE_MANUAL", "auto")  # auto | yes | no

# Canonical source drawings — both DXF and DWG per drawing name
CANONICAL_FILES: list[tuple[str, Path]] = [
    ("warehouse_dxf", PROJECT_ROOT / "output/.dxf_cache/6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"),
    ("warehouse_dwg", PROJECT_ROOT / "input/6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg"),
    ("s111_a_dxf", PROJECT_ROOT / "output/.dxf_cache/S111_A.dxf"),
    ("s111_a_dwg", PROJECT_ROOT / "input/S111_A.dwg"),
    ("s111_j_dxf", PROJECT_ROOT / "output/.dxf_cache/S111_J.dxf"),
    ("s111_j_dwg", PROJECT_ROOT / "input/S111_J.dwg"),
]


def _bbox(polygons: list[dict]) -> tuple[float, float, float, float]:
    minx = miny = 1e18
    maxx = maxy = -1e18
    for poly in polygons:
        for pt in poly.get("ring") or []:
            x, y = float(pt[0]), float(pt[1])
            minx, miny = min(minx, x), min(miny, y)
            maxx, maxy = max(maxx, x), max(maxy, y)
    return minx, miny, maxx, maxy


def _empty_ring(polygons: list[dict], size: float = 5000.0) -> list[list[float]]:
    minx, miny, maxx, maxy = _bbox(polygons)
    x0, y0 = maxx + 10_000.0, miny + 10_000.0
    return [[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size]]


def _manual_available(client: httpx.Client) -> bool:
    if MANUAL_SUPPORTED == "yes":
        return True
    if MANUAL_SUPPORTED == "no":
        return False
    try:
        r = client.get(f"{ENGINE}/openapi.json", timeout=10.0)
        if r.status_code == 200 and "/polygon/manual" in r.text:
            return True
    except Exception:
        pass
    return (PROJECT_ROOT / "desktop/engine_sidecar/api.py").read_text(encoding="utf-8").find(
        '"/polygon/manual"'
    ) >= 0 and ENV_LABEL.startswith("dev")


def test_file(client: httpx.Client, label: str, path: Path, manual_ok: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "label": label,
        "file": str(path),
        "ext": path.suffix.lower(),
        "passed": True,
        "steps": {},
        "errors": [],
    }

    def record(step: str, ok: bool, detail: str, **extra: Any) -> None:
        result["steps"][step] = {"ok": ok, "detail": detail, **extra}
        if not ok:
            result["passed"] = False
            result["errors"].append(f"{step}: {detail}")

    if not path.is_file():
        record("preflight", False, f"File missing: {path}")
        return result

    try:
        r = client.post(f"{ENGINE}/session")
        r.raise_for_status()
        sid = r.json()["session_id"]

        t0 = time.time()
        with path.open("rb") as fh:
            r = client.post(
                f"{ENGINE}/upload",
                headers={"X-Session-Id": sid},
                files={"file": (path.name, fh, "application/octet-stream")},
            )
        elapsed = time.time() - t0

        if r.status_code != 200:
            record("import", False, f"HTTP {r.status_code}: {r.text[:300]}")
            return result

        upload = r.json()
        import_count = int(upload["counts"]["total"])
        result["counts"] = {"after_import": import_count}
        record(
            "import",
            import_count > 0,
            f"{import_count} polygons in {elapsed:.1f}s",
            source=upload.get("source_file"),
        )
        if import_count == 0:
            return result

        r = client.get(f"{ENGINE}/scene", headers={"X-Session-Id": sid})
        refresh = int(r.json()["summary"]["counts"]["total"])
        record("detect_refresh", refresh == import_count, f"Count {refresh}")

        final_count = import_count
        if manual_ok:
            ring = _empty_ring(upload["scene"]["polygons"])
            r = client.post(
                f"{ENGINE}/polygon/manual",
                headers={"X-Session-Id": sid, "Content-Type": "application/json"},
                json={"ring": ring},
            )
            if r.status_code == 200:
                final_count = int(r.json()["counts"]["total"])
                result["counts"]["after_manual"] = final_count
                record("manual_polygon", final_count == import_count + 1, f"Total {final_count}")
            else:
                record("manual_polygon", False, r.text[:200])
        else:
            record(
                "manual_polygon",
                True,
                "Skipped — not in this engine build",
                skipped=True,
            )

        save_path = Path(tempfile.gettempdir()) / f"qa_{ENV_LABEL}_{label}.pjson"
        r = client.post(
            f"{ENGINE}/workspace/save",
            headers={"X-Session-Id": sid, "Content-Type": "application/json"},
            json={"path": str(save_path)},
        )
        r.raise_for_status()
        record("save", save_path.is_file(), str(save_path))

        sid2 = client.post(f"{ENGINE}/session").json()["session_id"]
        with save_path.open("rb") as fh:
            r = client.post(
                f"{ENGINE}/workspace/load-project",
                headers={"X-Session-Id": sid2},
                files={"file": (save_path.name, fh, "application/json")},
            )
        if r.status_code != 200:
            record("reopen", False, r.text[:300])
            return result

        loaded = r.json()
        reopen_count = int(loaded["counts"]["total"])
        cad_ok = bool(loaded.get("cad_available", True))
        result["counts"]["after_reopen"] = reopen_count
        record(
            "reopen",
            reopen_count == final_count and cad_ok,
            f"{reopen_count} polygons; cad={cad_ok}",
        )

    except Exception as exc:
        result["passed"] = False
        result["errors"].append(str(exc))

    return result


def main() -> int:
    client = httpx.Client(timeout=600.0)
    try:
        r = client.get(f"{ENGINE}/health")
        if r.status_code != 200:
            print(f"Engine down at {ENGINE}")
            return 1

        manual_ok = _manual_available(client)
        print(f"\n=== {ENV_LABEL} @ {ENGINE} | manual={'yes' if manual_ok else 'no'} ===\n")

        results: list[dict] = []
        for label, path in CANONICAL_FILES:
            print(f"--- {label} ({path.suffix}) ---")
            res = test_file(client, label, path, manual_ok)
            results.append(res)
            status = "PASS" if res["passed"] else "FAIL"
            print(f"  {status}: {path.name}")
            for err in res.get("errors", []):
                print(f"    ! {err}")

        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        report = {
            "environment": ENV_LABEL,
            "engine": ENGINE,
            "manual_supported": manual_ok,
            "passed": passed,
            "total": total,
            "all_passed": passed == total,
            "files": results,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        out = PROJECT_ROOT / "output" / f"all_files_qa_{ENV_LABEL}.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\n=== {ENV_LABEL}: {passed}/{total} PASS ===")
        print(f"Report: {out}")
        return 0 if passed == total else 1
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
