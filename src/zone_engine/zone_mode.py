"""P4 — Run INT zone pipeline from main.py (Stage 1 + Stage 2 + export)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.calculator import compute_all
from src.converter import ensure_dxf
from src.detector import detect_regions
from src.exporter import export_results
from src.extractor import extract_all_segments, extract_entities
from src.gap_handler import close_gaps, snap_endpoints
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.units import scale_factor
from src.zone_engine.face_assigner import polygons_to_faces
from src.zone_engine.int_schedule_export import export_int_pipeline_outputs
from src.zone_engine.int_zone_pipeline import build_int_zone_pipeline
from src.zone_engine.profile_classifier import resolve_zone_profile
from src.zone_engine.zone_coverage_report import write_int_zone_report

logger = logging.getLogger(__name__)


def process_file_zones(
    cad_path: Path,
    config: dict[str, Any],
    project_root: Path,
    *,
    manifest_path: Path | None = None,
    zone_profile: str | None = None,
    cache_dir: Path | None = None,
    auto_fallback: bool = True,
) -> int:
    """Stage 1 micro-faces + Stage 2 INT zones + dual export."""
    if cache_dir is None:
        cache_dir = project_root / "output" / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    original_name = cad_path.name
    dxf_path = (
        ensure_dxf(cad_path, cache_dir)
        if cad_path.suffix.lower() == ".dwg"
        else cad_path
    )

    profile, manifest = resolve_zone_profile(
        config,
        manifest_path=manifest_path,
        cli_profile=zone_profile,
    )
    zone_cfg = dict(config.get("zone_engine", {}))
    zone_cfg["profile"] = profile

    expected = manifest.get("zone_count_expected")
    expected_int = int(expected) if expected is not None else None

    doc = load_dxf(dxf_path)
    msp = get_modelspace(doc)
    unit_scale = scale_factor(config.get("geometry", {}).get("drawing_unit", "mm"))

    # Stage 1 — faces for debug export; pipeline uses same face list
    layers_cfg = config.get("layers", {})
    resolution = resolve_wall_layers(msp, config, auto_fallback=auto_fallback)
    if not resolution.wall_layers:
        logger.error("No wall layers for zone mode on %s", original_name)
        return 1

    entities = extract_entities(
        msp,
        resolution.wall_layers,
        layers_cfg.get("ignore_layers", []),
    )
    accuracy_cfg = config.get("accuracy", {})
    segments = extract_all_segments(
        entities,
        arc_segments=int(accuracy_cfg.get("arc_segments", 64)),
    )
    geometry_cfg = config.get("geometry", {})
    segments = snap_endpoints(segments, float(geometry_cfg.get("snap_tolerance", 1)))
    segments, gaps_closed = close_gaps(
        segments,
        float(geometry_cfg.get("gap_threshold", 500)),
        float(geometry_cfg.get("max_gap_angle", 30)),
    )
    polygons = detect_regions(segments, config)
    faces = polygons_to_faces(polygons, unit_scale_m=unit_scale)

    pipeline = build_int_zone_pipeline(
        msp,
        config,
        source_file=original_name,
        unit_scale_m=unit_scale,
        expected_int_count=expected_int,
        manifest_path=manifest_path,
        faces=faces,
        zone_cfg=zone_cfg,
        auto_detect_faces=False,
    )

    output_dir = Path(config.get("output", {}).get("output_dir", "./output"))
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = cad_path.stem
    paths = {
        "dxf": output_dir / f"{stem}_annotated.dxf",
        "excel": output_dir / f"{stem}_results.xlsx",
        "int_dxf": output_dir / f"{stem}_int_zones.dxf",
        "int_excel": output_dir / f"{stem}_int_schedule.xlsx",
        "int_report": output_dir / f"{stem}_int_zone_report.md",
    }

    regions = compute_all(polygons, config, str(cad_path.resolve()))
    debug_written = export_results(doc, regions, paths, config)
    int_written = export_int_pipeline_outputs(doc, pipeline, paths, config)
    report_path = write_int_zone_report(pipeline, paths["int_report"])

    assignment = pipeline.assignment
    print(f"=== INT Zone Mode: {original_name} (profile={profile}) ===")
    print(f"Stage 1 faces: {assignment.total_faces} (assigned {assignment.assigned_count})")
    print(f"Orphans: {assignment.orphan_count} | Slivers: {assignment.sliver_count}")
    print(f"INT zones: {len(pipeline.zones)} (expected {expected_int or '—'})")
    print(f"Gaps closed: {gaps_closed}")
    for key, path in {**debug_written, **int_written}.items():
        print(f"Exported ({key}): {path}")
    print(f"INT report: {report_path}")

    for gate in pipeline.readiness:
        print(f"  [{gate.status}] {gate.name}: {gate.detail}")

    fail = [g for g in pipeline.readiness if g.status == "FAIL"]
    if assignment.orphan_count > int(zone_cfg.get("max_orphan_faces", 0)):
        return 1
    if fail:
        return 1
    return 0
