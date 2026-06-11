"""Slab scope (user-defined boundary) workspace object — persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shapely.geometry import Polygon

SCOPE_BOUNDARY_SOURCES = frozenset({"drawn", "cad_pick", "auto_layer"})


def empty_scope() -> dict[str, Any]:
    return {
        "boundary": None,
        "detection_scoped": False,
        "boundary_stale": False,
        "obstacles": None,
    }


def set_scope_obstacles(
    scope: dict[str, Any],
    *,
    footprints: list[dict[str, Any]],
    classified_count: int,
    appended_count: int = 0,
) -> dict[str, Any]:
    """Attach obstacle extraction metadata to scope (boundary workflow unchanged)."""
    out = normalize_scope(scope)
    public_footprints: list[dict[str, Any]] = []
    for fp in footprints:
        public_footprints.append(
            {
                "ring": normalize_ring(fp.get("ring") or []),
                "area_m2": fp.get("area_m2"),
                "centroid": fp.get("centroid"),
                "layer": fp.get("layer"),
                "block_name": fp.get("block_name"),
                "source": fp.get("source", "column_insert"),
            }
        )
    out["obstacles"] = {
        "footprints": public_footprints,
        "classified_count": int(classified_count),
        "appended_count": int(appended_count),
        "footprint_count": len(public_footprints),
    }
    return out


def boundary_ring(scope: dict[str, Any] | None) -> list[list[float]]:
    """Return normalized boundary ring vertices, or empty list."""
    if not scope or not isinstance(scope, dict):
        return []
    boundary = scope.get("boundary")
    if not boundary or not isinstance(boundary, dict):
        return []
    return normalize_ring(boundary.get("ring") or [])


def set_scope_flags(
    scope: dict[str, Any],
    *,
    detection_scoped: bool | None = None,
    boundary_stale: bool | None = None,
) -> dict[str, Any]:
    """Return scope with updated detection/boundary flags."""
    out = normalize_scope(scope)
    if detection_scoped is not None:
        out["detection_scoped"] = bool(detection_scoped)
    if boundary_stale is not None:
        out["boundary_stale"] = bool(boundary_stale)
    return out


def normalize_ring(ring: list[Any]) -> list[list[float]]:
    """Return a clean vertex list (no duplicate closing vertex)."""
    out: list[list[float]] = []
    for pt in ring or []:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            continue
        out.append([float(pt[0]), float(pt[1])])
    if len(out) >= 2 and out[0][0] == out[-1][0] and out[0][1] == out[-1][1]:
        out = out[:-1]
    return out


def ring_metrics(ring: list[list[float]], unit_scale_m: float) -> dict[str, Any]:
    vertices = normalize_ring(ring)
    if len(vertices) < 3:
        raise ValueError("Boundary requires at least 3 vertices")
    poly = Polygon(vertices)
    if poly.is_empty:
        raise ValueError("Boundary polygon is empty")
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        raise ValueError("Boundary polygon is invalid")
    cx, cy = poly.centroid.x, poly.centroid.y
    area_m2 = float(poly.area) * (unit_scale_m**2)
    perimeter_m = float(poly.length) * unit_scale_m
    return {
        "ring": vertices,
        "area_m2": round(area_m2, 4),
        "perimeter_m": round(perimeter_m, 4),
        "centroid": [round(float(cx), 4), round(float(cy), 4)],
    }


def build_boundary(
    ring: list[list[float]],
    *,
    source: str = "drawn",
    unit_scale_m: float = 0.001,
    defined_by: str = "",
    cad_ref: dict[str, Any] | None = None,
    auto_layer: str | None = None,
) -> dict[str, Any]:
    if source not in SCOPE_BOUNDARY_SOURCES:
        raise ValueError(f"Invalid boundary source: {source!r}")
    metrics = ring_metrics(ring, unit_scale_m)
    boundary: dict[str, Any] = {
        **metrics,
        "source": source,
        "defined_at": datetime.now(timezone.utc).isoformat(),
    }
    if defined_by:
        boundary["defined_by"] = defined_by
    if cad_ref:
        boundary["cad_ref"] = cad_ref
    if auto_layer:
        boundary["auto_layer"] = auto_layer
    return boundary


def normalize_scope(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Coerce loaded JSON into a stable scope object (v2 → empty boundary)."""
    if not raw or not isinstance(raw, dict):
        return empty_scope()
    detection_scoped = bool(raw.get("detection_scoped", False))
    boundary_stale = bool(raw.get("boundary_stale", False))
    boundary = raw.get("boundary")
    obstacles = _normalize_obstacles(raw.get("obstacles"))

    if not boundary or not isinstance(boundary, dict):
        return {
            "boundary": None,
            "detection_scoped": detection_scoped,
            "boundary_stale": boundary_stale,
            "obstacles": obstacles,
        }
    ring = normalize_ring(boundary.get("ring") or [])
    if len(ring) < 3:
        return {
            "boundary": None,
            "detection_scoped": detection_scoped,
            "boundary_stale": boundary_stale,
            "obstacles": obstacles,
        }
    source = boundary.get("source", "drawn")
    if source not in SCOPE_BOUNDARY_SOURCES:
        source = "drawn"
    boundary_out: dict[str, Any] = {
        "ring": ring,
        "area_m2": boundary.get("area_m2"),
        "perimeter_m": boundary.get("perimeter_m"),
        "centroid": boundary.get("centroid"),
        "source": source,
        "defined_at": boundary.get("defined_at"),
    }
    if boundary.get("defined_by"):
        boundary_out["defined_by"] = boundary["defined_by"]
    if boundary.get("cad_ref"):
        boundary_out["cad_ref"] = boundary["cad_ref"]
    if boundary.get("auto_layer"):
        boundary_out["auto_layer"] = boundary["auto_layer"]
    return {
        "boundary": boundary_out,
        "detection_scoped": detection_scoped,
        "boundary_stale": boundary_stale,
        "obstacles": obstacles,
    }


def _normalize_obstacles(raw: Any) -> dict[str, Any] | None:
    if not raw or not isinstance(raw, dict):
        return None
    footprints_in = raw.get("footprints")
    if not footprints_in or not isinstance(footprints_in, list):
        return None
    footprints: list[dict[str, Any]] = []
    for fp in footprints_in:
        if not isinstance(fp, dict):
            continue
        ring = normalize_ring(fp.get("ring") or [])
        if len(ring) < 3:
            continue
        footprints.append(
            {
                "ring": ring,
                "area_m2": fp.get("area_m2"),
                "centroid": fp.get("centroid"),
                "layer": fp.get("layer"),
                "block_name": fp.get("block_name"),
                "source": fp.get("source", "column_insert"),
            }
        )
    if not footprints:
        return None
    return {
        "footprints": footprints,
        "classified_count": int(raw.get("classified_count", 0)),
        "appended_count": int(raw.get("appended_count", 0)),
        "footprint_count": int(raw.get("footprint_count", len(footprints))),
    }


def scope_public(scope: dict[str, Any] | None) -> dict[str, Any]:
    """API-safe scope payload."""
    normalized = normalize_scope(scope)
    return normalized
