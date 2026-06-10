"""Verify CAD label density rules for warehouse-scale drawings (618 polygons)."""

from __future__ import annotations

from pathlib import Path

import yaml

from desktop.engine_sidecar.detect_pipeline import detect_from_dxf_path
from desktop.engine_sidecar.polygon_records import faces_to_polygon_records

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"


def _zoom_tier(scale: float, fit_scale: float) -> str:
    ratio = scale / (fit_scale or 1)
    if ratio < 0.45:
        return "low"
    if ratio < 1.8:
        return "medium"
    return "high"


def _area_threshold(polygons: list[dict]) -> float:
    areas = sorted((p.get("area_m2") or 0 for p in polygons), reverse=True)
    if not areas:
        return 0.0
    return areas[int(len(areas) * 0.2)]


def _count_visible_labels(
    polygons: list[dict],
    *,
    mode: str,
    zoom_tier: str,
    selected_id: int | None = None,
) -> int:
    """Mirror of geometry.ts shouldShowPolygonId + basic bbox gate."""
    threshold = _area_threshold(polygons)
    count = 0
    for poly in polygons:
        if poly.get("status") == "deleted":
            continue
        pid = poly["id"]
        is_selected = pid == selected_id
        if is_selected:
            count += 1
            continue
        if mode == "off":
            continue
        if mode == "selected":
            continue
        if mode == "all":
            count += 1
            continue
        if zoom_tier == "low":
            continue
        if zoom_tier == "medium":
            if (poly.get("area_m2") or 0) >= threshold:
                count += 1
            continue
        count += 1
    return count


def test_warehouse_labels_off_by_default():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    records = faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)
    assert len(records) == 618

    assert _count_visible_labels(records, mode="off", zoom_tier="high") == 0


def test_warehouse_visible_ids_zoom_out_near_empty():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    records = faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)

    low_count = _count_visible_labels(records, mode="visible", zoom_tier="low")
    assert low_count == 0, f"expected 0 labels at low zoom, got {low_count}"


def test_warehouse_visible_ids_medium_zoom_not_all():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    records = faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)

    medium_count = _count_visible_labels(records, mode="visible", zoom_tier="medium")
    assert medium_count < 150, f"medium zoom too aggressive: {medium_count} labels"
    assert medium_count > 0


def test_selected_polygon_always_gets_label():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    records = faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)

    for tier in ("low", "medium", "high"):
        count = _count_visible_labels(
            records, mode="off", zoom_tier=tier, selected_id=records[0]["id"]
        )
        assert count == 1, f"selected label missing at {tier} zoom"


def test_zoom_tier_thresholds():
    fit = 0.01
    assert _zoom_tier(0.004, fit) == "low"
    assert _zoom_tier(0.008, fit) == "medium"
    assert _zoom_tier(0.02, fit) == "high"
