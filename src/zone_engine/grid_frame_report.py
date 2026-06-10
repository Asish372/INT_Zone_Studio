"""Markdown report for grid frame builder (P1/P2 diagnostics)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.zone_engine.bay_geometry import GridFrameGeometryResult
from src.zone_engine.grid_frame import GridFrameResult


def _format_axis_table(axis_name: str, positions: list[float]) -> list[str]:
    lines = [
        f"### {axis_name}",
        "",
        "| Index | Position (mm) |",
        "| ---: | ---: |",
    ]
    for index, position in enumerate(positions, start=1):
        lines.append(f"| {index} | {position:,.2f} |")
    lines.append("")
    return lines


def _format_bay_table_geometry(result: GridFrameGeometryResult, max_rows: int = 30) -> list[str]:
    lines = [
        "### Bay cells (raw vs clipped)",
        "",
        "| INT | Row | Col | Raw (m²) | Clipped (m²) | Coverage % | Flags |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    bays = sorted(result.bays, key=lambda b: int(b.int_label.split("-")[1]))
    for bay in bays[:max_rows]:
        flags = next(
            (v.flags for v in result.validation.bay_validations if v.int_label == bay.int_label),
            [],
        )
        lines.append(
            f"| {bay.int_label} | {bay.row} | {bay.col} | {bay.raw_area_m2:,.2f} | "
            f"{bay.clipped_area_m2:,.2f} | {bay.coverage_pct:,.1f} | {', '.join(flags) or '—'} |"
        )
    if len(bays) > max_rows:
        lines.append(f"| … | | | | | | *({len(bays) - max_rows} more)* |")
    lines.append("")
    return lines


def _format_bay_table_p1(result: GridFrameResult, max_rows: int = 30) -> list[str]:
    lines = [
        "### Bay cells",
        "",
        "| Bay | Row | Col | Area (m²) | Centroid X (mm) | Centroid Y (mm) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for bay in result.bays[:max_rows]:
        lines.append(
            f"| {bay.bay_id} | {bay.row} | {bay.col} | {bay.area_m2:,.2f} | "
            f"{bay.centroid[0]:,.0f} | {bay.centroid[1]:,.0f} |"
        )
    if len(result.bays) > max_rows:
        lines.append(f"| … | | | | | *({len(result.bays) - max_rows} more)* |")
    lines.append("")
    return lines


def render_grid_frame_report_markdown(
    result: GridFrameResult | GridFrameGeometryResult,
) -> str:
    """Build markdown report body."""
    geometry = isinstance(result, GridFrameGeometryResult)
    frame = result.frame if geometry else result
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    expected = frame.expected_int_count
    phase = "P2" if geometry else "P1"

    match_status = "—"
    if expected is not None:
        if frame.bay_count == expected:
            match_status = "PASS (bay count matches expected INT count)"
        else:
            match_status = f"REVIEW (bay count {frame.bay_count} vs expected {expected})"

    lines = [
        f"# Grid Frame Report ({phase})",
        "",
        f"**Generated:** {timestamp}  ",
        f"**Source:** `{frame.source_file}`  ",
        f"**Frame mode:** `{frame.frame_mode}`  ",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Grid layers used | {', '.join(frame.grid_layers_used) or '—'} |",
        f"| Candidate grid layers | {', '.join(frame.candidate_grid_layers) or '—'} |",
        f"| Raw grid segments | {frame.raw_line_count} |",
        f"| Axis family count | {len(frame.axis_families)} |",
    ]

    if frame.axis_a:
        lines.append(
            f"| Axis A lines / merged positions | {frame.axis_a.line_count} / "
            f"{len(frame.axis_a.positions_mm)} |"
        )
    if frame.axis_b:
        lines.append(
            f"| Axis B lines / merged positions | {frame.axis_b.line_count} / "
            f"{len(frame.axis_b.positions_mm)} |"
        )

    lines.extend(
        [
            f"| Raw bay count (all adjacent axes) | {frame.raw_bay_count} |",
            f"| Bay count (frame used) | {frame.bay_count} |",
            f"| Expected INT count | {expected if expected is not None else '—'} |",
            f"| Validation | {match_status} |",
        ]
    )

    if geometry:
        geo = result
        lines.extend(
            [
                f"| Slab layer | {geo.slab.layer} |",
                f"| Slab outline method | {geo.slab.method} |",
                f"| Slab outline area (m²) | {geo.slab.area_m2:,.2f} |",
                f"| Bays before clip | {geo.bay_count_before_clip} |",
                f"| Bays non-empty after clip | {geo.bay_count_after_clip} |",
            ]
        )

    lines.append("")

    all_warnings = list(frame.warnings)
    if geometry:
        all_warnings.extend(result.warnings)

    if all_warnings:
        lines.extend(["## Warnings", ""])
        for warning in all_warnings:
            lines.append(f"- {warning}")
        lines.append("")

    if geometry:
        val = result.validation
        lines.extend(
            [
                "## Slab clipping statistics",
                "",
                f"- **Slab outline:** `{result.slab.method}` on `{result.slab.layer}`",
                f"- **Slab area:** {result.slab.area_m2:,.2f} m²",
                f"- **Total raw bay area:** {val.total_raw_area_m2:,.2f} m²",
                f"- **Total clipped bay area:** {val.total_clipped_area_m2:,.2f} m²",
                f"- **Area retained after clip:** "
                f"{(val.total_clipped_area_m2 / val.total_raw_area_m2 * 100) if val.total_raw_area_m2 else 0:.1f}%",
                f"- **Mean per-bay coverage:** {val.mean_coverage_pct:.1f}%",
                "",
                "## Geometry validation summary",
                "",
                "| Check | Count |",
                "| --- | ---: |",
                f"| Invalid clipped geometry | {val.invalid_bay_count} |",
                f"| Low coverage bays | {val.low_coverage_count} |",
                f"| Empty after clip | {val.empty_clip_count} |",
                f"| Overlapping bay pairs | {val.overlap_pair_count} |",
                "",
            ]
        )
        if val.overlaps:
            lines.extend(["### Overlap pairs", "", "| INT A | INT B | Overlap (m²) |", "| --- | --- | ---: |"])
            for record in val.overlaps:
                lines.append(
                    f"| {record.int_label_a} | {record.int_label_b} | {record.overlap_area_m2:,.4f} |"
                )
            lines.append("")

        lines.extend(
            [
                "## INT labels",
                "",
                "Labels assigned deterministically in **row-major** order (row ascending, then column ascending). "
                "Repeated runs with the same grid produce identical `INT-n` mapping.",
                "",
            ]
        )

    lines.extend(["## Grid line extraction", ""])
    layer_counts: dict[str, int] = {}
    for line in frame.grid_lines:
        layer_counts[line.layer] = layer_counts.get(line.layer, 0) + 1
    lines.extend(["| Layer | Segments |", "| --- | ---: |"])
    for layer, count in sorted(layer_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {layer} | {count} |")
    lines.append("")

    if frame.axis_families:
        lines.extend(["## Axis families", ""])
        for family in frame.axis_families:
            lines.append(
                f"- **{family.name}**: angle {family.angle_deg:.1f}°, "
                f"{family.line_count} segments → {len(family.positions_mm)} axis positions "
                f"(layers: {', '.join(family.source_layers)})"
            )
        lines.append("")

    if frame.axis_a and frame.axis_b:
        lines.extend(["## Sorted axis positions", ""])
        lines.extend(_format_axis_table("Axis A (primary family)", frame.axis_a.positions_mm))
        lines.extend(_format_axis_table("Axis B (secondary family)", frame.axis_b.positions_mm))

    if frame.bays:
        if geometry:
            lines.extend(["## Bay diagnostics", ""])
            lines.extend(_format_bay_table_geometry(result))
        else:
            total_area = sum(bay.area_m2 for bay in frame.bays)
            areas = [bay.area_m2 for bay in frame.bays]
            lines.extend(
                [
                    "## Bay diagnostics",
                    "",
                    f"- **Bay count:** {frame.bay_count}",
                    f"- **Total bay area (sum of cells, m²):** {total_area:,.2f}",
                    f"- **Min / max / mean bay area (m²):** "
                    f"{min(areas):,.2f} / {max(areas):,.2f} / {total_area / len(areas):,.2f}",
                    "",
                ]
            )
            lines.extend(_format_bay_table_p1(frame))

    lines.extend(
        [
            "## Expected INT count",
            "",
            "INT zones are intended to align **one pour per structural bay** on grid warehouse drawings. "
            "Face assignment to micro-polygons is **not** included in this phase.",
            "",
        ]
    )
    if expected is not None:
        lines.append(
            f"Manifest / profile expects **{expected}** INT zones. "
            f"Current frame yields **{frame.bay_count}** bay polygons."
        )
    else:
        lines.append("No expected INT count was supplied (set via manifest `zone_count_expected`).")

    lines.extend(["", "---", "", f"*End of grid frame report ({phase})*", ""])
    return "\n".join(lines)


def write_grid_frame_report(
    result: GridFrameResult | GridFrameGeometryResult,
    output_path: str | Path,
) -> Path:
    """Write grid frame markdown report to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_grid_frame_report_markdown(result), encoding="utf-8")
    return path
