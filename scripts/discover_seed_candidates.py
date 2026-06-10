#!/usr/bin/env python3
"""Discover candidate seed points from gap diagnostics and validate recovery."""

from __future__ import annotations

import json
import logging
import math
import sys
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.converter import ensure_dxf, find_oda_converter
from src.detector import detect_regions
from src.endpoint_matching import DEFAULT_TIER2_STRUCTURAL_LAYERS
from src.gap_handler import iterative_close_gaps
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.seed_resolver import resolve_seed_region
from src.validation_diagnostics import (
    analyze_gaps,
    endpoint_layer_map,
    extract_tagged_segments,
    snap_tagged_endpoints,
)

logger = logging.getLogger(__name__)


def _gap_midpoint(gap) -> tuple[float, float]:
    if not math.isnan(gap.endpoint_b_x):
        return (
            (gap.endpoint_a_x + gap.endpoint_b_x) / 2,
            (gap.endpoint_a_y + gap.endpoint_b_y) / 2,
        )
    return (gap.endpoint_a_x, gap.endpoint_a_y)


def _offset_inward(x: float, y: float, segments, delta: float = 75.0) -> tuple[float, float]:
    """Nudge seed slightly off gap endpoints toward interior."""
    from shapely.geometry import LineString, Point
    from shapely.ops import nearest_points

    pt = Point(x, y)
    if not segments:
        return x, y
    nearest_seg = min(segments, key=lambda s: pt.distance(s))
    p_on_seg, _ = nearest_points(nearest_seg, pt)
    dx = x - p_on_seg.x
    dy = y - p_on_seg.y
    length = math.hypot(dx, dy)
    if length < 1e-6:
        # Perpendicular nudge along segment normal
        coords = list(nearest_seg.coords)
        sx, sy = coords[0]
        ex, ey = coords[-1]
        nx, ny = -(ey - sy), (ex - sx)
        nlen = math.hypot(nx, ny) or 1.0
        return x + nx / nlen * delta, y + ny / nlen * delta
    return x + dx / length * delta, y + dy / length * delta


def prepare_segments(msp, config: dict) -> list:
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


def discover_seeds_for_drawing(cad_path: Path, config: dict, cache_dir: Path) -> dict:
    dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
    doc = load_dxf(dxf_path)
    msp = get_modelspace(doc)
    segments = prepare_segments(msp, config)
    auto = detect_regions(segments, config)
    gap_threshold = float(config.get("geometry", {}).get("gap_threshold", 500))
    tagged = extract_tagged_segments(
        msp,
        resolve_wall_layers(msp, config, auto_fallback=True).wall_layers,
        config.get("layers", {}).get("ignore_layers", []),
        int(config.get("accuracy", {}).get("arc_segments", 64)),
    )
    snapped = snap_tagged_endpoints(tagged, float(config.get("geometry", {}).get("snap_tolerance", 1)))
    gaps = analyze_gaps(snapped, cad_path.name, gap_threshold)

    priority_status = {
        "within_threshold_unclosed",
        "above_threshold_close",
        "orphan_endpoint",
        "large_gap_manual_review",
    }

    candidates = []
    seen: set[tuple[float, float]] = set()
    idx = 0
    for gap in gaps:
        if gap.status not in priority_status:
            continue
        mx, my = _gap_midpoint(gap)
        sx, sy = _offset_inward(mx, my, segments)
        key = (round(sx, 1), round(sy, 1))
        if key in seen:
            continue
        seen.add(key)

        from src.models import SeedRequest

        seed = SeedRequest(
            drawing=cad_path.name,
            x=sx,
            y=sy,
            id=f"auto-{idx:03d}",
            label_hint=f"gap-{gap.status}",
        )
        idx += 1
        res = resolve_seed_region(seed, segments, config, auto_polygons=auto)
        if res.status != "ok":
            continue
        candidates.append(
            {
                "id": seed.id,
                "x": round(sx, 3),
                "y": round(sy, 3),
                "label_hint": seed.label_hint,
                "gap_status": gap.status,
                "gap_distance": gap.gap_distance,
                "area_m2": round(res.area_m2_drawing or 0, 4),
            }
        )

    return {
        "drawing": cad_path.name,
        "auto_detected": len(auto),
        "candidate_seeds": len(candidates),
        "seeds": candidates,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    config_path = PROJECT_ROOT / "config.yaml"
    with config_path.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    input_dir = PROJECT_ROOT / config.get("input", {}).get("input_dir", "./input")
    cache_dir = PROJECT_ROOT / config.get("output", {}).get("output_dir", "./output") / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not find_oda_converter():
        logger.error("ODA File Converter required for DWG inputs")
        return 1

    cad_files = sorted({*input_dir.glob("*.dwg"), *input_dir.glob("*.DWG")})
    if not cad_files:
        logger.error("No DWG files in %s", input_dir)
        return 1

    manifest = {"generated": datetime.now().isoformat(), "drawings": []}
    total_recoverable = 0
    for cad_path in cad_files:
        logger.info("Discovering seeds: %s", cad_path.name)
        result = discover_seeds_for_drawing(cad_path, config, cache_dir)
        manifest["drawings"].append(result)
        total_recoverable += result["candidate_seeds"]
        logger.info(
            "  auto=%d recoverable_seeds=%d",
            result["auto_detected"],
            result["candidate_seeds"],
        )

    out_json = PROJECT_ROOT / "reference" / "seed_discovery_report.json"
    out_yaml = PROJECT_ROOT / "reference" / "missed_regions_seeds.yaml"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    yaml_seeds = {
        "description": "Auto-discovered seed candidates from gap diagnostics (POC validation)",
        "drawings": [
            {
                "drawing": d["drawing"],
                "seeds": [
                    {k: v for k, v in s.items() if k in ("id", "x", "y", "label_hint")}
                    for s in d["seeds"]
                ],
            }
            for d in manifest["drawings"]
            if d["seeds"]
        ],
    }
    with out_yaml.open("w", encoding="utf-8") as fh:
        yaml.dump(yaml_seeds, fh, default_flow_style=False, sort_keys=False)

    print(f"\nTotal recoverable seed candidates: {total_recoverable}")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_yaml}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
