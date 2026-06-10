"""Undo/redo snapshot history for workspace sessions."""

from __future__ import annotations

import copy
from typing import Any


class HistoryStack:
    def __init__(self, max_depth: int = 30) -> None:
        self._undo: list[list[dict[str, Any]]] = []
        self._redo: list[list[dict[str, Any]]] = []
        self._max = max_depth

    def push(self, polygons: list[dict[str, Any]]) -> None:
        self._undo.append(copy.deepcopy(polygons))
        if len(self._undo) > self._max:
            self._undo.pop(0)
        self._redo.clear()

    def can_undo(self) -> bool:
        return len(self._undo) > 1

    def can_redo(self) -> bool:
        return len(self._redo) > 0

    def undo(self, current: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        if not self.can_undo():
            return None
        self._redo.append(copy.deepcopy(current))
        self._undo.pop()
        return copy.deepcopy(self._undo[-1])

    def redo(self, current: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        if not self._redo:
            return None
        self._undo.append(copy.deepcopy(current))
        return copy.deepcopy(self._redo.pop())

    def seed(self, polygons: list[dict[str, Any]]) -> None:
        self._undo = [copy.deepcopy(polygons)]
        self._redo.clear()
