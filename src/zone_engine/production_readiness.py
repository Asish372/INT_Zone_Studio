"""P3 — Production readiness gates for INT zone pipeline."""

from __future__ import annotations

from src.zone_engine.models import (
    FaceAssignmentSummary,
    IntZoneData,
    ManifestReconciliation,
    ProductionReadinessGate,
)


def assess_production_readiness(
    zones: list[IntZoneData],
    assignment: FaceAssignmentSummary,
    *,
    expected_zone_count: int | None,
    manifest: ManifestReconciliation | None = None,
    min_bay_coverage_pct: float = 5.0,
    max_orphan_faces: int = 0,
) -> list[ProductionReadinessGate]:
    """Evaluate P3 gates for warehouse / production sign-off."""
    gates: list[ProductionReadinessGate] = []

    # Zone count
    if expected_zone_count is not None:
        match = len(zones) == expected_zone_count
        gates.append(
            ProductionReadinessGate(
                name="zone_count",
                status="PASS" if match else "REVIEW",
                detail=f"{len(zones)} zones vs expected {expected_zone_count}",
            )
        )
    else:
        gates.append(
            ProductionReadinessGate(
                name="zone_count",
                status="SKIP",
                detail="No expected zone count provided",
            )
        )

    # Orphan faces
    orphan_ok = assignment.orphan_count <= max_orphan_faces
    gates.append(
        ProductionReadinessGate(
            name="orphan_faces",
            status="PASS" if orphan_ok else "FAIL",
            detail=f"{assignment.orphan_count} orphan(s) (max allowed {max_orphan_faces})",
        )
    )

    # Every zone has at least one face
    empty_zones = [z.label for z in zones if z.face_count == 0]
    gates.append(
        ProductionReadinessGate(
            name="zone_face_coverage",
            status="PASS" if not empty_zones else "REVIEW",
            detail="All zones have faces"
            if not empty_zones
            else f"Empty zones: {', '.join(empty_zones[:8])}"
            + (f" (+{len(empty_zones) - 8} more)" if len(empty_zones) > 8 else ""),
        )
    )

    # Union area vs clipped bay (face rollup sanity)
    low_coverage = [
        z.label
        for z in zones
        if z.clipped_bay_area_m2 > 1e-6 and z.bay_coverage_pct < min_bay_coverage_pct
    ]
    gates.append(
        ProductionReadinessGate(
            name="union_vs_clipped_bay",
            status="PASS" if not low_coverage else "REVIEW",
            detail="Union area tracks clipped bays"
            if not low_coverage
            else f"Low union/bay coverage: {', '.join(low_coverage[:6])}",
        )
    )

    # Face sum vs union (disjoint faces should match union area)
    drift_zones = [
        z.label
        for z in zones
        if z.area_m2 > 1e-6
        and abs(z.face_sum_area_m2 - z.area_m2) / z.area_m2 > 0.02
    ]
    gates.append(
        ProductionReadinessGate(
            name="face_sum_vs_union",
            status="PASS" if not drift_zones else "REVIEW",
            detail="Face areas consistent with union"
            if not drift_zones
            else f"Sum != union (>2%): {', '.join(drift_zones[:6])}",
        )
    )

    # Manifest area tolerance
    if manifest is None:
        gates.append(
            ProductionReadinessGate(
                name="manifest_area",
                status="SKIP",
                detail="No manifest reconciliation run",
            )
        )
    elif manifest.transcription_status == "template":
        gates.append(
            ProductionReadinessGate(
                name="manifest_area",
                status="SKIP",
                detail="Manifest not transcribed (P0 template)",
            )
        )
    elif manifest.zones_with_manifest_area == 0:
        gates.append(
            ProductionReadinessGate(
                name="manifest_area",
                status="SKIP",
                detail="No manifest area_sqm values filled",
            )
        )
    else:
        all_ok = manifest.zones_within_tolerance == manifest.zones_with_manifest_area
        gates.append(
            ProductionReadinessGate(
                name="manifest_area",
                status="PASS" if all_ok else "FAIL",
                detail=(
                    f"{manifest.zones_within_tolerance}/{manifest.zones_with_manifest_area} "
                    f"within {manifest.area_tolerance_pct}% tolerance"
                ),
            )
        )

    return gates
