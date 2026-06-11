"""Manual INT zone edits (merge/rename) after authoritative pipeline assignment."""

from __future__ import annotations

from typing import Any


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
