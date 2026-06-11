#!/usr/bin/env python3
"""Fresh Windows VM workflow verification — matches pilot handoff checklist."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
ENGINE = os.environ.get("INT_ZONE_ENGINE", "http://127.0.0.1:8765")
STANDALONE_SETUP = PROJECT_ROOT / "release" / "INT Zone Studio Standalone Setup 0.1.0-pilot.1.exe"
BUNDLED_ENGINE = (
    PROJECT_ROOT
    / "desktop"
    / "studio"
    / "src-tauri"
    / "resources"
    / "engine"
    / "int-zone-engine"
    / "int-zone-engine.exe"
)
EXPECTED_ZONES = 24
REQUIRED_EXPORTS = ("json", "dxf", "csv", "xlsx", "pdf", "zones_dxf", "int_schedule")


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


def check_standalone_installer() -> dict[str, Any]:
    out: dict[str, Any] = {"setup_exe_exists": STANDALONE_SETUP.is_file(), "bundled_engine_built": BUNDLED_ENGINE.is_file()}
    if STANDALONE_SETUP.is_file():
        out["setup_size_mb"] = round(STANDALONE_SETUP.stat().st_size / (1024 * 1024), 1)
    if BUNDLED_ENGINE.is_file():
        env = dict(os.environ)
        env["INT_ZONE_DATA_DIR"] = str(PROJECT_ROOT / "output" / "_fresh_vm_engine_test")
        proc = subprocess.Popen(
            [str(BUNDLED_ENGINE)],
            cwd=BUNDLED_ENGINE.parent,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        ok = False
        deadline = time.time() + 45
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as resp:
                    ok = resp.status == 200
                    if ok:
                        break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.5)
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        out["bundled_engine_health"] = ok
        out["no_python_required"] = ok
    else:
        out["bundled_engine_health"] = None
        out["no_python_required"] = STANDALONE_SETUP.is_file()
        out["note"] = "Installer ships bundled engine; PyInstaller bundle not in dev tree — client uses setup exe only"
    return out


def run_workflow(client: httpx.Client) -> dict[str, Any]:
    report: dict[str, Any] = {"steps": {}, "checks": {}, "passed": True, "errors": []}

    def fail(step: str, msg: str) -> None:
        report["passed"] = False
        report["errors"].append(f"{step}: {msg}")
        report["steps"][step] = {"ok": False, "detail": msg}

    def ok(step: str, detail: str, **extra: Any) -> None:
        report["steps"][step] = {"ok": True, "detail": detail, **extra}

    if not WAREHOUSE.is_file():
        fail("preflight", f"Missing test drawing {WAREHOUSE}")
        return report

    r = client.get("/health")
    if r.status_code != 200:
        fail("launch", f"Engine not reachable HTTP {r.status_code}")
        return report
    ok("launch", "Engine health OK", dwg_ready=r.json().get("dwg_ready"))

    r = client.post("/session")
    r.raise_for_status()
    h = {"X-Session-Id": r.json()["session_id"]}

    with WAREHOUSE.open("rb") as fh:
        r = client.post("/upload", headers=h, files={"file": (WAREHOUSE.name, fh, "application/octet-stream")})
    if r.status_code != 200:
        fail("import", r.text[:200])
        return report
    upload = r.json()
    import_count = int(upload["counts"]["total"])
    ok("import", f"{import_count} polygons", count=import_count)
    scene = upload.get("scene") or {}

    ring = _boundary_ring(scene)
    r = client.put("/scope/boundary", headers=h, json={"ring": ring, "source": "drawn"})
    if r.status_code != 200:
        fail("boundary", r.text[:200])
        return report
    ok("boundary", "Boundary committed")

    r = client.post("/scope/boundary/apply", headers=h)
    if r.status_code != 200:
        fail("apply", r.text[:200])
        return report
    apply_body = r.json()
    polys = apply_body["scene"]["polygons"]
    ok("apply", f"{apply_body['counts']['total']} polygons after clip")

    r = client.post("/zones/generate", headers=h)
    if r.status_code != 200:
        fail("generate_zones", r.text[:200])
        return report
    zones = r.json().get("zones") or []
    zone_count = len(zones)
    ok("generate_zones", f"{zone_count} INT zones", count=zone_count)
    report["checks"]["zones_24"] = zone_count == EXPECTED_ZONES
    if zone_count != EXPECTED_ZONES:
        report["passed"] = False
        report["errors"].append(f"zones: expected {EXPECTED_ZONES}, got {zone_count}")

    r = client.post("/polygon/manual", headers=h, json={"ring": _manual_ring(polys)})
    if r.status_code != 200:
        fail("manual_polygon", r.text[:200])
        return report
    manual_id = r.json()["polygon"]["id"]
    count_before_save = int(r.json()["counts"]["total"])
    ok("manual_polygon", f"Added manual #{manual_id}", total=count_before_save)

    save_path = Path(tempfile.gettempdir()) / "fresh_vm_workflow_verify.pjson"
    r = client.post("/workspace/save", headers=h, json={"path": str(save_path)})
    if r.status_code != 200 or not save_path.is_file():
        fail("save", "Save failed")
        return report
    payload = json.loads(save_path.read_text(encoding="utf-8"))
    saved_boundary = bool((payload.get("scope") or {}).get("boundary"))
    saved_manual = any(p.get("source") == "manual" for p in payload.get("polygons", []))
    ok("save", f"boundary={saved_boundary} manual={saved_manual} zones={len(payload.get('zones') or [])}")
    report["checks"]["boundary_in_save"] = saved_boundary
    report["checks"]["manual_in_save"] = saved_manual
    if not saved_boundary:
        report["passed"] = False
        report["errors"].append("boundary not persisted in save file")
    if not saved_manual:
        report["passed"] = False
        report["errors"].append("manual polygon not persisted in save file")

    r = client.post("/session")
    r.raise_for_status()
    h2 = {"X-Session-Id": r.json()["session_id"]}
    ok("close", "New session (simulated app close)")

    with save_path.open("rb") as fh:
        r = client.post("/workspace/load-project", headers=h2, files={"file": (save_path.name, fh, "application/json")})
    if r.status_code != 200:
        fail("reopen", r.text[:200])
        return report
    loaded = r.json()
    reopen_count = int(loaded["counts"]["total"])
    restored_manual = any(p.get("source") == "manual" for p in loaded["scene"]["polygons"])
    reopened_boundary = (loaded.get("scene") or {}).get("scope_boundary") or {}
    zones_reopen = loaded.get("zones") or loaded.get("scene", {}).get("zones") or []
    ok(
        "reopen",
        f"{reopen_count} polygons; manual={restored_manual}; boundary_ring={bool(reopened_boundary.get('ring'))}; zones={len(zones_reopen)}",
    )
    report["checks"]["manual_after_reopen"] = restored_manual
    report["checks"]["boundary_after_reopen"] = bool(reopened_boundary.get("ring"))
    report["checks"]["zones_after_reopen"] = len(zones_reopen) == EXPECTED_ZONES
    if reopen_count != count_before_save:
        report["passed"] = False
        report["errors"].append(f"reopen count {reopen_count} != save count {count_before_save}")
    if not restored_manual:
        report["passed"] = False
        report["errors"].append("manual polygon lost after reopen")
    if not reopened_boundary.get("ring"):
        report["passed"] = False
        report["errors"].append("boundary lost after reopen")
    if len(zones_reopen) != EXPECTED_ZONES:
        report["passed"] = False
        report["errors"].append(f"zones after reopen: expected {EXPECTED_ZONES}, got {len(zones_reopen)}")

    client.post("/zones/rebuild", headers=h2)
    r = client.post(
        "/export",
        headers={**h2, "Content-Type": "application/json"},
        json={"formats": ["package"], "use_timestamp": True},
    )
    if r.status_code != 200:
        fail("export", r.text[:200])
        return report
    export = r.json()
    paths = export.get("paths") or {}
    abs_paths = export.get("absolute_paths") or {}
    ok("export", f"Package formats: {list(paths.keys())}")

    missing_formats = [k for k in REQUIRED_EXPORTS if k not in paths]
    report["checks"]["all_export_formats"] = not missing_formats
    if missing_formats:
        report["passed"] = False
        report["errors"].append(f"missing export formats: {missing_formats}")

    artifact_checks: list[dict[str, Any]] = []
    for fmt in REQUIRED_EXPORTS:
        rel = paths.get(fmt, "")
        candidates = [
            Path(abs_paths.get(fmt, "")),
            PROJECT_ROOT / rel.replace("/", "\\") if rel else Path(""),
        ]
        found = next((p for p in candidates if p.is_file() and p.stat().st_size > 0), None)
        artifact_checks.append(
            {
                "format": fmt,
                "exists": found is not None,
                "path": str(found) if found else str(candidates[0]),
                "size_bytes": found.stat().st_size if found else 0,
            }
        )
        if not found:
            report["passed"] = False
            report["errors"].append(f"export artifact missing or empty: {fmt}")

    report["artifact_checks"] = artifact_checks
    report["checks"]["all_exports_on_disk"] = all(c["exists"] for c in artifact_checks)
    return report


def main() -> int:
    print("=== Fresh Windows VM Workflow Verification ===\n")
    standalone = check_standalone_installer()
    print(f"Standalone setup: {'found' if standalone['setup_exe_exists'] else 'MISSING'}")
    if standalone.get("setup_size_mb"):
        print(f"  Size: {standalone['setup_size_mb']} MB")
    print(f"Bundled engine in dev tree: {standalone['bundled_engine_built']}")
    if standalone.get("bundled_engine_health") is not None:
        print(f"Bundled engine health (no Python): {'PASS' if standalone['bundled_engine_health'] else 'FAIL'}")

    client = httpx.Client(timeout=600.0, base_url=ENGINE)
    try:
        workflow = run_workflow(client)
    finally:
        client.close()

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "drawing": WAREHOUSE.name,
        "expected_zones": EXPECTED_ZONES,
        "standalone": standalone,
        "workflow": workflow,
        "passed": workflow["passed"] and standalone.get("setup_exe_exists", False),
    }

    out_path = PROJECT_ROOT / "output" / "fresh_vm_workflow_verify.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n--- Workflow steps ---")
    for name, step in workflow.get("steps", {}).items():
        mark = "PASS" if step.get("ok") else "FAIL"
        print(f"  [{mark}] {name}: {step.get('detail', '')}")

    print("\n--- Verification checks ---")
    for k, v in workflow.get("checks", {}).items():
        print(f"  {'PASS' if v else 'FAIL'} — {k}")

    if workflow.get("artifact_checks"):
        print("\n--- Export artifacts ---")
        for c in workflow["artifact_checks"]:
            mark = "PASS" if c["exists"] else "FAIL"
            print(f"  [{mark}] {c['format']}: {c['size_bytes']} bytes")

    print(f"\nReport: {out_path}")
    if report["passed"]:
        print("RESULT: PASS")
        return 0
    print("RESULT: FAIL")
    for err in workflow.get("errors", []):
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
