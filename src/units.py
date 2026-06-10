"""Drawing unit conversion helpers."""

from __future__ import annotations

UNIT_SCALE = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
}


def scale_factor(unit: str) -> float:
    """Convert drawing units to metres."""
    key = unit.lower().strip()
    if key not in UNIT_SCALE:
        raise ValueError(
            f"Invalid drawing_unit '{unit}'. Use one of: {', '.join(UNIT_SCALE)}"
        )
    return UNIT_SCALE[key]
