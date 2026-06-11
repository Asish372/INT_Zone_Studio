"""Post-detection clipping against user-defined slab boundary."""

from __future__ import annotations

from typing import Any

from shapely.geometry import Point, Polygon

from desktop.engine_sidecar.workspace_scope import boundary_ring, normalize_scope


def boundary_polygon(scope: dict[str, Any] | None) -> Polygon | None:
    """Build a valid boundary polygon from scope, or None if unset."""
    ring = boundary_ring(scope)
    if len(ring) < 3:
        return None
    poly = Polygon(ring)
    if poly.is_empty:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if not poly.is_empty else None


def point_in_boundary(scope: dict[str, Any] | None, x: float, y: float) -> bool:
    """True when (x, y) lies inside the active slab boundary."""
    poly = boundary_polygon(scope)
    if poly is None:
        return True
    return bool(poly.covers(Point(x, y)))


def polygon_in_boundary(rec: dict[str, Any], boundary: Polygon) -> bool:
    """In-scope when polygon centroid is covered by the boundary."""
    ring = rec.get("ring") or []
    if len(ring) < 3:
        return False
    try:
        poly = Polygon(ring)
        if poly.is_empty:
            return False
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            return False
        return bool(boundary.covers(poly.centroid))
    except Exception:
        return False


def apply_scope_clip(
    records: list[dict[str, Any]],
    scope: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], int]:
    """
    Mark records outside the slab boundary with scope_excluded=True.

    Returns (updated records, excluded count). Detection pipeline is unchanged;
    this runs after full detection.
    """
    boundary = boundary_polygon(scope)
    if boundary is None:
        out: list[dict[str, Any]] = []
        for rec in records:
            item = dict(rec)
            item["scope_excluded"] = False
            out.append(item)
        return out, 0

    excluded = 0
    clipped: list[dict[str, Any]] = []
    for rec in records:
        item = dict(rec)
        inside = polygon_in_boundary(item, boundary)
        item["scope_excluded"] = not inside
        if not inside:
            excluded += 1
        clipped.append(item)
    return clipped, excluded


def clear_scope_exclusion(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reset scope_excluded on all records (e.g. when boundary is cleared)."""
    out: list[dict[str, Any]] = []
    for rec in records:
        item = dict(rec)
        item["scope_excluded"] = False
        out.append(item)
    return out


def scope_is_applied(scope: dict[str, Any] | None) -> bool:
    normalized = normalize_scope(scope)
    return bool(normalized.get("detection_scoped"))
