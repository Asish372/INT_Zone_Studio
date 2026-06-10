#!/usr/bin/env python3
"""Generate civil-engineer detection visuals (intermediate PNGs) and manifest for PDF."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
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
    render_detection_page_set,
    verify_step2_faces,
)
from src.zone_engine.face_assigner import polygons_to_faces

OUT_DIR = PROJECT_ROOT / "output" / "detection_visualization"

DRAWINGS = [
    {
        "file_key": "S111_A",
        "delivery_folder": "S111_A",
        "title": "S111_A",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_A.dxf",
        "manifest": PROJECT_ROOT / "reference" / "s111_a_zones_manifest.yaml",
    },
    {
        "file_key": "S111_J",
        "delivery_folder": "J33B",
        "title": "S111_J (J33B)",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_J.dxf",
        "manifest": PROJECT_ROOT / "reference" / "j33b_zones_manifest.yaml",
    },
    {
        "file_key": "6276.S111-WAREHOUSE_SLAB_PLAN-Rev_F",
        "delivery_folder": "J33A",
        "title": "6276.S111-WAREHOUSE (J33A)",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf",
        "manifest": PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml",
    },
]


def extract_source_segments(msp, config):
    layers_cfg = config.get("layers", {})
    ignore_layers = layers_cfg.get("ignore_layers", [])
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    entities = extract_entities(msp, resolution.wall_layers, ignore_layers)
    arc_segments = int(config.get("accuracy", {}).get("arc_segments", 64))
    return extract_all_segments(entities, arc_segments=arc_segments)


def process_drawing(item: dict, config: dict, date_str: str) -> dict:
    file_key = item["file_key"]
    out_sub = OUT_DIR / file_key
    out_sub.mkdir(parents=True, exist_ok=True)

    manifest = yaml.safe_load(item["manifest"].read_text(encoding="utf-8"))
    expected = manifest.get("zone_count_expected")

    doc = load_dxf(item["dxf"])
    msp = get_modelspace(doc)
    unit_scale = scale_factor(config.get("geometry", {}).get("drawing_unit", "mm"))

    result = build_int_zone_pipeline(
        msp,
        config,
        source_file=item["dxf"].name,
        unit_scale_m=unit_scale,
        expected_int_count=int(expected) if expected is not None else None,
        manifest_path=item["manifest"],
    )

    polygons = detect_faces_from_modelspace(msp, config)
    all_faces = polygons_to_faces(polygons, unit_scale_m=unit_scale)
    segments = extract_source_segments(msp, config)
    check = verify_step2_faces(result, all_faces)
    if not check["assigned_equals_zones"]:
        raise RuntimeError(f"{file_key}: face assignment != zone union (lineage broken)")

    zoom_labels = pick_dense_zoom_targets(result, count=5)

    pages = render_detection_page_set(
        result, all_faces, segments, out_sub, file_key,
        zoom_count=5, date_str=date_str,
    )

    return {
        "file_key": file_key,
        "title": item["title"],
        "delivery_folder": item["delivery_folder"],
        "source_dxf": item["dxf"].name,
        "zoom_zones": zoom_labels,
        "detected_faces": len(all_faces),
        "assigned_faces": check["assigned_count"],
        "lineage_ok": check["assigned_equals_zones"],
        "pages": {k: str(v.relative_to(PROJECT_ROOT)) for k, v in pages.items()},
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    results = []
    for item in DRAWINGS:
        print(f"Rendering civil detection visuals: {item['file_key']}...")
        results.append(process_drawing(item, config, date_str))

    manifest_path = OUT_DIR / "detection_visualization_manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    readme = OUT_DIR / "README.txt"
    readme.write_text(
        "\n".join(
            [
                "INT Zone Detection Visualization",
                "================================",
                "",
                "Client deliverable (PDF only):",
                "  DETECTION_VISUALIZATION_REPORT.pdf",
                "",
                "Intermediate PNGs in per-drawing folders are build artifacts.",
                "Do not ship PNG folders to client.",
                "",
                "Regenerate:",
                "  python scripts/generate_detection_visualization.py",
                "  python scripts/generate_detection_visualization_pdf.py",
                "  python scripts/assemble_delivery_package.py",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"\nWrote {manifest_path}")
    for r in results:
        print(
            f"  {r['file_key']}: {r['detected_faces']} detected / "
            f"{r['assigned_faces']} INT-assigned, lineage OK={r['lineage_ok']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
