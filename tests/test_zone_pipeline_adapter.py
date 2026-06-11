"""Authoritative INT zone pipeline integration for Studio sidecar."""

from __future__ import annotations

from pathlib import Path

import yaml

from desktop.engine_sidecar.detect_pipeline import detect_from_dxf_path
from desktop.engine_sidecar.polygon_records import faces_to_polygon_records
from desktop.engine_sidecar.session_store import create_session
from desktop.engine_sidecar.zone_pipeline_adapter import (
    resolve_manifest_path,
    run_zone_pipeline_for_session,
)
from src.zone_engine.int_zone_pipeline import build_int_zone_pipeline
from src.zone_engine.profile_classifier import resolve_zone_profile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
WAREHOUSE_SOURCE = "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"


def _warehouse_session():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert WAREHOUSE_DXF.is_file(), f"Missing fixture: {WAREHOUSE_DXF}"
    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    session = create_session()
    session.source_file = WAREHOUSE_SOURCE
    session.dxf_path = WAREHOUSE_DXF
    session.cad_available = True
    session.unit_scale_m = result.unit_scale_m
    session.polygons = faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)
    return session, config


def test_resolve_manifest_path_warehouse():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    manifest = resolve_manifest_path(PROJECT_ROOT, WAREHOUSE_SOURCE, config)
    assert manifest is not None
    assert manifest.name == "j33a_zones_manifest.yaml"


def test_studio_pipeline_matches_cli_warehouse_baseline():
    session, config = _warehouse_session()
    manifest_path = resolve_manifest_path(PROJECT_ROOT, session.source_file, config)
    profile, manifest = resolve_zone_profile(config, manifest_path=manifest_path)
    zone_cfg = dict(config.get("zone_engine", {}))
    zone_cfg["profile"] = profile
    expected = int(manifest["zone_count_expected"])

    from src.parser import get_modelspace, load_dxf

    from desktop.engine_sidecar.zone_pipeline_adapter import polygon_records_to_faces

    doc = load_dxf(session.dxf_path)
    msp = get_modelspace(doc)
    faces = polygon_records_to_faces(session.polygons, unit_scale_m=session.unit_scale_m)

    cli_result = build_int_zone_pipeline(
        msp,
        config,
        source_file=session.source_file,
        unit_scale_m=session.unit_scale_m,
        expected_int_count=expected,
        manifest_path=manifest_path,
        faces=faces,
        zone_cfg=zone_cfg,
        auto_detect_faces=False,
    )

    studio_result = run_zone_pipeline_for_session(session, config, project_root=PROJECT_ROOT)

    assert len(session.zones) == expected == 24
    assert len(studio_result.zones) == len(cli_result.zones) == 24

    cli_labels = [zone.label for zone in cli_result.zones]
    studio_labels = [zone["label"] for zone in session.zones]
    assert cli_labels == studio_labels
    assert cli_labels[0] == "INT-1"
    assert cli_labels[-1] == "INT-24"

    cli_assignments = {
        item.face_id: item.int_label for item in cli_result.assignment.assignments
    }
    for rec in session.polygons:
        if rec.get("status") == "deleted":
            continue
        face_id = rec["id"]
        if face_id in cli_assignments:
            assert rec.get("int_zone") == cli_assignments[face_id]

    assert session.zone_pipeline_version == 1
    assert session.zones_stale is False
    assert session.zone_profile == "GRID_WAREHOUSE"
