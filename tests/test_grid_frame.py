"""Tests for P1 grid frame builder."""

from __future__ import annotations

import ezdxf
from shapely.geometry import LineString

from src.zone_engine.grid_frame import (
    _cluster_positions,
    _factor_bay_count,
    _select_axis_positions,
    build_grid_frame,
    extract_grid_lines,
)


def _add_line(msp, layer: str, x0: float, y0: float, x1: float, y1: float) -> None:
    msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": layer})


def test_cluster_positions_merges_close_axes():
    merged = _cluster_positions([0.0, 100.0, 150.0, 5000.0], tolerance_mm=200.0)
    assert merged == [83.33333333333333, 5000.0]


def test_factor_bay_count_24():
    assert _factor_bay_count(24) == (4, 6) or _factor_bay_count(24) == (6, 4)


def test_select_axis_positions_evenly():
    positions = list(range(0, 18))
    selected = _select_axis_positions(positions, target_cells=6)
    assert len(selected) == 7
    assert selected[0] == 0
    assert selected[-1] == 17


def test_build_grid_frame_synthetic_6x4():
    doc = ezdxf.new()
    msp = doc.modelspace()
    xs = [0, 10000, 20000, 30000, 40000, 50000, 60000]
    ys = [0, 20000, 40000, 60000, 80000]
    for x in xs:
        _add_line(msp, "S-GRID-1", x, -1000, x, 90000)
    for y in ys:
        _add_line(msp, "S-GRID-1", -1000, y, 70000, y)

    result = build_grid_frame(
        msp,
        grid_layers=["S-GRID-1"],
        include_candidate_layers=False,
        position_cluster_mm=1.0,
        min_line_length_mm=100.0,
        expected_int_count=24,
        unit_scale_m=0.001,
    )
    assert result.bay_count == 24
    assert result.axis_a is not None
    assert result.axis_b is not None


def test_extract_grid_lines_respects_min_length():
    doc = ezdxf.new()
    msp = doc.modelspace()
    _add_line(msp, "S-GRID-2", 0, 0, 500, 0)
    _add_line(msp, "S-GRID-1", 0, 0, 20000, 0)
    lines = extract_grid_lines(msp, ["S-GRID-1", "S-GRID-2"], min_line_length_mm=1000.0)
    assert len(lines) == 1
    assert lines[0].layer == "S-GRID-1"
