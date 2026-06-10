"""Tests for area/volume calculator module."""

from __future__ import annotations

from shapely.geometry import Polygon

import pytest

from src.calculator import compute_all
from src.units import scale_factor


def test_scale_factor_mm() -> None:
    assert scale_factor("mm") == pytest.approx(0.001)


def test_scale_factor_invalid() -> None:
    with pytest.raises(ValueError):
        scale_factor("feet")


def test_compute_all_area(sample_config: dict) -> None:
    # 10m x 10m in mm drawing units
    poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    regions = compute_all([poly], sample_config, "test.dxf")
    assert len(regions) == 1
    assert regions[0].area_m2 == pytest.approx(100.0, rel=1e-4)
    assert regions[0].volume_m3 == pytest.approx(15.0, rel=1e-4)
