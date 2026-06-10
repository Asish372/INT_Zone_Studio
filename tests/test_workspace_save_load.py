"""Workspace save/load round-trip tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from desktop.engine_sidecar.workspace_save import (
    build_workspace_payload,
    load_workspace_state,
    save_workspace_state,
)


def test_workspace_round_trip_preserves_metadata():
    polygons = [
        {
            "id": 1,
            "source": "auto",
            "status": "active",
            "review_status": "approved",
            "ring": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
            "area_m2": 1.0,
            "perimeter_m": 4.0,
            "centroid": [500, 500],
        }
    ]
    payload = build_workspace_payload(
        polygons=polygons,
        source_file="test.dxf",
        source_file_path="C:/drawings/test.dxf",
        session_id="sess-1",
        expected_polygon_count=5,
        project_id="proj-1",
        zones=[{"label": "INT-1", "area_m2": 1.0, "face_count": 1, "polygon_ids": [1]}],
        validation={"ok": True, "counts": {"gaps": 2}, "issues": []},
        comments={1: [{"user": "QA", "text": "ok", "at": "2026-01-01T00:00:00Z"}]},
        markups=[{"id": 1, "x": 10, "y": 20, "text": "note", "user": "QA", "at": "2026-01-01"}],
        unit_label="mm",
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "workspace.pjson"
        save_workspace_state(payload, path)
        loaded = load_workspace_state(path)
    assert loaded["source_file"] == "test.dxf"
    assert loaded["expected_polygon_count"] == 5
    assert loaded["zones"][0]["label"] == "INT-1"
    assert loaded["validation"]["counts"]["gaps"] == 2
    assert loaded["comments"]["1"][0]["text"] == "ok"
    assert loaded["markups"][0]["text"] == "note"
    assert len(loaded["polygons"]) == 1
