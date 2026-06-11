"""Extract column / pillar footprint polygons from CAD INSERT entities."""

from __future__ import annotations

import logging
from typing import Any

from ezdxf.document import Drawing
from ezdxf.entities import DXFEntity
from ezdxf.layouts import Modelspace
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.ops import polygonize, unary_union

from src.extractor import entity_to_segments

logger = logging.getLogger(__name__)

DEFAULT_COLUMN_LAYERS = ("S-COLS", "S-COLS-1")


def _obstacle_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("obstacles") or {}


def column_layers(config: dict[str, Any]) -> tuple[str, ...]:
    layers = _obstacle_cfg(config).get("column_layers")
    if not layers:
        return DEFAULT_COLUMN_LAYERS
    return tuple(str(layer) for layer in layers)


def obstacles_enabled(config: dict[str, Any]) -> bool:
    return bool(_obstacle_cfg(config).get("enabled", False))


def _layer_set(config: dict[str, Any]) -> frozenset[str]:
    return frozenset(name.upper() for name in column_layers(config))


def _default_footprint_mm(config: dict[str, Any]) -> float:
    return float(_obstacle_cfg(config).get("default_footprint_mm", 400.0))


def _footprint_dict(
    poly: Polygon,
    *,
    layer: str,
    block_name: str,
    unit_scale_m: float,
    source: str = "column_insert",
) -> dict[str, Any]:
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        raise ValueError("empty footprint")
    ring = [[float(x), float(y)] for x, y in poly.exterior.coords[:-1]]
    area_m2 = float(poly.area) * (unit_scale_m**2)
    cx, cy = poly.centroid.x, poly.centroid.y
    return {
        "ring": ring,
        "area_m2": round(area_m2, 4),
        "centroid": [round(float(cx), 4), round(float(cy), 4)],
        "layer": layer,
        "block_name": block_name,
        "source": source,
    }


def _placeholder_footprint(
    x: float,
    y: float,
    half_size: float,
    *,
    layer: str,
    block_name: str,
    unit_scale_m: float,
) -> dict[str, Any]:
    poly = Polygon(
        [
            (x - half_size, y - half_size),
            (x + half_size, y - half_size),
            (x + half_size, y + half_size),
            (x - half_size, y + half_size),
        ]
    )
    return _footprint_dict(
        poly,
        layer=layer,
        block_name=block_name,
        unit_scale_m=unit_scale_m,
        source="column_insert_placeholder",
    )


def _entity_closed_polygon(entity: DXFEntity) -> Polygon | None:
    dxftype = entity.dxftype()
    if dxftype == "LWPOLYLINE":
        points = [(p[0], p[1]) for p in entity.get_points("xy")]
        if len(points) < 3 or not bool(entity.closed):
            return None
        poly = Polygon(points)
        return poly if not poly.is_empty else None
    if dxftype == "POLYLINE" and entity.is_closed:
        points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
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


def _segments_to_footprint(segments: list[LineString]) -> Polygon | None:
    if not segments:
        return None
    polys = list(polygonize(MultiLineString(segments)))
    if not polys:
        merged = unary_union(segments)
        if merged.is_empty:
            return None
        hull = merged.convex_hull
        return hull if isinstance(hull, Polygon) and not hull.is_empty else None
    polys.sort(key=lambda p: p.area)
    candidate = polys[0]
    if candidate.is_empty:
        return None
    if not candidate.is_valid:
        candidate = candidate.buffer(0)
    return candidate if not candidate.is_empty else None


def _insert_footprint(
    insert: DXFEntity,
    doc: Drawing,
    config: dict[str, Any],
    *,
    unit_scale_m: float,
    arc_segments: int,
) -> dict[str, Any] | None:
    layer = (insert.dxf.layer or "").upper()
    block_name = str(insert.dxf.name)
    closed_polys: list[Polygon] = []
    segments: list[LineString] = []

    try:
        virtual = list(insert.virtual_entities())
    except Exception as exc:
        logger.debug("virtual_entities failed for %s: %s", block_name, exc)
        virtual = []

    for entity in virtual:
        closed = _entity_closed_polygon(entity)
        if closed is not None and not closed.is_empty:
            closed_polys.append(closed)
            continue
        try:
            segments.extend(entity_to_segments(entity, arc_segments))
        except Exception:
            continue

    if closed_polys:
        closed_polys.sort(key=lambda p: p.area)
        try:
            return _footprint_dict(
                closed_polys[0],
                layer=layer,
                block_name=block_name,
                unit_scale_m=unit_scale_m,
            )
        except ValueError:
            pass

    footprint = _segments_to_footprint(segments)
    if footprint is not None:
        try:
            return _footprint_dict(
                footprint,
                layer=layer,
                block_name=block_name,
                unit_scale_m=unit_scale_m,
            )
        except ValueError:
            pass

    insert_pt = insert.dxf.insert
    half = _default_footprint_mm(config) / 2.0
    return _placeholder_footprint(
        float(insert_pt.x),
        float(insert_pt.y),
        half,
        layer=layer,
        block_name=block_name,
        unit_scale_m=unit_scale_m,
    )


def extract_column_footprints(
    msp: Modelspace,
    doc: Drawing,
    config: dict[str, Any],
    *,
    unit_scale_m: float = 0.001,
) -> list[dict[str, Any]]:
    """
    Return footprint dicts for INSERT entities on configured column layers.

    Does not modify detection segments or wall-layer extraction.
    """
    if not obstacles_enabled(config):
        return []

    layers = _layer_set(config)
    arc_segments = int(config.get("accuracy", {}).get("arc_segments", 64))
    footprints: list[dict[str, Any]] = []
    seen: set[tuple[str, float, float]] = set()

    for entity in msp:
        if entity.dxftype() != "INSERT":
            continue
        layer = (entity.dxf.layer or "").upper()
        if layer not in layers:
            continue
        insert_pt = entity.dxf.insert
        key = (layer, round(float(insert_pt.x), 3), round(float(insert_pt.y), 3))
        if key in seen:
            continue
        seen.add(key)

        fp = _insert_footprint(
            entity,
            doc,
            config,
            unit_scale_m=unit_scale_m,
            arc_segments=arc_segments,
        )
        if fp is not None:
            footprints.append(fp)

    logger.info("Extracted %d column footprints from layers %s", len(footprints), layers)
    return footprints
