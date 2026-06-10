#!/usr/bin/env python3
"""CLI entry point for DXF CAD Room Detection & Area Calculation."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src import __version__
from src.calculator import compute_all
from src.detector import detect_regions
from src.exporter import export_results
from src.extractor import extract_entities
from src.endpoint_matching import DEFAULT_TIER2_STRUCTURAL_LAYERS
from src.gap_handler import close_gaps, iterative_close_gaps, snap_endpoints
from src.seed_resolver import (
    filter_seeds_for_drawing,
    load_seeds,
    merge_regions,
    resolve_all_seeds,
)
from src.validation_diagnostics import endpoint_layer_map, extract_tagged_segments, snap_tagged_endpoints
from src.converter import ensure_dxf
from src.layer_resolver import LayerResolution, resolve_wall_layers
from src.parser import get_modelspace, list_layers, load_dxf

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"


def load_config(config_path: Path) -> dict[str, Any]:
    """Load YAML configuration file."""
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def apply_cli_overrides(config: dict[str, Any], args: argparse.Namespace) -> None:
    """Apply command-line overrides to configuration."""
    geometry = config.setdefault("geometry", {})
    output = config.setdefault("output", {})

    if args.thickness is not None:
        geometry["slab_thickness"] = args.thickness
    if args.gap is not None:
        geometry["gap_threshold"] = args.gap
    if args.prefix is not None:
        output["label_prefix"] = args.prefix


def setup_logging(config: dict[str, Any], project_root: Path) -> Path:
    """Configure logging to file and console."""
    log_cfg = config.get("logging", {})
    log_dir = project_root / log_cfg.get("log_dir", "./logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"run_{timestamp}.log"

    level_name = log_cfg.get("log_level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_path


def resolve_output_dir(config: dict[str, Any], project_root: Path) -> Path:
    """Resolve and create output directory."""
    output_dir = Path(config.get("output", {}).get("output_dir", "./output"))
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _print_layer_ranking(ranking: list[tuple[str, int]], limit: int = 15) -> None:
    for layer, count in ranking[:limit]:
        print(f"    {layer}: {count} boundary entities")
    if len(ranking) > limit:
        print(f"    ... and {len(ranking) - limit} more layers")


def confirm_layer_resolution(
    resolution: LayerResolution,
    cad_name: str,
    *,
    interactive: bool,
) -> bool:
    """Log or prompt before using auto-discovered layers."""
    if resolution.source != "auto_fallback":
        return True

    logger = logging.getLogger(__name__)
    logger.warning(
        "No entities on configured wall_layers for %s — using auto-discovered layers",
        cad_name,
    )
    print(f"\nLayer auto-fallback: {cad_name}")
    print(f"  Configured layers had 0 boundary entities.")
    print(f"  Top layers by geometry density:")
    _print_layer_ranking(resolution.layer_ranking)
    print(f"  Using {len(resolution.wall_layers)} candidate layer(s):")
    for name in resolution.wall_layers:
        print(f"    - {name}")

    if not interactive:
        print("  Continuing automatically (use --confirm-layers to approve each file).\n")
        return True

    try:
        answer = input("  Continue with these layers? [Y/n]: ").strip().lower()
    except EOFError:
        return True
    if answer in ("n", "no"):
        print("  Skipped.\n")
        return False
    print("")
    return True


def process_file(
    cad_path: Path,
    config: dict[str, Any],
    project_root: Path,
    cache_dir: Path | None = None,
    *,
    auto_fallback: bool = True,
    confirm_layers: bool = False,
    zone_mode: bool = False,
    zone_profile: str | None = None,
    manifest_path: Path | None = None,
    seeds_path: Path | None = None,
) -> int:
    """Run the full pipeline on a single DXF or DWG file."""
    if zone_mode or config.get("zone_engine", {}).get("enabled", False):
        from src.zone_engine.zone_mode import process_file_zones

        return process_file_zones(
            cad_path,
            config,
            project_root,
            manifest_path=manifest_path,
            zone_profile=zone_profile,
            cache_dir=cache_dir,
            auto_fallback=auto_fallback,
        )
    logger = logging.getLogger(__name__)
    layers_cfg = config.get("layers", {})
    ignore_layers = layers_cfg.get("ignore_layers", [])

    if cache_dir is None:
        cache_dir = project_root / "output" / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    original_name = cad_path.name
    if cad_path.suffix.lower() == ".dwg":
        logger.info("Converting DWG to DXF: %s", cad_path.name)
        dxf_path = ensure_dxf(cad_path, cache_dir)
    else:
        dxf_path = cad_path

    doc = load_dxf(dxf_path)
    msp = get_modelspace(doc)
    all_layers = list_layers(doc)
    logger.debug("Available layers: %s", all_layers)

    resolution = resolve_wall_layers(msp, config, auto_fallback=auto_fallback)
    if not confirm_layer_resolution(
        resolution, original_name, interactive=confirm_layers
    ):
        return 1

    wall_layers = resolution.wall_layers
    if resolution.source == "auto_fallback":
        logger.info(
            "Auto-fallback layers (%d entities): %s",
            resolution.candidate_entity_count,
            ", ".join(wall_layers),
        )
    else:
        logger.info(
            "Configured layers (%d entities): %s",
            resolution.configured_entity_count,
            ", ".join(wall_layers),
        )

    entities = extract_entities(msp, wall_layers, ignore_layers)
    if not entities:
        logger.error(
            "No boundary entities after layer resolution (source=%s). "
            "Check config.yaml or use --list-layers.",
            resolution.source,
        )
        return 1

    accuracy_cfg = config.get("accuracy", {})
    arc_segments = int(accuracy_cfg.get("arc_segments", 64))
    tagged = extract_tagged_segments(msp, wall_layers, ignore_layers, arc_segments)
    if not tagged:
        logger.warning("No line segments extracted from %s", original_name)
        return 1

    geometry_cfg = config.get("geometry", {})
    snap_tol = float(geometry_cfg.get("snap_tolerance", 1))
    gap_threshold = float(geometry_cfg.get("gap_threshold", 500))
    max_angle = float(geometry_cfg.get("max_gap_angle", 30))
    colinear_profile = bool(geometry_cfg.get("colinear_profile_match", True))
    tier2_enabled = bool(geometry_cfg.get("tier2_threshold_enabled", False))
    tier2_threshold = float(geometry_cfg.get("tier2_gap_threshold", 1000))
    tier2_layers = frozenset(
        geometry_cfg.get("tier2_structural_layers", list(DEFAULT_TIER2_STRUCTURAL_LAYERS))
    )

    snapped = snap_tagged_endpoints(tagged, snap_tol)
    layers_map = endpoint_layer_map(snapped)
    segments = [t.line for t in snapped]

    iterative = bool(geometry_cfg.get("iterative_gap_close", True))
    max_passes = int(geometry_cfg.get("iterative_max_passes", 3))
    if iterative:
        segments, gaps_closed = iterative_close_gaps(
            segments,
            gap_threshold,
            max_angle,
            snap_tol=0.0,
            max_passes=max_passes,
            colinear_profile=colinear_profile,
            tier2_enabled=tier2_enabled,
            tier2_threshold=tier2_threshold,
            endpoint_layers=layers_map,
            structural_layers=tier2_layers,
        )
    else:
        segments, gaps_closed = close_gaps(
            segments, gap_threshold, max_angle, colinear_profile=colinear_profile
        )
        if tier2_enabled:
            from src.gap_handler import close_gaps_tier2

            segments, tier2_closed = close_gaps_tier2(
                segments,
                gap_threshold,
                tier2_threshold,
                max_angle,
                endpoint_layers=layers_map,
                structural_layers=tier2_layers,
                colinear_profile=colinear_profile,
            )
            gaps_closed += tier2_closed

    auto_polygons = detect_regions(segments, config)
    auto_count = len(auto_polygons)

    seed_cfg = config.get("seed_assist", {})
    seed_enabled = bool(seed_cfg.get("enabled", True))
    effective_seeds_path = seeds_path
    if effective_seeds_path is None and seed_cfg.get("seeds_file"):
        candidate = Path(str(seed_cfg["seeds_file"]))
        if not candidate.is_absolute():
            candidate = project_root / candidate
        if candidate.is_file():
            effective_seeds_path = candidate

    seed_resolutions = []
    merged = None
    if seed_enabled and effective_seeds_path is not None:
        all_seeds = load_seeds(effective_seeds_path)
        drawing_seeds = filter_seeds_for_drawing(all_seeds, original_name)
        if drawing_seeds:
            logger.info(
                "Seed assist: resolving %d seed(s) from %s",
                len(drawing_seeds),
                effective_seeds_path.name,
            )
            seed_resolutions = resolve_all_seeds(
                drawing_seeds, segments, config, auto_polygons, layers_map
            )
            merged = merge_regions(auto_polygons, seed_resolutions, config)
        elif all_seeds:
            logger.info(
                "Seed file %s has no seeds for %s",
                effective_seeds_path.name,
                original_name,
            )

    if merged is not None:
        polygons = [m.polygon for m in merged]
        region_meta = [
            {
                "detection_method": m.detection_method,
                "seed_x": m.seed_x,
                "seed_y": m.seed_y,
                "seed_id": m.seed_id,
                "label_hint": m.label_hint,
            }
            for m in merged
        ]
    else:
        polygons = auto_polygons
        region_meta = None

    if not polygons:
        logger.warning("Zero regions detected in %s", original_name)

    regions = compute_all(polygons, config, str(cad_path.resolve()), region_meta=region_meta)

    output_dir = resolve_output_dir(config, project_root)
    stem = cad_path.stem
    paths = {
        "dxf": output_dir / f"{stem}_annotated.dxf",
        "excel": output_dir / f"{stem}_results.xlsx",
        "csv": output_dir / f"{stem}_results.csv",
    }

    written = export_results(doc, regions, paths, config)

    print(
        f"Loaded: {original_name} ({len(entities)} entities, "
        f"layers={resolution.source}, {len(segments)} segments)"
    )
    print(f"Gaps closed: {gaps_closed}")
    print(f"Regions detected: {len(regions)} (auto={auto_count})")
    if seed_resolutions:
        ok = sum(1 for r in seed_resolutions if r.status == "ok")
        dup = sum(1 for r in seed_resolutions if r.status == "duplicate_of_auto")
        fail = len(seed_resolutions) - ok - dup
        print(f"Seed assist: ok={ok} duplicate={dup} failed={fail}")
        for res in seed_resolutions:
            if res.status != "ok":
                print(f"  [{res.status}] {res.seed.id or res.seed.label_hint}: {res.message}")
    for key, path in written.items():
        print(f"Exported ({key}): {path}")

    if regions:
        total_area = sum(r.area_m2 for r in regions)
        total_volume = sum(r.volume_m3 for r in regions)
        print("\nSUMMARY")
        print("-----------------------------")
        print(f"Total Regions : {len(regions):>6}")
        print(f"Total Area    : {total_area:>10.2f} m2")
        print(f"Total Volume  : {total_volume:>10.2f} m3")
        print("-----------------------------")

    return 0


def collect_cad_files(input_path: Path, patterns: list[str]) -> list[Path]:
    """Collect DXF/DWG files from a file path or directory."""
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        files: list[Path] = []
        for pattern in patterns:
            files.extend(input_path.glob(pattern))
        return sorted({f.resolve() for f in files})
    return []


def list_layers_command(cad_path: Path, project_root: Path) -> int:
    """Print layer names from a DXF/DWG file (helps configure config.yaml)."""
    cache_dir = project_root / "output" / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
    doc = load_dxf(dxf_path)
    layers = list_layers(doc)
    print(f"Layers in {cad_path.name} ({len(layers)} total):")
    for name in sorted(layers):
        print(f"  - {name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser."""
    parser = argparse.ArgumentParser(
        description="Detect enclosed regions in DXF files and export area/volume reports.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a .dxf/.dwg file or folder (with --batch)",
    )
    parser.add_argument(
        "--input",
        "-i",
        dest="input_flag",
        help="Path to input CAD file (alternative to positional argument)",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=str(DEFAULT_CONFIG),
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all DXF/DWG files in input folder",
    )
    parser.add_argument(
        "--list-layers",
        action="store_true",
        help="List layer names in the input file and exit (for config.yaml)",
    )
    parser.add_argument(
        "--confirm-layers",
        action="store_true",
        help="When auto-fallback applies, prompt before processing each file",
    )
    parser.add_argument(
        "--no-auto-layers",
        action="store_true",
        help="Do not auto-discover layers; fail if configured wall_layers are empty",
    )
    parser.add_argument("--thickness", type=float, help="Slab thickness in metres")
    parser.add_argument("--gap", type=float, help="Gap closure threshold in drawing units")
    parser.add_argument("--prefix", help="Region label prefix (e.g. Room, Slab)")
    parser.add_argument(
        "--zones",
        action="store_true",
        help="Run INT zone engine (Stage 1 faces + Stage 2 zones + schedule export)",
    )
    parser.add_argument(
        "--zone-profile",
        choices=["auto", "GRID_WAREHOUSE", "JOINT_WAREHOUSE", "MANIFEST_OVERRIDE"],
        help="Zone engine profile override (default: auto from manifest/config)",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to INT zone manifest YAML (e.g. reference/j33a_zones_manifest.yaml)",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        help="Path to JSON/YAML/CSV seed file for missed-region recovery",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main() -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    input_arg = args.input_flag or args.input
    if not input_arg:
        parser.error("Provide a DXF file path or use --input")

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path

    config = load_config(config_path)
    apply_cli_overrides(config, args)

    log_path = setup_logging(config, PROJECT_ROOT)
    logger = logging.getLogger(__name__)
    logger.info("DXF CAD Room Detector v%s", __version__)

    input_path = Path(input_arg)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    if args.list_layers:
        if not input_path.is_file():
            logger.error("--list-layers requires a single file path")
            return 1
        try:
            return list_layers_command(input_path, PROJECT_ROOT)
        except Exception as exc:
            logger.exception("Failed to list layers: %s", exc)
            return 1

    pattern = config.get("input", {}).get("file_pattern", "*.dxf")
    patterns = [pattern]
    if "*.dwg" not in patterns and pattern != "*.dwg":
        patterns.append("*.dwg")

    if args.batch or input_path.is_dir():
        cad_files = collect_cad_files(input_path, patterns)
    else:
        if input_path.suffix.lower() not in (".dxf", ".dwg"):
            logger.error("Input must be a .dxf or .dwg file: %s", input_path)
            return 1
        cad_files = [input_path]

    if not cad_files:
        logger.error("No DXF/DWG files found at: %s", input_path)
        return 1

    manifest_path: Path | None = None
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_absolute():
            manifest_path = PROJECT_ROOT / manifest_path

    seeds_path: Path | None = None
    if args.seeds:
        seeds_path = Path(args.seeds)
        if not seeds_path.is_absolute():
            seeds_path = PROJECT_ROOT / seeds_path

    exit_code = 0
    for cad_file in cad_files:
        try:
            code = process_file(
                cad_file,
                config,
                PROJECT_ROOT,
                auto_fallback=not args.no_auto_layers,
                confirm_layers=args.confirm_layers,
                zone_mode=args.zones,
                zone_profile=args.zone_profile,
                manifest_path=manifest_path,
                seeds_path=seeds_path,
            )
            exit_code = max(exit_code, code)
        except FileNotFoundError as exc:
            logger.error("%s", exc)
            exit_code = 1
        except RuntimeError as exc:
            logger.error("%s", exc)
            exit_code = 1
        except Exception as exc:
            logger.exception("Failed processing %s: %s", cad_file, exc)
            exit_code = 1

    print(f"Log saved to: {log_path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
