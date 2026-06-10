"""Tests for seed-assisted region detection (P1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point, Polygon

from src.calculator import compute_all
from src.detector import detect_regions
from src.models import SeedRequest
from src.seed_resolver import (
    filter_seeds_for_drawing,
    load_seeds,
    merge_regions,
    resolve_all_seeds,
    resolve_seed_region,
)


def _rect_segments(x0: float, y0: float, x1: float, y1: float) -> list[LineString]:
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    return [LineString([pts[i], pts[i + 1]]) for i in range(4)]


def _outer_inner_segments() -> list[LineString]:
    outer = _rect_segments(0, 0, 20000, 20000)
    inner = _rect_segments(5000, 5000, 15000, 15000)
    return outer + inner


@pytest.fixture
def seed_config(sample_config: dict) -> dict:
    import copy

    cfg = copy.deepcopy(sample_config)
    cfg.setdefault("accuracy", {})
    cfg["seed_assist"] = {
        "enabled": True,
        "search_radius": 50000,
        "interior_epsilon": 1.0,
        "dedupe_iou_threshold": 0.90,
        "min_area_m2": 0.01,
    }
    cfg["accuracy"]["detection_mode"] = "exhaustive"
    cfg["accuracy"]["exhaustive_min_area_m2"] = 0.01
    return cfg


def test_resolve_seed_inside_10x10_m_room(seed_config: dict) -> None:
    segments = _rect_segments(0, 0, 10000, 10000)
    seed = SeedRequest(drawing="room.dxf", x=5000, y=5000, id="s1")
    res = resolve_seed_region(seed, segments, seed_config, auto_polygons=[])
    assert res.status == "ok"
    assert res.polygon is not None
    assert res.area_m2_drawing is not None
    assert abs(res.area_m2_drawing - 100.0) < 0.5


def test_nested_seed_picks_smallest_face(seed_config: dict) -> None:
    segments = _outer_inner_segments()
    seed = SeedRequest(drawing="nested.dxf", x=10000, y=10000, id="inner")
    res = resolve_seed_region(seed, segments, seed_config, auto_polygons=[])
    assert res.status == "ok"
    assert res.polygon is not None
    # Inner 10m x 10m = 100 m²
    assert abs((res.area_m2_drawing or 0) - 100.0) < 1.0


def test_duplicate_of_auto_when_iou_high(seed_config: dict) -> None:
    segments = _rect_segments(0, 0, 10000, 10000)
    auto = detect_regions(segments, seed_config)
    assert len(auto) >= 1
    seed = SeedRequest(drawing="room.dxf", x=5000, y=5000, id="dup")
    res = resolve_seed_region(seed, segments, seed_config, auto_polygons=auto)
    assert res.status == "duplicate_of_auto"


def test_merge_adds_seed_region(seed_config: dict) -> None:
    # Outer only — inner room open (missing one wall)
    segments = _rect_segments(0, 0, 20000, 20000)
    segments += [
        LineString([(5000, 5000), (15000, 5000)]),
        LineString([(15000, 5000), (15000, 15000)]),
        LineString([(15000, 15000), (5000, 15000)]),
        # missing closing edge at x=5000
    ]
    auto = detect_regions(segments, seed_config)
    seed = SeedRequest(drawing="open.dxf", x=10000, y=10000, id="recover")
    resolutions = resolve_all_seeds([seed], segments, seed_config, auto)
    merged = merge_regions(auto, resolutions, seed_config)
    methods = [m.detection_method for m in merged]
    assert "seed_assisted" in methods or resolutions[0].status != "ok"


def test_load_seeds_json(tmp_path: Path) -> None:
    path = tmp_path / "seeds.json"
    path.write_text(
        json.dumps(
            {
                "drawing": "plan.dwg",
                "seeds": [{"id": "a", "x": 100.0, "y": 200.0, "label_hint": "Slab A"}],
            }
        ),
        encoding="utf-8",
    )
    seeds = load_seeds(path, drawing="plan.dwg")
    assert len(seeds) == 1
    assert seeds[0].x == 100.0
    assert seeds[0].label_hint == "Slab A"


def test_filter_seeds_for_drawing() -> None:
    seeds = [
        SeedRequest(drawing="S111_A.dwg", x=1, y=2),
        SeedRequest(drawing="S111_J.dwg", x=3, y=4),
    ]
    filtered = filter_seeds_for_drawing(seeds, "S111_A.dwg")
    assert len(filtered) == 1
    assert filtered[0].x == 1


def test_no_boundary_when_open(seed_config: dict) -> None:
    segments = [
        LineString([(0, 0), (10000, 0)]),
        LineString([(10000, 0), (10000, 10000)]),
        LineString([(10000, 10000), (0, 10000)]),
    ]
    seed = SeedRequest(drawing="open.dxf", x=5000, y=5000, id="open")
    res = resolve_seed_region(seed, segments, seed_config, auto_polygons=[])
    assert res.status == "no_boundary"


def test_compute_all_preserves_seed_metadata(seed_config: dict) -> None:
    poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    meta = [
        {
            "detection_method": "seed_assisted",
            "seed_x": 5000.0,
            "seed_y": 5000.0,
            "seed_id": "miss-01",
        }
    ]
    regions = compute_all([poly], seed_config, "test.dxf", region_meta=meta)
    assert len(regions) == 1
    assert regions[0].detection_method == "seed_assisted"
    assert regions[0].seed_x == 5000.0
    assert regions[0].seed_id == "miss-01"


def test_seed_recovers_region_absent_from_auto(seed_config: dict) -> None:
    """Simulated FN: auto set omits one closed room; seed restores it."""
    segments = _rect_segments(0, 0, 10000, 10000) + _rect_segments(20000, 0, 30000, 10000)
    auto_full = detect_regions(segments, seed_config)
    assert len(auto_full) == 2
    auto_partial = [auto_full[0]]
    seed = SeedRequest(drawing="sim.dxf", x=25000, y=5000, id="miss-b")
    resolutions = resolve_all_seeds([seed], segments, seed_config, auto_partial)
    assert resolutions[0].status == "ok"
    merged = merge_regions(auto_partial, resolutions, seed_config)
    assert len(merged) == 2
    assert sum(1 for m in merged if m.detection_method == "seed_assisted") == 1


def test_local_repair_recovers_open_cell(seed_config: dict) -> None:
    """P2: 745 mm gap closed locally when global tier-2 crossing guard blocks."""
    segments = [
        LineString([(0, 0), (10000, 0)]),
        LineString([(10000, 0), (10000, 10000)]),
        LineString([(10000, 10000), (1745, 10000)]),
        LineString([(0, 10000), (1000, 10000)]),
        LineString([(0, 0), (0, 10000)]),
    ]
    seed_config["geometry"]["gap_threshold"] = 500
    seed_config["seed_assist"]["local_repair_enabled"] = True
    seed_config["seed_assist"]["local_repair_reject_crossing"] = False
    seed = SeedRequest(drawing="repair.dxf", x=5000, y=5000, id="local-745")
    res = resolve_seed_region(seed, segments, seed_config, auto_polygons=[])
    assert res.status == "ok", res.message
    assert res.repair_bridges >= 1
    assert res.polygon is not None
    assert abs((res.area_m2_drawing or 0) - 100.0) < 2.0


def test_local_repair_disabled_returns_no_boundary(seed_config: dict) -> None:
    segments = [
        LineString([(0, 0), (10000, 0)]),
        LineString([(10000, 0), (10000, 10000)]),
        LineString([(10000, 10000), (0, 10000)]),
    ]
    seed_config["seed_assist"]["local_repair_enabled"] = False
    seed = SeedRequest(drawing="open.dxf", x=5000, y=5000, id="open")
    res = resolve_seed_region(seed, segments, seed_config, auto_polygons=[])
    assert res.status == "no_boundary"


def test_merge_local_repair_provenance(seed_config: dict) -> None:
    poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    from src.models import SeedResolution

    resolutions = [
        SeedResolution(
            seed=SeedRequest(drawing="x.dxf", x=1, y=2, id="r1"),
            polygon=poly,
            status="ok",
            message="ok",
            area_m2_drawing=100.0,
            repair_bridges=2,
        )
    ]
    merged = merge_regions([], resolutions, seed_config)
    assert merged[0].detection_method == "seed_assisted_local_repair"


def test_pipeline_without_seeds_unchanged(sample_dxf_path: Path, sample_config: dict) -> None:
    """Regression: zero seeds must not alter auto detection."""
    from src.extractor import extract_all_segments, extract_entities
    from src.gap_handler import close_gaps, snap_endpoints
    from src.parser import get_modelspace, load_dxf

    doc = load_dxf(sample_dxf_path)
    msp = get_modelspace(doc)
    entities = extract_entities(msp, sample_config["layers"]["wall_layers"])
    segments = extract_all_segments(entities)
    geom = sample_config["geometry"]
    segments = snap_endpoints(segments, geom["snap_tolerance"])
    segments, _ = close_gaps(segments, geom["gap_threshold"], geom["max_gap_angle"])

    auto = detect_regions(segments, sample_config)
    merged = merge_regions(auto, [], sample_config)
    assert len(merged) == len(auto)
    assert all(m.detection_method == "auto" for m in merged)
