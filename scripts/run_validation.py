#!/usr/bin/env python3
"""Validation phase: diagnostics on real DWG/DXF drawings (no product features)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.converter import ensure_dxf, find_oda_converter
from src.parser import load_dxf
from src.validation_diagnostics import DrawingDiagnostics, GapRecord, diagnose_drawing


def load_config() -> dict:
    path = PROJECT_ROOT / "config.yaml"
    with path.open(encoding="utf-8") as fh:
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


def render_drawing_section(diag: DrawingDiagnostics) -> str:
    lines = [
        f"### {Path(diag.source_path).name}",
        "",
        f"- **Source:** `{diag.source_path}`",
        f"- **DXF used:** `{diag.dxf_path}`",
        f"- **Conversion:** {diag.conversion_note}",
        "",
    ]

    if diag.error:
        lines.extend([f"**ERROR:** {diag.error}", ""])
        return "\n".join(lines)

    lines.extend(
        [
            "| Metric | Value |",
            "| --- | --- |",
            f"| Total entities (modelspace) | {diag.total_entities} |",
            f"| Configured wall layers | {', '.join(diag.configured_wall_layers) or '_none_'} |",
            f"| Entities on configured layers | {diag.configured_entities} |",
            f"| Segments (configured layers) | {diag.configured_segments} |",
            f"| Candidate wall layers (count) | {len(diag.candidate_wall_layers)} |",
            f"| Entities on candidate layers | {diag.candidate_entities} |",
            f"| Segments (candidate layers) | {diag.candidate_segments} |",
            f"| Open endpoints (before gap close) | {diag.open_endpoints_before_close} |",
            f"| Gaps auto-closed | {diag.gaps_closed} |",
            f"| Open endpoints (after gap close) | {diag.open_endpoints_after_close} |",
            f"| Raw polygons (polygonize) | {diag.raw_polygon_count} |",
            f"| Invalid polygons | {diag.invalid_polygon_count} |",
            f"| **Regions detected** (configured layers) | **{diag.regions_detected}** |",
            f"| Regions (candidate layers) | {diag.regions_with_candidate_layers} |",
            f"| Largest area (m2) | {diag.largest_area_m2 if diag.largest_area_m2 is not None else 'N/A'} |",
            f"| Smallest area (m2) | {diag.smallest_area_m2 if diag.smallest_area_m2 is not None else 'N/A'} |",
            f"| **Total detected area (m2)** | **{diag.total_detected_area_m2:.4f}** |",
            f"| Candidate largest area (m2) | {diag.candidate_largest_area_m2 if diag.candidate_largest_area_m2 is not None else 'N/A'} |",
            f"| Candidate smallest area (m2) | {diag.candidate_smallest_area_m2 if diag.candidate_smallest_area_m2 is not None else 'N/A'} |",
            f"| Candidate total area (m2) | {diag.candidate_total_area_m2:.4f} |",
            "",
        ]
    )

    if diag.configured_entities == 0:
        lines.extend(
            [
                "> **Likely failure:** No entities on configured `wall_layers`. "
                "Compare **Candidate wall layers** below and update `config.yaml`.",
                "",
            ]
        )

    if diag.regions_detected == 0 and diag.regions_with_candidate_layers > 0:
        lines.extend(
            [
                "> **Primary issue:** `wall_layers` in config do not match this drawing. "
                f"Candidate layers would detect **{diag.regions_with_candidate_layers}** regions "
                f"({diag.candidate_total_area_m2:.2f} m2 total). Update `config.yaml`.",
                "",
            ]
        )

    type_rows = [
        [t, str(c)] for t, c in sorted(diag.entity_type_counts.items(), key=lambda x: -x[1])
    ]
    lines.append("#### Entity types (modelspace)\n")
    lines.append(format_md_table(["Type", "Count"], type_rows[:30]))

    layer_rows = [
        [layer, str(diag.layer_entity_counts[layer]), str(diag.layer_geometry_counts.get(layer, 0))]
        for layer in sorted(diag.layer_entity_counts, key=lambda name: -diag.layer_entity_counts[name])
    ]
    lines.append("#### Layer breakdown (all entities / boundary geometry)\n")
    lines.append(format_md_table(["Layer", "All entities", "LINE/LWPOLY/ARC/POLY"], layer_rows[:40]))

    cand_rows = [[layer, str(diag.layer_geometry_counts.get(layer, 0))] for layer in diag.candidate_wall_layers]
    lines.append("#### Candidate wall layers\n")
    lines.append(format_md_table(["Layer", "Boundary entities"], cand_rows))

    return "\n".join(lines)


def write_validation_report(
    path: Path,
    diagnostics: list[DrawingDiagnostics],
    gap_records: list[GapRecord],
    config: dict,
) -> None:
    oda = find_oda_converter()
    geometry = config.get("geometry", {})
    accuracy = config.get("accuracy", {})

    lines = [
        "# Validation Report — DXF Room Detection",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Run configuration",
        "",
        format_md_table(
            ["Setting", "Value"],
            [
                ["gap_threshold", str(geometry.get("gap_threshold"))],
                ["snap_tolerance", str(geometry.get("snap_tolerance"))],
                ["drawing_unit", str(geometry.get("drawing_unit"))],
                ["detection_mode", str(accuracy.get("detection_mode"))],
                ["configured wall_layers", ", ".join(config.get("layers", {}).get("wall_layers", []))],
                ["ODA File Converter", str(oda) if oda else "NOT FOUND"],
            ],
        ),
        "",
        "## Executive summary",
        "",
    ]

    for diag in diagnostics:
        name = Path(diag.source_path).name
        if diag.error:
            lines.append(f"- **{name}:** FAILED — {diag.error}")
        else:
            lines.append(
                f"- **{name}:** configured={diag.regions_detected} regions "
                f"({diag.total_detected_area_m2:.2f} m2), "
                f"candidate={diag.regions_with_candidate_layers} regions "
                f"({diag.candidate_total_area_m2:.2f} m2), "
                f"open endpoints after gap close={diag.open_endpoints_after_close}"
            )

    lines.extend(["", "## Per-drawing diagnostics", ""])
    for diag in diagnostics:
        lines.append(render_drawing_section(diag))

    lines.extend(
        [
            "## Gap analysis summary",
            "",
            f"Total gap/orphan records: **{len(gap_records)}** (see `gap_report.xlsx`)",
            "",
            "| Status | Count |",
            "| --- | --- |",
        ]
    )
    status_counts: dict[str, int] = {}
    for rec in gap_records:
        status_counts[rec.status] = status_counts.get(rec.status, 0) + 1
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            "## Recommended next tuning steps",
            "",
            "1. If **configured entities = 0**, set `wall_layers` from candidate layers table.",
            "2. If **open endpoints after close > 0**, raise `gap_threshold` using suggested values in `gap_report.xlsx`.",
            "3. If **candidate regions >> configured regions**, current layer filter is too narrow.",
            "4. Compare total area and region count to AutoCAD manual takeoff (ground truth).",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_gap_report(path: Path, records: list[GapRecord], gap_threshold: float) -> None:
    rows = [
        {
            "Drawing": r.drawing,
            "Endpoint A X": r.endpoint_a_x,
            "Endpoint A Y": r.endpoint_a_y,
            "Endpoint B X": r.endpoint_b_x,
            "Endpoint B Y": r.endpoint_b_y,
            "Gap distance": r.gap_distance,
            "Layer A": r.layer_a,
            "Layer B": r.layer_b,
            "Within current threshold": r.within_current_threshold,
            "Current gap_threshold": gap_threshold,
            "Suggested closure threshold": r.suggested_closure_threshold,
            "Status": r.status,
        }
        for r in records
    ]
    df = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {
                "Drawing": "ALL",
                "Status": "total_records",
                "Gap distance": len(records),
            }
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Gaps", index=False)
        if not df.empty:
            by_status = df.groupby(["Drawing", "Status"]).size().reset_index(name="Count")
            by_status.to_excel(writer, sheet_name="Summary_by_status", index=False)
            over = df[df["Gap distance"].notna() & (df["Gap distance"] > gap_threshold)]
            over.to_excel(writer, sheet_name="Above_threshold", index=False)
        summary.to_excel(writer, sheet_name="Meta", index=False)


def main() -> int:
    config = load_config()
    input_dir = PROJECT_ROOT / config.get("input", {}).get("input_dir", "./input")
    output_dir = PROJECT_ROOT / config.get("output", {}).get("output_dir", "./output")
    cache_dir = output_dir / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cad_files = collect_cad_files(input_dir)
    if not cad_files:
        print(f"No DWG/DXF files in {input_dir}")
        return 1

    diagnostics: list[DrawingDiagnostics] = []
    all_gaps: list[GapRecord] = []

    for cad_path in cad_files:
        print(f"Validating: {cad_path.name}")
        diag = DrawingDiagnostics(
            source_path=str(cad_path),
            dxf_path="",
            conversion_note="",
        )
        try:
            if cad_path.suffix.lower() == ".dwg":
                oda = find_oda_converter()
                if not oda:
                    diag.error = (
                        "ODA File Converter not installed — cannot read DWG. "
                        "Install from opendesign.com or export to DXF manually."
                    )
                    diagnostics.append(diag)
                    continue
                dxf_path = ensure_dxf(cad_path, cache_dir)
                diag.conversion_note = f"DWG converted via ODA ({oda})"
            else:
                dxf_path = cad_path
                diag.conversion_note = "Native DXF"

            diag.dxf_path = str(dxf_path)
            doc = load_dxf(dxf_path)
            diag, gaps = diagnose_drawing(cad_path, dxf_path, doc, config, diag.conversion_note)
            all_gaps.extend(gaps)
            diagnostics.append(diag)
            print(
                f"  -> regions={diag.regions_detected}, "
                f"open_after={diag.open_endpoints_after_close}, "
                f"gaps_logged={len(gaps)}"
            )
        except Exception as exc:
            diag.error = str(exc)
            diagnostics.append(diag)
            print(f"  -> ERROR: {exc}")

    report_path = PROJECT_ROOT / "validation_report.md"
    gap_path = PROJECT_ROOT / "gap_report.xlsx"
    gap_threshold = float(config.get("geometry", {}).get("gap_threshold", 500))

    write_validation_report(report_path, diagnostics, all_gaps, config)
    write_gap_report(gap_path, all_gaps, gap_threshold)

    print(f"\nWrote {report_path}")
    print(f"Wrote {gap_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
