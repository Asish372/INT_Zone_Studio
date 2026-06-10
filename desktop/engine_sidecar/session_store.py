"""In-memory workspace sessions (one per client tab)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from shapely.geometry import LineString, Polygon

from desktop.engine_sidecar.workspace_history import HistoryStack


@dataclass
class ActionEntry:
    message: str
    kind: str = "info"
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user: str = "System"


@dataclass
class WorkspaceSession:
    session_id: str = ""
    source_file: str = ""
    dxf_path: Path | None = None
    upload_path: Path | None = None
    segments: list[LineString] = field(default_factory=list)
    cad_segments: list[LineString] = field(default_factory=list)
    polygons: list[dict[str, Any]] = field(default_factory=list)
    auto_polygons: list[Polygon] = field(default_factory=list)
    next_id: int = 1
    unit_label: str = "mm"
    unit_scale_m: float = 0.001
    actions: list[ActionEntry] = field(default_factory=list)
    selected_id: int | None = None
    selected_ids: list[int] = field(default_factory=list)
    current_user: str = "Engineer A"
    current_role: str = "engineer"
    expected_polygon_count: int | None = None
    zones: list[dict[str, Any]] = field(default_factory=list)
    validation_result: dict[str, Any] | None = None
    comments: dict[int, list[dict[str, str]]] = field(default_factory=dict)
    markups: list[dict[str, Any]] = field(default_factory=list)
    project_id: str | None = None
    workspace_save_path: str | None = None
    source_file_path: str | None = None
    cad_available: bool = False
    history: HistoryStack = field(default_factory=HistoryStack)

    def log(self, message: str, *, kind: str = "info", user: str | None = None) -> None:
        self.actions.insert(
            0,
            ActionEntry(message=message, kind=kind, user=user or self.current_user),
        )
        self.actions = self.actions[:100]

    def snapshot_polygons(self) -> None:
        self.history.push(self.polygons)

    def restore_polygons(self, polygons: list[dict[str, Any]]) -> None:
        self.polygons = polygons

    def counts(self) -> dict[str, int]:
        active = [p for p in self.polygons if p.get("status", "active") != "deleted"]
        auto = sum(1 for p in active if p.get("source") == "auto")
        seed = sum(1 for p in active if p.get("source") == "seed")
        deleted = sum(1 for p in self.polygons if p.get("status") == "deleted")
        return {
            "detected": auto,
            "seed_added": seed,
            "deleted": deleted,
            "total": len(active),
        }


_sessions: dict[str, WorkspaceSession] = {}


def create_session() -> WorkspaceSession:
    session_id = str(uuid4())
    session = WorkspaceSession(session_id=session_id)
    _sessions[session_id] = session
    return session


def get_session(session_id: str | None) -> WorkspaceSession | None:
    if not session_id:
        return None
    return _sessions.get(session_id)


def get_or_create_session(session_id: str | None) -> WorkspaceSession:
    session = get_session(session_id)
    if session is not None:
        return session
    return create_session()
