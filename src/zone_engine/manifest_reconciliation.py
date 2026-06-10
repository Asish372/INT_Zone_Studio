"""P3 — Reconcile computed INT zone areas against manifest ground truth."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from src.zone_engine.models import (
    IntZoneData,
    ManifestReconciliation,
    ManifestZoneComparison,
    ManifestZoneRow,
)

logger = logging.getLogger(__name__)


def load_manifest(path: Path | str | None) -> dict[str, Any]:
    """Load manifest YAML; returns empty dict if missing."""
    if path is None:
        return {}
    manifest_path = Path(path)
    if not manifest_path.is_file():
        return {}
    with manifest_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def parse_manifest_zones(manifest: dict[str, Any]) -> list[ManifestZoneRow]:
    """Parse zone rows from manifest document."""
    rows: list[ManifestZoneRow] = []
    for entry in manifest.get("zones", []) or []:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label", "")).strip()
        if not label:
            continue
        rows.append(
            ManifestZoneRow(
                label=label,
                area_sqm=_optional_float(entry.get("area_sqm")),
                volume_cum=_optional_float(entry.get("volume_cum")),
                grid_ref=entry.get("grid_ref"),
                notes=entry.get("notes"),
            )
        )
    return rows


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def reconcile_zones_to_manifest(
    zones: list[IntZoneData],
    manifest: dict[str, Any],
    *,
    area_tolerance_pct: float = 0.05,
) -> ManifestReconciliation:
    """Compare union zone areas to manifest schedule rows."""
    project = str(manifest.get("project", ""))
    profile = str(manifest.get("profile", ""))
    transcription = manifest.get("transcription") or {}
    transcription_status = str(transcription.get("status", "unknown"))
    expected_count = int(manifest.get("zone_count_expected") or len(manifest.get("zones") or []))

    manifest_rows = parse_manifest_zones(manifest)
    manifest_by_label = {row.label: row for row in manifest_rows}
    zone_by_label = {zone.label: zone for zone in zones}

    comparisons: list[ManifestZoneComparison] = []
    zones_with_manifest_area = 0
    zones_within_tolerance = 0
    warnings: list[str] = []

    labels = sorted(
        set(manifest_by_label) | set(zone_by_label),
        key=lambda label: int(label.split("-")[1]) if "-" in label else 0,
    )

    for label in labels:
        zone = zone_by_label.get(label)
        row = manifest_by_label.get(label)
        computed = zone.area_m2 if zone else 0.0
        manifest_area = row.area_sqm if row else None
        face_count = zone.face_count if zone else 0

        delta_sqm: float | None = None
        delta_pct: float | None = None
        within: bool | None = None

        if manifest_area is not None and manifest_area > 0:
            zones_with_manifest_area += 1
            delta_sqm = computed - manifest_area
            delta_pct = abs(delta_sqm) / manifest_area * 100.0
            within = delta_pct <= area_tolerance_pct
            if within:
                zones_within_tolerance += 1
            else:
                warnings.append(
                    f"{label}: area delta {delta_pct:.3f}% "
                    f"(computed {computed:.2f} vs manifest {manifest_area:.2f} m²)"
                )
        elif manifest_area is None and row is not None:
            warnings.append(f"{label}: manifest area not transcribed (P0 pending).")

        comparisons.append(
            ManifestZoneComparison(
                label=label,
                computed_area_sqm=computed,
                manifest_area_sqm=manifest_area,
                delta_sqm=delta_sqm,
                delta_pct=delta_pct,
                within_tolerance=within,
                face_count=face_count,
                has_assigned_faces=face_count > 0,
            )
        )

    total_computed = sum(zone.area_m2 for zone in zones)
    manifest_areas = [row.area_sqm for row in manifest_rows if row.area_sqm is not None]
    total_manifest = sum(manifest_areas) if manifest_areas else None
    total_delta_pct: float | None = None
    if total_manifest is not None and total_manifest > 0:
        total_delta_pct = abs(total_computed - total_manifest) / total_manifest * 100.0

    if transcription_status == "template":
        warnings.append("Manifest transcription status is 'template' — area gates are SKIP until P0 complete.")

    return ManifestReconciliation(
        project=project,
        profile=profile,
        transcription_status=transcription_status,
        expected_zone_count=expected_count,
        computed_zone_count=len(zones),
        zone_count_match=len(zones) == expected_count if expected_count else True,
        area_tolerance_pct=area_tolerance_pct,
        comparisons=comparisons,
        total_computed_sqm=total_computed,
        total_manifest_sqm=total_manifest,
        total_delta_pct=total_delta_pct,
        zones_with_manifest_area=zones_with_manifest_area,
        zones_within_tolerance=zones_within_tolerance,
        warnings=warnings,
    )
