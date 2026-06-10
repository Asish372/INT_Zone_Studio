"""Tests for entity extractor module."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.extractor import entity_to_segments, extract_all_segments, extract_entities
from src.parser import get_modelspace, load_dxf


def test_extract_entities_from_sample(sample_dxf_path: Path, sample_config: dict) -> None:
    doc = load_dxf(sample_dxf_path)
    msp = get_modelspace(doc)
    layers = sample_config["layers"]["wall_layers"]
    entities = extract_entities(msp, layers)
    assert len(entities) == 4


def test_extract_all_segments(sample_dxf_path: Path, sample_config: dict) -> None:
    doc = load_dxf(sample_dxf_path)
    msp = get_modelspace(doc)
    entities = extract_entities(msp, sample_config["layers"]["wall_layers"])
    segments = extract_all_segments(entities)
    assert len(segments) == 4


def test_entity_to_segments_line() -> None:
    import ezdxf

    doc = ezdxf.new()
    line = doc.modelspace().add_line((0, 0), (10, 0))
    segments = entity_to_segments(line)
    assert len(segments) == 1
    assert segments[0].length == pytest.approx(10.0)
