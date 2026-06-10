"""P3 — Markdown coverage and manifest reconciliation report."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.zone_engine.models import IntZonePipelineResult


def render_int_zone_report_markdown(result: IntZonePipelineResult) -> str:
    """Build P3 section markdown for zone assignment and coverage."""
    geometry = result.geometry
    frame = geometry.frame
    assignment = result.assignment
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# INT Zone Pipeline Report (P3)",
        "",
        f"**Generated:** {timestamp}  ",
        f"**Source:** `{frame.source_file}`  ",
        f"**Profile:** `{result.zones[0].profile if result.zones else '—'}`  ",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Grid bays (P2) | {geometry.bay_count_after_clip} non-empty / {geometry.bay_count_before_clip} total |",
        f"| Micro-faces (Stage 1) | {assignment.total_faces} |",
        f"| Slivers filtered | {assignment.sliver_count} |",
        f"| Faces assigned | {assignment.assigned_count} |",
        f"| Orphan faces | {assignment.orphan_count} |",
        f"| INT zones (union) | {len(result.zones)} |",
        f"| Assignment method | `{assignment.method}` |",
        "",
    ]

    total_union = sum(z.area_m2 for z in result.zones)
    total_clipped = geometry.validation.total_clipped_area_m2
    lines.extend(
        [
            "### Area metrics (dual view)",
            "",
            "| Metric | m² |",
            "| --- | ---: |",
            f"| Sum clipped bay areas (P2 grid) | {total_clipped:,.2f} |",
            f"| Sum INT zone union areas (P3) | {total_union:,.2f} |",
            f"| P2 mean slab coverage | {geometry.validation.mean_coverage_pct:.1f}% |",
            "",
        ]
    )

    lines.extend(_readiness_table(result))
    lines.extend(_zone_table(result, max_rows=30))
    lines.extend(_orphan_table(result))
    lines.extend(_manifest_section(result))

    if result.warnings:
        lines.extend(["## Warnings", ""])
        for warning in result.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    return "\n".join(lines)


def _readiness_table(result: IntZonePipelineResult) -> list[str]:
    lines = [
        "## Production readiness",
        "",
        "| Gate | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for gate in result.readiness:
        lines.append(f"| {gate.name} | **{gate.status}** | {gate.detail} |")
    lines.append("")
    return lines


def _zone_table(result: IntZonePipelineResult, max_rows: int) -> list[str]:
    lines = [
        "## INT zones (union of assigned faces)",
        "",
        "| INT | Faces | Union (m²) | Face sum (m²) | Clipped bay (m²) | Union/bay % |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    zones = sorted(result.zones, key=lambda z: int(z.label.split("-")[1]))
    for zone in zones[:max_rows]:
        lines.append(
            f"| {zone.label} | {zone.face_count} | {zone.area_m2:,.2f} | "
            f"{zone.face_sum_area_m2:,.2f} | {zone.clipped_bay_area_m2:,.2f} | "
            f"{zone.bay_coverage_pct:,.1f} |"
        )
    if len(zones) > max_rows:
        lines.append(f"| … | | | | | *({len(zones) - max_rows} more)* |")
    lines.append("")
    return lines


def _orphan_table(result: IntZonePipelineResult) -> list[str]:
    orphans = result.assignment.orphans
    if not orphans:
        return []
    lines = [
        "## Orphan faces",
        "",
        "| Face ID | Area (m²) | Reason | Nearest INT |",
        "| ---: | ---: | --- | --- |",
    ]
    for orphan in orphans[:20]:
        lines.append(
            f"| {orphan.face_id} | {orphan.area_m2:,.2f} | {orphan.reason} | "
            f"{orphan.nearest_int_label or '—'} |"
        )
    if len(orphans) > 20:
        lines.append(f"| … | | | *({len(orphans) - 20} more)* |")
    lines.append("")
    return lines


def _manifest_section(result: IntZonePipelineResult) -> list[str]:
    manifest = result.manifest
    if manifest is None:
        return []

    lines = [
        "## Manifest reconciliation",
        "",
        f"**Project:** {manifest.project or '—'}  ",
        f"**Transcription:** `{manifest.transcription_status}`  ",
        f"**Zone count:** {'PASS' if manifest.zone_count_match else 'REVIEW'} "
        f"({manifest.computed_zone_count} computed vs {manifest.expected_zone_count} expected)  ",
        "",
        "| INT | Computed (m²) | Manifest (m²) | Δ % | Status | Faces |",
        "| --- | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in manifest.comparisons[:30]:
        manifest_col = f"{row.manifest_area_sqm:,.2f}" if row.manifest_area_sqm is not None else "—"
        delta_col = f"{row.delta_pct:.3f}" if row.delta_pct is not None else "—"
        if row.within_tolerance is True:
            status = "PASS"
        elif row.within_tolerance is False:
            status = "FAIL"
        else:
            status = "SKIP"
        lines.append(
            f"| {row.label} | {row.computed_area_sqm:,.2f} | {manifest_col} | "
            f"{delta_col} | {status} | {row.face_count} |"
        )
    if len(manifest.comparisons) > 30:
        lines.append(f"| … | | | | | |")
    lines.append("")
    return lines


def write_int_zone_report(result: IntZonePipelineResult, path: Path | str) -> Path:
    """Write P3 markdown report to disk."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    body = render_int_zone_report_markdown(result)
    out.write_text(body, encoding="utf-8")
    return out
