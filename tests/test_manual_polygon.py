"""Tests for manual polygon draw validation and session counts."""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from desktop.engine_sidecar.manual_polygon_validation import (
    ring_to_polygon,
    validate_manual_polygon_in_scope,
    validate_manual_polygon_ring,
)
from desktop.engine_sidecar.polygon_records import polygon_to_record
from desktop.engine_sidecar.session_store import create_session
from desktop.engine_sidecar.workspace_scope import build_boundary, set_scope_flags


def _square_ring(x0: float, y0: float, size: float) -> list[list[float]]:
    return [
        [x0, y0],
        [x0 + size, y0],
        [x0 + size, y0 + size],
        [x0, y0 + size],
    ]


def test_ring_to_polygon_rejects_self_intersection():
    bowtie = [[0, 0], [10, 10], [10, 0], [0, 10]]
    with pytest.raises(ValueError, match="self-intersecting"):
        ring_to_polygon(bowtie)


def test_validate_manual_polygon_in_scope_when_detection_scoped():
    scope = set_scope_flags(
        {"boundary": build_boundary(_square_ring(0, 0, 100), unit_scale_m=0.001)},
        detection_scoped=True,
    )
    inside = Polygon(_square_ring(10, 10, 20))
    outside = Polygon(_square_ring(200, 200, 20))
    assert validate_manual_polygon_in_scope(scope, inside, scope_feature_enabled=True) is None
    assert (
        validate_manual_polygon_in_scope(scope, outside, scope_feature_enabled=True)
        == "Manual polygon must be inside the applied slab boundary."
    )


def test_validate_manual_polygon_ring_rejects_overlap():
    existing = polygon_to_record(
        Polygon(_square_ring(0, 0, 10)),
        polygon_id=1,
        source="auto",
        unit_scale_m=0.001,
    )
    with pytest.raises(ValueError, match="overlaps"):
        validate_manual_polygon_ring(
            _square_ring(0, 0, 10),
            records=[existing],
            scope=None,
            scope_feature_enabled=False,
        )


def test_session_counts_manual_added():
    session = create_session()
    session.polygons = [
        {"id": 1, "source": "auto", "status": "active", "geometry_role": "partition"},
        {"id": 2, "source": "manual", "status": "active", "geometry_role": "partition"},
        {"id": 3, "source": "seed", "status": "active", "geometry_role": "partition"},
    ]
    counts = session.counts()
    assert counts["detected"] == 1
    assert counts["seed_added"] == 1
    assert counts["manual_added"] == 1
    assert counts["total"] == 3
