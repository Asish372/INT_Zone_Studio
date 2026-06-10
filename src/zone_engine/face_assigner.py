"""P3 — Assign Stage 1 micro-faces to INT bay cells."""

from __future__ import annotations

import logging
from typing import Literal

from shapely.geometry import Point, Polygon

from src.geometry_precision import normalize_polygon
from src.zone_engine.grid_frame import BayCell
from src.zone_engine.models import (
    FaceAssignment,
    FaceAssignmentSummary,
    FaceData,
    OrphanFace,
)

logger = logging.getLogger(__name__)

AssignmentMethod = Literal["max_intersection_area", "centroid_in_cell"]

DEFAULT_SLIVER_MAX_M2 = 1.0
DEFAULT_ORPHAN_MIN_INTERSECTION_M2 = 0.01


def polygons_to_faces(
    polygons: list[Polygon],
    *,
    unit_scale_m: float = 0.001,
    start_id: int = 1,
) -> list[FaceData]:
    """Convert detector polygons to FaceData with stable ids."""
    faces: list[FaceData] = []
    next_id = start_id
    for poly in polygons:
        normalized = normalize_polygon(poly)
        if normalized is None or normalized.is_empty:
            continue
        area_m2 = normalized.area * (unit_scale_m**2)
        faces.append(FaceData(face_id=next_id, polygon=normalized, area_m2=area_m2))
        next_id += 1
    return faces


def filter_sliver_faces(
    faces: list[FaceData],
    *,
    sliver_max_m2: float = DEFAULT_SLIVER_MAX_M2,
) -> tuple[list[FaceData], int]:
    """Drop faces below sliver threshold (noise before assignment)."""
    kept: list[FaceData] = []
    sliver_count = 0
    for face in faces:
        if face.area_m2 < sliver_max_m2:
            sliver_count += 1
            continue
        kept.append(face)
    return kept, sliver_count


def _bay_target_polygon(bay: BayCell) -> Polygon:
    """Cell boundary used for assignment (clipped to slab when available)."""
    clipped = bay.clipped_polygon
    if clipped is not None and not clipped.is_empty and bay.clipped_area_m2 > 1e-6:
        return clipped
    return bay.polygon


def _intersection_area_m2(face: Polygon, cell: Polygon, unit_scale_m: float) -> float:
    if face.is_empty or cell.is_empty:
        return 0.0
    inter = face.intersection(cell)
    if inter.is_empty:
        return 0.0
    return inter.area * (unit_scale_m**2)


def _centroid_in_cell(face: Polygon, cell: Polygon, *, buffer_m: float, unit_scale_m: float) -> bool:
    centroid = face.centroid
    if cell.contains(centroid):
        return True
    if buffer_m <= 0:
        return False
    buffer_native = buffer_m / unit_scale_m if unit_scale_m > 0 else buffer_m
    return cell.buffer(buffer_native).contains(centroid)


def _pick_bay_max_intersection(
    face: FaceData,
    bays: list[BayCell],
    *,
    unit_scale_m: float,
    min_intersection_m2: float,
) -> tuple[BayCell | None, float]:
    best_bay: BayCell | None = None
    best_area = 0.0
    for bay in bays:
        cell = _bay_target_polygon(bay)
        area = _intersection_area_m2(face.polygon, cell, unit_scale_m)
        if area > best_area:
            best_area = area
            best_bay = bay
    if best_bay is None or best_area < min_intersection_m2:
        return None, best_area
    return best_bay, best_area


def _pick_bay_centroid(
    face: FaceData,
    bays: list[BayCell],
    *,
    unit_scale_m: float,
    centroid_buffer_m: float,
) -> BayCell | None:
    matches: list[BayCell] = []
    for bay in bays:
        cell = _bay_target_polygon(bay)
        if _centroid_in_cell(face.polygon, cell, buffer_m=centroid_buffer_m, unit_scale_m=unit_scale_m):
            matches.append(bay)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    # Tie-break: smallest cell area (interior room vs building shell)
    return min(matches, key=lambda bay: _bay_target_polygon(bay).area)


def _nearest_bay_by_centroid(face: FaceData, bays: list[BayCell]) -> BayCell | None:
    if not bays:
        return None
    pt = face.polygon.centroid
    return min(
        bays,
        key=lambda bay: pt.distance(Point(bay.centroid)),
    )


def assign_faces_to_bays(
    faces: list[FaceData],
    bays: list[BayCell],
    *,
    method: AssignmentMethod = "max_intersection_area",
    unit_scale_m: float = 0.001,
    sliver_max_m2: float = DEFAULT_SLIVER_MAX_M2,
    orphan_min_intersection_m2: float = DEFAULT_ORPHAN_MIN_INTERSECTION_M2,
    assign_orphans_to_nearest: bool = True,
    centroid_buffer_m: float = 0.05,
    slab_polygon: Polygon | None = None,
) -> FaceAssignmentSummary:
    """
    Map each non-sliver face to exactly one INT bay.

    Uses clipped bay polygons when slab clipping produced a non-empty cell.
  """
    warnings: list[str] = []
    active_faces, sliver_count = filter_sliver_faces(faces, sliver_max_m2=sliver_max_m2)

    if slab_polygon is not None and not slab_polygon.is_empty:
        outside = 0
        filtered: list[FaceData] = []
        for face in active_faces:
            centroid = face.polygon.centroid
            if slab_polygon.contains(centroid) or slab_polygon.covers(centroid):
                filtered.append(face)
            else:
                outside += 1
        if outside:
            warnings.append(f"{outside} face(s) with centroid outside slab outline (skipped).")
        active_faces = filtered

    assignments: list[FaceAssignment] = []
    orphans: list[OrphanFace] = []

    for face in active_faces:
        bay: BayCell | None = None
        intersection_m2 = 0.0

        if method == "centroid_in_cell":
            bay = _pick_bay_centroid(
                face,
                bays,
                unit_scale_m=unit_scale_m,
                centroid_buffer_m=centroid_buffer_m,
            )
            if bay is not None:
                intersection_m2 = _intersection_area_m2(
                    face.polygon,
                    _bay_target_polygon(bay),
                    unit_scale_m,
                )
        else:
            bay, intersection_m2 = _pick_bay_max_intersection(
                face,
                bays,
                unit_scale_m=unit_scale_m,
                min_intersection_m2=orphan_min_intersection_m2,
            )

        if bay is None:
            nearest = _nearest_bay_by_centroid(face, bays) if assign_orphans_to_nearest else None
            if nearest is not None and assign_orphans_to_nearest:
                intersection_m2 = _intersection_area_m2(
                    face.polygon,
                    _bay_target_polygon(nearest),
                    unit_scale_m,
                )
                assignments.append(
                    FaceAssignment(
                        face_id=face.face_id,
                        int_label=nearest.int_label,
                        bay_id=nearest.bay_id,
                        intersection_area_m2=intersection_m2,
                        method=f"{method}+nearest",
                    )
                )
                continue
            orphans.append(
                OrphanFace(
                    face_id=face.face_id,
                    area_m2=face.area_m2,
                    reason="no_bay_intersection",
                    nearest_int_label=nearest.int_label if nearest else None,
                )
            )
            continue

        assignments.append(
            FaceAssignment(
                face_id=face.face_id,
                int_label=bay.int_label,
                bay_id=bay.bay_id,
                intersection_area_m2=intersection_m2,
                method=method,
            )
        )

    if orphans:
        warnings.append(f"{len(orphans)} orphan face(s) could not be assigned to a bay.")

    logger.info(
        "Face assignment: %d assigned, %d orphans, %d slivers (method=%s)",
        len(assignments),
        len(orphans),
        sliver_count,
        method,
    )

    return FaceAssignmentSummary(
        total_faces=len(faces),
        sliver_count=sliver_count,
        assigned_count=len(assignments),
        orphan_count=len(orphans),
        assignments=assignments,
        orphans=orphans,
        method=method,
        warnings=warnings,
    )
