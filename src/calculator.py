"""Module 6: Area, perimeter, volume, and label assignment."""

from __future__ import annotations

import logging
from typing import Any

from shapely.geometry import Point, Polygon

from src.geometry_precision import normalize_polygon
from src.models import RegionData
from src.units import scale_factor

# Target alignment with AutoCAD AREA (see PRD NFR-02 / success metrics).
AREA_TOLERANCE_FRACTION = 0.0005  # 0.05%

logger = logging.getLogger(__name__)

__all__ = ["scale_factor", "compute_all"]


def compute_area(polygon: Polygon, scale: float) -> float:
    """Return area in square metres using a validated polygon."""
    normalized = normalize_polygon(polygon)
    if normalized is None:
        return 0.0
    return normalized.area * (scale**2)


def compute_perimeter(polygon: Polygon, scale: float) -> float:
    """Return perimeter in metres."""
    normalized = normalize_polygon(polygon)
    if normalized is None:
        return 0.0
    return normalized.length * scale


def compute_centroid(polygon: Polygon) -> Point:
    """Return polygon centroid as a Shapely Point."""
    normalized = normalize_polygon(polygon)
    if normalized is None:
        return polygon.centroid
    return normalized.centroid


def compute_volume(area_m2: float, thickness: float) -> float:
    """Return volume in cubic metres."""
    return area_m2 * thickness


def format_label_text(region_id: int, label: str, area_m2: float, volume_m3: float) -> str:
    """Format multi-line label for DXF TEXT entities."""
    return f"{label}\nArea: {area_m2:.2f} m2\nVol: {volume_m3:.2f} m3"


def compute_all(
    polygons: list[Polygon],
    config: dict[str, Any],
    source_file: str,
    *,
    region_meta: list[dict[str, Any]] | None = None,
) -> list[RegionData]:
    """Compute metrics and assign labels for all polygons."""
    geometry_cfg = config.get("geometry", {})
    output_cfg = config.get("output", {})
    accuracy_cfg = config.get("accuracy", {})

    unit = geometry_cfg.get("drawing_unit", "mm")
    thickness = float(geometry_cfg.get("slab_thickness", 0.15))
    prefix = output_cfg.get("label_prefix", "Room")
    scale = scale_factor(unit)
    area_decimals = int(accuracy_cfg.get("area_decimals", 4))
    vol_decimals = int(accuracy_cfg.get("volume_decimals", 4))

    regions: list[RegionData] = []
    for idx, polygon in enumerate(polygons, start=1):
        normalized = normalize_polygon(polygon)
        if normalized is None:
            continue

        meta = region_meta[idx - 1] if region_meta and idx - 1 < len(region_meta) else {}
        area_m2 = compute_area(normalized, scale)
        perimeter_m = compute_perimeter(normalized, scale)
        volume_m3 = compute_volume(area_m2, thickness)
        centroid = compute_centroid(normalized)
        label = f"{prefix} {idx}"

        regions.append(
            RegionData(
                region_id=idx,
                label=label,
                polygon=normalized,
                area_m2=round(area_m2, area_decimals),
                perimeter_m=round(perimeter_m, area_decimals),
                volume_m3=round(volume_m3, vol_decimals),
                centroid=centroid,
                label_text=format_label_text(idx, label, area_m2, volume_m3),
                source_file=source_file,
                detection_method=str(meta.get("detection_method", "auto")),
                seed_x=meta.get("seed_x"),
                seed_y=meta.get("seed_y"),
                seed_id=meta.get("seed_id"),
            )
        )

    total_area = sum(r.area_m2 for r in regions)
    total_volume = sum(r.volume_m3 for r in regions)
    logger.info(
        "Computed %d regions - total area %.2f m2, total volume %.2f m3",
        len(regions),
        total_area,
        total_volume,
    )
    return regions
