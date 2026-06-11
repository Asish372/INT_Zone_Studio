"""Undo/redo snapshot history for workspace sessions."""

from __future__ import annotations

import copy
from typing import Any, TypedDict


class WorkspaceSnapshot(TypedDict):
    polygons: list[dict[str, Any]]
    scope: dict[str, Any]


def freeze_workspace_snapshot(
    polygons: list[dict[str, Any]],
    scope: dict[str, Any],
) -> WorkspaceSnapshot:
    """Return an immutable deep copy of polygons + scope for the history stack."""
    return {
        "polygons": copy.deepcopy(polygons),
        "scope": copy.deepcopy(scope),
    }


class HistoryStack:
    def __init__(self, max_depth: int = 30) -> None:
        self._undo: list[WorkspaceSnapshot] = []
        self._redo: list[WorkspaceSnapshot] = []
        self._max = max_depth

    @property
    def max_depth(self) -> int:
        return self._max

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    def push(self, polygons: list[dict[str, Any]], scope: dict[str, Any]) -> None:
        self._undo.append(freeze_workspace_snapshot(polygons, scope))
        if len(self._undo) > self._max:
            self._undo.pop(0)
        self._redo.clear()

    def can_undo(self) -> bool:
        return len(self._undo) > 1

    def can_redo(self) -> bool:
        return len(self._redo) > 0

    def undo(
        self,
        current_polygons: list[dict[str, Any]],
        current_scope: dict[str, Any],
    ) -> WorkspaceSnapshot | None:
        if not self.can_undo():
            return None
        self._redo.append(freeze_workspace_snapshot(current_polygons, current_scope))
        popped = self._undo.pop()
        return freeze_workspace_snapshot(popped["polygons"], popped["scope"])

    def redo(
        self,
        current_polygons: list[dict[str, Any]],
        current_scope: dict[str, Any],
    ) -> WorkspaceSnapshot | None:
        if not self._redo:
            return None
        self._undo.append(freeze_workspace_snapshot(current_polygons, current_scope))
        snap = self._redo.pop()
        return freeze_workspace_snapshot(snap["polygons"], snap["scope"])

    def seed(self, polygons: list[dict[str, Any]], scope: dict[str, Any]) -> None:
        self._undo = [freeze_workspace_snapshot(polygons, scope)]
        self._redo.clear()
