#!/usr/bin/env python3
"""Build seed manifest from polygon centroids missing after auto dedupe/filter."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.converter import ensure_dxf, find_oda_converter
from src.detector import detect_regions, filter_polygons, polygonize_regions, remove_duplicates
from src.endpoint_matching import DEFAULT_TIER2_STRUCTURAL_LAYERS
from src.gap_handler import iterative_close_gaps
from src.geometry_precision import normalize_polygon
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.seed_resolver import polygon_iou, resolve_seed_region
from src.models import SeedRequest
from src.validation_diagnostics import endpoint_layer_map, extract_tagged_segments, snap_tagged_endpoints
from shapely.geometry import MultiLineString, Point

logger = logging.getLogger(__name__)


def prepare_segments(msp, config):
    layers_cfg = config.get("layers", {})
    accuracy_cfg = config.get("accuracy", {})
    geometry_cfg = config.get("geometry", {})
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    tagged = extract_tagged_segments(
        msp,
        resolution.wall_layers,
        layers_cfg.get("ignore_layers", []),
        int(accuracy_cfg.get("arc_segments", 64)),
    )
    snap_tol = float(geometry_cfg.get("snap_tolerance", 1))
    snapped = snap_tagged_endpoints(tagged, snap_tol)
    layers_map = endpoint_layer_map(snapped)
    segments = [t.line for t in snapped]
    segments, _ = iterative_close_gaps(
        segments,
        float(geometry_cfg.get("gap_threshold", 500)),
        float(geometry_cfg.get("max_gap_angle", 30)),
        snap_tol=0.0,
        max_passes=int(geometry_cfg.get("iterative_max_passes", 3)),
        colinear_profile=bool(geometry_cfg.get("colinear_profile_match", True)),
        tier2_enabled=bool(geometry_cfg.get("tier2_threshold_enabled", False)),
        tier2_threshold=float(geometry_cfg.get("tier2_gap_threshold", 1000)),
        endpoint_layers=layers_map,
        structural_layers=frozenset(
            geometry_cfg.get("tier2_structural_layers", list(DEFAULT_TIER2_STRUCTURAL_LAYERS))
        ),
    )
    return segments


def _auto_polygons(segments, config):
    return detect_regions(segments, config)


def _raw_polygons(segments, config):
    geometry_cfg = config.get("geometry", {})
    accuracy_cfg = config.get("accuracy", {})
    unit = geometry_cfg.get("drawing_unit", "mm")
    min_area = float(accuracy_cfg.get("exhaustive_min_area_m2", 0.01))
    raw = polygonize_regions(MultiLineString(segments) if segments else MultiLineString())
    return filter_polygons(raw, min_area, unit, exhaustive=True)


def find_missed_centroid_seeds(cad_path: Path, config: dict, cache_dir: Path, iou_threshold: float = 0.90):
    dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
    doc = load_dxf(dxf_path)
    msp = get_modelspace(doc)
    segments = prepare_segments(msp, config)
    auto = _auto_polygons(segments, config)
    raw = _raw_polygons(segments, config)

    missed = []
    for idx, poly in enumerate(raw):
        norm = normalize_polygon(poly)
        if norm is None:
            continue
        if any(polygon_iou(norm, a) >= iou_threshold for a in auto):
            continue
        c = norm.centroid
        seed = SeedRequest(
            drawing=cad_path.name,
            x=c.x,
            y=c.y,
            id=f"miss-centroid-{idx:04d}",
            label_hint="auto-discovered miss",
        )
        res = resolve_seed_region(seed, segments, config, auto_polygons=auto)
        if res.status != "ok":
            continue
        missed.append(
            {
                "id": seed.id,
                "x": round(c.x, 3),
                "y": round(c.y, 3),
                "label_hint": seed.label_hint,
                "area_m2": round(res.area_m2_drawing or 0, 4),
            }
        )

    return {
        "drawing": cad_path.name,
        "auto_detected": len(auto),
        "raw_faces": len(raw),
        "missed_seeds": len(missed),
        "seeds": missed,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    cache_dir = PROJECT_ROOT / "output" / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    input_dir = PROJECT_ROOT / "input"

    if not find_oda_converter():
        logger.error("ODA required")
        return 1

    cad_files = sorted({*input_dir.glob("*.dwg"), *input_dir.glob("*.DWG")})
    manifest = {"generated": datetime.now().isoformat(), "drawings": []}
    total_seeds = 0
    total_gain = 0

    for cad_path in cad_files:
        result = find_missed_centroid_seeds(cad_path, config, cache_dir)
        manifest["drawings"].append(result)
        total_seeds += result["missed_seeds"]
        total_gain += result["missed_seeds"]
        logger.info(
            "%s: auto=%d raw=%d missed_seeds=%d",
            cad_path.name,
            result["auto_detected"],
            result["raw_faces"],
            result["missed_seeds"],
        )

    out_yaml = PROJECT_ROOT / "reference" / "missed_regions_seeds.yaml"
    yaml_doc = {
        "description": "Centroid seeds for raw faces not present in auto-detected output",
        "drawings": [
            {"drawing": d["drawing"], "seeds": d["seeds"]}
            for d in manifest["drawings"]
            if d["seeds"]
        ],
    }
    with out_yaml.open("w", encoding="utf-8") as fh:
        yaml.dump(yaml_doc, fh, default_flow_style=False, sort_keys=False)

    report = PROJECT_ROOT / "reference" / "seed_centroid_discovery.json"
    report.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Total recoverable via centroid seeds: {total_gain}")
    print(f"Wrote {out_yaml}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
