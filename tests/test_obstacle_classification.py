"""Phase 1.6 — column obstacle extraction and classification (warehouse baseline)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from desktop.engine_sidecar.detect_pipeline import detect_from_dxf_path
from desktop.engine_sidecar.obstacle_classify import (
    GEOMETRY_ROLE_OBSTACLE,
    run_obstacle_classification,
)
from desktop.engine_sidecar.obstacle_extract import extract_column_footprints
from desktop.engine_sidecar.obstacle_validation import validate_obstacle_recovery_point
from desktop.engine_sidecar.polygon_records import faces_to_polygon_records
from desktop.engine_sidecar.workspace_save import (
    active_polygons,
    build_workspace_payload,
    is_partition_polygon,
    load_workspace_state,
    obstacle_polygons,
    save_workspace_state,
)
from desktop.engine_sidecar.workspace_scope import empty_scope
from src.parser import get_modelspace, load_dxf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"


def _warehouse_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))


def _warehouse_records():
    assert WAREHOUSE_DXF.is_file(), f"Missing fixture: {WAREHOUSE_DXF}"
    result = detect_from_dxf_path(WAREHOUSE_DXF, _warehouse_config())
    return result, faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)


def test_warehouse_column_footprints_extracted():
    config = _warehouse_config()
    doc = load_dxf(WAREHOUSE_DXF)
    msp = get_modelspace(doc)
    footprints = extract_column_footprints(msp, doc, config, unit_scale_m=0.001)
    assert len(footprints) >= 80
    layers = {fp["layer"] for fp in footprints}
    assert "S-COLS" in layers or "S-COLS-1" in layers
    for fp in footprints:
        assert len(fp.get("ring") or []) >= 3
        assert fp.get("area_m2", 0) > 0


def test_warehouse_detection_count_unchanged_before_classification():
    _, records = _warehouse_records()
    assert len(records) == 618


def test_warehouse_obstacle_classification_partitions():
    config = _warehouse_config()
    _, records = _warehouse_records()
    classified, scope, _ = run_obstacle_classification(
        records,
        dxf_path=WAREHOUSE_DXF,
        config=config,
        scope=empty_scope(),
        unit_scale_m=0.001,
        next_id=max((r["id"] for r in records), default=0),
    )
    assert len([r for r in records if r.get("geometry_role", "partition") == "partition"]) == 618
    obstacles = obstacle_polygons(classified)
    partitions = active_polygons(classified)
    assert len(obstacles) > 0
    assert len(partitions) < 618
    assert len(partitions) + len(obstacles) >= 618
    assert scope.get("obstacles", {}).get("footprint_count", 0) >= 80
    assert all(r.get("geometry_role") == GEOMETRY_ROLE_OBSTACLE for r in obstacles)


def test_partition_filter_excludes_obstacles():
    config = _warehouse_config()
    _, records = _warehouse_records()
    classified, _, _ = run_obstacle_classification(
        records,
        dxf_path=WAREHOUSE_DXF,
        config=config,
        scope=empty_scope(),
        unit_scale_m=0.001,
        next_id=max((r["id"] for r in records), default=0),
    )
    for rec in classified:
        if rec.get("geometry_role") == GEOMETRY_ROLE_OBSTACLE:
            assert not is_partition_polygon(rec)
        elif not rec.get("scope_excluded"):
            assert is_partition_polygon(rec)


def test_obstacle_metadata_save_reopen():
    config = _warehouse_config()
    _, records = _warehouse_records()
    classified, scope, _ = run_obstacle_classification(
        records,
        dxf_path=WAREHOUSE_DXF,
        config=config,
        scope=empty_scope(),
        unit_scale_m=0.001,
        next_id=max((r["id"] for r in records), default=0),
    )
    payload = build_workspace_payload(
        polygons=classified,
        source_file="warehouse.dxf",
        scope=scope,
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "warehouse.pjson"
        save_workspace_state(payload, path)
        loaded = load_workspace_state(path)
    assert loaded["scope"].get("obstacles")
    obstacle_ids = {
        p["id"] for p in loaded["polygons"] if p.get("geometry_role") == GEOMETRY_ROLE_OBSTACLE
    }
    assert len(obstacle_ids) > 0
    reloaded_obstacles = [p for p in loaded["polygons"] if p["id"] in obstacle_ids]
    assert all(p.get("geometry_role") == GEOMETRY_ROLE_OBSTACLE for p in reloaded_obstacles)


def test_recovery_blocked_on_obstacle_footprint():
    config = _warehouse_config()
    doc = load_dxf(WAREHOUSE_DXF)
    msp = get_modelspace(doc)
    footprints = extract_column_footprints(msp, doc, config, unit_scale_m=0.001)
    assert footprints
    fp = footprints[0]
    cx, cy = fp["centroid"]
    scope = {
        "boundary": None,
        "detection_scoped": False,
        "boundary_stale": False,
        "obstacles": {"footprints": footprints, "footprint_count": len(footprints)},
    }
    err = validate_obstacle_recovery_point(scope, cx, cy, config)
    assert err is not None
    assert "obstacle" in err.lower()
