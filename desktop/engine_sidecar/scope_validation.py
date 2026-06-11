"""Informational validation checks for slab scope / scoped detection."""

from __future__ import annotations

from typing import Any

from desktop.engine_sidecar.workspace_save import active_polygons, is_workspace_active
from desktop.engine_sidecar.workspace_scope import boundary_ring, normalize_scope


def append_scope_validation_issues(
    result: dict[str, Any],
    *,
    scope: dict[str, Any] | None,
    polygons: list[dict[str, Any]],
    scope_feature_enabled: bool,
) -> None:
    """Add boundary_not_applied and polygons_outside_boundary info issues."""
    if not scope_feature_enabled:
        return

    normalized = normalize_scope(scope)
    has_boundary = len(boundary_ring(normalized)) >= 3
    detection_scoped = bool(normalized.get("detection_scoped"))
    excluded_count = sum(1 for p in polygons if p.get("scope_excluded"))

    counts = result.setdefault("counts", {})
    issues = result.setdefault("issues", [])

    if has_boundary and not detection_scoped:
        counts["boundary_not_applied"] = 1
        issues.append(
            {
                "type": "boundary_not_applied",
                "severity": "info",
                "message": "Slab boundary is defined but not applied. Use Apply Boundary to rerun detection inside scope.",
            }
        )
    else:
        counts.setdefault("boundary_not_applied", 0)

    if detection_scoped and excluded_count > 0:
        counts["polygons_outside_boundary"] = excluded_count
        active = len(active_polygons(polygons))
        issues.append(
            {
                "type": "polygons_outside_boundary",
                "severity": "info",
                "message": (
                    f"{excluded_count} polygon(s) outside the applied slab boundary "
                    f"({active} active in scope)"
                ),
            }
        )
    else:
        counts.setdefault("polygons_outside_boundary", 0)


def validate_scope_recovery_point(
    scope: dict[str, Any] | None,
    x: float,
    y: float,
    *,
    scope_feature_enabled: bool,
) -> str | None:
    """Return error message when recovery is outside applied boundary, else None."""
    if not scope_feature_enabled:
        return None
    normalized = normalize_scope(scope)
    if not normalized.get("detection_scoped"):
        return None
    if len(boundary_ring(normalized)) < 3:
        return None
    from desktop.engine_sidecar.scope_clip import point_in_boundary

    if point_in_boundary(normalized, x, y):
        return None
    return "Recovery point is outside the applied slab boundary."
