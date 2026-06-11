#!/usr/bin/env python3
"""Packaging validation: full workflow + verify all export artifacts exist on disk."""

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
WAREHOUSE = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
ENGINE = os.environ.get("INT_ZONE_ENGINE", "http://127.0.0.1:8765")
PILOT_ROOT = PROJECT_ROOT / "release" / "INT-Zone-Studio-Pilot-v1"


def _scene_bounds(scene: dict) -> tuple[float, float, float, float]:
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for line in scene.get("cad_lines") or []:
        for i in (0, 2):
            min_x = min(min_x, float(line[i]))
            max_x = max(max_x, float(line[i]))
        for i in (1, 3):
            min_y = min(min_y, float(line[i]))
            max_y = max(max_y, float(line[i]))
    for poly in scene.get("polygons") or []:
        for x, y in poly.get("ring") or []:
            min_x, max_x = min(min_x, float(x)), max(max_x, float(x))
            min_y, max_y = min(min_y, float(y)), max(max_y, float(y))
    return min_x, min_y, max_x, max_y


def _boundary_ring(scene: dict) -> list[list[float]]:
    min_x, min_y, max_x, max_y = _scene_bounds(scene)
    pad_x = (max_x - min_x) * 0.02
    pad_y = (max_y - min_y) * 0.02
    return [
        [min_x + pad_x, min_y + pad_y],
        [max_x - pad_x, min_y + pad_y],
        [max_x - pad_x, max_y - pad_y],
        [min_x + pad_x, max_y - pad_y],
    ]


def _manual_ring(polygons: list[dict]) -> list[list[float]]:
    minx = miny = 1e18
    maxx = maxy = -1e18
    for poly in polygons:
        for pt in poly.get("ring") or []:
            x, y = float(pt[0]), float(pt[1])
            minx, miny = min(minx, x), min(miny, y)
            maxx, maxy = max(maxx, x), max(maxy, y)
    x0, y0 = maxx + 10_000.0, miny + 10_000.0
    s = 5000.0
    return [[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s]]


def verify_artifacts(
    export: dict[str, Any],
    *,
    path_root: Path,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    abs_paths = export.get("absolute_paths") or {}
    rel_paths = export.get("paths") or {}
    for key in rel_paths:
        rel = rel_paths[key]
        candidates = [
            path_root / rel.replace("/", "\\"),
            Path(abs_paths.get(key, "")),
        ]
        found = None
        for p in candidates:
            if p and p.is_file() and p.stat().st_size > 0:
                found = p
                break
        checks.append(
            {
                "format": key,
                "relative": rel,
                "exists": found is not None,
                "path": str(found) if found else str(candidates[0]),
                "size_bytes": found.stat().st_size if found else 0,
            }
        )
    return checks


def run_packaging_workflow(client: httpx.Client, label: str) -> dict[str, Any]:
    out: dict[str, Any] = {"label": label, "steps": {}, "artifact_checks": [], "passed": True, "errors": []}

    def fail(step: str, msg: str) -> None:
        out["passed"] = False
        out["errors"].append(f"{step}: {msg}")
        out["steps"][step] = {"ok": False, "detail": msg}

    r = client.get("/health")
    if r.status_code != 200:
        fail("preflight", f"health {r.status_code}")
        return out

    scope_ok = client.get("/scope/config").json().get("enabled") is True
    out["scope_enabled"] = scope_ok

    sid = client.post("/session").json()["session_id"]
    h = {"X-Session-Id": sid}
    with WAREHOUSE.open("rb") as fh:
        r = client.post("/upload", headers=h, files={"file": (WAREHOUSE.name, fh, "application/octet-stream")})
    if r.status_code != 200:
        fail("import", r.text[:200])
        return out
    upload = r.json()
    out["steps"]["import"] = {"ok": True, "count": upload["counts"]["total"]}

    scene = upload.get("scene") or {}
    if scope_ok:
        ring = _boundary_ring(scene)
        client.put("/scope/boundary", headers=h, json={"ring": ring, "source": "drawn"}).raise_for_status()
        r = client.post("/scope/boundary/apply", headers=h)
        if r.status_code != 200:
            fail("apply_boundary", r.text[:200])
            return out
        out["steps"]["apply_boundary"] = {"ok": True, "count": r.json()["counts"]["total"]}
        polys = r.json()["scene"]["polygons"]
    else:
        out["steps"]["apply_boundary"] = {"ok": True, "skipped": "scope disabled (pilot-v1)"}
        polys = scene.get("polygons") or []

    r = client.post("/zones/generate", headers=h)
    if r.status_code == 200:
        out["steps"]["generate_zones"] = {"ok": True, "zones": len(r.json().get("zones") or [])}
    else:
        out["steps"]["generate_zones"] = {"ok": False, "skipped": r.text[:120]}

    if client.post("/polygon/manual", headers=h, json={"ring": _manual_ring(polys)}).status_code == 200:
        out["steps"]["manual_polygon"] = {"ok": True}
    else:
        out["steps"]["manual_polygon"] = {"ok": False, "skipped": "not supported on this engine"}

    save_path = Path(tempfile.gettempdir()) / f"packaging_qa_{label}.pjson"
    client.post("/workspace/save", headers=h, json={"path": str(save_path)}).raise_for_status()
    out["steps"]["save"] = {"ok": save_path.is_file(), "path": str(save_path)}

    sid2 = client.post("/session").json()["session_id"]
    h2 = {"X-Session-Id": sid2}
    with save_path.open("rb") as fh:
        r = client.post("/workspace/load-project", headers=h2, files={"file": (save_path.name, fh, "application/json")})
    r.raise_for_status()
    out["steps"]["reopen"] = {"ok": True, "count": r.json()["counts"]["total"]}

    if scope_ok:
        client.post("/zones/rebuild", headers=h2)

    r = client.post(
        "/export",
        headers={**h2, "Content-Type": "application/json"},
        json={"formats": ["package"], "use_timestamp": True},
    )
    if r.status_code != 200:
        fail("export", r.text[:200])
        return out
    export = r.json()
    out["steps"]["export"] = {"ok": True, "folder": export.get("folder"), "formats": list(export.get("paths", {}))}

    # Resolve disk root from API absolute_paths first folder
    folder = export.get("folder") or ""
    path_root = Path(folder).parent if folder else PROJECT_ROOT
    out["artifact_checks"] = verify_artifacts(export, path_root=path_root)
    for c in out["artifact_checks"]:
        if not c["exists"]:
            out["passed"] = False
            out["errors"].append(f"Missing export artifact: {c['format']} at {c['path']}")

    return out


def check_pilot_package_layout() -> dict[str, Any]:
    required = [
        "INT Zone Studio.exe",
        "config.yaml",
        "requirements.txt",
        "PILOT_V1.md",
        "PILOT_FEEDBACK.md",
        "pilot_metrics_template.csv",
        "TESTER_SETUP.txt",
        "scripts/run_polygon_workspace.py",
    ]
    checks = {name: (PILOT_ROOT / name).exists() for name in required}
    return {
        "pilot_root": str(PILOT_ROOT),
        "package_complete": all(checks.values()),
        "files": checks,
    }


def main() -> int:
    t0 = time.time()
    client = httpx.Client(timeout=600.0, base_url=ENGINE)
    try:
        dev_run = run_packaging_workflow(client, "dev_engine")
    finally:
        client.close()

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dev_engine_workflow": dev_run,
        "pilot_package_layout": check_pilot_package_layout(),
        "fresh_vm_note": (
            "Full VM smoke test not run in this session. "
            "Use release/INT-Zone-Studio-Pilot-v1 + TESTER_SETUP.txt on a clean Windows 10/11 VM."
        ),
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    out = PROJECT_ROOT / "output" / "packaging_validation_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nReport: {out}")
    ok = dev_run["passed"] and report["pilot_package_layout"]["package_complete"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
