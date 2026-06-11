"""Build JSON scene payloads for the polygon workspace canvas."""

from __future__ import annotations

from typing import Any

from shapely.geometry import LineString

from desktop.engine_sidecar.workspace_save import is_partition_polygon


def build_scene(
    *,
    source_file: str,
    cad_segments: list[LineString],
    polygons: list[dict[str, Any]],
    unit_label: str = "mm",
    scope_boundary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return scene JSON for the canvas viewer."""
    cad_lines: list[list[float]] = []
    for seg in cad_segments:
        coords = list(seg.coords)
        if len(coords) < 2:
            continue
        x1, y1 = coords[0]
        x2, y2 = coords[-1]
        cad_lines.append([float(x1), float(y1), float(x2), float(y2)])

    return {
        "source_file": source_file,
        "unit_label": unit_label,
        "polygon_count": len([p for p in polygons if is_partition_polygon(p)]),
        "cad_lines": cad_lines,
        "polygons": polygons,
        "scope_boundary": scope_boundary,
    }
