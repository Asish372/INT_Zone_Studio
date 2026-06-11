"""CAD pick and auto-detect helpers for slab boundary UX (no detection changes)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ezdxf.entities import DXFEntity
from ezdxf.layouts import Modelspace
from shapely.geometry import Point, Polygon

from src.extractor import extract_entities
from src.layer_resolver import resolve_wall_layers
from src.units import scale_factor
from src.zone_engine.slab_outline import extract_slab_outline

from desktop.engine_sidecar.workspace_scope import build_boundary, normalize_ring


@dataclass
class CadClosedLoop:
    ring: list[list[float]]
    layer: str
    handle: str
    entity_type: str
    area_native: float


def _polygon_from_entity(entity: DXFEntity) -> Polygon | None:
    dxftype = entity.dxftype()
    if dxftype == "LWPOLYLINE":
        points = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
        if len(points) < 3 or not bool(entity.closed):
            return None
        poly = Polygon(points)
        return poly if not poly.is_empty else None
    if dxftype == "POLYLINE" and entity.is_closed:
        points = [
            (float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices
        ]
        if len(points) < 3:
            return None
        poly = Polygon(points)
        return poly if not poly.is_empty else None
    if dxftype == "CIRCLE":
        center = entity.dxf.center
        radius = float(entity.dxf.radius)
        if radius <= 0:
            return None
        return Point(center.x, center.y).buffer(radius, resolution=32)
    return None


def _loop_from_entity(entity: DXFEntity) -> CadClosedLoop | None:
    poly = _polygon_from_entity(entity)
    if poly is None or poly.is_empty:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None
    ring = normalize_ring([[x, y] for x, y in poly.exterior.coords[:-1]])
    if len(ring) < 3:
        return None
    return CadClosedLoop(
        ring=ring,
        layer=str(entity.dxf.layer or ""),
        handle=str(entity.dxf.handle),
        entity_type=entity.dxftype(),
        area_native=float(poly.area),
    )


def collect_closed_cad_loops(msp: Modelspace, config: dict[str, Any]) -> list[CadClosedLoop]:
    """Enumerate closed polylines/circles on resolved wall layers."""
    layers_cfg = config.get("layers", {})
    ignore_layers = layers_cfg.get("ignore_layers", [])
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    if not resolution.wall_layers:
        return []
    entities = extract_entities(msp, resolution.wall_layers, ignore_layers)
    loops: list[CadClosedLoop] = []
    seen_handles: set[str] = set()
    for entity in entities:
        handle = str(entity.dxf.handle)
        if handle in seen_handles:
            continue
        loop = _loop_from_entity(entity)
        if loop is None:
            continue
        seen_handles.add(handle)
        loops.append(loop)
    loops.sort(key=lambda item: item.area_native, reverse=True)
    return loops


def _loop_polygon(loop: CadClosedLoop) -> Polygon:
    poly = Polygon(loop.ring)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def pick_loop_at_point(
    loops: list[CadClosedLoop],
    x: float,
    y: float,
    *,
    pick_tolerance_native: float,
) -> CadClosedLoop | None:
    """Pick smallest containing loop, else nearest boundary within tolerance."""
    if not loops:
        return None
    pt = Point(x, y)
    containing: list[CadClosedLoop] = []
    for loop in loops:
        poly = _loop_polygon(loop)
        if poly.is_empty:
            continue
        if poly.contains(pt) or poly.buffer(1.0).contains(pt):
            containing.append(loop)
    if containing:
        return min(containing, key=lambda item: item.area_native)

    nearest: CadClosedLoop | None = None
    best_dist = pick_tolerance_native
    for loop in loops:
        poly = _loop_polygon(loop)
        if poly.is_empty:
            continue
        dist = float(poly.boundary.distance(pt))
        if dist < best_dist:
            best_dist = dist
            nearest = loop
    return nearest


def loop_candidates_public(
    loops: list[CadClosedLoop],
    *,
    unit_scale_m: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for loop in loops:
        area_m2 = loop.area_native * (unit_scale_m**2)
        out.append(
            {
                "ring": loop.ring,
                "layer": loop.layer,
                "entity_handle": loop.handle,
                "entity_type": loop.entity_type,
                "area_m2": round(area_m2, 4),
            }
        )
    return out


def pick_boundary_preview(
    msp: Modelspace,
    config: dict[str, Any],
    x: float,
    y: float,
    *,
    unit_scale_m: float,
    defined_by: str = "",
) -> dict[str, Any]:
    scope_cfg = config.get("scope", {})
    pick_tol = float(scope_cfg.get("pick_tolerance_mm", 500))
    loops = collect_closed_cad_loops(msp, config)
    loop = pick_loop_at_point(loops, x, y, pick_tolerance_native=pick_tol)
    if loop is None:
        raise ValueError(
            "No closed CAD polyline at click. Click directly on a slab outline "
            "or use Draw Boundary."
        )
    cad_ref = {
        "layer": loop.layer,
        "entity_handle": loop.handle,
        "entity_type": loop.entity_type,
    }
    return build_boundary(
        loop.ring,
        source="cad_pick",
        unit_scale_m=unit_scale_m,
        defined_by=defined_by,
        cad_ref=cad_ref,
    )


def auto_boundary_preview(
    msp: Modelspace,
    config: dict[str, Any],
    *,
    unit_scale_m: float,
    defined_by: str = "",
) -> dict[str, Any]:
    scope_cfg = config.get("scope", {})
    zone_cfg = config.get("zone_engine", {})
    slab_layer = str(
        scope_cfg.get("slab_outline_layer")
        or zone_cfg.get("slab_outline_layer", "S-FNDN-1")
    )
    min_area = float(
        scope_cfg.get("slab_min_polygon_area_m2")
        or zone_cfg.get("slab_min_polygon_area_m2", 100.0)
    )
    hull_ratio = float(
        scope_cfg.get("slab_concave_hull_ratio")
        or zone_cfg.get("slab_concave_hull_ratio", 0.2)
    )
    result = extract_slab_outline(
        msp,
        config,
        slab_layer=slab_layer,
        unit_scale_m=unit_scale_m,
        min_polygon_area_m2=min_area,
        concave_hull_ratio=hull_ratio,
    )
    if result.polygon.is_empty:
        detail = "; ".join(result.warnings) if result.warnings else "slab outline empty"
        raise ValueError(f"Auto boundary could not find a slab outline ({detail}).")
    ring = normalize_ring(
        [[float(x), float(y)] for x, y in result.polygon.exterior.coords[:-1]]
    )
    return build_boundary(
        ring,
        source="auto_layer",
        unit_scale_m=unit_scale_m,
        defined_by=defined_by,
        auto_layer=result.layer,
    )


def default_unit_scale_m(config: dict[str, Any]) -> float:
    geometry_cfg = config.get("geometry", {})
    return scale_factor(geometry_cfg.get("drawing_unit", "mm"))


def load_modelspace(dxf_path: Path) -> Modelspace:
    from src.parser import get_modelspace, load_dxf

    return get_modelspace(load_dxf(dxf_path))
