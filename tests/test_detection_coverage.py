"""Tests for P1 detection coverage instrumentation."""

from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest

from src.detection_coverage import (
    MISS_GAP_BLOCKED,
    MISS_LAYER_SELECTION,
    MISS_NONE,
    MISS_UNSUPPORTED_ENTITY,
    analyze_drawing_coverage,
    records_to_rows,
    render_coverage_report_markdown,
)
from src.parser import load_dxf


@pytest.fixture
def coverage_dxf(tmp_path: Path) -> Path:
    """Closed rectangle room + INSERT for entity-support instrumentation."""
    path = tmp_path / "coverage_room.dxf"
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Closed 10m square in mm on WALL layer
    points = [(0, 0), (10000, 0), (10000, 10000), (0, 10000), (0, 0)]
    for i in range(len(points) - 1):
        msp.add_line(points[i], points[i + 1], dxfattribs={"layer": "WALL"})

    msp.add_blockref("COL", (5000, 5000), dxfattribs={"layer": "S-COLS"})

    doc.saveas(str(path))
    return path


@pytest.fixture
def open_gap_dxf(tmp_path: Path) -> Path:
    """Open rectangle with gap + INSERT near gap endpoint."""
    path = tmp_path / "open_gap_room.dxf"
    doc = ezdxf.new()
    msp = doc.modelspace()

    msp.add_line((0, 0), (10000, 0), dxfattribs={"layer": "WALL"})
    msp.add_line((10000, 0), (10000, 10000), dxfattribs={"layer": "WALL"})
    msp.add_line((10000, 10000), (5000, 10000), dxfattribs={"layer": "WALL"})
    msp.add_line((0, 10000), (0, 0), dxfattribs={"layer": "WALL"})
    msp.add_blockref("COL", (5000, 10000), dxfattribs={"layer": "S-COLS"})

    doc.saveas(str(path))
    return path


@pytest.fixture
def coverage_config() -> dict:
    return {
        "layers": {
            "wall_layers": ["WALL"],
            "ignore_layers": ["TEXT"],
        },
        "geometry": {
            "drawing_unit": "mm",
            "gap_threshold": 500,
            "snap_tolerance": 1,
            "max_gap_angle": 30,
            "min_area": 1.0,
        },
        "accuracy": {
            "detection_mode": "exhaustive",
            "exhaustive_min_area_m2": 0.01,
            "dedupe_iou_threshold": 0.98,
            "arc_segments": 64,
        },
    }


def test_analyze_drawing_coverage_detects_blocks(
    coverage_dxf: Path, coverage_config: dict
) -> None:
    doc = load_dxf(coverage_dxf)
    result = analyze_drawing_coverage(
        drawing_name=coverage_dxf.name,
        source_path=str(coverage_dxf),
        dxf_path=str(coverage_dxf),
        doc=doc,
        config=coverage_config,
    )

    assert result.error is None
    assert result.detected_count >= 1
    detected = [r for r in result.records if r.detection_status == "detected"]
    assert all(r.miss_category == MISS_NONE for r in detected)
    assert detected[0].layer == "WALL"


def test_analyze_drawing_coverage_classifies_gaps_and_entities(
    open_gap_dxf: Path, coverage_config: dict
) -> None:
    doc = load_dxf(open_gap_dxf)
    result = analyze_drawing_coverage(
        drawing_name=open_gap_dxf.name,
        source_path=str(open_gap_dxf),
        dxf_path=str(open_gap_dxf),
        doc=doc,
        config=coverage_config,
    )

    categories = {r.miss_category for r in result.records if r.miss_category != MISS_NONE}
    assert MISS_GAP_BLOCKED in categories or result.open_endpoints_after_close > 0
    assert MISS_UNSUPPORTED_ENTITY in categories


def test_layer_miss_when_configured_empty(tmp_path: Path, coverage_config: dict) -> None:
    path = tmp_path / "wrong_layers.dxf"
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (10000, 0), dxfattribs={"layer": "S-FNDN-1"})
    msp.add_line((10000, 0), (10000, 10000), dxfattribs={"layer": "S-FNDN-1"})
    msp.add_line((10000, 10000), (0, 10000), dxfattribs={"layer": "S-FNDN-1"})
    msp.add_line((0, 10000), (0, 0), dxfattribs={"layer": "S-FNDN-1"})
    doc.saveas(str(path))

    coverage_config["layers"]["wall_layers"] = ["WALL", "S-WALL"]
    doc = load_dxf(path)
    result = analyze_drawing_coverage(
        drawing_name=path.name,
        source_path=str(path),
        dxf_path=str(path),
        doc=doc,
        config=coverage_config,
    )

    layer_misses = [r for r in result.records if r.miss_category == MISS_LAYER_SELECTION]
    assert any(r.block_id == "layer-miss-configured-empty" for r in layer_misses)
    assert result.layer_source == "auto_fallback"


def test_records_to_rows_and_report(coverage_dxf: Path, coverage_config: dict) -> None:
    doc = load_dxf(coverage_dxf)
    result = analyze_drawing_coverage(
        drawing_name=coverage_dxf.name,
        source_path=str(coverage_dxf),
        dxf_path=str(coverage_dxf),
        doc=doc,
        config=coverage_config,
    )
    rows = records_to_rows(result.records)
    assert rows
    assert "detection_status" in rows[0]

    md = render_coverage_report_markdown([result], coverage_config)
    assert "# Detection Coverage Report" in md
    assert coverage_dxf.name in md
