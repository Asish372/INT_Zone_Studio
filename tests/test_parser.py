"""Tests for DXF parser module."""

from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest

from src.parser import get_modelspace, list_layers, load_dxf


def test_load_dxf_success(sample_dxf_path: Path) -> None:
    doc = load_dxf(sample_dxf_path)
    assert doc is not None
    msp = get_modelspace(doc)
    assert len(list(msp)) >= 4


def test_list_layers(sample_dxf_path: Path) -> None:
    doc = load_dxf(sample_dxf_path)
    layers = list_layers(doc)
    assert "WALL" in layers or "0" in layers


def test_load_dxf_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_dxf("nonexistent_file.dxf")
