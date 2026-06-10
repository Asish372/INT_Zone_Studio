#!/usr/bin/env python3
"""P1/P2 — Grid frame, slab clipping, validation, preview, and report."""

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
from src.zone_engine import (
    build_grid_frame_geometry,
    render_grid_frame_preview,
    write_grid_frame_report,
)

DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"
DEFAULT_MANIFEST = PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml"
DEFAULT_DWG = PROJECT_ROOT / "input" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg"
DEFAULT_REPORT = PROJECT_ROOT / "grid_frame_report.md"
DEFAULT_PREVIEW = PROJECT_ROOT / "output" / "grid_frame_preview"


def load_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_manifest(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Grid frame builder (P1 + P2 geometry)")
    parser.add_argument("--dwg", type=Path, default=DEFAULT_DWG, help="Warehouse DWG/DXF path")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Manifest YAML for expected INT count",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Project config.yaml")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Markdown report path")
    parser.add_argument(
        "--preview",
        type=Path,
        default=DEFAULT_PREVIEW,
        help="Preview output path (stem; writes .svg and .png)",
    )
    parser.add_argument(
        "--p1-only",
        action="store_true",
        help="Skip P2 slab clip / validation / preview",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = load_config(args.config)
    manifest = load_manifest(args.manifest)
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

    if args.p1_only:
        from src.zone_engine import build_grid_frame

        result = build_grid_frame(
            msp,
            source_file=str(dwg_path.name),
            grid_layers=zone_cfg.get("grid_layers", ["S-GRID-1", "S-GRID-IDEN"]),
            expected_int_count=int(expected) if expected is not None else None,
            unit_scale_m=unit_scale,
        )
        write_grid_frame_report(result, args.report)
        print(f"Grid frame: {result.bay_count} bays (raw {result.raw_bay_count})")
        return 0 if result.bay_count > 0 else 1

    geometry = build_grid_frame_geometry(
        msp,
        config,
        source_file=str(dwg_path.name),
        unit_scale_m=unit_scale,
        expected_int_count=int(expected) if expected is not None else None,
        zone_cfg=zone_cfg,
    )

    write_grid_frame_report(geometry, args.report)
    preview_paths = render_grid_frame_preview(geometry, args.preview)

    frame = geometry.frame
    val = geometry.validation
    print("=== Grid frame geometry (P2) ===")
    print(f"Bays (frame): {frame.bay_count} (raw grid cells: {frame.raw_bay_count})")
    print(f"Bays before clip: {geometry.bay_count_before_clip}")
    print(f"Bays non-empty after clip: {geometry.bay_count_after_clip}")
    print(f"Slab outline: {geometry.slab.method} ({geometry.slab.area_m2:,.1f} m²)")
    print(f"Total raw area: {val.total_raw_area_m2:,.2f} m²")
    print(f"Total clipped area: {val.total_clipped_area_m2:,.2f} m²")
    print(f"Mean coverage: {val.mean_coverage_pct:.1f}%")
    print(f"Low coverage: {val.low_coverage_count} | Empty: {val.empty_clip_count} | Overlaps: {val.overlap_pair_count}")
    print(f"Report: {args.report}")
    for path in preview_paths:
        print(f"Preview: {path}")

    if geometry.warnings:
        for warning in geometry.warnings:
            print(f"  WARN: {warning}")

    return 0 if geometry.bay_count_after_clip > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
