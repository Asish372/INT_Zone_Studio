"""Boundary undo/redo history tests (Phase 1 gate)."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from desktop.engine_sidecar.api import _apply_workspace_to_session
from desktop.engine_sidecar.session_store import create_session
from desktop.engine_sidecar.workspace_history import HistoryStack
from desktop.engine_sidecar.workspace_save import (
    build_workspace_payload,
    load_workspace_state,
    save_workspace_state,
)
from desktop.engine_sidecar.workspace_scope import build_boundary, empty_scope, normalize_ring, set_scope_flags


def _ring_a() -> list[list[float]]:
    return [[0.0, 0.0], [10000.0, 0.0], [10000.0, 8000.0], [0.0, 8000.0]]


def _ring_b() -> list[list[float]]:
    return [[1000.0, 1000.0], [9000.0, 1000.0], [9000.0, 7000.0], [1000.0, 7000.0]]


def _commit_boundary(session, ring: list[list[float]]) -> dict:
    session.snapshot_workspace()
    boundary = build_boundary(ring, source="drawn", unit_scale_m=0.001)
    session.scope = set_scope_flags(
        {"boundary": boundary},
        detection_scoped=False,
        boundary_stale=True,
    )
    return boundary


def _clear_boundary(session) -> None:
    session.snapshot_workspace()
    session.scope = empty_scope()


def _undo(session) -> None:
    restored = session.history.undo(session.polygons, session.scope)
    assert restored is not None
    session.restore_workspace(restored["polygons"], restored["scope"])


def _redo(session) -> None:
    restored = session.history.redo(session.polygons, session.scope)
    assert restored is not None
    session.restore_workspace(restored["polygons"], restored["scope"])


def _boundary_ring(session) -> list[list[float]] | None:
    b = session.scope.get("boundary")
    if not b:
        return None
    return normalize_ring(b.get("ring") or [])


def test_draw_boundary_undo_removes_boundary():
    session = create_session()
    session.polygons = [{"id": 1, "source": "auto", "status": "active"}]
    session.seed_history()

    _commit_boundary(session, _ring_a())
    assert _boundary_ring(session) == normalize_ring(_ring_a())

    _undo(session)
    assert session.scope.get("boundary") is None


def test_undo_redo_restores_boundary():
    session = create_session()
    session.polygons = [{"id": 1, "source": "auto", "status": "active"}]
    session.seed_history()

    committed = _commit_boundary(session, _ring_a())
    _undo(session)
    assert session.scope.get("boundary") is None

    _redo(session)
    assert _boundary_ring(session) == normalize_ring(committed["ring"])


def test_clear_boundary_undo_restores_boundary():
    session = create_session()
    session.polygons = [{"id": 1, "source": "auto", "status": "active"}]
    session.seed_history()

    committed = _commit_boundary(session, _ring_a())
    _clear_boundary(session)
    assert session.scope.get("boundary") is None

    _undo(session)
    assert _boundary_ring(session) == normalize_ring(committed["ring"])


def test_save_after_undo_reopen_preserves_state():
    session = create_session()
    session.polygons = [{"id": 1, "source": "auto", "status": "active", "ring": _ring_a()}]
    session.seed_history()
    _commit_boundary(session, _ring_a())
    _undo(session)
    assert session.scope.get("boundary") is None

    payload = build_workspace_payload(
        polygons=session.polygons,
        source_file="undo_save_test.dxf",
        scope=session.scope,
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "after_undo.pjson"
        save_workspace_state(payload, path)
        loaded = load_workspace_state(path)

    restarted = create_session()
    _apply_workspace_to_session(restarted, loaded)
    assert restarted.scope.get("boundary") is None
    assert restarted.history.can_undo() is False


def test_boundary_replace_undo_redo_a_then_b():
    session = create_session()
    session.polygons = [{"id": 1, "source": "auto", "status": "active"}]
    session.seed_history()

    boundary_a = _commit_boundary(session, _ring_a())
    boundary_b = _commit_boundary(session, _ring_b())
    assert _boundary_ring(session) == normalize_ring(boundary_b["ring"])

    _undo(session)
    assert _boundary_ring(session) == normalize_ring(boundary_a["ring"])

    _redo(session)
    assert _boundary_ring(session) == normalize_ring(boundary_b["ring"])


def test_history_snapshots_immutable_after_boundary_mutate():
    session = create_session()
    session.polygons = [{"id": 1, "source": "auto", "status": "active"}]
    session.seed_history()
    boundary_a = _commit_boundary(session, _ring_a())

    _undo(session)
    assert session.scope.get("boundary") is None

    # In-place mutation of live session must not corrupt frozen redo snapshot
    session.scope = {"boundary": copy.deepcopy(boundary_a)}
    session.scope["boundary"]["ring"][0][0] = 999999.0

    _redo(session)
    assert _boundary_ring(session) == normalize_ring(boundary_a["ring"])
    assert session.scope["boundary"]["ring"][0][0] != 999999.0


def test_history_max_depth_preserved_with_scope():
    stack = HistoryStack(max_depth=30)
    scope = empty_scope()
    polys: list[dict] = [{"id": 1}]
    stack.seed(polys, scope)

    for i in range(35):
        scope = {
            "boundary": build_boundary(
                [[float(i), 0], [float(i + 1), 0], [float(i + 1), 1]],
                source="drawn",
                unit_scale_m=0.001,
            )
        }
        stack.push(polys, scope)

    assert stack.undo_depth == 30
    assert stack.max_depth == 30


def test_open_project_resets_history_no_stale_boundary_undo():
    session = create_session()
    session.polygons = [{"id": 1, "source": "auto", "status": "active"}]
    session.seed_history()
    _commit_boundary(session, _ring_a())

    payload = build_workspace_payload(
        polygons=[{"id": 2, "source": "auto", "status": "active"}],
        source_file="other.dxf",
        scope=empty_scope(),
    )
    restarted = create_session()
    _apply_workspace_to_session(restarted, payload)

    assert restarted.scope.get("boundary") is None
    assert restarted.history.can_undo() is False

    # Simulate stale undo attempt on fresh load
    restored = restarted.history.undo(restarted.polygons, restarted.scope)
    assert restored is None


def test_upload_resets_history_cannot_undo_previous_boundary():
    session = create_session()
    session.polygons = [{"id": 1, "source": "auto", "status": "active"}]
    session.seed_history()
    _commit_boundary(session, _ring_a())

    session.polygons = [{"id": 10, "source": "auto", "status": "active"}]
    session.scope = empty_scope()
    session.seed_history()

    assert session.history.can_undo() is False
    restored = session.history.undo(session.polygons, session.scope)
    assert restored is None
    assert session.scope.get("boundary") is None
