"""Tests for slab boundary pick/auto helpers."""

from __future__ import annotations

from desktop.engine_sidecar.scope_boundary_ops import (
    CadClosedLoop,
    pick_loop_at_point,
)


def test_pick_loop_prefers_smallest_containing_polygon():
    outer = CadClosedLoop(
        ring=[[0, 0], [100, 0], [100, 100], [0, 100]],
        layer="S-FNDN-1",
        handle="1",
        entity_type="LWPOLYLINE",
        area_native=10000,
    )
    inner = CadClosedLoop(
        ring=[[10, 10], [40, 10], [40, 40], [10, 40]],
        layer="S-FNDN-1",
        handle="2",
        entity_type="LWPOLYLINE",
        area_native=900,
    )
    picked = pick_loop_at_point([outer, inner], 20, 20, pick_tolerance_native=50)
    assert picked is not None
    assert picked.handle == "2"


def test_pick_loop_nearest_boundary_within_tolerance():
    loop = CadClosedLoop(
        ring=[[0, 0], [100, 0], [100, 100], [0, 100]],
        layer="S-FNDN-1",
        handle="1",
        entity_type="LWPOLYLINE",
        area_native=10000,
    )
    picked = pick_loop_at_point([loop], 50, -10, pick_tolerance_native=20)
    assert picked is not None
    assert picked.handle == "1"
