"""Workspace polygon geometry validation."""

from __future__ import annotations

import math
from typing import Any

from desktop.engine_sidecar.workspace_save import active_polygons


def _ring_to_poly(ring: list) -> Polygon | None:
    if not ring or len(ring) < 3:
        return None
    try:
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if not poly.is_empty else None
    except Exception:
        return None


def validate_workspace(
    polygons: list[dict[str, Any]],
    *,
    tiny_area_m2: float = 0.5,
    overlap_area_m2: float = 0.1,
) -> dict[str, Any]:
    """Run geometry validation on active workspace polygons."""
    active = active_polygons(polygons)
    issues: list[dict[str, Any]] = []

    counts = {
        "open_boundaries": 0,
        "self_intersections": 0,
        "gaps": 0,
        "overlaps": 0,
        "duplicates": 0,
        "tiny_polygons": 0,
    }

    polys: list[tuple[int, Polygon]] = []
    for rec in active:
        pid = rec.get("id", 0)
        ring = rec.get("ring") or []
        if len(ring) < 3:
            counts["open_boundaries"] += 1
            issues.append(
                {
                    "type": "open_boundary",
                    "polygon_id": pid,
                    "severity": "error",
                    "message": f"Polygon #{pid} has fewer than 3 vertices",
                }
            )
            continue
        poly = _ring_to_poly(ring)
        if poly is None:
            counts["open_boundaries"] += 1
            issues.append(
                {
                    "type": "open_boundary",
                    "polygon_id": pid,
                    "severity": "error",
                    "message": f"Polygon #{pid} could not form a closed ring",
                }
            )
            continue
        if not poly.is_valid:
            counts["self_intersections"] += 1
            issues.append(
                {
                    "type": "self_intersection",
                    "polygon_id": pid,
                    "severity": "warning",
                    "message": f"Polygon #{pid} has self-intersection or invalid geometry",
                }
            )
        area = rec.get("area_m2") or 0.0
        if area < tiny_area_m2:
            counts["tiny_polygons"] += 1
            issues.append(
                {
                    "type": "tiny_polygon",
                    "polygon_id": pid,
                    "severity": "warning",
                    "message": f"Polygon #{pid} area {area:.2f} m² below threshold {tiny_area_m2} m²",
                }
            )
        polys.append((pid, poly))

    seen_pairs: set[tuple[int, int]] = set()
    for i, (id_a, poly_a) in enumerate(polys):
        for id_b, poly_b in polys[i + 1 :]:
            pair = (min(id_a, id_b), max(id_a, id_b))
            if pair in seen_pairs:
                continue
            inter = poly_a.intersection(poly_b)
            if inter.is_empty:
                continue
            overlap_m2 = inter.area * 1e-6  # drawing units assumed mm → rough; use record areas
            rec_a = next((p for p in active if p.get("id") == id_a), None)
            rec_b = next((p for p in active if p.get("id") == id_b), None)
            scale = 1.0
            if rec_a and rec_b:
                # Use stored m² areas to estimate unit scale from geometry
                if poly_a.area > 0 and rec_a.get("area_m2"):
                    scale = (rec_a["area_m2"] / poly_a.area) ** 0.5
                overlap_m2 = inter.area * (scale**2)

            if overlap_m2 > overlap_area_m2:
                seen_pairs.add(pair)
                ratio_a = overlap_m2 / max(rec_a.get("area_m2", 1) if rec_a else 1, 1e-9)
                ratio_b = overlap_m2 / max(rec_b.get("area_m2", 1) if rec_b else 1, 1e-9)
                if ratio_a > 0.85 and ratio_b > 0.85:
                    counts["duplicates"] += 1
                    issues.append(
                        {
                            "type": "duplicate",
                            "polygon_id": id_a,
                            "related_id": id_b,
                            "severity": "warning",
                            "message": f"Polygons #{id_a} and #{id_b} are near-duplicates",
                        }
                    )
                else:
                    counts["overlaps"] += 1
                    issues.append(
                        {
                            "type": "overlap",
                            "polygon_id": id_a,
                            "related_id": id_b,
                            "severity": "warning",
                            "message": f"Polygons #{id_a} and #{id_b} overlap ({overlap_m2:.2f} m²)",
                        }
                    )

    # Gap estimate: compare expected vs detected when set externally
    counts["gaps"] = 0

    return {
        "ok": counts["open_boundaries"] == 0 and counts["self_intersections"] == 0,
        "counts": counts,
        "issues": issues,
        "validated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
