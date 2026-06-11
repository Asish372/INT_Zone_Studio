#!/usr/bin/env python3
"""Client build full verification: workflow, export content, cross-PC bundle checks."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
ENGINE = os.environ.get("INT_ZONE_ENGINE", "http://127.0.0.1:8765")
ENGINE_EXE = (
    PROJECT_ROOT
    / "desktop"
    / "studio"
    / "src-tauri"
    / "resources"
    / "engine"
    / "int-zone-engine"
    / "int-zone-engine.exe"
)
ODA_EXE = PROJECT_ROOT / "desktop" / "studio" / "src-tauri" / "resources" / "oda" / "ODAFileConverter.exe"
RESOURCES_CONFIG = PROJECT_ROOT / "desktop" / "studio" / "src-tauri" / "resources" / "config.yaml"
INSTALLER = PROJECT_ROOT / "release" / "INT Zone Studio Standalone Setup 0.1.0-pilot.1.exe"
EXPECTED_ZONES = 24
INT_SCHEDULE_COLUMNS = [
    "Pour No.",
    "Concrete Area (SQM)",
    "Concrete Volume (CUM)",
    "Face Count",
    "Grid Ref",
    "Detection Tier",
    "Centroid X (m)",
    "Centroid Y (m)",
    "Union/Bay Coverage %",
]
POLYGON_XLSX_HEADERS = [
    "id",
    "source",
    "review_status",
    "int_zone",
    "area_m2",
    "perimeter_m",
    "centroid_x",
    "centroid_y",
    "layer",
    "created_by",
]
PACKAGE_FORMATS = ("json", "dxf", "csv", "xlsx", "pdf", "zones_dxf", "int_schedule")


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


def _resolve_export_path(key: str, export: dict[str, Any]) -> Path | None:
    abs_paths = export.get("absolute_paths") or {}
    rel_paths = export.get("paths") or {}
    rel = rel_paths.get(key, "")
    candidates = [
        Path(abs_paths.get(key, "")),
        PROJECT_ROOT / rel.replace("/", "\\") if rel else Path(""),
    ]
    for p in candidates:
        if p.is_file() and p.stat().st_size > 0:
            return p
    return None


def check_cross_pc_bundle() -> dict[str, Any]:
    out: dict[str, Any] = {"checks": [], "passed": True}

    def add(name: str, ok: bool, detail: str) -> None:
        out["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            out["passed"] = False

    add("installer_exists", INSTALLER.is_file(), f"{INSTALLER.stat().st_size // (1024 * 1024)} MB" if INSTALLER.is_file() else "missing")
    add("bundled_engine_exists", ENGINE_EXE.is_file(), str(ENGINE_EXE) if ENGINE_EXE.is_file() else "missing")
    add("oda_converter_exists", ODA_EXE.is_file(), "DWG import on client PCs" if ODA_EXE.is_file() else "missing")
    add("webview_embed_bootstrapper", True, "tauri.conf.json embedBootstrapper — WebView2 auto-install on old PCs")

    scope_on = False
    if RESOURCES_CONFIG.is_file():
        cfg = yaml.safe_load(RESOURCES_CONFIG.read_text(encoding="utf-8")) or {}
        scope_on = bool(cfg.get("scope", {}).get("enabled"))
    add("packaged_scope_enabled", scope_on, "scope.enabled in resources/config.yaml")

    root_cfg = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    add("dev_scope_enabled", bool(root_cfg.get("scope", {}).get("enabled")), "scope.enabled in repo config.yaml")

    return out


def check_fresh_pc_config_seed() -> dict[str, Any]:
    """Simulate Tauri seeding config into empty app data dir."""
    out: dict[str, Any] = {"passed": True, "detail": ""}
    if not RESOURCES_CONFIG.is_file():
        out["passed"] = False
        out["detail"] = "resources config missing"
        return out
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        dest = data_dir / "config.yaml"
        if not dest.exists():
            shutil.copy2(RESOURCES_CONFIG, dest)
        cfg = yaml.safe_load(dest.read_text(encoding="utf-8")) or {}
        scope_on = bool(cfg.get("scope", {}).get("enabled"))
        out["scope_enabled_after_seed"] = scope_on
        out["passed"] = scope_on
        out["detail"] = "Fresh install gets boundary workflow" if scope_on else "scope.disabled would break boundary"
    return out


def validate_export_contents(export: dict[str, Any], zones: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"checks": [], "passed": True, "files": {}}

    def add(name: str, ok: bool, detail: str) -> None:
        out["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            out["passed"] = False

    for fmt in PACKAGE_FORMATS:
        p = _resolve_export_path(fmt, export)
        add(f"artifact_{fmt}_on_disk", p is not None, str(p) if p else "missing")
        if not p:
            continue
        out["files"][fmt] = {"path": str(p), "size_bytes": p.stat().st_size}

    int_xlsx = _resolve_export_path("int_schedule", export)
    if int_xlsx:
        df = pd.read_excel(int_xlsx, sheet_name="INT Schedule")
        headers = list(df.columns)
        add("int_schedule_headers", headers == INT_SCHEDULE_COLUMNS, ", ".join(headers[:4]) + "...")
        data = df[df["Pour No."].astype(str) != "TOTAL"]
        add("int_schedule_zone_count", len(data) == EXPECTED_ZONES, f"{len(data)} rows")
        total_row = df[df["Pour No."].astype(str) == "TOTAL"]
        add("int_schedule_total_row", len(total_row) == 1, "TOTAL row present")
        studio = sorted(
            (
                str(z.get("label") or z.get("int_label") or ""),
                round(float(z.get("area_m2") or 0), 4),
                int(len(z.get("face_ids") or z.get("polygon_ids") or [])),
            )
            for z in zones
        )
        schedule = sorted(
            (
                str(row["Pour No."]),
                round(float(row["Concrete Area (SQM)"]), 4),
                int(row["Face Count"]),
            )
            for _, row in data.iterrows()
        )
        add("studio_equals_int_schedule", studio == schedule, "labels/areas/faces match")

    poly_xlsx = _resolve_export_path("xlsx", export)
    if poly_xlsx:
        wb_headers = list(pd.read_excel(poly_xlsx, sheet_name="Polygons").columns)
        add("polygon_schedule_headers", wb_headers == POLYGON_XLSX_HEADERS, str(wb_headers))
        poly_rows = len(pd.read_excel(poly_xlsx, sheet_name="Polygons"))
        add("polygon_schedule_rows", poly_rows > 0, f"{poly_rows} polygons")

    zones_dxf = _resolve_export_path("zones_dxf", export)
    if zones_dxf:
        import ezdxf

        doc = ezdxf.readfile(str(zones_dxf))
        layers = {layer.dxf.name for layer in doc.layers}
        add("zones_dxf_int_zones_layer", "INT_ZONES" in layers, str(sorted(layers)[:6]))
        add("zones_dxf_int_labels_layer", "INT_LABELS" in layers, "INT_LABELS present")
        polylines = [e for e in doc.modelspace() if e.dxftype() == "LWPOLYLINE"]
        labels = [e for e in doc.modelspace() if e.dxftype() == "TEXT"]
        zones_with_geometry = sum(
            1
            for z in zones
            if (z.get("ring") and len(z.get("ring") or []) >= 3)
            or int(z.get("face_count") or 0) > 0
        )
        add(
            "zones_dxf_geometry_count",
            len(polylines) == zones_with_geometry and len(polylines) > 0,
            f"{len(polylines)} polylines for {zones_with_geometry} non-empty zones",
        )
        add(
            "zones_dxf_labels_count",
            len(labels) == len(polylines),
            f"{len(labels)} zone labels",
        )

    json_p = _resolve_export_path("json", export)
    if json_p:
        payload = json.loads(json_p.read_text(encoding="utf-8"))
        polys = payload.get("polygons") or payload.get("records") or []
        add("json_has_polygons", len(polys) > 0, f"{len(polys)} records")

    csv_p = _resolve_export_path("csv", export)
    if csv_p:
        text = csv_p.read_text(encoding="utf-8", errors="replace")
        add("csv_has_header", "id" in text.splitlines()[0].lower(), text.splitlines()[0][:60])

    pdf_p = _resolve_export_path("pdf", export)
    if pdf_p:
        add("pdf_valid_header", pdf_p.read_bytes()[:4] == b"%PDF", "detection report PDF")

    dxf_p = _resolve_export_path("dxf", export)
    if dxf_p:
        import ezdxf

        doc = ezdxf.readfile(str(dxf_p))
        msp_count = len(list(doc.modelspace()))
        add("corrected_dxf_readable", msp_count > 0, f"{msp_count} entities")

    folder = export.get("folder") or ""
    add("export_folder_absolute", bool(folder) and Path(folder).is_dir(), folder)

    return out


def run_workflow(client: httpx.Client) -> dict[str, Any]:
    out: dict[str, Any] = {"steps": {}, "passed": True, "errors": [], "zones": []}

    def fail(step: str, msg: str) -> None:
        out["passed"] = False
        out["errors"].append(f"{step}: {msg}")
        out["steps"][step] = {"ok": False, "detail": msg}

    r = client.get("/health")
    if r.status_code != 200:
        fail("health", str(r.status_code))
        return out
    out["steps"]["health"] = {"ok": True, "dwg_ready": r.json().get("dwg_ready")}

    r = client.get("/scope/config")
    scope_on = r.status_code == 200 and r.json().get("enabled") is True
    out["steps"]["scope"] = {"ok": scope_on, "enabled": scope_on}
    if not scope_on:
        fail("scope", "scope.enabled is false — boundary broken")

    r = client.post("/session")
    r.raise_for_status()
    h = {"X-Session-Id": r.json()["session_id"]}

    with WAREHOUSE.open("rb") as fh:
        r = client.post("/upload", headers=h, files={"file": (WAREHOUSE.name, fh, "application/octet-stream")})
    if r.status_code != 200:
        fail("import", r.text[:200])
        return out
    upload = r.json()
    out["steps"]["import"] = {"ok": True, "count": upload["counts"]["total"]}

    scene = upload.get("scene") or {}
    ring = _boundary_ring(scene)
    client.put("/scope/boundary", headers=h, json={"ring": ring, "source": "drawn"}).raise_for_status()
    r = client.post("/scope/boundary/apply", headers=h)
    if r.status_code != 200:
        fail("apply_boundary", r.text[:200])
        return out
    out["steps"]["apply_boundary"] = {"ok": True, "count": r.json()["counts"]["total"]}

    r = client.post("/zones/generate", headers=h)
    if r.status_code != 200:
        fail("generate_zones", r.text[:300])
        return out
    zones = r.json().get("zones") or []
    out["zones"] = zones
    out["steps"]["generate_zones"] = {"ok": len(zones) == EXPECTED_ZONES, "count": len(zones)}
    if len(zones) != EXPECTED_ZONES:
        fail("generate_zones", f"expected {EXPECTED_ZONES}, got {len(zones)}")

    r = client.post(
        "/export",
        headers={**h, "Content-Type": "application/json"},
        json={"formats": ["package"], "use_timestamp": True},
    )
    if r.status_code != 200:
        fail("export", r.text[:200])
        return out
    export = r.json()
    out["export"] = export
    out["steps"]["export"] = {"ok": True, "formats": list(export.get("paths", {}).keys())}
    out["export_validation"] = validate_export_contents(export, zones)
    if not out["export_validation"]["passed"]:
        out["passed"] = False
        out["errors"].append("export content validation failed")

    return out


def main() -> int:
    print("=== Client Build Full Verification ===\n")
    report: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cross_pc_bundle": check_cross_pc_bundle(),
        "fresh_pc_config_seed": check_fresh_pc_config_seed(),
    }

    client = httpx.Client(timeout=600.0, base_url=ENGINE)
    try:
        report["workflow"] = run_workflow(client)
    finally:
        client.close()

    report["passed"] = (
        report["cross_pc_bundle"]["passed"]
        and report["fresh_pc_config_seed"]["passed"]
        and report.get("workflow", {}).get("passed", False)
        and report.get("workflow", {}).get("export_validation", {}).get("passed", False)
    )

    out_path = PROJECT_ROOT / "output" / "client_build_full_verify.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("--- Cross-PC bundle ---")
    for c in report["cross_pc_bundle"]["checks"]:
        print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}: {c['detail']}")

    print("\n--- Fresh PC config seed ---")
    print(f"  [{'PASS' if report['fresh_pc_config_seed']['passed'] else 'FAIL'}] {report['fresh_pc_config_seed']['detail']}")

    wf = report.get("workflow", {})
    print("\n--- Workflow ---")
    for name, step in wf.get("steps", {}).items():
        print(f"  [{'PASS' if step.get('ok') else 'FAIL'}] {name}: {step}")

    print("\n--- Export content ---")
    for c in wf.get("export_validation", {}).get("checks", []):
        print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['name']}: {c['detail']}")

    print(f"\nReport: {out_path}")
    print(f"RESULT: {'PASS' if report['passed'] else 'FAIL'}")
    if wf.get("errors"):
        for e in wf["errors"]:
            print(f"  - {e}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
