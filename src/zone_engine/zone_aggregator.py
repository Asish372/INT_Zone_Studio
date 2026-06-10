"""P3 — Aggregate assigned faces into INT zone polygons via unary_union."""

from __future__ import annotations

import logging

from shapely.geometry import Polygon
from shapely.ops import unary_union

from src.calculator import compute_area, compute_volume
from src.geometry_precision import normalize_polygon
from src.zone_engine.grid_frame import BayCell
from src.zone_engine.int_labels import sort_bays_for_display
from src.zone_engine.models import FaceAssignmentSummary, FaceData, IntZoneData

logger = logging.getLogger(__name__)


def _union_to_polygon(geometry) -> Polygon:
    if geometry.is_empty:
        return Polygon()
    if geometry.geom_type == "Polygon":
        return geometry
    if geometry.geom_type == "MultiPolygon":
        return max(geometry.geoms, key=lambda geom: geom.area)
    if geometry.geom_type == "GeometryCollection":
        polys = [g for g in geometry.geoms if g.geom_type == "Polygon"]
        if polys:
            return max(polys, key=lambda geom: geom.area)
    return Polygon()


def _zone_overlap_pairs(
    zones: list[IntZoneData],
    *,
    unit_scale_m: float,
    overlap_area_m2: float,
) -> list[tuple[str, str, float]]:
    pairs: list[tuple[str, str, float]] = []
    for i, zone_a in enumerate(zones):
        if zone_a.polygon.is_empty:
            continue
        for zone_b in zones[i + 1 :]:
            if zone_b.polygon.is_empty:
                continue
            inter = zone_a.polygon.intersection(zone_b.polygon)
            if inter.is_empty:
                continue
            overlap_m2 = inter.area * (unit_scale_m**2)
            if overlap_m2 > overlap_area_m2:
                pairs.append((zone_a.label, zone_b.label, overlap_m2))
    return pairs


def aggregate_int_zones(
    bays: list[BayCell],
    assignment: FaceAssignmentSummary,
    faces: list[FaceData],
    *,
    unit_scale_m: float = 0.001,
    slab_thickness_m: float = 0.15,
    profile: str = "GRID_WAREHOUSE",
    detection_tier: str = "T3",
    source_file: str = "",
    overlap_area_m2: float = 0.5,
) -> tuple[list[IntZoneData], list[str]]:
    """
    Build one IntZoneData per bay from unary_union of assigned micro-faces.

    Bays with no assigned faces still appear with empty polygon and zero area.
    """
    face_by_id = {face.face_id: face for face in faces}
    faces_by_label: dict[str, list[Polygon]] = {}
    face_ids_by_label: dict[str, list[int]] = {}
    face_sum_by_label: dict[str, float] = {}

    for item in assignment.assignments:
        face = face_by_id.get(item.face_id)
        if face is None:
            continue
        faces_by_label.setdefault(item.int_label, []).append(face.polygon)
        face_ids_by_label.setdefault(item.int_label, []).append(face.face_id)
        face_sum_by_label[item.int_label] = face_sum_by_label.get(item.int_label, 0.0) + face.area_m2

    zones: list[IntZoneData] = []
    warnings: list[str] = []

    for index, bay in enumerate(sort_bays_for_display(bays), start=1):
        label = bay.int_label
        polys = faces_by_label.get(label, [])
        clipped_bay_m2 = bay.clipped_area_m2 if bay.clipped_area_m2 > 0 else bay.area_m2

        if polys:
            merged = unary_union(polys)
            zone_poly = normalize_polygon(_union_to_polygon(merged)) or Polygon()
        else:
            zone_poly = Polygon()
            warnings.append(f"{label}: no faces assigned (empty zone).")

        area_m2 = compute_area(zone_poly, unit_scale_m) if not zone_poly.is_empty else 0.0
        volume_m3 = compute_volume(area_m2, slab_thickness_m)
        face_sum = face_sum_by_label.get(label, 0.0)
        coverage = (area_m2 / clipped_bay_m2 * 100.0) if clipped_bay_m2 > 1e-9 else 0.0

        zones.append(
            IntZoneData(
                zone_id=index,
                label=label,
                polygon=zone_poly,
                area_m2=area_m2,
                volume_m3=volume_m3,
                face_ids=face_ids_by_label.get(label, []),
                face_count=len(face_ids_by_label.get(label, [])),
                face_sum_area_m2=face_sum,
                clipped_bay_area_m2=clipped_bay_m2,
                bay_coverage_pct=coverage,
                profile=profile,
                detection_tier=detection_tier,
                grid_ref=None,
                source_file=source_file,
            )
        )

    overlaps = _zone_overlap_pairs(zones, unit_scale_m=unit_scale_m, overlap_area_m2=overlap_area_m2)
    if overlaps:
        for label_a, label_b, area in overlaps:
            warnings.append(
                f"Zone overlap: {label_a} ∩ {label_b} = {area:.2f} m²"
            )

    logger.info("Aggregated %d INT zones from %d face assignments", len(zones), assignment.assigned_count)
    return zones, warnings
