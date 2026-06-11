"""Validation for engineer-drawn manual partition polygons."""

from __future__ import annotations

from typing import Any

from shapely.geometry import Polygon

from desktop.engine_sidecar.polygon_records import polygon_overlaps_existing
from desktop.engine_sidecar.scope_clip import boundary_polygon
from desktop.engine_sidecar.workspace_save import active_polygons
from desktop.engine_sidecar.workspace_scope import normalize_ring, normalize_scope


def ring_to_polygon(ring: list[Any]) -> Polygon:
    """Build a Shapely polygon from a vertex ring; reject invalid geometry."""
    vertices = normalize_ring(ring)
    if len(vertices) < 3:
        raise ValueError("Polygon requires at least 3 vertices")
    poly = Polygon(vertices)
    if poly.is_empty:
        raise ValueError("Polygon is empty")
    if not poly.is_valid:
        raise ValueError("Polygon ring is self-intersecting or invalid")
    return poly


def validate_manual_polygon_in_scope(
    scope: dict[str, Any] | None,
    polygon: Polygon,
    *,
    scope_feature_enabled: bool,
) -> str | None:
    """Return error when detection is scoped and polygon lies outside boundary."""
    if not scope_feature_enabled:
        return None
    normalized = normalize_scope(scope)
    if not normalized.get("detection_scoped"):
        return None
    boundary = boundary_polygon(normalized)
    if boundary is None:
        return None
    if boundary.covers(polygon):
        return None
    return "Manual polygon must be inside the applied slab boundary."


def validate_manual_polygon_ring(
    ring: list[Any],
    *,
    records: list[dict[str, Any]],
    scope: dict[str, Any] | None,
    scope_feature_enabled: bool,
    overlap_iou_threshold: float = 0.95,
) -> Polygon:
    """Validate ring and return polygon; raises ValueError on rejection."""
    polygon = ring_to_polygon(ring)
    scope_error = validate_manual_polygon_in_scope(
        scope,
        polygon,
        scope_feature_enabled=scope_feature_enabled,
    )
    if scope_error:
        raise ValueError(scope_error)
    active = active_polygons(records)
    if polygon_overlaps_existing(
        polygon,
        active,
        iou_threshold=overlap_iou_threshold,
    ):
        raise ValueError("Polygon overlaps an existing partition")
    return polygon
