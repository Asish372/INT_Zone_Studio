#!/usr/bin/env python3
"""Verification: within_threshold_unclosed gap diagnostics → gap_failure_analysis.md"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.converter import ensure_dxf
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.validation_diagnostics import (
    extract_tagged_segments,
    explain_within_threshold_unclosed,
    snap_tagged_endpoints,
)


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
        return "_No rows._\n"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    config = load_config()
    input_dir = PROJECT_ROOT / "input"
    cache_dir = PROJECT_ROOT / "output" / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    geometry_cfg = config.get("geometry", {})
    accuracy_cfg = config.get("accuracy", {})
    gap_threshold = float(geometry_cfg.get("gap_threshold", 500))
    snap_tol = float(geometry_cfg.get("snap_tolerance", 1))
    max_angle = float(geometry_cfg.get("max_gap_angle", 30))
    arc_segments = int(accuracy_cfg.get("arc_segments", 64))
    ignore_layers = list(config.get("layers", {}).get("ignore_layers", []))

    cad_files = collect_cad_files(input_dir)
    if not cad_files:
        print("No CAD files in input/")
        return 1

    all_details: list = []
    per_drawing_counts: list[tuple[str, int]] = []

    for cad_path in cad_files:
        dxf_path = (
            ensure_dxf(cad_path, cache_dir)
            if cad_path.suffix.lower() == ".dwg"
            else cad_path
        )
        doc = load_dxf(dxf_path)
        msp = get_modelspace(doc)
        resolution = resolve_wall_layers(msp, config, auto_fallback=True)
        tagged = extract_tagged_segments(
            msp, resolution.wall_layers, ignore_layers, arc_segments
        )
        snapped = snap_tagged_endpoints(tagged, snap_tol)
        details = explain_within_threshold_unclosed(
            snapped, cad_path.name, gap_threshold, max_angle
        )
        all_details.extend(details)
        per_drawing_counts.append((cad_path.name, len(details)))

    lines = [
        "# Gap Failure Analysis",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Scope",
        "",
        "Only **`within_threshold_unclosed`** gaps (distance ≤ `gap_threshold` but not bridged).",
        "No new product features — diagnostics for recall tuning.",
        "",
        "## Configuration",
        "",
        format_md_table(
            ["Setting", "Value"],
            [
                ["gap_threshold", str(gap_threshold)],
                ["snap_tolerance", str(snap_tol)],
                ["max_gap_angle", str(max_angle)],
            ],
        ),
        "## Summary",
        "",
        format_md_table(
            ["Drawing", "within_threshold_unclosed count"],
            [[name, str(count)] for name, count in per_drawing_counts],
        ),
        f"**Total:** {len(all_details)} gaps",
        "",
        "## Failure reasons (aggregate)",
        "",
    ]

    reason_counts: dict[str, int] = {}
    for d in all_details:
        reason_counts[d.failure_reason] = reason_counts.get(d.failure_reason, 0) + 1
    lines.append(
        format_md_table(
            ["failure_reason", "count"],
            [[k, str(v)] for k, v in sorted(reason_counts.items(), key=lambda x: -x[1])],
        )
    )

    lines.extend(
        [
            "## Recommended next tuning (no code yet)",
            "",
            "1. If **greedy_pairing_conflict** dominates: consider sorting gap pairs by distance ascending before bridging.",
            "2. If **bearing_mismatch_suspected** appears: review `max_gap_angle` or allow orthogonal door gaps.",
            "3. Re-measure recall after threshold-only changes.",
            "",
            "## Detail table (first 100 rows)",
            "",
        ]
    )

    detail_rows: list[list[str]] = []
    for d in all_details[:100]:
        detail_rows.append(
            [
                d.drawing,
                f"{d.gap_distance}",
                d.layer_a,
                d.layer_b,
                f"({d.endpoint_a_x:.1f}, {d.endpoint_a_y:.1f})",
                f"({d.endpoint_b_x:.1f}, {d.endpoint_b_y:.1f})",
                d.failure_reason,
                f"{d.bearing_delta_deg}",
                d.note[:80] + ("…" if len(d.note) > 80 else ""),
            ]
        )

    lines.append(
        format_md_table(
            [
                "drawing",
                "gap_dist",
                "layer_a",
                "layer_b",
                "point_a",
                "point_b",
                "reason",
                "bearing_Δ°",
                "note",
            ],
            detail_rows,
        )
    )

    if len(all_details) > 100:
        lines.append(f"\n_… {len(all_details) - 100} more rows omitted._\n")

    out_path = PROJECT_ROOT / "gap_failure_analysis.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path} ({len(all_details)} within_threshold_unclosed gaps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
