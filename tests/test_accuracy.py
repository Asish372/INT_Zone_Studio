"""Accuracy benchmarks aligned with PRD success metrics."""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from src.calculator import AREA_TOLERANCE_FRACTION, compute_area
from src.units import scale_factor


def test_area_within_0_05_percent_of_known_rectangle() -> None:
    """10 m x 10 m rectangle in mm drawing units -> 100 m2."""
    poly = Polygon([(0, 0), (10000, 0), (10000, 10000), (0, 10000)])
    known_m2 = 100.0
    computed = compute_area(poly, scale_factor("mm"))
    deviation = abs(computed - known_m2) / known_m2
    assert deviation <= AREA_TOLERANCE_FRACTION


def test_area_tolerance_constant_matches_prd() -> None:
    assert AREA_TOLERANCE_FRACTION == pytest.approx(0.0005)
