"""Tests for region detector module."""

from __future__ import annotations

from pathlib import Path

from src.detector import detect_regions
from src.extractor import extract_all_segments, extract_entities
from src.gap_handler import close_gaps, snap_endpoints
from src.parser import get_modelspace, load_dxf


def test_detect_regions_rectangle(sample_dxf_path: Path, sample_config: dict) -> None:
    doc = load_dxf(sample_dxf_path)
    msp = get_modelspace(doc)
    entities = extract_entities(msp, sample_config["layers"]["wall_layers"])
    segments = extract_all_segments(entities)

    geom = sample_config["geometry"]
    segments = snap_endpoints(segments, geom["snap_tolerance"])
    segments, _ = close_gaps(segments, geom["gap_threshold"], geom["max_gap_angle"])

    polygons = detect_regions(segments, sample_config)
    assert len(polygons) >= 1
