"""Post-detection classification of column / pillar obstacles."""

from __future__ import annotations

import copy
import logging
from typing import Any

from shapely.geometry import Point, Polygon

from pathlib import Path

from desktop.engine_sidecar.obstacle_extract import (
    extract_column_footprints,
    obstacles_enabled,
)
from desktop.engine_sidecar.polygon_records import polygon_to_record
from desktop.engine_sidecar.workspace_scope import set_scope_obstacles
from src.parser import get_modelspace, load_dxf

logger = logging.getLogger(__name__)

GEOMETRY_ROLE_PARTITION = "partition"
GEOMETRY_ROLE_OBSTACLE = "obstacle"


def _obstacle_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("obstacles") or {}


def _ring_polygon(ring: list[Any]) -> Polygon | None:
    if not ring or len(ring) < 3:
        return None
    try:
        poly = Polygon(ring)
        if poly.is_empty:
            return None
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if not poly.is_empty else None
    except Exception:
        return None


def _iou(a: Polygon, b: Polygon) -> float:
    inter = a.intersection(b).area
    if inter <= 0:
        return 0.0
    union = a.union(b).area
    if union <= 0:
        return 0.0
    return inter / union


def matches_obstacle_footprint(
    rec: dict[str, Any],
    footprint: dict[str, Any],
    config: dict[str, Any],
) -> bool:
    """True when a detected polygon should be treated as a column obstacle."""
    cfg = _obstacle_cfg(config)
    max_area = float(cfg.get("max_match_area_m2", 25.0))
    iou_threshold = float(cfg.get("iou_threshold", 0.35))
    centroid_match = bool(cfg.get("centroid_match", True))

    rec_poly = _ring_polygon(rec.get("ring") or [])
    fp_poly = _ring_polygon(footprint.get("ring") or [])
    if rec_poly is None or fp_poly is None:
        return False

    centroid = rec_poly.centroid
    if centroid_match and fp_poly.contains(centroid):
        return True

    area_m2 = float(rec.get("area_m2") or 0.0)
    if area_m2 <= max_area:
        c = rec.get("centroid") or [centroid.x, centroid.y]
        if fp_poly.contains(Point(float(c[0]), float(c[1]))):
            return True

    return _iou(rec_poly, fp_poly) >= iou_threshold


def classify_records(
    records: list[dict[str, Any]],
    footprints: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    next_id: int = 0,
    unit_scale_m: float = 0.001,
    append_unmatched: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Mark matching polygons as geometry_role=obstacle.

    Optionally append audit-only obstacle records for unmatched column footprints.
    """
    if not footprints:
        out = [_default_partition(rec) for rec in records]
        return out, {"classified": 0, "appended": 0, "max_id": next_id}

    matched_fp: set[int] = set()
    classified = 0
    out: list[dict[str, Any]] = []

    for rec in records:
        item = _default_partition(rec)
        if item.get("scope_excluded"):
            out.append(item)
            continue
        for idx, fp in enumerate(footprints):
            if matches_obstacle_footprint(item, fp, config):
                item["geometry_role"] = GEOMETRY_ROLE_OBSTACLE
                item["obstacle_source"] = "detected_match"
                item["obstacle_layer"] = fp.get("layer", "")
                matched_fp.add(idx)
                classified += 1
                break
        out.append(item)

    appended = 0
    max_id = next_id
    if append_unmatched:
        for idx, fp in enumerate(footprints):
            if idx in matched_fp:
                continue
            max_id += 1
            ring = fp.get("ring") or []
            if len(ring) < 3:
                continue
            try:
                poly = Polygon(ring)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_empty:
                    continue
                record = polygon_to_record(
                    poly,
                    polygon_id=max_id,
                    source="column_insert",
                    unit_scale_m=unit_scale_m,
                )
                record["geometry_role"] = GEOMETRY_ROLE_OBSTACLE
                record["obstacle_source"] = "column_insert"
                record["obstacle_layer"] = fp.get("layer", "")
                record["obstacle_block"] = fp.get("block_name", "")
                out.append(record)
                appended += 1
            except Exception:
                continue

    return out, {
        "classified": classified,
        "appended": appended,
        "max_id": max_id,
    }


def _default_partition(rec: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(rec)
    item.setdefault("geometry_role", GEOMETRY_ROLE_PARTITION)
    return item


def run_obstacle_classification(
    records: list[dict[str, Any]],
    *,
    dxf_path,
    config: dict[str, Any],
    scope: dict[str, Any] | None,
    unit_scale_m: float,
    next_id: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    """
    Extract column footprints from CAD, classify records, update scope obstacles metadata.

    Returns (records, updated_scope, new_next_id). No-op when obstacles disabled or no DXF.
    """
    scope_out = copy.deepcopy(scope) if scope else {}
    if not obstacles_enabled(config):
        return [_default_partition(r) for r in records], scope_out, next_id
    if dxf_path is None:
        return [_default_partition(r) for r in records], scope_out, next_id

    path = Path(dxf_path)
    if not path.is_file():
        return [_default_partition(r) for r in records], scope_out, next_id

    doc = load_dxf(path)
    msp = get_modelspace(doc)
    footprints = extract_column_footprints(
        msp, doc, config, unit_scale_m=unit_scale_m
    )
    classified_records, stats = classify_records(
        records,
        footprints,
        config,
        next_id=next_id,
        unit_scale_m=unit_scale_m,
        append_unmatched=True,
    )
    scope_out = set_scope_obstacles(
        scope_out,
        footprints=footprints,
        classified_count=stats["classified"],
        appended_count=stats["appended"],
    )
    new_next_id = max(next_id, stats["max_id"])
    logger.info(
        "Obstacle classification — %d matched, %d audit footprints appended",
        stats["classified"],
        stats["appended"],
    )
    return classified_records, scope_out, new_next_id


def point_in_obstacle_footprint(
    x: float,
    y: float,
    scope: dict[str, Any] | None,
) -> bool:
    """True when (x, y) lies inside a stored column footprint."""
    if not scope or not isinstance(scope, dict):
        return False
    obstacles = scope.get("obstacles")
    if not obstacles or not isinstance(obstacles, dict):
        return False
    pt = Point(x, y)
    for fp in obstacles.get("footprints") or []:
        poly = _ring_polygon(fp.get("ring") or [])
        if poly is not None and poly.contains(pt):
            return True
    return False
