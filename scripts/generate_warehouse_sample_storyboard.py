#!/usr/bin/env python3
"""Generate warehouse 5-page detection visual sample (PDF blocked until approved)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src.extractor import extract_all_segments, extract_entities
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.units import scale_factor
from src.zone_engine import build_int_zone_pipeline, detect_faces_from_modelspace
from src.zone_engine.detection_visualize import (
    pick_dense_zoom_targets,
    render_all_detected_with_usage,
    render_detection_page_set,
    verify_step2_faces,
)
from src.zone_engine.face_assigner import polygons_to_faces

WAREHOUSE_KEY = "6276.S111-WAREHOUSE_SLAB_PLAN-Rev_F"
DXF = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
MANIFEST = PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml"
OUT_DIR = PROJECT_ROOT / "output" / "detection_visualization" / "sample"


def extract_source_segments(msp, config):
    layers_cfg = config.get("layers", {})
    ignore_layers = layers_cfg.get("ignore_layers", [])
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    entities = extract_entities(msp, resolution.wall_layers, ignore_layers)
    arc_segments = int(config.get("accuracy", {}).get("arc_segments", 64))
    return extract_all_segments(entities, arc_segments=arc_segments)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))

    doc = load_dxf(DXF)
    msp = get_modelspace(doc)
    unit_scale = scale_factor(config.get("geometry", {}).get("drawing_unit", "mm"))
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest.get("zone_count_expected")

    result = build_int_zone_pipeline(
        msp, config,
        source_file=DXF.name,
        unit_scale_m=unit_scale,
        expected_int_count=int(expected) if expected else None,
        manifest_path=MANIFEST,
    )

    polygons = detect_faces_from_modelspace(msp, config)
    all_faces = polygons_to_faces(polygons, unit_scale_m=unit_scale)
    segments = extract_source_segments(msp, config)
    check = verify_step2_faces(result, all_faces)
    zoom_labels = pick_dense_zoom_targets(result, count=5)

    pages = render_detection_page_set(
        result, all_faces, segments, OUT_DIR, WAREHOUSE_KEY, dpi=200, zoom_count=5,
    )

    import matplotlib.pyplot as plt

    ax = render_all_detected_with_usage(result, all_faces, segments)
    diag_path = OUT_DIR / f"{WAREHOUSE_KEY}_all_detected_diagnostic.png"
    ax.figure.savefig(diag_path, dpi=150, bbox_inches="tight")
    plt.close(ax.figure)

    meta = {
        "drawing": WAREHOUSE_KEY,
        "verification": {k: v for k, v in check.items() if k not in ("assigned_ids", "zone_ids")},
        "pages": {k: str(v.relative_to(PROJECT_ROOT)) for k, v in pages.items()},
        "diagnostic_all_detected": str(diag_path.relative_to(PROJECT_ROOT)),
        "zoom_zones": zoom_labels,
        "step2_definition": (
            "Page 2/3: assignment.assignments polygons — same face_ids unioned in aggregate_int_zones()"
        ),
        "pdf_status": "BLOCKED — awaiting visual approval of page2 + page3",
    }
    meta_path = OUT_DIR / "warehouse_sample_verification.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("=" * 60)
    print("WAREHOUSE DETECTION VISUAL SAMPLE (5 pages)")
    print("=" * 60)
    print(f"Step 2 faces (INT input): {check['assigned_count']} polygons")
    print(f"assigned == zone.face_ids: {check['assigned_equals_zones']}")
    print(f"Zoom callouts: {', '.join(zoom_labels)}")
    print()
    for name, path in pages.items():
        print(f"  {name}: {path}")
    print(f"  diagnostic: {diag_path}")
    print()
    print("PDF: BLOCKED — approve page2_detected + page3_zooms first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
