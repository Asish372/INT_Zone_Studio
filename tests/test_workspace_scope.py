"""Workspace scope (slab boundary) save/load and v2 compatibility tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from desktop.engine_sidecar.workspace_save import (
    WORKSPACE_VERSION,
    build_workspace_payload,
    load_workspace_state,
    save_workspace_state,
)
from desktop.engine_sidecar.workspace_scope import (
    build_boundary,
    empty_scope,
    normalize_ring,
    normalize_scope,
    ring_metrics,
)


def test_empty_scope_round_trip():
    assert normalize_scope(None) == empty_scope()
    assert normalize_scope({}) == empty_scope()


def test_v2_payload_loads_without_scope():
    v2_payload = {
        "format": "polygon_workspace_project",
        "version": 2,
        "polygons": [],
        "source_file": "legacy.dxf",
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "legacy.pjson"
        path.write_text(json.dumps(v2_payload), encoding="utf-8")
        loaded = load_workspace_state(path)
    assert loaded["version"] == 2
    assert loaded["scope"] == empty_scope()


def test_v3_boundary_round_trip_preserves_vertices_and_area():
    ring = [[0.0, 0.0], [10000.0, 0.0], [10000.0, 8000.0], [0.0, 8000.0]]
    boundary = build_boundary(ring, source="drawn", unit_scale_m=0.001, defined_by="QA")
    polygons = [
        {
            "id": 1,
            "source": "auto",
            "status": "active",
            "ring": ring,
            "area_m2": boundary["area_m2"],
            "perimeter_m": boundary["perimeter_m"],
            "centroid": boundary["centroid"],
        }
    ]
    payload = build_workspace_payload(
        polygons=polygons,
        source_file="scope_test.dxf",
        scope={"boundary": boundary},
    )
    assert payload["version"] == WORKSPACE_VERSION
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "scoped.pjson"
        save_workspace_state(payload, path)
        loaded = load_workspace_state(path)

    loaded_boundary = loaded["scope"]["boundary"]
    assert loaded_boundary is not None
    assert normalize_ring(loaded_boundary["ring"]) == normalize_ring(ring)
    assert loaded_boundary["area_m2"] == boundary["area_m2"]
    assert loaded_boundary["source"] == "drawn"
    assert loaded_boundary["defined_by"] == "QA"


def test_ring_metrics_rejects_open_ring():
    with pytest.raises(ValueError):
        ring_metrics([[0, 0], [1, 0]], unit_scale_m=0.001)


def test_normalize_ring_strips_duplicate_close():
    ring = [[0, 0], [1, 0], [1, 1], [0, 0]]
    assert normalize_ring(ring) == [[0, 0], [1, 0], [1, 1]]
