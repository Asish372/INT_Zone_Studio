"""Bridge workspace polygons to authoritative build_int_zone_pipeline."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from shapely.geometry import Polygon

from desktop.engine_sidecar.session_store import WorkspaceSession
from desktop.engine_sidecar.workspace_save import is_partition_polygon
from src.geometry_precision import normalize_polygon
from src.parser import get_modelspace, load_dxf
from src.zone_engine.int_zone_pipeline import build_int_zone_pipeline
from src.zone_engine.models import (
    FaceAssignmentSummary,
    FaceData,
    IntZoneData,
    IntZonePipelineResult,
    ProductionReadinessGate,
)
from src.zone_engine.profile_classifier import resolve_zone_profile

logger = logging.getLogger(__name__)

ZONE_PIPELINE_VERSION = 1


def _polygon_ring(poly: Polygon) -> list[list[float]]:
    return [[float(x), float(y)] for x, y in poly.exterior.coords]


def _normalize_source_name(name: str) -> str:
    return Path(name).name.lower()


def resolve_manifest_path(
    project_root: Path,
    source_file: str,
    config: dict[str, Any],
) -> Path | None:
    """Resolve manifest YAML from config, dwg_counterpart match, or reference defaults."""
    zone_cfg = config.get("zone_engine", {})
    configured = zone_cfg.get("manifest_path")
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = project_root / path
        if path.is_file():
            return path

    ref_dir = project_root / "reference"
    if not ref_dir.is_dir():
        return None

    source_key = _normalize_source_name(source_file)
    for manifest_file in sorted(ref_dir.glob("*_zones_manifest.yaml")):
        try:
            with manifest_file.open(encoding="utf-8") as fh:
                doc = yaml.safe_load(fh) or {}
        except OSError:
            continue
        counterpart = doc.get("dwg_counterpart")
        if counterpart and _normalize_source_name(str(counterpart)) == source_key:
            return manifest_file

    default = ref_dir / "j33a_zones_manifest.yaml"
    if default.is_file() and ("warehouse" in source_key or "s111" in source_key):
        return default
    return None


def polygon_records_to_faces(
    polygons: list[dict[str, Any]],
    *,
    unit_scale_m: float = 0.001,
) -> list[FaceData]:
    """Rebuild FaceData from active partition polygon records."""
    faces: list[FaceData] = []
    for rec in polygons:
        if not is_partition_polygon(rec):
            continue
        if rec.get("status") == "deleted":
            continue
        ring = rec.get("ring") or []
        if len(ring) < 3:
            continue
        try:
            poly = normalize_polygon(Polygon(ring))
        except Exception:
            continue
        if poly is None or poly.is_empty:
            continue
        face_id = int(rec["id"])
        area_m2 = float(rec.get("area_m2", poly.area * (unit_scale_m**2)))
        faces.append(FaceData(face_id=face_id, polygon=poly, area_m2=area_m2))
    return faces


def apply_face_assignments_to_polygons(
    polygons: list[dict[str, Any]],
    assignment: FaceAssignmentSummary,
) -> None:
    """Write authoritative INT labels onto polygon records."""
    label_by_face = {item.face_id: item.int_label for item in assignment.assignments}
    for rec in polygons:
        if not is_partition_polygon(rec):
            continue
        if rec.get("status") == "deleted":
            continue
        face_id = rec.get("id")
        if face_id in label_by_face:
            rec["int_zone"] = label_by_face[face_id]
        else:
            rec.pop("int_zone", None)


def _manifest_comparison_for_label(
    result: IntZonePipelineResult,
    label: str,
) -> dict[str, Any] | None:
    manifest = result.manifest
    if manifest is None:
        return None
    for row in manifest.comparisons:
        if row.label == label:
            status = "PASS" if row.within_tolerance else "REVIEW"
            if row.manifest_area_sqm is None:
                status = "SKIP"
            return {
                "manifest_area_sqm": row.manifest_area_sqm,
                "manifest_delta_pct": row.delta_pct,
                "manifest_status": status,
            }
    return None


def int_zone_data_to_record(
    zone: IntZoneData,
    *,
    manifest_overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ring = None if zone.polygon.is_empty else _polygon_ring(zone.polygon)
    record: dict[str, Any] = {
        "label": zone.label,
        "zone_id": zone.zone_id,
        "area_m2": round(zone.area_m2, 4),
        "volume_m3": round(zone.volume_m3, 4),
        "face_count": zone.face_count,
        "polygon_ids": list(zone.face_ids),
        "face_sum_area_m2": round(zone.face_sum_area_m2, 4),
        "clipped_bay_area_m2": round(zone.clipped_bay_area_m2, 4),
        "bay_coverage_pct": round(zone.bay_coverage_pct, 1),
        "empty": zone.face_count == 0 or (ring is None),
        "ring": ring,
        "profile": zone.profile,
        "detection_tier": zone.detection_tier,
        "grid_ref": zone.grid_ref,
    }
    if manifest_overlay:
        record.update(manifest_overlay)
    return record


def int_zones_to_api_records(result: IntZonePipelineResult) -> list[dict[str, Any]]:
    """Map pipeline zones to JSON-safe session/API records."""
    records: list[dict[str, Any]] = []
    for zone in sorted(result.zones, key=lambda z: z.zone_id):
        overlay = _manifest_comparison_for_label(result, zone.label)
        records.append(int_zone_data_to_record(zone, manifest_overlay=overlay))
    return records


def serialize_readiness(gates: list[ProductionReadinessGate]) -> list[dict[str, str]]:
    return [{"name": gate.name, "status": gate.status, "detail": gate.detail} for gate in gates]


def zone_records_to_int_zone_data(
    zones: list[dict[str, Any]],
    *,
    source_file: str = "",
) -> list[IntZoneData]:
    """Reconstruct IntZoneData for CLI-compatible schedule export."""
    rebuilt: list[IntZoneData] = []
    for rec in zones:
        ring = rec.get("ring")
        polygon = Polygon()
        if ring and len(ring) >= 3:
            normalized = normalize_polygon(Polygon(ring))
            if normalized is not None and not normalized.is_empty:
                polygon = normalized
        rebuilt.append(
            IntZoneData(
                zone_id=int(rec.get("zone_id", 0)),
                label=str(rec["label"]),
                polygon=polygon,
                area_m2=float(rec.get("area_m2", 0)),
                volume_m3=float(rec.get("volume_m3", 0)),
                face_ids=[int(pid) for pid in rec.get("polygon_ids", [])],
                face_count=int(rec.get("face_count", 0)),
                face_sum_area_m2=float(rec.get("face_sum_area_m2", 0)),
                clipped_bay_area_m2=float(rec.get("clipped_bay_area_m2", 0)),
                bay_coverage_pct=float(rec.get("bay_coverage_pct", 0)),
                profile=str(rec.get("profile", "GRID_WAREHOUSE")),
                detection_tier=str(rec.get("detection_tier", "T3")),
                grid_ref=rec.get("grid_ref"),
                source_file=source_file,
            )
        )
    return rebuilt


def mark_zones_stale(session: WorkspaceSession) -> None:
    session.zones_stale = True


def run_zone_pipeline_for_session(
    session: WorkspaceSession,
    config: dict[str, Any],
    *,
    project_root: Path,
) -> IntZonePipelineResult:
    """
    Run authoritative INT zone pipeline using reviewed workspace polygons.

    Requires CAD modelspace for grid/slab geometry; faces come from session.polygons.
    """
    if not session.polygons:
        raise ValueError("No polygons loaded")
    if not session.cad_available or not session.dxf_path:
        raise ValueError(
            "CAD source required for INT zone pipeline. Import the original drawing first."
        )

    manifest_path = resolve_manifest_path(project_root, session.source_file, config)
    profile, manifest = resolve_zone_profile(
        config,
        manifest_path=manifest_path,
        cli_profile=None,
    )
    zone_cfg = dict(config.get("zone_engine", {}))
    zone_cfg["profile"] = profile

    expected = manifest.get("zone_count_expected")
    expected_int = int(expected) if expected is not None else None

    doc = load_dxf(session.dxf_path)
    msp = get_modelspace(doc)
    faces = polygon_records_to_faces(session.polygons, unit_scale_m=session.unit_scale_m)
    if not faces:
        raise ValueError("No active partition polygons available for zone assignment")

    result = build_int_zone_pipeline(
        msp,
        config,
        source_file=session.source_file,
        unit_scale_m=session.unit_scale_m,
        expected_int_count=expected_int,
        manifest_path=manifest_path,
        faces=faces,
        zone_cfg=zone_cfg,
        auto_detect_faces=False,
    )

    session.zones = int_zones_to_api_records(result)
    apply_face_assignments_to_polygons(session.polygons, result.assignment)
    session.zone_pipeline_version = ZONE_PIPELINE_VERSION
    session.zone_profile = profile
    session.manifest_path = str(manifest_path) if manifest_path else None
    session.readiness = serialize_readiness(result.readiness)
    session.zones_stale = False

    orphan_limit = int(zone_cfg.get("max_orphan_faces", 0))
    if result.assignment.orphan_count > orphan_limit:
        logger.warning(
            "Zone pipeline orphans (%s) exceed limit (%s)",
            result.assignment.orphan_count,
            orphan_limit,
        )

    return result


def ensure_zones_for_session(
    session: WorkspaceSession,
    config: dict[str, Any],
    *,
    project_root: Path,
) -> list[dict[str, Any]]:
    """Return pipeline-backed zones, rebuilding when missing or stale."""
    if session.zones and not session.zones_stale:
        return session.zones
    run_zone_pipeline_for_session(session, config, project_root=project_root)
    return session.zones
