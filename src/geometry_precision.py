"""High-precision geometry helpers for area calculation."""

from __future__ import annotations

import logging

from shapely.geometry import Polygon
from shapely.validation import make_valid

logger = logging.getLogger(__name__)


def normalize_polygon(polygon: Polygon) -> Polygon | None:
    """
    Repair invalid polygons and return the largest polygon face.

    Improves agreement with AutoCAD AREA on messy or nearly-closed boundaries.
    """
    if polygon.is_empty:
        return None

    geom = polygon
    if not geom.is_valid:
        geom = make_valid(geom)

    if geom.geom_type == "Polygon":
        return geom
    if geom.geom_type == "MultiPolygon":
        return max(geom.geoms, key=lambda g: g.area)
    if geom.geom_type == "GeometryCollection":
        polys = [g for g in geom.geoms if g.geom_type == "Polygon"]
        if polys:
            return max(polys, key=lambda g: g.area)
    logger.debug("Could not normalize geometry type: %s", geom.geom_type)
    return None
