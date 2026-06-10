#!/usr/bin/env python3
"""P3 — Face-to-zone assignment, union metrics, manifest reconciliation, readiness gates."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src.converter import ensure_dxf
from src.parser import get_modelspace, load_dxf
from src.units import scale_factor
from src.zone_engine import build_int_zone_pipeline, write_int_zone_report

DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"
DEFAULT_MANIFEST = PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml"
DEFAULT_DWG = PROJECT_ROOT / "input" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg"
DEFAULT_REPORT = PROJECT_ROOT / "int_zone_report.md"


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="INT zone pipeline (P2 + P3)")
    parser.add_argument("--dwg", type=Path, default=DEFAULT_DWG, help="Warehouse DWG/DXF")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--skip-face-detect",
        action="store_true",
        help="Skip Stage 1 polygonize (assignment-only smoke test)",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_yaml(args.config)
    manifest = load_yaml(args.manifest)
    zone_cfg = config.get("zone_engine", {})
    expected = manifest.get("zone_count_expected")

    dwg_path = args.dwg
    if not dwg_path.is_file():
        logging.error("Drawing not found: %s", dwg_path)
        return 1

    dxf_path = ensure_dxf(dwg_path, PROJECT_ROOT / "output" / ".dxf_cache")
    doc = load_dxf(dxf_path)
    msp = get_modelspace(doc)
    unit_scale = scale_factor(config.get("geometry", {}).get("drawing_unit", "mm"))

    result = build_int_zone_pipeline(
        msp,
        config,
        source_file=str(dwg_path.name),
        unit_scale_m=unit_scale,
        expected_int_count=int(expected) if expected is not None else None,
        manifest_path=args.manifest,
        auto_detect_faces=not args.skip_face_detect,
        zone_cfg=zone_cfg,
    )

    write_int_zone_report(result, args.report)

    assignment = result.assignment
    geometry = result.geometry
    print("=== INT Zone Pipeline (P3) ===")
    print(f"Bays: {geometry.bay_count_after_clip} non-empty after clip")
    print(f"Faces: {assignment.total_faces} total, {assignment.assigned_count} assigned")
    print(f"Slivers: {assignment.sliver_count} | Orphans: {assignment.orphan_count}")
    print(f"INT zones: {len(result.zones)}")
    print(f"Union area total: {sum(z.area_m2 for z in result.zones):,.2f} m²")
    print(f"Clipped bay total: {geometry.validation.total_clipped_area_m2:,.2f} m²")
    print(f"Report: {args.report}")
    print("--- Readiness ---")
    for gate in result.readiness:
        print(f"  [{gate.status}] {gate.name}: {gate.detail}")

    fail_gates = [g for g in result.readiness if g.status == "FAIL"]
    return 1 if fail_gates or assignment.orphan_count > int(zone_cfg.get("max_orphan_faces", 0)) else 0


if __name__ == "__main__":
    sys.exit(main())
