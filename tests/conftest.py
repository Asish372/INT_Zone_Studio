"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest


@pytest.fixture
def sample_dxf_path(tmp_path: Path) -> Path:
    """Create a simple rectangular room DXF for testing."""
    path = tmp_path / "room.dxf"
    doc = ezdxf.new()
    msp = doc.modelspace()

    # 10m x 10m room in mm (10000 x 10000) — closed rectangle on WALL layer
    points = [(0, 0), (10000, 0), (10000, 10000), (0, 10000), (0, 0)]
    for i in range(len(points) - 1):
        msp.add_line(points[i], points[i + 1], dxfattribs={"layer": "WALL"})

    doc.saveas(str(path))
    return path


@pytest.fixture
def sample_config() -> dict:
    """Minimal config matching config.yaml structure."""
    return {
        "layers": {
            "wall_layers": ["WALL"],
            "ignore_layers": ["TEXT"],
        },
        "geometry": {
            "drawing_unit": "mm",
            "slab_thickness": 0.15,
            "gap_threshold": 500,
            "snap_tolerance": 1,
            "max_gap_angle": 30,
            "min_area": 1.0,
        },
        "output": {
            "output_dir": "./output",
            "export_dxf": True,
            "export_excel": True,
            "export_csv": False,
            "label_prefix": "Room",
            "dxf_region_layer": "DETECTED_REGIONS",
            "dxf_label_layer": "REGION_LABELS",
        },
    }
