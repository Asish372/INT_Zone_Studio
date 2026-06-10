"""Module 5: Polygonize line networks into enclosed regions."""

from __future__ import annotations

import logging
from typing import Any

from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.ops import polygonize, unary_union

from src.geometry_precision import normalize_polygon
from src.units import scale_factor

logger = logging.getLogger(__name__)

DETECTION_MODES = ("standard", "exhaustive")


def node_geometry(multi_line: MultiLineString) -> MultiLineString:
    """Node intersections via unary_union."""
    if multi_line.is_empty:
        return multi_line

    merged = unary_union(multi_line)
    if merged.geom_type == "LineString":
        return MultiLineString([merged])
    if merged.geom_type == "MultiLineString":
        return merged
    if merged.geom_type == "GeometryCollection":
        lines = [g for g in merged.geoms if g.geom_type == "LineString"]
        return MultiLineString(lines) if lines else MultiLineString()
    return MultiLineString()


def polygonize_regions(geometry: MultiLineString) -> list[Polygon]:
    """Extract all fully enclosed polygons from a line network."""
    if geometry.is_empty:
        return []

    noded = node_geometry(geometry)
    polygons = list(polygonize(noded))
    logger.info("Polygonize produced %d raw polygons", len(polygons))
    return polygons


def filter_polygons(
    polys: list[Polygon],
    min_area_m2: float,
    unit: str,
    *,
    exhaustive: bool = False,
) -> list[Polygon]:
    """Remove polygons smaller than min_area in square metres."""
    scale = scale_factor(unit)
    min_drawing_area = min_area_m2 / (scale**2) if scale > 0 else min_area_m2

    filtered: list[Polygon] = []
    for p in polys:
        normalized = normalize_polygon(p)
        if normalized is None:
            continue
        area_m2 = normalized.area * (scale**2)
        if area_m2 >= min_area_m2:
            filtered.append(normalized)
        elif exhaustive:
            logger.debug("Exhaustive mode: keeping small region %.6f m2", area_m2)
            filtered.append(normalized)
    removed = len(polys) - len(filtered)
    if removed:
        logger.info("Filtered out %d polygons below min_area %.2f m2", removed, min_area_m2)
    return filtered


def _polygon_iou(a: Polygon, b: Polygon) -> float:
    if not a.intersects(b):
        return 0.0
    inter = a.intersection(b).area
    union = a.union(b).area
    return inter / union if union > 0 else 0.0


def remove_duplicates(polys: list[Polygon], iou_threshold: float = 0.95) -> list[Polygon]:
    """Remove overlapping or near-identical polygons."""
    if len(polys) <= 1:
        return polys

    keep: list[Polygon] = []
    for poly in sorted(polys, key=lambda p: p.area, reverse=True):
        duplicate = False
        for existing in keep:
            if _polygon_iou(poly, existing) >= iou_threshold:
                duplicate = True
                break
        if not duplicate:
            keep.append(poly)
    return keep


def sort_polygons(polys: list[Polygon]) -> list[Polygon]:
    """Sort polygons by area descending for consistent labelling."""
    return sorted(polys, key=lambda p: p.area, reverse=True)


def detect_regions(segments: list[LineString], config: dict[str, Any]) -> list[Polygon]:
    """Full detection pipeline: polygonize, filter, dedupe, sort."""
    geometry_cfg = config.get("geometry", {})
    accuracy_cfg = config.get("accuracy", {})
    unit = geometry_cfg.get("drawing_unit", "mm")

    mode = str(accuracy_cfg.get("detection_mode", "exhaustive")).lower()
    exhaustive = mode == "exhaustive"
    if mode not in DETECTION_MODES:
        logger.warning("Unknown detection_mode '%s'; using exhaustive", mode)
        exhaustive = True

    min_area = float(geometry_cfg.get("min_area", 1.0))
    if exhaustive:
        min_area = float(accuracy_cfg.get("exhaustive_min_area_m2", 0.01))

    dedupe_iou = float(
        accuracy_cfg.get(
            "dedupe_iou_threshold",
            0.98 if exhaustive else 0.95,
        )
    )

    multi = MultiLineString(segments) if segments else MultiLineString()

    polygons = polygonize_regions(multi)
    polygons = filter_polygons(polygons, min_area, unit, exhaustive=exhaustive)
    polygons = remove_duplicates(polygons, iou_threshold=dedupe_iou)
    polygons = sort_polygons(polygons)

    logger.info("Detected %d regions after filtering", len(polygons))
    return polygons
