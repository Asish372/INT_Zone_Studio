"""Tests for polygon workspace MVP."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from desktop.engine_sidecar.detect_pipeline import detect_from_cad_path, detect_from_dxf_path
from desktop.engine_sidecar.polygon_records import faces_to_polygon_records, polygon_to_record
from desktop.engine_sidecar.scene_builder import build_scene
from desktop.engine_sidecar.session_store import create_session
from desktop.engine_sidecar.workspace_save import (
    save_polygons_csv,
    save_polygons_dxf,
    save_polygons_json,
)
from src.converter import ensure_dxf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"


def test_warehouse_detects_618_polygons():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert WAREHOUSE_DXF.is_file()
    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    assert len(result.polygons) == 618
    assert len(result.faces) == 618


def test_detect_from_cad_path_accepts_dxf():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert WAREHOUSE_DXF.is_file()
    result = detect_from_cad_path(WAREHOUSE_DXF, config, source_file="warehouse.dxf")
    assert result.source_file == "warehouse.dxf"
    assert len(result.polygons) == 618


def test_ensure_dxf_passthrough_for_dxf(tmp_path: Path):
    assert WAREHOUSE_DXF.is_file()
    assert ensure_dxf(WAREHOUSE_DXF, tmp_path) == WAREHOUSE_DXF


def test_scene_builder_and_save_warehouse(tmp_path: Path):
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert WAREHOUSE_DXF.is_file()

    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    records = faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)
    scene = build_scene(
        source_file=result.source_file,
        cad_segments=result.cad_segments,
        polygons=records,
    )
    assert scene["polygon_count"] == 618
    assert len(scene["cad_lines"]) > 0
    assert len(scene["polygons"]) == 618

    json_path = tmp_path / "corrected_polygons.json"
    dxf_path = tmp_path / "corrected_polygons.dxf"
    csv_path = tmp_path / "corrected_polygons.csv"
    save_polygons_json(records, json_path)
    save_polygons_dxf(records, dxf_path)
    save_polygons_csv(records, csv_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["polygon_count"] == 618
    assert dxf_path.stat().st_size > 0
    assert csv_path.stat().st_size > 0


def test_session_counts():
    session = create_session()
    session.polygons = [
        {"id": 1, "source": "auto", "status": "active"},
        {"id": 2, "source": "seed", "status": "active"},
        {"id": 3, "source": "auto", "status": "deleted"},
        {"id": 4, "source": "auto", "status": "active", "scope_excluded": True},
    ]
    counts = session.counts()
    assert counts == {
        "detected": 1,
        "seed_added": 1,
        "manual_added": 0,
        "deleted": 1,
        "scope_excluded": 1,
        "obstacles": 0,
        "total": 2,
    }


def test_polygon_record_metrics():
    config = yaml.safe_load((PROJECT_ROOT / "config.yaml").read_text(encoding="utf-8"))
    result = detect_from_dxf_path(WAREHOUSE_DXF, config)
    rec = faces_to_polygon_records(result.faces[:1], unit_scale_m=result.unit_scale_m)[0]
    assert rec["area_m2"] > 0
    assert rec["perimeter_m"] > 0
    assert len(rec["centroid"]) == 2

    seed_rec = polygon_to_record(
        result.polygons[0],
        polygon_id=9999,
        unit_scale_m=result.unit_scale_m,
    )
    assert seed_rec["source"] == "seed"
