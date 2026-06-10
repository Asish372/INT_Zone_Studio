#!/usr/bin/env python3
"""Analyze unsupported entity types vs block boundary contribution."""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from shapely.geometry import LineString, Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.detection_coverage import INSERT_PROXIMITY_RADIUS, UNSUPPORTED_BOUNDARY_TYPES
from src.gap_handler import _round_point
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.validation_diagnostics import (
    analyze_gaps,
    extract_tagged_segments,
    snap_tagged_endpoints,
)

ANNOTATION_LAYER_HINTS = (
    "ANNO",
    "TEXT",
    "NOTE",
    "DIM",
    "IDEN",
    "GRID",
    "TITLE",
    "VIEWPORT",
    "GENF",
    "COLS",
    "FSTN",
)


def _is_annotation_layer(layer: str) -> bool:
    upper = layer.upper()
    return any(h in upper for h in ANNOTATION_LAYER_HINTS)


def _entity_point(entity) -> tuple[float, float] | None:
    dxftype = entity.dxftype()
    try:
        if dxftype == "INSERT":
            ins = entity.dxf.insert
            return ins.x, ins.y
        if dxftype in ("MTEXT", "TEXT"):
            ins = entity.dxf.insert
            return ins.x, ins.y
        if dxftype == "CIRCLE":
            c = entity.dxf.center
            return c.x, c.y
        if dxftype == "HATCH":
            paths = entity.paths
            if paths:
                for path in paths:
                    if hasattr(path, "vertices") and path.vertices:
                        v = path.vertices[0]
                        return v[0], v[1]
            return None
        if dxftype == "DIMENSION":
            defpoint = getattr(entity.dxf, "defpoint", None)
            if defpoint:
                return defpoint.x, defpoint.y
    except Exception:
        return None
    return None


def _insert_block_geometry_stats(doc, entity) -> dict:
    """Inspect block definition geometry for an INSERT."""
    name = entity.dxf.name
    try:
        block = doc.blocks.get(name)
    except Exception:
        return {"block_name": name, "found": False}

    type_counts: Counter[str] = Counter()
    line_count = 0
    for e in block:
        type_counts[e.dxftype()] += 1
        if e.dxftype() in ("LINE", "LWPOLYLINE", "POLYLINE", "ARC"):
            line_count += 1

    return {
        "block_name": name,
        "found": True,
        "entity_types": dict(type_counts),
        "boundary_entities": line_count,
        "has_boundary_geometry": line_count > 0,
    }


def _nearest_segment_distance(
    x: float, y: float, segments: list[LineString]
) -> float:
    pt = Point(x, y)
    best = float("inf")
    for seg in segments:
        d = pt.distance(seg)
        if d < best:
            best = d
    return best


def _free_endpoints(tagged) -> list[tuple[float, float]]:
    counts: dict[tuple[float, float], int] = defaultdict(int)
    for item in tagged:
        coords = list(item.line.coords)
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        counts[a] += 1
        counts[b] += 1
    return [pt for pt, c in counts.items() if c == 1]


def analyze_drawing(dxf_path: Path, config: dict) -> dict:
    doc = load_dxf(dxf_path)
    msp = get_modelspace(doc)
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    ignore_layers = config.get("layers", {}).get("ignore_layers", [])
    arc_segments = int(config.get("accuracy", {}).get("arc_segments", 64))
    gap_threshold = float(config.get("geometry", {}).get("gap_threshold", 500))

    tagged = extract_tagged_segments(
        msp, resolution.wall_layers, ignore_layers, arc_segments
    )
    segments = [t.line for t in tagged]
    snapped = snap_tagged_endpoints(tagged, float(config.get("geometry", {}).get("snap_tolerance", 1)))
    gap_records = analyze_gaps(snapped, dxf_path.name, gap_threshold)
    free_pts = _free_endpoints(snapped)

    gap_pts: list[tuple[float, float]] = []
    for g in gap_records:
        if g.status in (
            "within_threshold_unclosed",
            "large_gap_manual_review",
            "orphan_endpoint",
            "above_threshold_close",
        ):
            gap_pts.append((g.endpoint_a_x, g.endpoint_a_y))
            if not math.isnan(g.endpoint_b_x):
                gap_pts.append((g.endpoint_b_x, g.endpoint_b_y))

    unsupported_by_type: Counter[str] = Counter()
    annotation_by_type: Counter[str] = Counter()
    boundary_candidate_by_type: Counter[str] = Counter()
    near_gap_by_type: Counter[str] = Counter()
    near_segment_by_type: Counter[str] = Counter()
    near_free_endpoint_by_type: Counter[str] = Counter()
    layer_by_type: dict[str, Counter[str]] = defaultdict(Counter)

    insert_stats: list[dict] = []
    insert_block_summary: Counter[str] = Counter()
    insert_with_boundary_blocks = 0
    insert_without_boundary_blocks = 0

    SEGMENT_NEAR_RADIUS = 500.0

    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype not in UNSUPPORTED_BOUNDARY_TYPES:
            continue

        unsupported_by_type[dxftype] += 1
        layer = entity.dxf.layer or "0"
        layer_by_type[dxftype][layer] += 1

        if _is_annotation_layer(layer):
            annotation_by_type[dxftype] += 1
        else:
            boundary_candidate_by_type[dxftype] += 1

        pt = _entity_point(entity)
        if pt is None:
            continue
        x, y = pt

        if any(math.hypot(x - gx, y - gy) <= INSERT_PROXIMITY_RADIUS for gx, gy in gap_pts):
            near_gap_by_type[dxftype] += 1

        if any(math.hypot(x - fx, y - fy) <= INSERT_PROXIMITY_RADIUS for fx, fy in free_pts):
            near_free_endpoint_by_type[dxftype] += 1

        seg_dist = _nearest_segment_distance(x, y, segments)
        if seg_dist <= SEGMENT_NEAR_RADIUS:
            near_segment_by_type[dxftype] += 1

        if dxftype == "INSERT":
            stats = _insert_block_geometry_stats(doc, entity)
            stats["layer"] = layer
            stats["insert_x"] = x
            stats["insert_y"] = y
            stats["nearest_segment_dist"] = round(seg_dist, 2)
            stats["near_gap"] = dxftype in near_gap_by_type  # approximate
            insert_stats.append(stats)
            insert_block_summary[stats["block_name"]] += 1
            if stats.get("has_boundary_geometry"):
                insert_with_boundary_blocks += 1
            else:
                insert_without_boundary_blocks += 1

    # HATCH boundary path analysis
    hatch_with_paths = 0
    hatch_on_boundary_layers = 0
    for entity in msp:
        if entity.dxftype() != "HATCH":
            continue
        layer = entity.dxf.layer or "0"
        if entity.paths:
            hatch_with_paths += 1
        if not _is_annotation_layer(layer):
            hatch_on_boundary_layers += 1

    return {
        "drawing": dxf_path.name,
        "detected_segments": len(segments),
        "open_gap_points": len(gap_pts),
        "free_endpoints": len(free_pts),
        "unsupported_by_type": dict(unsupported_by_type),
        "annotation_by_type": dict(annotation_by_type),
        "boundary_candidate_by_type": dict(boundary_candidate_by_type),
        "near_gap_by_type": dict(near_gap_by_type),
        "near_free_endpoint_by_type": dict(near_free_endpoint_by_type),
        "near_segment_by_type": dict(near_segment_by_type),
        "layer_by_type": {k: dict(v.most_common(10)) for k, v in layer_by_type.items()},
        "insert_total": unsupported_by_type.get("INSERT", 0),
        "insert_with_boundary_blocks": insert_with_boundary_blocks,
        "insert_without_boundary_blocks": insert_without_boundary_blocks,
        "insert_block_names": dict(insert_block_summary.most_common(15)),
        "insert_near_gap_count": near_gap_by_type.get("INSERT", 0),
        "insert_near_segment_count": near_segment_by_type.get("INSERT", 0),
        "hatch_total": unsupported_by_type.get("HATCH", 0),
        "hatch_with_paths": hatch_with_paths,
        "hatch_on_boundary_layers": hatch_on_boundary_layers,
        "mtext_total": unsupported_by_type.get("MTEXT", 0),
        "mtext_annotation_layers": annotation_by_type.get("MTEXT", 0),
        "mtext_near_gap": near_gap_by_type.get("MTEXT", 0),
        "mtext_near_segment": near_segment_by_type.get("MTEXT", 0),
    }


def main() -> int:
    config_path = PROJECT_ROOT / "config.yaml"
    with config_path.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    cache_dir = PROJECT_ROOT / "output" / ".dxf_cache"
    drawings = sorted(cache_dir.glob("*.dxf"))
    results = [analyze_drawing(p, config) for p in drawings]

    out = PROJECT_ROOT / "output" / "entity_support_analysis_data.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
