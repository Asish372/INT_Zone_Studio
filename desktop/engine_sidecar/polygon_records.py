"""Polygon record helpers for workspace API and UI."""

from __future__ import annotations

from typing import Any

from shapely.geometry import Polygon

from src.zone_engine.models import FaceData

from desktop.engine_sidecar.workspace_save import is_partition_polygon


def _polygon_ring(poly: Polygon) -> list[list[float]]:
    return [[float(x), float(y)] for x, y in poly.exterior.coords]


def _metrics(polygon: Polygon, unit_scale_m: float) -> dict[str, Any]:
    area_m2 = float(polygon.area) * (unit_scale_m**2)
    perimeter_m = float(polygon.length) * unit_scale_m
    cx, cy = polygon.centroid.x, polygon.centroid.y
    return {
        "area_m2": round(area_m2, 4),
        "perimeter_m": round(perimeter_m, 4),
        "centroid": [float(cx), float(cy)],
    }


def face_to_record(face: FaceData, unit_scale_m: float = 0.001) -> dict[str, Any]:
    cx, cy = face.polygon.centroid.x, face.polygon.centroid.y
    return {
        "id": face.face_id,
        "source": "auto",
        "status": "active",
        "scope_excluded": False,
        "geometry_role": "partition",
        "ring": _polygon_ring(face.polygon),
        "area_m2": round(face.area_m2, 4),
        "perimeter_m": round(float(face.polygon.length) * unit_scale_m, 4),
        "centroid": [float(cx), float(cy)],
    }


def faces_to_polygon_records(
    faces: list[FaceData],
    *,
    unit_scale_m: float = 0.001,
) -> list[dict[str, Any]]:
    return [face_to_record(face, unit_scale_m) for face in faces]


def polygon_to_record(
    polygon: Polygon,
    *,
    polygon_id: int,
    source: str = "seed",
    unit_scale_m: float = 0.001,
    status: str = "active",
) -> dict[str, Any]:
    return {
        "id": polygon_id,
        "source": source,
        "status": status,
        "scope_excluded": False,
        "geometry_role": "partition",
        "ring": _polygon_ring(polygon),
        **_metrics(polygon, unit_scale_m),
    }


def polygon_overlaps_existing(
    polygon: Polygon,
    records: list[dict[str, Any]],
    *,
    iou_threshold: float = 0.95,
) -> bool:
    for rec in records:
        if not is_partition_polygon(rec):
            continue
        ring = rec.get("ring")
        if not ring or len(ring) < 3:
            continue
        try:
            existing = Polygon(ring)
            if existing.is_empty or polygon.is_empty:
                continue
            inter = existing.intersection(polygon).area
            union = existing.union(polygon).area
            if union <= 0:
                continue
            if inter / union >= iou_threshold or existing.equals(polygon):
                return True
        except Exception:
            continue
    return False
