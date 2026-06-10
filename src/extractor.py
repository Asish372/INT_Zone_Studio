"""Module 2: Extract geometric entities from DXF modelspace."""

from __future__ import annotations

import logging
import math
from typing import Any

from ezdxf.entities import DXFEntity
from ezdxf.layouts import Modelspace
from shapely.geometry import LineString

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {"LINE", "LWPOLYLINE", "POLYLINE", "ARC"}
DEFAULT_ARC_SEGMENTS = 64


def extract_entities(
    msp: Modelspace,
    layers: list[str],
    ignore_layers: list[str] | None = None,
) -> list[DXFEntity]:
    """Return LINE, LWPOLYLINE, and ARC entities on the specified layers."""
    layer_set = {name.upper() for name in layers}
    ignore_set = {name.upper() for name in (ignore_layers or [])}
    entities: list[DXFEntity] = []

    for entity in msp:
        if entity.dxftype() not in SUPPORTED_TYPES:
            continue
        layer_name = (entity.dxf.layer or "").upper()
        if layer_name in ignore_set:
            continue
        if layer_set and layer_name not in layer_set:
            continue
        entities.append(entity)

    logger.info("Extracted %d entities from layers %s", len(entities), layers)
    return entities


def _arc_to_linestring(entity: DXFEntity, arc_segments: int = DEFAULT_ARC_SEGMENTS) -> LineString:
    """Approximate an ARC as a polyline with arc_segments points."""
    center = entity.dxf.center
    radius = entity.dxf.radius
    start_angle = math.radians(entity.dxf.start_angle)
    end_angle = math.radians(entity.dxf.end_angle)

    if end_angle < start_angle:
        end_angle += 2 * math.pi

    points = []
    for i in range(arc_segments + 1):
        t = start_angle + (end_angle - start_angle) * i / arc_segments
        x = center.x + radius * math.cos(t)
        y = center.y + radius * math.sin(t)
        points.append((x, y))

    return LineString(points)


def entity_to_segments(
    entity: DXFEntity,
    arc_segments: int = DEFAULT_ARC_SEGMENTS,
) -> list[LineString]:
    """Convert a single DXF entity to Shapely LineString segment(s)."""
    dxftype = entity.dxftype()

    if dxftype == "LINE":
        start = entity.dxf.start
        end = entity.dxf.end
        return [LineString([(start.x, start.y), (end.x, end.y)])]

    if dxftype in ("LWPOLYLINE", "POLYLINE"):
        if dxftype == "LWPOLYLINE":
            points = [(p[0], p[1]) for p in entity.get_points("xy")]
            closed = bool(entity.closed)
        else:
            points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
            closed = bool(entity.is_closed)
        if len(points) < 2:
            return []
        segments = []
        for i in range(len(points) - 1):
            segments.append(LineString([points[i], points[i + 1]]))
        if closed and len(points) >= 3:
            segments.append(LineString([points[-1], points[0]]))
        return segments

    if dxftype == "ARC":
        return [_arc_to_linestring(entity, arc_segments)]

    logger.debug("Skipping unsupported entity type: %s", dxftype)
    return []


def extract_all_segments(
    entities: list[DXFEntity],
    arc_segments: int = DEFAULT_ARC_SEGMENTS,
) -> list[LineString]:
    """Convert all entities to Shapely segments; skip unsupported types."""
    segments: list[LineString] = []
    skipped = 0

    for entity in entities:
        try:
            entity_segments = entity_to_segments(entity, arc_segments)
            if entity_segments:
                segments.extend(entity_segments)
            else:
                skipped += 1
        except Exception as exc:
            logger.warning(
                "Skipped entity %s on layer %s: %s",
                entity.dxftype(),
                getattr(entity.dxf, "layer", "?"),
                exc,
            )
            skipped += 1

    logger.info("Built %d segments (%d entities skipped)", len(segments), skipped)
    return segments
