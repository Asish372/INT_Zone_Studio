"""P2 — Slab clipping, INT labels, and geometry validation for grid bays."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ezdxf.layouts import Modelspace
from shapely.geometry import Polygon

from src.zone_engine.geometry_validation import (
    GeometryValidationSummary,
    validate_bay_geometries,
)
from src.zone_engine.grid_frame import BayCell, GridFrameResult, build_grid_frame
from src.zone_engine.int_labels import assign_int_labels
from src.zone_engine.slab_outline import SlabOutlineResult, extract_slab_outline

logger = logging.getLogger(__name__)


@dataclass
class GridFrameGeometryResult:
    """Grid frame with slab-clipped bays and validation."""

    frame: GridFrameResult
    slab: SlabOutlineResult
    bays: list[BayCell]
    validation: GeometryValidationSummary
    bay_count_before_clip: int
    bay_count_after_clip: int
    warnings: list[str] = field(default_factory=list)


def _clip_bay_to_slab(bay: BayCell, slab: Polygon, unit_scale_m: float) -> None:
    intersection = bay.polygon.intersection(slab)
    if intersection.is_empty:
        bay.clipped_polygon = Polygon()
        bay.clipped_area_m2 = 0.0
        bay.coverage_pct = 0.0
        return

    if intersection.geom_type == "Polygon":
        clipped = intersection
    elif intersection.geom_type == "MultiPolygon":
        clipped = max(intersection.geoms, key=lambda geom: geom.area)
    elif intersection.geom_type == "GeometryCollection":
        polys = [g for g in intersection.geoms if g.geom_type == "Polygon"]
        clipped = max(polys, key=lambda geom: geom.area) if polys else Polygon()
    else:
        clipped = Polygon()

    bay.clipped_polygon = clipped
    bay.clipped_area_m2 = clipped.area * (unit_scale_m**2)
    raw = bay.raw_area_m2
    bay.coverage_pct = (bay.clipped_area_m2 / raw * 100.0) if raw > 1e-9 else 0.0


def clip_bays_to_slab(
    bays: list[BayCell],
    slab: SlabOutlineResult,
    *,
    unit_scale_m: float = 0.001,
) -> int:
    """Clip each bay polygon to the slab outline. Returns count of non-empty clips."""
    if slab.polygon.is_empty:
        for bay in bays:
            bay.clipped_polygon = Polygon()
            bay.clipped_area_m2 = 0.0
            bay.coverage_pct = 0.0
        return 0

    non_empty = 0
    for bay in bays:
        _clip_bay_to_slab(bay, slab.polygon, unit_scale_m)
        if bay.clipped_area_m2 > 1e-6:
            non_empty += 1
    return non_empty


def trim_bays_to_target_count(
    bays: list[BayCell],
    target_count: int,
) -> tuple[list[BayCell], int]:
    """
    Reduce bay list to target_count when grid overshoots manifest (e.g. J33B 18→17).

    Drops empty clipped bays first, then smallest clipped bays. Returns (bays, removed).
    """
    if target_count < 1 or len(bays) <= target_count:
        return bays, 0

    working = list(bays)
    removed = 0

    while len(working) > target_count:
        empty = [b for b in working if b.clipped_area_m2 < 1e-6]
        if empty:
            working.remove(empty[0])
            removed += 1
            continue
        smallest = min(working, key=lambda b: b.clipped_area_m2)
        working.remove(smallest)
        removed += 1

    return working, removed


def build_grid_frame_geometry(
    msp: Modelspace,
    config: dict,
    *,
    source_file: str = "",
    unit_scale_m: float = 0.001,
    expected_int_count: int | None = None,
    zone_cfg: dict | None = None,
) -> GridFrameGeometryResult:
    """Run P1 grid frame, slab clip, INT labels, and validation."""
    zone_cfg = zone_cfg or config.get("zone_engine", {})
    warnings: list[str] = []

    frame = build_grid_frame(
        msp,
        source_file=source_file,
        grid_layers=zone_cfg.get("grid_layers"),
        include_candidate_layers=zone_cfg.get("include_candidate_layers", True),
        angle_tolerance_deg=float(zone_cfg.get("grid_angle_tolerance_deg", 2.0)),
        position_cluster_mm=float(zone_cfg.get("position_cluster_mm", 500.0)),
        min_line_length_mm=float(zone_cfg.get("min_grid_line_length_mm", 1000.0)),
        expected_int_count=expected_int_count,
        unit_scale_m=unit_scale_m,
    )
    warnings.extend(frame.warnings)

    slab = extract_slab_outline(
        msp,
        config,
        slab_layer=zone_cfg.get("slab_outline_layer", "S-FNDN-1"),
        unit_scale_m=unit_scale_m,
        min_polygon_area_m2=float(zone_cfg.get("slab_min_polygon_area_m2", 100.0)),
        concave_hull_ratio=float(zone_cfg.get("slab_concave_hull_ratio", 0.2)),
    )
    warnings.extend(slab.warnings)

    bays = list(frame.bays)
    for bay in bays:
        bay.raw_area_m2 = bay.area_m2

    count_before = len(bays)
    non_empty = clip_bays_to_slab(bays, slab, unit_scale_m=unit_scale_m)
    count_after = non_empty

    if count_before and non_empty < count_before:
        warnings.append(
            f"{count_before - non_empty} bay(s) are empty after slab clipping."
        )

    target_bays = expected_int_count
    if target_bays is not None and len(bays) > target_bays:
        bays, trimmed = trim_bays_to_target_count(bays, target_bays)
        if trimmed:
            warnings.append(
                f"Trimmed {trimmed} bay(s) to match expected INT count {target_bays}."
            )
            non_empty = sum(1 for b in bays if b.clipped_area_m2 > 1e-6)
            count_after = non_empty

    assign_int_labels(bays)

    validation = validate_bay_geometries(
        bays,
        unit_scale_m=unit_scale_m,
        low_coverage_pct=float(zone_cfg.get("low_coverage_pct", 25.0)),
        overlap_area_m2=float(zone_cfg.get("overlap_area_m2", 0.5)),
    )
    warnings.extend(validation.warnings)

    logger.info(
        "Grid geometry: %d bays, %d non-empty after clip, slab method=%s",
        count_before,
        count_after,
        slab.method,
    )

    return GridFrameGeometryResult(
        frame=frame,
        slab=slab,
        bays=bays,
        validation=validation,
        bay_count_before_clip=count_before,
        bay_count_after_clip=count_after,
        warnings=warnings,
    )
