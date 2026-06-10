"""Extract authoritative slab boundary from S-FNDN-1 linework."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ezdxf.layouts import Modelspace
from shapely import concave_hull
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import polygonize, unary_union

from src.detector import node_geometry, polygonize_regions
from src.extractor import extract_entities, extract_all_segments
from src.gap_handler import prepare_for_polygonize

logger = logging.getLogger(__name__)

DEFAULT_SLAB_LAYER = "S-FNDN-1"
DEFAULT_MIN_POLYGON_AREA_M2 = 100.0
DEFAULT_CONCAVE_HULL_RATIO = 0.2


@dataclass
class SlabOutlineResult:
    """Slab boundary derived from foundation layer geometry."""

    layer: str
    method: str
    polygon: Polygon
    area_m2: float
    segment_count: int
    polygonize_count: int
    warnings: list[str]


def _area_m2(polygon: Polygon, unit_scale_m: float) -> float:
    return polygon.area * (unit_scale_m**2)


def _largest_polygon(geometry) -> Polygon | None:
    if geometry is None or geometry.is_empty:
        return None
    if geometry.geom_type == "Polygon":
        return geometry
    if geometry.geom_type == "MultiPolygon":
        polys = list(geometry.geoms)
        if not polys:
            return None
        return max(polys, key=lambda poly: poly.area)
    if geometry.geom_type == "GeometryCollection":
        polys = [g for g in geometry.geoms if g.geom_type == "Polygon"]
        if polys:
            return max(polys, key=lambda poly: poly.area)
    return None


def extract_slab_outline(
    msp: Modelspace,
    config: dict,
    *,
    slab_layer: str = DEFAULT_SLAB_LAYER,
    unit_scale_m: float = 0.001,
    min_polygon_area_m2: float = DEFAULT_MIN_POLYGON_AREA_M2,
    concave_hull_ratio: float = DEFAULT_CONCAVE_HULL_RATIO,
) -> SlabOutlineResult:
    """
    Build slab outline from S-FNDN-1.

    Tries closed regions from polygonized linework first; if no sufficiently
    large polygon exists, uses concave hull of all S-FNDN-1 vertices (still
  sourced only from that layer).
    """
    warnings: list[str] = []
    entities = extract_entities(msp, [slab_layer])
    segments = extract_all_segments(entities)

    if not segments:
        empty = Polygon()
        warnings.append(f"No linework found on layer {slab_layer}.")
        return SlabOutlineResult(
            layer=slab_layer,
            method="empty",
            polygon=empty,
            area_m2=0.0,
            segment_count=0,
            polygonize_count=0,
            warnings=warnings,
        )

    prepared = prepare_for_polygonize(segments, config)
    noded = node_geometry(prepared)
    polygons = polygonize_regions(noded)
    min_area_native = min_polygon_area_m2 / (unit_scale_m**2)
    large_polygons = [poly for poly in polygons if poly.area >= min_area_native]

    if large_polygons:
        merged = unary_union(large_polygons)
        outline = _largest_polygon(merged)
        if outline is not None and not outline.is_empty:
            method = "polygonize_union" if len(large_polygons) > 1 else "polygonize"
            logger.info(
                "Slab outline from %s polygonize (%d regions, %.1f m²)",
                slab_layer,
                len(large_polygons),
                _area_m2(outline, unit_scale_m),
            )
            return SlabOutlineResult(
                layer=slab_layer,
                method=method,
                polygon=outline,
                area_m2=_area_m2(outline, unit_scale_m),
                segment_count=len(segments),
                polygonize_count=len(polygons),
                warnings=warnings,
            )
        warnings.append(
            "Polygonize produced regions but union did not yield a valid polygon; "
            "falling back to concave hull."
        )
    else:
        warnings.append(
            f"No S-FNDN-1 polygonize region >= {min_polygon_area_m2:.0f} m² "
            f"({len(polygons)} small regions); using concave hull of linework vertices."
        )

    points = [Point(coord) for seg in segments for coord in seg.coords]
    hull = concave_hull(MultiPoint(points), ratio=concave_hull_ratio)
    outline = _largest_polygon(hull)
    if outline is None or outline.is_empty:
        warnings.append("Concave hull failed; slab outline is empty.")
        outline = Polygon()

    logger.info(
        "Slab outline from %s concave_hull (ratio=%.2f, %.1f m²)",
        slab_layer,
        concave_hull_ratio,
        _area_m2(outline, unit_scale_m),
    )
    return SlabOutlineResult(
        layer=slab_layer,
        method="concave_hull",
        polygon=outline,
        area_m2=_area_m2(outline, unit_scale_m),
        segment_count=len(segments),
        polygonize_count=len(polygons),
        warnings=warnings,
    )
