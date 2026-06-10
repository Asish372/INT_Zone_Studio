#!/usr/bin/env python3
"""Analyze P2.2 iterative close -> repolygonize potential (planning only)."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import yaml
from shapely.geometry import LineString, MultiLineString

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.converter import ensure_dxf
from src.detector import (
    filter_polygons,
    node_geometry,
    polygonize_regions,
    remove_duplicates,
)
from src.gap_handler import _round_point, close_gaps, snap_endpoints
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.validation_diagnostics import (
    TaggedSegment,
    analyze_gaps,
    count_open_endpoints,
    extract_tagged_segments,
    snap_tagged_endpoints,
)


def count_free(segments: list[LineString]) -> int:
    counts: dict[tuple[float, float], int] = defaultdict(int)
    for seg in segments:
        coords = list(seg.coords)
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        counts[a] += 1
        counts[b] += 1
    return sum(1 for value in counts.values() if value == 1)


def extract_lines_from_noded(multi: MultiLineString) -> list[LineString]:
    merged = node_geometry(multi)
    if merged.is_empty:
        return []
    if merged.geom_type == "LineString":
        return [merged]
    return list(merged.geoms)


def iterative_close(
    segments: list[LineString],
    threshold: float,
    max_angle: float,
    snap_tol: float,
    *,
    max_passes: int = 5,
    renod_each_pass: bool,
) -> tuple[list[LineString], int, list[dict[str, int]]]:
    history: list[dict[str, int]] = []
    segs = segments
    total_closed = 0
    for pass_num in range(1, max_passes + 1):
        segs = snap_endpoints(segs, snap_tol)
        before_free = count_free(segs)
        segs, closed = close_gaps(segs, threshold, max_angle)
        total_closed += closed
        after_close_free = count_free(segs)
        if renod_each_pass:
            segs = extract_lines_from_noded(MultiLineString(segs))
            after_renod_free = count_free(segs)
        else:
            after_renod_free = after_close_free
        history.append(
            {
                "pass": pass_num,
                "closed_this_pass": closed,
                "free_before": before_free,
                "free_after_close": after_close_free,
                "free_after_renod": after_renod_free,
            }
        )
        if closed == 0:
            break
    return segs, total_closed, history


def count_gap_status(tagged: list[TaggedSegment], drawing: str, gap_threshold: float) -> dict[str, int]:
    gaps = analyze_gaps(tagged, drawing, gap_threshold)
    out: dict[str, int] = defaultdict(int)
    for gap in gaps:
        out[gap.status] += 1
    return dict(out)


def detect_blocks_from_tagged(tagged: list[TaggedSegment], config: dict) -> int:
    """Match validation_diagnostics.detect_from_tagged counting."""
    geometry_cfg = config.get("geometry", {})
    accuracy_cfg = config.get("accuracy", {})
    unit = geometry_cfg.get("drawing_unit", "mm")
    mode = str(accuracy_cfg.get("detection_mode", "exhaustive")).lower()
    exhaustive = mode == "exhaustive"
    min_area = float(geometry_cfg.get("min_area", 1.0))
    if exhaustive:
        min_area = float(accuracy_cfg.get("exhaustive_min_area_m2", 0.01))
    dedupe_iou = float(accuracy_cfg.get("dedupe_iou_threshold", 0.98))

    lines = [t.line for t in tagged]
    raw = polygonize_regions(MultiLineString(lines) if lines else MultiLineString())
    filtered = filter_polygons(raw, min_area, unit, exhaustive=exhaustive)
    return len(remove_duplicates(filtered, iou_threshold=dedupe_iou))


def iterative_close_tagged(
    tagged: list[TaggedSegment],
    threshold: float,
    max_angle: float,
    snap_tol: float,
    *,
    max_passes: int = 5,
) -> tuple[list[TaggedSegment], int, list[dict[str, int]]]:
    """Proposed P2.2 loop: snap -> close -> node -> re-extract -> repeat."""
    from src.validation_diagnostics import close_gaps_tagged

    history: list[dict[str, int]] = []
    current = tagged
    total_closed = 0
    for pass_num in range(1, max_passes + 1):
        snapped = snap_tagged_endpoints(current, snap_tol)
        closed_tagged, closed = close_gaps_tagged(snapped, threshold, max_angle)
        total_closed += closed
        free_after_close = count_open_endpoints(closed_tagged)
        lines = [t.line for t in closed_tagged]
        noded_lines = extract_lines_from_noded(MultiLineString(lines))
        renod_tagged = [TaggedSegment(line=line, layer="SRC") for line in noded_lines]
        free_after_renod = count_open_endpoints(renod_tagged)
        history.append(
            {
                "pass": pass_num,
                "closed_this_pass": closed,
                "free_after_close": free_after_close,
                "free_after_renod": free_after_renod,
            }
        )
        current = renod_tagged
        if closed == 0:
            break
    return current, total_closed, history


def tagged_from_segments(segments: list[LineString], source_count: int) -> list[TaggedSegment]:
    tagged: list[TaggedSegment] = []
    for idx, seg in enumerate(segments):
        layer = "GAP_BRIDGE" if idx >= source_count else "SRC"
        tagged.append(TaggedSegment(line=seg, layer=layer))
    return tagged


def main() -> int:
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        config = yaml.safe_load(fh) or {}

    geom = config.get("geometry", {})
    snap_tol = float(geom.get("snap_tolerance", 1))
    gap_threshold = float(geom.get("gap_threshold", 500))
    max_angle = float(geom.get("max_gap_angle", 30))

    input_dir = PROJECT_ROOT / config.get("input", {}).get("input_dir", "./input")
    cache_dir = PROJECT_ROOT / config.get("output", {}).get("output_dir", "./output") / ".dxf_cache"

    cad_files = sorted({*input_dir.glob("*.dwg"), *input_dir.glob("*.DWG")})
    if not cad_files:
        print("No DWG files found")
        return 1

    totals = {
        "single_blocks": 0,
        "iter_renod_blocks": 0,
        "single_wtu": 0,
        "iter_renod_wtu": 0,
    }

    for cad_path in cad_files:
        name = cad_path.name
        dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
        doc = load_dxf(dxf_path)
        msp = get_modelspace(doc)
        resolution = resolve_wall_layers(msp, config, auto_fallback=True)
        ignore_layers = list(config.get("layers", {}).get("ignore_layers", []))
        arc_segments = int(config.get("accuracy", {}).get("arc_segments", 64))
        tagged_src = extract_tagged_segments(
            msp, resolution.wall_layers, ignore_layers, arc_segments
        )
        lines = [item.line for item in tagged_src]

        from src.validation_diagnostics import close_gaps_tagged, detect_from_tagged

        snapped = snap_tagged_endpoints(tagged_src, snap_tol)
        closed_single, closed_single_n = close_gaps_tagged(snapped, gap_threshold, max_angle)
        gap_single = count_gap_status(closed_single, name, gap_threshold)
        polygons_single, *_ = detect_from_tagged(tagged_src, config)
        blocks_single = len(polygons_single)
        open_single = count_open_endpoints(closed_single)

        iter_final, closed_iter, hist_iter = iterative_close_tagged(
            tagged_src, gap_threshold, max_angle, snap_tol, max_passes=5
        )
        snapped_iter = snap_tagged_endpoints(iter_final, snap_tol)
        closed_iter_final, closed_iter_final_n = close_gaps_tagged(
            snapped_iter, gap_threshold, max_angle
        )
        gap_iter = count_gap_status(closed_iter_final, name, gap_threshold)
        blocks_iter = detect_blocks_from_tagged(closed_iter_final, config)
        open_iter = count_open_endpoints(closed_iter_final)

        print(f"=== {name} ===")
        print(f"  source segments: {len(lines)}")
        print(
            f"  P2.1 production path: closed={closed_single_n} open={open_single} "
            f"within_unclosed={gap_single.get('within_threshold_unclosed', 0)} "
            f"blocks={blocks_single}"
        )
        print(
            f"  P2.2 iterative path: total_closed={closed_iter + closed_iter_final_n} "
            f"open={open_iter} within_unclosed={gap_iter.get('within_threshold_unclosed', 0)} "
            f"blocks={blocks_iter} delta_blocks={blocks_iter - blocks_single}"
        )
        print(f"    close history: {hist_iter}")
        print(f"    final pass closed: {closed_iter_final_n}")
        print()

        totals["single_blocks"] += blocks_single
        totals["iter_renod_blocks"] += blocks_iter
        totals["single_wtu"] += gap_single.get("within_threshold_unclosed", 0)
        totals["iter_renod_wtu"] += gap_iter.get("within_threshold_unclosed", 0)

    print("=== TOTALS ===")
    print(f"  blocks P2.1: {totals['single_blocks']}")
    delta = totals["iter_renod_blocks"] - totals["single_blocks"]
    print(f"  blocks P2.2 iterative: {totals['iter_renod_blocks']} (delta {delta})")
    print(f"  within_unclosed P2.1: {totals['single_wtu']}")
    print(f"  within_unclosed P2.2: {totals['iter_renod_wtu']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
