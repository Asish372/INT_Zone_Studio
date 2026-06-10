"""Geometry validation for clipped bay polygons."""

from __future__ import annotations

from dataclasses import dataclass, field

from shapely.geometry import Polygon
from shapely.validation import explain_validity

from src.zone_engine.grid_frame import BayCell

DEFAULT_LOW_COVERAGE_PCT = 25.0
DEFAULT_OVERLAP_AREA_M2 = 0.5


@dataclass
class BayValidation:
    """Per-bay geometry checks."""

    bay_id: int
    int_label: str
    raw_area_m2: float
    clipped_area_m2: float
    coverage_pct: float
    is_valid: bool
    validity_reason: str
    low_coverage: bool
    empty_clip: bool
    flags: list[str] = field(default_factory=list)


@dataclass
class OverlapRecord:
    """Pairwise overlap between two clipped bays."""

    int_label_a: str
    int_label_b: str
    overlap_area_m2: float


@dataclass
class GeometryValidationSummary:
    """Aggregate validation for all bays."""

    bay_validations: list[BayValidation]
    overlaps: list[OverlapRecord]
    invalid_bay_count: int
    low_coverage_count: int
    empty_clip_count: int
    overlap_pair_count: int
    total_raw_area_m2: float
    total_clipped_area_m2: float
    mean_coverage_pct: float
    warnings: list[str] = field(default_factory=list)


def _normalize_clipped(polygon: Polygon, buffer_fix: float) -> tuple[Polygon, bool, str]:
    if polygon.is_empty:
        return polygon, True, ""
    if polygon.is_valid:
        return polygon, True, ""
    fixed = polygon.buffer(buffer_fix)
    if fixed.is_empty:
        return polygon, False, explain_validity(polygon)
    if fixed.geom_type == "MultiPolygon":
        fixed = max(fixed.geoms, key=lambda geom: geom.area)
    if fixed.is_valid:
        return fixed, True, explain_validity(polygon)
    return fixed, False, explain_validity(polygon)


def validate_bay_geometries(
    bays: list[BayCell],
    *,
    unit_scale_m: float = 0.001,
    low_coverage_pct: float = DEFAULT_LOW_COVERAGE_PCT,
    overlap_area_m2: float = DEFAULT_OVERLAP_AREA_M2,
) -> GeometryValidationSummary:
    """Validate clipped bays: coverage, validity, overlaps."""
    buffer_fix = -0.001 / unit_scale_m if unit_scale_m > 0 else -1.0
    overlap_native = overlap_area_m2 / (unit_scale_m**2)

    validations: list[BayValidation] = []
    for bay in bays:
        clipped, is_valid, reason = _normalize_clipped(bay.clipped_polygon, buffer_fix)
        bay.clipped_polygon = clipped
        bay.clipped_area_m2 = clipped.area * (unit_scale_m**2)

        raw_area = bay.raw_area_m2
        clipped_area = bay.clipped_area_m2
        coverage = (clipped_area / raw_area * 100.0) if raw_area > 1e-9 else 0.0
        bay.coverage_pct = coverage

        empty_clip = clipped_area < 1e-6
        low_coverage = not empty_clip and coverage < low_coverage_pct
        flags: list[str] = []
        if empty_clip:
            flags.append("empty_clip")
        if low_coverage:
            flags.append("low_coverage")
        if not is_valid:
            flags.append("invalid_geometry")

        validations.append(
            BayValidation(
                bay_id=bay.bay_id,
                int_label=bay.int_label,
                raw_area_m2=raw_area,
                clipped_area_m2=clipped_area,
                coverage_pct=coverage,
                is_valid=is_valid and not empty_clip,
                validity_reason=reason,
                low_coverage=low_coverage,
                empty_clip=empty_clip,
                flags=flags,
            )
        )

    overlaps: list[OverlapRecord] = []
    for i, bay_a in enumerate(bays):
        if bay_a.clipped_polygon.is_empty:
            continue
        for bay_b in bays[i + 1 :]:
            if bay_b.clipped_polygon.is_empty:
                continue
            intersection = bay_a.clipped_polygon.intersection(bay_b.clipped_polygon)
            if intersection.is_empty:
                continue
            overlap_m2 = intersection.area * (unit_scale_m**2)
            if overlap_m2 > overlap_area_m2:
                overlaps.append(
                    OverlapRecord(
                        int_label_a=bay_a.int_label,
                        int_label_b=bay_b.int_label,
                        overlap_area_m2=overlap_m2,
                    )
                )

    total_raw = sum(v.raw_area_m2 for v in validations)
    total_clipped = sum(v.clipped_area_m2 for v in validations)
    coverages = [v.coverage_pct for v in validations if v.raw_area_m2 > 1e-9]
    mean_coverage = sum(coverages) / len(coverages) if coverages else 0.0

    warnings: list[str] = []
    invalid_count = sum(1 for v in validations if not v.is_valid)
    low_count = sum(1 for v in validations if v.low_coverage)
    empty_count = sum(1 for v in validations if v.empty_clip)
    if invalid_count:
        warnings.append(f"{invalid_count} bay(s) have invalid clipped geometry.")
    if empty_count:
        warnings.append(f"{empty_count} bay(s) are empty after slab clipping.")
    if overlaps:
        warnings.append(f"{len(overlaps)} overlapping clipped bay pair(s) detected.")

    return GeometryValidationSummary(
        bay_validations=validations,
        overlaps=overlaps,
        invalid_bay_count=invalid_count,
        low_coverage_count=low_count,
        empty_clip_count=empty_count,
        overlap_pair_count=len(overlaps),
        total_raw_area_m2=total_raw,
        total_clipped_area_m2=total_clipped,
        mean_coverage_pct=mean_coverage,
        warnings=warnings,
    )
