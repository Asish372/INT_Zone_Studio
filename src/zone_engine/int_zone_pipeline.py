"""P3 — Orchestrate grid geometry, face detection, assignment, and manifest reconciliation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ezdxf.layouts import Modelspace
from shapely.geometry import Polygon

from src.detector import detect_regions
from src.extractor import extract_all_segments, extract_entities
from src.gap_handler import close_gaps, snap_endpoints
from src.layer_resolver import resolve_wall_layers
from src.zone_engine.bay_geometry import GridFrameGeometryResult, build_grid_frame_geometry
from src.zone_engine.face_assigner import assign_faces_to_bays, polygons_to_faces
from src.zone_engine.manifest_reconciliation import load_manifest, reconcile_zones_to_manifest
from src.zone_engine.models import FaceData, IntZonePipelineResult
from src.zone_engine.production_readiness import assess_production_readiness
from src.zone_engine.zone_aggregator import aggregate_int_zones

logger = logging.getLogger(__name__)


def detect_faces_from_modelspace(
    msp: Modelspace,
    config: dict[str, Any],
    *,
    auto_fallback: bool = True,
) -> list[Polygon]:
    """Run Stage 1 polygonize pipeline and return micro-face polygons."""
    layers_cfg = config.get("layers", {})
    ignore_layers = layers_cfg.get("ignore_layers", [])
    resolution = resolve_wall_layers(msp, config, auto_fallback=auto_fallback)
    if not resolution.wall_layers:
        logger.warning("No wall layers resolved for face detection")
        return []

    entities = extract_entities(msp, resolution.wall_layers, ignore_layers)
    if not entities:
        return []

    accuracy_cfg = config.get("accuracy", {})
    arc_segments = int(accuracy_cfg.get("arc_segments", 64))
    segments = extract_all_segments(entities, arc_segments=arc_segments)
    if not segments:
        return []

    geometry_cfg = config.get("geometry", {})
    segments = snap_endpoints(segments, float(geometry_cfg.get("snap_tolerance", 1)))
    segments, _ = close_gaps(
        segments,
        float(geometry_cfg.get("gap_threshold", 500)),
        float(geometry_cfg.get("max_gap_angle", 30)),
    )
    return detect_regions(segments, config)


def build_int_zone_pipeline(
    msp: Modelspace,
    config: dict[str, Any],
    *,
    source_file: str = "",
    unit_scale_m: float = 0.001,
    expected_int_count: int | None = None,
    manifest_path: Path | str | None = None,
    faces: list[FaceData] | None = None,
    zone_cfg: dict | None = None,
    auto_detect_faces: bool = True,
) -> IntZonePipelineResult:
    """
    Full P2 + P3: grid frame geometry, face assignment, zone union, manifest gates.
    """
    zone_cfg = zone_cfg or config.get("zone_engine", {})
    warnings: list[str] = []

    geometry = build_grid_frame_geometry(
        msp,
        config,
        source_file=source_file,
        unit_scale_m=unit_scale_m,
        expected_int_count=expected_int_count,
        zone_cfg=zone_cfg,
    )
    warnings.extend(geometry.warnings)

    if faces is None and auto_detect_faces:
        polygons = detect_faces_from_modelspace(msp, config)
        faces = polygons_to_faces(polygons, unit_scale_m=unit_scale_m)
    elif faces is None:
        faces = []

    method = str(zone_cfg.get("assignment_method", "max_intersection_area"))
    if method not in ("max_intersection_area", "centroid_in_cell"):
        method = "max_intersection_area"

    assignment = assign_faces_to_bays(
        faces,
        geometry.bays,
        method=method,  # type: ignore[arg-type]
        unit_scale_m=unit_scale_m,
        sliver_max_m2=float(zone_cfg.get("sliver_max_m2", 1.0)),
        orphan_min_intersection_m2=float(zone_cfg.get("orphan_min_intersection_m2", 0.01)),
        assign_orphans_to_nearest=bool(zone_cfg.get("assign_orphans_to_nearest", True)),
        centroid_buffer_m=float(zone_cfg.get("centroid_buffer_m", 0.05)),
        slab_polygon=geometry.slab.polygon,
    )
    warnings.extend(assignment.warnings)

    geometry_cfg = config.get("geometry", {})
    thickness = float(geometry_cfg.get("slab_thickness", 0.15))
    profile = str(zone_cfg.get("profile", "GRID_WAREHOUSE"))

    zones, agg_warnings = aggregate_int_zones(
        geometry.bays,
        assignment,
        faces,
        unit_scale_m=unit_scale_m,
        slab_thickness_m=thickness,
        profile=profile,
        detection_tier="T3",
        source_file=source_file,
        overlap_area_m2=float(zone_cfg.get("overlap_area_m2", 0.5)),
    )
    warnings.extend(agg_warnings)

    manifest_doc = load_manifest(manifest_path)
    manifest_recon = None
    if manifest_doc:
        tolerance = float(
            config.get("accuracy", {}).get(
                "area_tolerance_percent",
                zone_cfg.get("manifest_area_tolerance_pct", 0.05),
            )
        )
        manifest_recon = reconcile_zones_to_manifest(
            zones,
            manifest_doc,
            area_tolerance_pct=tolerance,
        )
        warnings.extend(manifest_recon.warnings)

    expected = expected_int_count
    if expected is None and manifest_doc:
        raw_expected = manifest_doc.get("zone_count_expected")
        if raw_expected is not None:
            expected = int(raw_expected)

    readiness = assess_production_readiness(
        zones,
        assignment,
        expected_zone_count=expected,
        manifest=manifest_recon,
        min_bay_coverage_pct=float(zone_cfg.get("min_union_bay_coverage_pct", 5.0)),
        max_orphan_faces=int(zone_cfg.get("max_orphan_faces", 0)),
    )

    return IntZonePipelineResult(
        geometry=geometry,
        zones=zones,
        assignment=assignment,
        manifest=manifest_recon,
        readiness=readiness,
        warnings=warnings,
    )
