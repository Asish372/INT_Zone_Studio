"""Suspected gap region discovery for workspace validation."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Point, Polygon

from src.endpoint_matching import DEFAULT_TIER2_STRUCTURAL_LAYERS
from src.gap_handler import iterative_close_gaps
from src.layer_resolver import resolve_wall_layers
from src.models import SeedRequest
from src.parser import get_modelspace, load_dxf
from src.seed_resolver import resolve_seed_region
from src.units import scale_factor
from src.validation_diagnostics import (
    analyze_gaps,
    endpoint_layer_map,
    explain_within_threshold_unclosed,
    extract_tagged_segments,
    snap_tagged_endpoints,
)

PRIORITY_STATUS = {
    "within_threshold_unclosed": 100,
    "above_threshold_close": 80,
    "orphan_endpoint": 60,
    "large_gap_manual_review": 40,
}


def _gap_midpoint(gap) -> tuple[float, float]:
    if not math.isnan(gap.endpoint_b_x):
        return (
            (gap.endpoint_a_x + gap.endpoint_b_x) / 2,
            (gap.endpoint_a_y + gap.endpoint_b_y) / 2,
        )
    return (gap.endpoint_a_x, gap.endpoint_a_y)


def _offset_inward(
    x: float,
    y: float,
    segments: list[LineString],
    delta: float = 75.0,
) -> tuple[float, float]:
    if not segments:
        return x, y
    pt = Point(x, y)
    nearest_seg = min(segments, key=lambda s: pt.distance(s))
    coords = list(nearest_seg.coords)
    sx, sy = coords[0]
    ex, ey = coords[-1]
    p_on = nearest_seg.interpolate(nearest_seg.project(pt))
    dx = x - p_on.x
    dy = y - p_on.y
    length = math.hypot(dx, dy)
    if length < 1e-6:
        nx, ny = -(ey - sy), (ex - sx)
        nlen = math.hypot(nx, ny) or 1.0
        return x + nx / nlen * delta, y + ny / nlen * delta
    return x + dx / length * delta, y + dy / length * delta


def _gap_bbox(
    ax: float,
    ay: float,
    bx: float | None,
    by: float | None,
    pad: float = 250.0,
) -> list[float]:
    if bx is not None and by is not None and not (math.isnan(bx) or math.isnan(by)):
        min_x = min(ax, bx) - pad
        max_x = max(ax, bx) + pad
        min_y = min(ay, by) - pad
        max_y = max(ay, by) + pad
    else:
        min_x = ax - pad
        max_x = ax + pad
        min_y = ay - pad
        max_y = ay + pad
    return [min_x, min_y, max_x, max_y]


def _prepare_tagged_and_segments(dxf_path: Path, config: dict[str, Any]):
    msp = get_modelspace(load_dxf(dxf_path))
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
    return snapped, segments


def analyze_suspected_gaps(
    *,
    dxf_path: Path | str | None,
    config: dict[str, Any],
    segments: list[LineString],
    auto_polygons: list[Polygon],
    source_file: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if dxf_path is None:
        return [], {"total": 0, "recoverable": 0, "informational": 0}

    path = Path(dxf_path)
    if not path.is_file():
        return [], {"total": 0, "recoverable": 0, "informational": 0}

    geometry_cfg = config.get("geometry", {})
    gap_threshold = float(geometry_cfg.get("gap_threshold", 500))
    max_angle = float(geometry_cfg.get("max_gap_angle", 30))
    unit = geometry_cfg.get("drawing_unit", "mm")
    scale = scale_factor(unit)

    try:
        snapped, closed_segments = _prepare_tagged_and_segments(path, config)
    except Exception:
        snapped = []
        closed_segments = segments

    gaps = analyze_gaps(snapped, source_file or path.name, gap_threshold)
    failure_details = {
        (d.endpoint_a_x, d.endpoint_a_y, d.endpoint_b_x, d.endpoint_b_y): d
        for d in explain_within_threshold_unclosed(
            snapped, source_file or path.name, gap_threshold, max_angle
        )
    }

    regions: list[dict[str, Any]] = []
    seen: set[tuple[float, float]] = set()
    idx = 0

    for gap in gaps:
        if gap.status not in PRIORITY_STATUS:
            continue
        mx, my = _gap_midpoint(gap)
        sx, sy = _offset_inward(mx, my, closed_segments or segments)
        key = (round(sx, 1), round(sy, 1))
        if key in seen:
            continue
        seen.add(key)

        failure = failure_details.get(
            (gap.endpoint_a_x, gap.endpoint_a_y, gap.endpoint_b_x, gap.endpoint_b_y)
        )
        failure_reason = failure.failure_reason if failure else None

        seed = SeedRequest(
            drawing=source_file or path.name,
            x=sx,
            y=sy,
            id=f"gap-{idx:03d}",
            label_hint=f"gap-{gap.status}",
        )
        resolution = resolve_seed_region(
            seed,
            closed_segments or segments,
            config,
            auto_polygons=auto_polygons,
        )
        recoverable = resolution.polygon is not None and resolution.status == "ok"
        area_m2 = None
        if resolution.polygon is not None:
            area_m2 = round(float(resolution.polygon.area) * (scale**2), 4)

        priority = PRIORITY_STATUS.get(gap.status, 0)
        confidence = priority + (20 if recoverable else 0)
        if failure_reason == "bearing_mismatch_suspected":
            confidence -= 5

        bx = gap.endpoint_b_x if not math.isnan(gap.endpoint_b_x) else None
        by = gap.endpoint_b_y if not math.isnan(gap.endpoint_b_y) else None
        bbox = _gap_bbox(gap.endpoint_a_x, gap.endpoint_a_y, bx, by)

        regions.append(
            {
                "id": f"gap-{idx:03d}",
                "center": [round(mx, 3), round(my, 3)],
                "seed_point": [round(sx, 3), round(sy, 3)],
                "bbox": bbox,
                "gap_distance": None
                if math.isnan(gap.gap_distance)
                else round(gap.gap_distance, 3),
                "status": gap.status,
                "failure_reason": failure_reason,
                "recoverable": recoverable,
                "priority": priority,
                "confidence": confidence,
                "area_estimate_m2": area_m2,
            }
        )
        idx += 1

    regions.sort(key=lambda r: (-r["confidence"], -r["priority"], r["id"]))
    recoverable_count = sum(1 for r in regions if r["recoverable"])
    summary = {
        "total": len(regions),
        "recoverable": recoverable_count,
        "informational": max(0, len(regions) - recoverable_count),
    }
    return regions, summary
