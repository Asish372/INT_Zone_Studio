"""INT zone grouping for workspace polygons."""

from __future__ import annotations

import math
from typing import Any


def _centroid(ring: list) -> tuple[float, float]:
    if not ring:
        return 0.0, 0.0
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    return cx, cy


def _bounds(polygons: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    min_x = min_y = math.inf
    max_x = max_y = -math.inf
    for rec in polygons:
        for x, y in rec.get("ring") or []:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    if not math.isfinite(min_x):
        return 0, 0, 1, 1
    return min_x, min_y, max_x, max_y


def generate_int_zones(
    polygons: list[dict[str, Any]],
    *,
    target_zones: int | None = None,
) -> list[dict[str, Any]]:
    """
    Spatial grid clustering: assign polygons to INT zones by centroid grid cell.
    """
    active = [p for p in polygons if p.get("status", "active") != "deleted"]
    if not active:
        return []

    min_x, min_y, max_x, max_y = _bounds(active)
    bw = max_x - min_x or 1
    bh = max_y - min_y or 1
    n = len(active)
    target = target_zones or max(1, min(24, int(math.sqrt(n))))
    cols = max(1, int(math.ceil(math.sqrt(target * bw / bh))))
    rows = max(1, int(math.ceil(target / cols)))
    cell_w = bw / cols
    cell_h = bh / rows

    zone_map: dict[str, list[int]] = {}
    zone_meta: dict[str, dict[str, Any]] = {}

    for rec in active:
        pid = rec["id"]
        cx, cy = _centroid(rec.get("ring") or [])
        col = min(cols - 1, max(0, int((cx - min_x) / cell_w)))
        row = min(rows - 1, max(0, int((cy - min_y) / cell_h)))
        cell_idx = row * cols + col
        label = f"INT-{cell_idx + 1:02d}"
        zone_map.setdefault(label, []).append(pid)
        rec["int_zone"] = label

    zones: list[dict[str, Any]] = []
    for label in sorted(zone_map.keys()):
        face_ids = zone_map[label]
        area = sum(
            next((p.get("area_m2", 0) for p in active if p["id"] == fid), 0)
            for fid in face_ids
        )
        zones.append(
            {
                "label": label,
                "area_m2": round(area, 2),
                "face_count": len(face_ids),
                "polygon_ids": face_ids,
            }
        )
        zone_meta[label] = zones[-1]

    return zones


def merge_zones(
    zones: list[dict[str, Any]],
    polygons: list[dict[str, Any]],
    label_a: str,
    label_b: str,
) -> list[dict[str, Any]]:
    """Merge two zones; reassign polygons to label_a."""
    if label_a == label_b:
        return zones
    target = label_a
    source = label_b
    for rec in polygons:
        if rec.get("int_zone") == source:
            rec["int_zone"] = target
    merged_ids: list[int] = []
    merged_area = 0.0
    new_zones: list[dict[str, Any]] = []
    for z in zones:
        if z["label"] == source:
            merged_ids.extend(z.get("polygon_ids", []))
            merged_area += z.get("area_m2", 0)
        elif z["label"] == target:
            z = dict(z)
            z["polygon_ids"] = list(z.get("polygon_ids", [])) + merged_ids
            z["face_count"] = len(z["polygon_ids"])
            z["area_m2"] = round(z.get("area_m2", 0) + merged_area, 2)
            new_zones.append(z)
        else:
            new_zones.append(z)
    return new_zones


def rename_zone(
    zones: list[dict[str, Any]],
    polygons: list[dict[str, Any]],
    old_label: str,
    new_label: str,
) -> list[dict[str, Any]]:
    for rec in polygons:
        if rec.get("int_zone") == old_label:
            rec["int_zone"] = new_label
    return [{**z, "label": new_label} if z["label"] == old_label else z for z in zones]
