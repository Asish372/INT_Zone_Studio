#!/usr/bin/env python3
"""Step 5: Export top regions per drawing for manual AutoCAD AREA comparison."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.calculator import compute_all
from src.converter import ensure_dxf
from src.detector import detect_regions
from src.extractor import extract_all_segments, extract_entities
from src.gap_handler import close_gaps, snap_endpoints
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf


def load_config() -> dict:
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def collect_cad_files(input_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.dwg", "*.DWG", "*.dxf", "*.DXF"):
        files.extend(input_dir.glob(pattern))
    return sorted({f.resolve() for f in files})


def format_md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No data._\n"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines) + "\n"


def process_drawing(cad_path: Path, config: dict, cache_dir: Path, top_n: int = 10) -> list[list[str]]:
    dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
    doc = load_dxf(dxf_path)
    msp = get_modelspace(doc)
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    ignore = list(config.get("layers", {}).get("ignore_layers", []))
    arc_segments = int(config.get("accuracy", {}).get("arc_segments", 64))
    entities = extract_entities(msp, resolution.wall_layers, ignore)
    segments = extract_all_segments(entities, arc_segments=arc_segments)
    geometry_cfg = config.get("geometry", {})
    segments = snap_endpoints(segments, float(geometry_cfg.get("snap_tolerance", 1)))
    segments, _ = close_gaps(
        segments,
        float(geometry_cfg.get("gap_threshold", 500)),
        float(geometry_cfg.get("max_gap_angle", 30)),
    )
    polygons = detect_regions(segments, config)
    regions = compute_all(polygons, config, str(cad_path.resolve()))
    regions.sort(key=lambda r: r.area_m2, reverse=True)

    rows: list[list[str]] = []
    for region in regions[:top_n]:
        cx = region.centroid.x
        cy = region.centroid.y
        rows.append(
            [
                cad_path.name,
                region.label,
                f"{region.area_m2:.4f}",
                "?",
                "?",
                f"({cx:.1f}, {cy:.1f})",
            ]
        )
    return rows


def main() -> int:
    config = load_config()
    cache_dir = PROJECT_ROOT / "output" / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[list[str]] = []

    for cad_path in collect_cad_files(PROJECT_ROOT / "input"):
        try:
            all_rows.extend(process_drawing(cad_path, config, cache_dir))
        except Exception as exc:
            all_rows.append([cad_path.name, "—", "—", "—", f"error: {exc}", "—"])

    lines = [
        "# Area Benchmark Template",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Measure each region in AutoCAD (`AREA` command) and fill **AutoCAD Area (m²)**.",
        "Then compute **Error %** = `|detector - autocad| / autocad * 100`.",
        "",
        "**PRD target:** max error ≤ **0.05%** on clean regions.",
        "",
        "## Regions to measure (largest per drawing)",
        "",
        format_md_table(
            [
                "Drawing",
                "Region ID",
                "Detector Area (m²)",
                "AutoCAD Area (m²)",
                "Error %",
                "Centroid (hint)",
            ],
            all_rows,
        ),
        "## Summary (fill after measurement)",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        "| Max Error % | ? |",
        "| Mean Error % | ? |",
        "| Median Error % | ? |",
        "| Regions within 0.05% | ? / ? |",
        "",
    ]

    out_path = PROJECT_ROOT / "area_benchmark_template.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path} ({len(all_rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
