"""Tests for exporter module."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from shapely.geometry import Polygon

from src.calculator import compute_all
from src.exporter import export_dxf, export_excel
from src.parser import load_dxf


def test_export_excel_columns(sample_config: dict, tmp_path: Path) -> None:
    poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    regions = compute_all([poly], sample_config, "room.dxf")
    out = tmp_path / "results.xlsx"
    export_excel(regions, out, sample_config)

    df = pd.read_excel(out)
    assert "Area (m²)" in df.columns
    assert "Volume (m³)" in df.columns
    assert len(df) >= 2  # data + summary row


def test_export_dxf_layers(sample_dxf_path: Path, sample_config: dict, tmp_path: Path) -> None:
    doc = load_dxf(sample_dxf_path)
    poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    regions = compute_all([poly], sample_config, str(sample_dxf_path))
    out = tmp_path / "annotated.dxf"
    export_dxf(doc, regions, out, sample_config)

    assert out.is_file()
    out_doc = load_dxf(out)
    layers = [layer.dxf.name for layer in out_doc.layers]
    assert "DETECTED_REGIONS" in layers
