"""Deterministic INT-n labelling for grid bay cells."""

from __future__ import annotations

from src.zone_engine.grid_frame import BayCell


def assign_int_labels(bays: list[BayCell]) -> list[BayCell]:
    """
    Assign INT-1 … INT-N in stable row-major order (row asc, then col asc).

    Same grid geometry always yields identical labels across runs.
    """
    ordered = sorted(bays, key=lambda bay: (bay.row, bay.col, bay.bay_id))
    for index, bay in enumerate(ordered, start=1):
        bay.int_label = f"INT-{index}"
    return ordered


def sort_bays_for_display(bays: list[BayCell]) -> list[BayCell]:
    """Sort bays by INT label number for reports and tables."""
    return sorted(bays, key=lambda bay: int(bay.int_label.split("-")[1]))
