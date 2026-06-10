"""Tests for P2 bay geometry (clip, labels, validation)."""

from __future__ import annotations

import ezdxf
from shapely.geometry import Polygon, box

from src.zone_engine.bay_geometry import build_grid_frame_geometry, clip_bays_to_slab
from src.zone_engine.grid_frame import BayCell, build_grid_frame
from src.zone_engine.int_labels import assign_int_labels
from src.zone_engine.slab_outline import SlabOutlineResult


def _add_line(msp, layer: str, x0: float, y0: float, x1: float, y1: float) -> None:
    msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": layer})


def test_int_labels_deterministic_row_major():
    bays = [
        BayCell(1, 1, 0, Polygon(), 1, (0, 0), (0, 0, 1, 1), 0, 1, 0, 1),
        BayCell(2, 0, 0, Polygon(), 1, (0, 0), (0, 0, 1, 1), 0, 1, 0, 1),
        BayCell(3, 0, 1, Polygon(), 1, (0, 0), (0, 0, 1, 1), 0, 1, 0, 1),
    ]
    assign_int_labels(bays)
    by_row_col = {(b.row, b.col): b.int_label for b in bays}
    assert by_row_col[(0, 0)] == "INT-1"
    assert by_row_col[(0, 1)] == "INT-2"
    assert by_row_col[(1, 0)] == "INT-3"


def test_clip_bays_reduces_perimeter_coverage():
    slab = SlabOutlineResult(
        layer="S-FNDN-1",
        method="test",
        polygon=box(0, 0, 50000, 50000),
        area_m2=2500.0,
        segment_count=4,
        polygonize_count=0,
        warnings=[],
    )
    bays = [
        BayCell(
            1,
            0,
            0,
            box(0, 0, 10000, 10000),
            100.0,
            (5000, 5000),
            (0, 0, 10000, 10000),
            0,
            10000,
            0,
            10000,
        ),
        BayCell(
            2,
            0,
            1,
            box(55000, 0, 65000, 10000),
            100.0,
            (60000, 5000),
            (55000, 0, 65000, 10000),
            55000,
            65000,
            0,
            10000,
        ),
    ]
    for bay in bays:
        bay.raw_area_m2 = bay.area_m2

    non_empty = clip_bays_to_slab(bays, slab, unit_scale_m=0.001)
    assert non_empty == 1
    assert bays[0].coverage_pct > 99.0
    assert bays[1].coverage_pct < 50.0


def test_build_grid_frame_geometry_synthetic():
    doc = ezdxf.new()
    msp = doc.modelspace()
    xs = [0, 10000, 20000, 30000, 40000, 50000, 60000]
    ys = [0, 20000, 40000, 60000, 80000]
    for x in xs:
        _add_line(msp, "S-GRID-1", x, -1000, x, 90000)
    for y in ys:
        _add_line(msp, "S-GRID-1", -1000, y, 70000, y)
    for x in range(0, 70000, 5000):
        _add_line(msp, "S-FNDN-1", x, 0, x + 2000, 0)
    _add_line(msp, "S-FNDN-1", 0, 0, 70000, 0)
    _add_line(msp, "S-FNDN-1", 0, 80000, 70000, 80000)
    _add_line(msp, "S-FNDN-1", 0, 0, 0, 80000)
    _add_line(msp, "S-FNDN-1", 70000, 0, 70000, 80000)

    config = {
        "geometry": {"gap_threshold": 500, "snap_tolerance": 1, "max_gap_angle": 30},
        "zone_engine": {"grid_layers": ["S-GRID-1"], "low_coverage_pct": 25.0},
    }
    result = build_grid_frame_geometry(
        msp,
        config,
        expected_int_count=24,
        unit_scale_m=0.001,
    )
    assert result.frame.bay_count == 24
    assert len(result.bays) == 24
    labels = [b.int_label for b in sorted(result.bays, key=lambda b: (b.row, b.col))]
    assert labels == [f"INT-{i}" for i in range(1, 25)]
    assert result.validation.overlap_pair_count == 0
