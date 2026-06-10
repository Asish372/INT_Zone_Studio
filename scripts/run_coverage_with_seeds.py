#!/usr/bin/env python3
"""Run detection coverage with optional seed-assisted fallback."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_detection_coverage import collect_cad_files, setup_logging
from src.converter import ensure_dxf, find_oda_converter
from src.detection_coverage import (
    analyze_drawing_coverage,
    render_coverage_report_markdown,
    write_coverage_excel,
    write_coverage_log,
)
from src.detector import detect_regions
from src.endpoint_matching import DEFAULT_TIER2_STRUCTURAL_LAYERS
from src.gap_handler import iterative_close_gaps
from src.layer_resolver import resolve_wall_layers
from src.parser import load_dxf
from src.seed_resolver import filter_seeds_for_drawing, load_seeds, merge_regions, resolve_all_seeds
from src.validation_diagnostics import endpoint_layer_map, extract_tagged_segments, snap_tagged_endpoints


def _prepare_segments(doc, config):
    msp = doc.modelspace()
    layers_cfg = config.get("layers", {})
    accuracy_cfg = config.get("accuracy", {})
    geometry_cfg = config.get("geometry", {})
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    tagged = extract_tagged_segments(
        msp,
        resolution.wall_layers,
        layers_cfg.get("ignore_layers", []),
        int(accuracy_cfg.get("arc_segments", 64)),
    )
    snap_tol = float(geometry_cfg.get("snap_tolerance", 1))
    snapped = snap_tagged_endpoints(tagged, snap_tol)
    layers_map = endpoint_layer_map(snapped)
    segments = [t.line for t in snapped]
    segments, _ = iterative_close_gaps(
        segments,
        float(geometry_cfg.get("gap_threshold", 500)),
        float(geometry_cfg.get("max_gap_angle", 30)),
        snap_tol=0.0,
        max_passes=int(geometry_cfg.get("iterative_max_passes", 3)),
        colinear_profile=bool(geometry_cfg.get("colinear_profile_match", True)),
        tier2_enabled=bool(geometry_cfg.get("tier2_threshold_enabled", False)),
        tier2_threshold=float(geometry_cfg.get("tier2_gap_threshold", 1000)),
        endpoint_layers=layers_map,
        structural_layers=frozenset(
            geometry_cfg.get("tier2_structural_layers", list(DEFAULT_TIER2_STRUCTURAL_LAYERS))
        ),
    )
    return segments, layers_map


def analyze_with_seeds(cad_path, doc, config, seeds_path: Path | None):
    base = analyze_drawing_coverage(
        drawing_name=cad_path.name,
        source_path=str(cad_path),
        dxf_path=str(cad_path),
        doc=doc,
        config=config,
    )
    if seeds_path is None or not config.get("seed_assist", {}).get("enabled", True):
        base.seed_assisted_count = 0
        base.total_with_seeds = base.detected_count
        return base

    all_seeds = load_seeds(seeds_path)
    drawing_seeds = filter_seeds_for_drawing(all_seeds, cad_path.name)
    if not drawing_seeds:
        base.seed_assisted_count = 0
        base.total_with_seeds = base.detected_count
        return base

    segments, layers_map = _prepare_segments(doc, config)
    auto = detect_regions(segments, config)
    resolutions = resolve_all_seeds(drawing_seeds, segments, config, auto, layers_map)
    merged = merge_regions(auto, resolutions, config)
    ok = sum(1 for r in resolutions if r.status == "ok")

    base.seed_assisted_count = ok
    base.total_with_seeds = len(merged)
    base.seed_resolutions = [
        {"id": r.seed.id, "status": r.status, "message": r.message} for r in resolutions
    ]
    return base


def render_seed_report(results, config, seeds_path: Path | None) -> str:
    report = render_coverage_report_markdown(results, config)
    if not seeds_path:
        return report

    report = report.replace(
        "# Detection Coverage Report (P2.5)",
        "# Detection Coverage Report (P2.5 + Seed Assist)",
    )
    report = report.replace(
        "**Phase:** P2.5 — tier-2 structural threshold + P2.3 profile matching",
        "**Phase:** P2.5 + Seed-Assisted Fallback (P1 + P2 local repair)",
    )
    extra = [
        "",
        f"**Seeds file:** `{seeds_path.name}`",
        "",
        "## Seed-assisted totals",
        "",
        "| Drawing | Auto | With seeds | Seed recovered |",
        "| --- | ---: | ---: | ---: |",
    ]
    for res in results:
        auto = res.detected_count
        total = getattr(res, "total_with_seeds", auto)
        seed_n = getattr(res, "seed_assisted_count", 0)
        extra.append(f"| {res.drawing} | {auto} | {total} | {seed_n} |")
    return report.replace("## Executive summary", "\n".join(extra) + "\n\n## Executive summary", 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Coverage report with seed assist")
    parser.add_argument("--seeds", type=str, help="Path to seed YAML/JSON file")
    args = parser.parse_args()

    config_path = PROJECT_ROOT / "config.yaml"
    with config_path.open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    input_dir = PROJECT_ROOT / config.get("input", {}).get("input_dir", "./input")
    log_dir = PROJECT_ROOT / config.get("logging", {}).get("log_dir", "./logs")
    cache_dir = PROJECT_ROOT / config.get("output", {}).get("output_dir", "./output") / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    log_path = setup_logging(Path(log_dir))
    logger = logging.getLogger(__name__)

    seeds_path = None
    if args.seeds:
        seeds_path = Path(args.seeds)
        if not seeds_path.is_absolute():
            seeds_path = PROJECT_ROOT / seeds_path

    cad_files = collect_cad_files(input_dir)
    results = []
    for cad_path in cad_files:
        if cad_path.suffix.lower() == ".dwg" and not find_oda_converter():
            logger.error("ODA required for %s", cad_path.name)
            continue
        dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
        doc = load_dxf(dxf_path)
        result = analyze_with_seeds(cad_path, doc, config, seeds_path)
        results.append(result)
        logger.info(
            "%s: auto=%d seed_recovered=%d total=%d",
            cad_path.name,
            result.detected_count,
            getattr(result, "seed_assisted_count", 0),
            getattr(result, "total_with_seeds", result.detected_count),
        )

    report_path = PROJECT_ROOT / "detection_coverage_report.md"
    report_path.write_text(render_seed_report(results, config, seeds_path), encoding="utf-8")
    json_log = log_dir / f"coverage_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    write_coverage_log(json_log, results, config)
    write_coverage_excel(PROJECT_ROOT / "coverage_metrics.xlsx", results)
    print(f"Wrote {report_path}")
    print(f"Log saved to: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
