"""Tests for P3 face assignment and zone aggregation."""

from __future__ import annotations

import ezdxf
from shapely.geometry import box

from src.zone_engine.bay_geometry import build_grid_frame_geometry
from src.zone_engine.face_assigner import assign_faces_to_bays, filter_sliver_faces, polygons_to_faces
from src.zone_engine.int_zone_pipeline import build_int_zone_pipeline
from src.zone_engine.manifest_reconciliation import load_manifest, reconcile_zones_to_manifest
from src.zone_engine.models import FaceData
from src.zone_engine.production_readiness import assess_production_readiness
from src.zone_engine.zone_aggregator import aggregate_int_zones


def _add_line(msp, layer: str, x0: float, y0: float, x1: float, y1: float) -> None:
    msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": layer})


def test_filter_sliver_faces():
    faces = [
        FaceData(1, box(0, 0, 100, 100), 0.5),
        FaceData(2, box(0, 0, 200, 200), 10.0),
    ]
    kept, sliver_count = filter_sliver_faces(faces, sliver_max_m2=1.0)
    assert sliver_count == 1
    assert len(kept) == 1
    assert kept[0].face_id == 2


def test_assign_faces_to_bays_max_intersection():
    doc = ezdxf.new()
    msp = doc.modelspace()
    xs = [0, 10000, 20000, 30000, 40000, 50000, 60000]
    ys = [0, 20000, 40000, 60000, 80000]
    for x in xs:
        _add_line(msp, "S-GRID-1", x, -1000, x, 90000)
    for y in ys:
        _add_line(msp, "S-GRID-1", -1000, y, 70000, y)
    for x in range(0, 70000, 5000):
        _add_line(msp, "S-FNDN-1", x, 0, x + 2000, 0)
    _add_line(msp, "S-FNDN-1", 0, 0, 70000, 0)
    _add_line(msp, "S-FNDN-1", 0, 80000, 70000, 80000)
    _add_line(msp, "S-FNDN-1", 0, 0, 0, 80000)
    _add_line(msp, "S-FNDN-1", 70000, 0, 70000, 80000)

    config = {
        "geometry": {"gap_threshold": 500, "snap_tolerance": 1, "max_gap_angle": 30},
        "zone_engine": {"grid_layers": ["S-GRID-1"]},
    }
    geometry = build_grid_frame_geometry(
        msp,
        config,
        expected_int_count=24,
        unit_scale_m=0.001,
    )

    # Two micro-faces in first bay cell (0,0), one in second (0,1)
    faces = [
        FaceData(1, box(500, 500, 4000, 4000), 12.0),
        FaceData(2, box(4500, 4500, 9000, 9000), 20.0),
        FaceData(3, box(10500, 500, 14000, 4000), 10.0),
    ]
    assignment = assign_faces_to_bays(
        faces,
        geometry.bays,
        method="max_intersection_area",
        unit_scale_m=0.001,
        sliver_max_m2=1.0,
    )
    assert assignment.assigned_count == 3
    assert assignment.orphan_count == 0

    by_label: dict[str, list[int]] = {}
    for item in assignment.assignments:
        by_label.setdefault(item.int_label, []).append(item.face_id)
    assert sorted(by_label.get("INT-1", [])) == [1, 2]
    assert by_label.get("INT-2", []) == [3]

    zones, warnings = aggregate_int_zones(
        geometry.bays,
        assignment,
        faces,
        unit_scale_m=0.001,
        slab_thickness_m=0.15,
    )
    assert len(zones) == 24
    int1 = next(z for z in zones if z.label == "INT-1")
    assert int1.face_count == 2
    assert int1.face_sum_area_m2 == 32.0
    assert int1.area_m2 > 0.0
    assert not any("overlap" in w.lower() for w in warnings)


def test_manifest_reconciliation_template_skip():
    manifest = load_manifest("reference/j33a_zones_manifest.yaml")
    from src.zone_engine.models import IntZoneData
    from shapely.geometry import Polygon

    real_zones = [
        IntZoneData(
            zone_id=i,
            label=f"INT-{i}",
            polygon=Polygon(),
            area_m2=800.0,
            volume_m3=120.0,
            face_ids=[1],
            face_count=5,
            face_sum_area_m2=800.0,
            clipped_bay_area_m2=850.0,
            bay_coverage_pct=94.0,
            profile="GRID_WAREHOUSE",
            detection_tier="T3",
            grid_ref=None,
            source_file="test",
        )
        for i in range(1, 25)
    ]
    recon = reconcile_zones_to_manifest(real_zones, manifest)
    assert recon.computed_zone_count == 24
    assert recon.zone_count_match
    assert recon.transcription_status == "template"
    assert recon.zones_with_manifest_area == 0

    gates = assess_production_readiness(
        real_zones,
        type(
            "A",
            (),
            {
                "orphan_count": 0,
                "assigned_count": 100,
                "total_faces": 100,
                "sliver_count": 0,
            },
        )(),
        expected_zone_count=24,
        manifest=recon,
    )
    manifest_gate = next(g for g in gates if g.name == "manifest_area")
    assert manifest_gate.status == "SKIP"


def test_build_int_zone_pipeline_synthetic_no_faces():
    doc = ezdxf.new()
    msp = doc.modelspace()
    xs = [0, 10000, 20000, 30000, 40000, 50000, 60000]
    ys = [0, 20000, 40000, 60000, 80000]
    for x in xs:
        _add_line(msp, "S-GRID-1", x, -1000, x, 90000)
    for y in ys:
        _add_line(msp, "S-GRID-1", -1000, y, 70000, y)
    _add_line(msp, "S-FNDN-1", 0, 0, 70000, 0)
    _add_line(msp, "S-FNDN-1", 0, 80000, 70000, 80000)
    _add_line(msp, "S-FNDN-1", 0, 0, 0, 80000)
    _add_line(msp, "S-FNDN-1", 70000, 0, 70000, 80000)

    config = {
        "geometry": {"gap_threshold": 500, "snap_tolerance": 1, "max_gap_angle": 30},
        "zone_engine": {"grid_layers": ["S-GRID-1"]},
    }
    result = build_int_zone_pipeline(
        msp,
        config,
        expected_int_count=24,
        unit_scale_m=0.001,
        auto_detect_faces=False,
        faces=[],
    )
    assert len(result.zones) == 24
    assert result.assignment.assigned_count == 0
    coverage_gate = next(g for g in result.readiness if g.name == "zone_face_coverage")
    assert coverage_gate.status == "REVIEW"
