"""Save/open torture test — simulates restart after full review workflow."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import yaml

from desktop.engine_sidecar.api import _apply_workspace_to_session
from desktop.engine_sidecar.detect_pipeline import detect_from_dxf_path
from desktop.engine_sidecar.polygon_records import faces_to_polygon_records
from desktop.engine_sidecar.session_store import create_session
from desktop.engine_sidecar.workspace_save import (
    build_workspace_payload,
    load_workspace_state,
    save_workspace_state,
)
from desktop.engine_sidecar.workspace_scope import empty_scope

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"


def _load_warehouse_session():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert WAREHOUSE_DXF.is_file()
    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    records = faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)

    session = create_session()
    session.source_file = "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
    session.source_file_path = str(WAREHOUSE_DXF)
    session.polygons = records
    session.expected_polygon_count = 620
    session.dxf_path = WAREHOUSE_DXF
    session.cad_available = True
    session.unit_label = "mm"
    return session


def test_save_open_torture_round_trip():
    """Load → mutate → save → new session → open → verify all persisted fields."""
    session = _load_warehouse_session()
    assert len(session.polygons) == 618

    # Simulate recovery + approvals
    recovered = {
        **session.polygons[0],
        "id": 9001,
        "source": "seed",
        "review_status": "pending",
    }
    session.polygons.append(recovered)

    for poly in session.polygons[:5]:
        poly["review_status"] = "approved"
    session.polygons[10]["review_status"] = "rejected"

    session.comments = {
        1: [{"user": "QA", "text": "slab ok", "at": "2026-06-10T09:00:00Z"}],
        9001: [{"user": "QA", "text": "recovered gap", "at": "2026-06-10T09:01:00Z"}],
    }
    session.markups = [
        {"id": 1, "x": 100.0, "y": 200.0, "text": "check beam", "user": "QA", "at": "2026-06-10"}
    ]
    session.zones = [
        {
            "label": "INT-1",
            "area_m2": 12.5,
            "face_count": 2,
            "polygon_ids": [1, 2],
        }
    ]
    session.validation_result = {
        "ok": True,
        "counts": {"gaps": 3, "overlaps": 0},
        "issues": [],
    }
    session.project_id = "pilot-warehouse-01"
    session.current_user = "Engineer A"
    session.current_role = "reviewer"
    session.selected_id = 42
    session.selected_ids = [42]

    payload = build_workspace_payload(
        polygons=session.polygons,
        source_file=session.source_file,
        source_file_path=session.source_file_path or "",
        session_id=session.session_id,
        expected_polygon_count=session.expected_polygon_count,
        project_id=session.project_id,
        zones=session.zones,
        validation=session.validation_result,
        comments=session.comments,
        markups=session.markups,
        unit_label=session.unit_label,
        current_user=session.current_user,
        current_role=session.current_role,
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "warehouse_review.pjson"
        save_workspace_state(payload, path)

        # Simulate app restart — fresh session
        restarted = create_session()
        loaded = load_workspace_state(path)
        _apply_workspace_to_session(restarted, loaded)

    assert len(restarted.polygons) == 619
    assert restarted.counts()["seed_added"] == 1
    assert restarted.counts()["total"] == 619
    assert restarted.expected_polygon_count == 620
    assert restarted.project_id == "pilot-warehouse-01"
    assert restarted.current_user == "Engineer A"
    assert restarted.current_role == "reviewer"

    approved = [p for p in restarted.polygons if p.get("review_status") == "approved"]
    rejected = [p for p in restarted.polygons if p.get("review_status") == "rejected"]
    assert len(approved) == 5
    assert len(rejected) == 1
    assert any(p["id"] == 9001 and p["source"] == "seed" for p in restarted.polygons)

    assert restarted.comments[1][0]["text"] == "slab ok"
    assert restarted.comments[9001][0]["text"] == "recovered gap"
    assert restarted.markups[0]["text"] == "check beam"
    assert restarted.zones[0]["label"] == "INT-1"
    assert restarted.validation_result["counts"]["gaps"] == 3

    # Selection is intentionally cleared on open (CAD-style fresh viewport)
    assert restarted.selected_id is None
    assert restarted.selected_ids == []


def test_workspace_file_is_valid_json_snapshot():
    session = _load_warehouse_session()
    payload = build_workspace_payload(
        polygons=session.polygons[:3],
        source_file=session.source_file,
        session_id="snap",
        comments={1: [{"user": "U", "text": "x", "at": "t"}]},
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "snap.pjson"
        save_workspace_state(payload, path)
        raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["format"] == "polygon_workspace_project"
    assert raw["version"] == 3
    assert raw["scope"] == empty_scope()
    assert len(raw["polygons"]) == 3
    assert raw["comments"]["1"][0]["text"] == "x"
