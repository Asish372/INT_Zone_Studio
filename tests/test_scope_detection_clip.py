"""Phase 1.5 — scoped detection clip tests (warehouse baseline)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import yaml

from desktop.engine_sidecar.api import _apply_scoped_detection, _apply_workspace_to_session
from desktop.engine_sidecar.detect_pipeline import detect_from_dxf_path
from desktop.engine_sidecar.polygon_records import faces_to_polygon_records
from desktop.engine_sidecar.scope_clip import apply_scope_clip
from desktop.engine_sidecar.scope_validation import validate_scope_recovery_point
from desktop.engine_sidecar.session_store import create_session
from desktop.engine_sidecar.workspace_save import (
    active_polygons,
    build_workspace_payload,
    load_workspace_state,
    save_workspace_state,
)
from desktop.engine_sidecar.workspace_scope import (
    build_boundary,
    empty_scope,
    normalize_scope,
    set_scope_flags,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"


def _warehouse_config() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))


def _warehouse_records():
    assert WAREHOUSE_DXF.is_file(), f"Missing fixture: {WAREHOUSE_DXF}"
    result = detect_from_dxf_path(WAREHOUSE_DXF, _warehouse_config())
    return result, faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)


def _warehouse_session_with_boundary():
    result, records = _warehouse_records()
    session = create_session()
    session.source_file = "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
    session.source_file_path = str(WAREHOUSE_DXF)
    session.dxf_path = WAREHOUSE_DXF
    session.polygons = records
    session.segments = result.segments
    session.cad_segments = result.cad_segments
    session.auto_polygons = list(result.polygons)
    session.unit_scale_m = result.unit_scale_m
    session.cad_available = True
    boundary = build_boundary(
        [[5000.0, 5000.0], [55000.0, 5000.0], [55000.0, 35000.0], [5000.0, 35000.0]],
        source="drawn",
        unit_scale_m=result.unit_scale_m,
    )
    session.scope = set_scope_flags(
        {"boundary": boundary},
        detection_scoped=False,
        boundary_stale=True,
    )
    return session


def test_warehouse_full_detection_618():
    _, records = _warehouse_records()
    assert len(records) == 618


def test_apply_boundary_reduces_active_count():
    session = _warehouse_session_with_boundary()
    stats = _apply_scoped_detection(session)
    auto_detected = sum(1 for p in session.polygons if p.get("source") == "auto")
    assert auto_detected == 618
    assert stats["full"] == len(session.polygons)
    assert stats["active"] < 618
    assert stats["excluded"] > 0
    assert session.scope["detection_scoped"] is True
    assert session.scope["boundary_stale"] is False
    assert session.counts()["total"] == stats["active"]
    assert session.counts()["scope_excluded"] == stats["excluded"]


def test_scope_excluded_field_not_status():
    session = _warehouse_session_with_boundary()
    _apply_scoped_detection(session)
    excluded = [p for p in session.polygons if p.get("scope_excluded")]
    assert excluded
    assert all(p.get("status", "active") == "active" for p in excluded)


def test_save_reopen_scoped_state():
    session = _warehouse_session_with_boundary()
    _apply_scoped_detection(session)
    payload = build_workspace_payload(
        polygons=session.polygons,
        source_file=session.source_file,
        source_file_path=session.source_file_path or "",
        session_id=session.session_id,
        scope=session.scope,
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "scoped.pjson"
        save_workspace_state(payload, path)
        loaded = load_workspace_state(path)

    assert loaded["scope"]["detection_scoped"] is True
    assert loaded["scope"]["boundary_stale"] is False
    excluded = sum(1 for p in loaded["polygons"] if p.get("scope_excluded"))
    assert excluded > 0

    restarted = create_session()
    _apply_workspace_to_session(restarted, loaded)
    assert restarted.scope["detection_scoped"] is True
    assert restarted.counts()["total"] == len(active_polygons(restarted.polygons))


def test_boundary_edit_resets_detection_scoped():
    session = _warehouse_session_with_boundary()
    _apply_scoped_detection(session)
    new_boundary = build_boundary(
        [[6000.0, 6000.0], [54000.0, 6000.0], [54000.0, 34000.0], [6000.0, 34000.0]],
        source="drawn",
        unit_scale_m=session.unit_scale_m,
    )
    session.scope = set_scope_flags(
        {"boundary": new_boundary},
        detection_scoped=False,
        boundary_stale=True,
    )
    assert session.scope["detection_scoped"] is False
    assert session.scope["boundary_stale"] is True


def test_recovery_outside_boundary_rejected():
    session = _warehouse_session_with_boundary()
    _apply_scoped_detection(session)
    msg = validate_scope_recovery_point(session.scope, 0.0, 0.0, scope_feature_enabled=True)
    assert msg is not None
    assert "outside" in msg.lower()


def test_recovery_inside_boundary_allowed():
    session = _warehouse_session_with_boundary()
    _apply_scoped_detection(session)
    boundary = session.scope["boundary"]
    cx, cy = boundary["centroid"]
    msg = validate_scope_recovery_point(session.scope, cx, cy, scope_feature_enabled=True)
    assert msg is None


def test_apply_scope_clip_marks_outside_centroids():
    _, records = _warehouse_records()
    boundary = build_boundary(
        [[10000.0, 10000.0], [40000.0, 10000.0], [40000.0, 30000.0], [10000.0, 30000.0]],
        source="drawn",
        unit_scale_m=0.001,
    )
    scope = {"boundary": boundary, "detection_scoped": False, "boundary_stale": True}
    clipped, excluded = apply_scope_clip(records, scope)
    assert len(clipped) == 618
    assert excluded > 0
    assert excluded + len(active_polygons(clipped)) == 618


def test_empty_scope_flags_default_false():
    assert normalize_scope(None) == empty_scope()
    assert empty_scope() == {
        "boundary": None,
        "detection_scoped": False,
        "boundary_stale": False,
        "obstacles": None,
    }


def test_v3_payload_without_flags_loads_defaults():
    payload = {
        "format": "polygon_workspace_project",
        "version": 3,
        "polygons": [],
        "scope": {"boundary": None},
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "legacy_flags.pjson"
        path.write_text(json.dumps(payload), encoding="utf-8")
        loaded = load_workspace_state(path)
    assert loaded["scope"]["detection_scoped"] is False
    assert loaded["scope"]["boundary_stale"] is False
