"""Validation helpers for column obstacle classification."""

from __future__ import annotations

from typing import Any

from desktop.engine_sidecar.obstacle_classify import point_in_obstacle_footprint
from desktop.engine_sidecar.obstacle_extract import obstacles_enabled
from desktop.engine_sidecar.workspace_save import obstacle_polygons


def validate_obstacle_recovery_point(
    scope: dict[str, Any] | None,
    x: float,
    y: float,
    config: dict[str, Any],
) -> str | None:
    """Return error when recovery targets a column obstacle footprint."""
    if not obstacles_enabled(config):
        return None
    if point_in_obstacle_footprint(x, y, scope):
        return "Recovery point is on a column obstacle footprint."
    return None


def append_obstacle_validation_issues(
    result: dict[str, Any],
    *,
    scope: dict[str, Any] | None,
    polygons: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Add informational obstacle classification counts to validation output."""
    if not obstacles_enabled(config):
        return

    obstacles = obstacle_polygons(polygons)
    scope_obstacles = (scope or {}).get("obstacles") if scope else None
    footprint_count = 0
    classified_count = len(obstacles)
    if isinstance(scope_obstacles, dict):
        footprint_count = int(scope_obstacles.get("footprint_count", 0))
        classified_count = int(scope_obstacles.get("classified_count", classified_count))

    counts = result.setdefault("counts", {})
    issues = result.setdefault("issues", [])
    counts["obstacles_classified"] = classified_count
    counts["obstacle_footprints"] = footprint_count

    if classified_count > 0 or footprint_count > 0:
        issues.append(
            {
                "type": "obstacles_classified",
                "severity": "info",
                "message": (
                    f"{classified_count} column obstacle(s) classified "
                    f"from {footprint_count} footprint(s) — excluded from partition counts"
                ),
            }
        )
