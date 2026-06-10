#!/usr/bin/env python3
"""Generate client-verifiable INT zone validation report from pipeline metrics."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src.parser import get_modelspace, load_dxf
from src.units import scale_factor
from src.zone_engine import build_int_zone_pipeline
from src.zone_engine.models import IntZonePipelineResult

OUT_DIR = PROJECT_ROOT / "output" / "geometry_validation"
REPORT_PATH = OUT_DIR / "CLIENT_VALIDATION_REPORT.md"

DRAWINGS = [
    {
        "file_key": "S111_A",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_A.dxf",
        "manifest": PROJECT_ROOT / "reference" / "s111_a_zones_manifest.yaml",
    },
    {
        "file_key": "S111_J",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_J.dxf",
        "manifest": PROJECT_ROOT / "reference" / "j33b_zones_manifest.yaml",
    },
    {
        "file_key": "6276.S111-WAREHOUSE_SLAB_PLAN-Rev_F",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf",
        "manifest": PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml",
    },
]


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def overall_gate(gates: list) -> str:
    statuses = {g.status for g in gates}
    if "FAIL" in statuses:
        return "FAIL"
    if "REVIEW" in statuses:
        return "REVIEW"
    return "PASS"


def overall_reason(gates: list) -> str:
    parts = []
    for g in gates:
        if g.status in ("FAIL", "REVIEW"):
            parts.append(f"{g.name}={g.status}: {g.detail}")
    return "; ".join(parts) if parts else "All gates PASS."


def labels_in_detail(detail: str, labels: list[str]) -> list[str]:
    found = []
    for label in labels:
        if re.search(rf"\b{re.escape(label)}\b", detail):
            found.append(label)
    return found


def flagged_by_gate(result: IntZonePipelineResult) -> dict[str, set[str]]:
    flagged: dict[str, set[str]] = {}
    labels = [z.label for z in result.zones]
    for gate in result.readiness:
        if gate.status not in ("REVIEW", "FAIL"):
            continue
        matched = labels_in_detail(gate.detail, labels)
        if matched:
            flagged[gate.name] = set(matched)
        if gate.name == "manifest_area" and gate.status == "FAIL" and result.manifest:
            for cmp in result.manifest.comparisons:
                if cmp.within_tolerance is False:
                    flagged.setdefault(gate.name, set()).add(cmp.label)
    return flagged


def all_flagged(result: IntZonePipelineResult) -> set[str]:
    out: set[str] = set()
    for labels in flagged_by_gate(result).values():
        out.update(labels)
    return out


def classify_zone(label: str, zone, gate_hits: set[str], manifest_area: float | None) -> str:
    classes: list[str] = []
    if zone.face_count == 0:
        classes.append("empty")
    if "manifest_area" in gate_hits:
        classes.append("manifest_variance")
    if "face_sum_vs_union" in gate_hits:
        classes.append("overlap")
    if "union_vs_clipped_bay" in gate_hits:
        classes.append("low_bay_coverage")
    if "zone_face_coverage" in gate_hits and zone.face_count == 0:
        if "empty" not in classes:
            classes.append("empty")
    if "orphan_faces" in gate_hits:
        classes.append("orphan")
    return " / ".join(classes) if classes else "flagged"


def zone_gate_hits(label: str, flagged_map: dict[str, set[str]]) -> set[str]:
    hits: set[str] = set()
    for gate, labels in flagged_map.items():
        if label in labels:
            hits.add(gate)
    return hits


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def zoom_path(file_key: str, label: str) -> Path:
    return OUT_DIR / file_key / f"{file_key}_{label.replace('-', '_')}_flagged.png"


def process(item: dict, config: dict) -> dict:
    dxf = item["dxf"]
    manifest_path = item["manifest"]
    file_key = item["file_key"]
    manifest = load_yaml(manifest_path)
    manifest_by_label = {z["label"]: z for z in manifest.get("zones", [])}

    doc = load_dxf(dxf)
    msp = get_modelspace(doc)
    unit_scale = scale_factor(config.get("geometry", {}).get("drawing_unit", "mm"))
    expected = manifest.get("zone_count_expected")

    result = build_int_zone_pipeline(
        msp,
        config,
        source_file=dxf.name,
        unit_scale_m=unit_scale,
        expected_int_count=int(expected) if expected is not None else None,
        manifest_path=manifest_path,
    )

    a = result.assignment
    flagged_map = flagged_by_gate(result)
    flagged_labels = all_flagged(result)

    non_sliver = a.total_faces - a.sliver_count
    unassigned_non_orphan = non_sliver - a.assigned_count - a.orphan_count

    overlay = OUT_DIR / file_key / f"{file_key}_full_overlay.png"

    flagged_rows = []
    for zone in result.zones:
        if zone.label not in flagged_labels:
            continue
        hits = zone_gate_hits(zone.label, flagged_map)
        man = manifest_by_label.get(zone.label, {})
        zp = zoom_path(file_key, zone.label)
        flagged_rows.append(
            {
                "label": zone.label,
                "area_m2": zone.area_m2,
                "face_count": zone.face_count,
                "classification": classify_zone(
                    zone.label, zone, hits, man.get("area_sqm")
                ),
                "triggering_gates": ", ".join(sorted(hits)),
                "zoom": rel(zp) if zp.is_file() else "Metric not available from current run.",
            }
        )

    return {
        "file_key": file_key,
        "source_dxf": dxf.name,
        "manifest": manifest_path.name,
        "polygons_detected": a.total_faces,
        "slivers_filtered": a.sliver_count,
        "faces_non_sliver": non_sliver,
        "faces_assigned": a.assigned_count,
        "int_zones": len(result.zones),
        "expected_zones": expected,
        "flagged_int_zones": len(flagged_labels),
        "orphan_faces": a.orphan_count,
        "unassigned_non_orphan_faces": unassigned_non_orphan,
        "overall_gate": overall_gate(result.readiness),
        "overall_reason": overall_reason(result.readiness),
        "gates": [(g.name, g.status, g.detail) for g in result.readiness],
        "overlay": rel(overlay) if overlay.is_file() else "Metric not available from current run.",
        "flagged_rows": flagged_rows,
    }


def render_report(rows: list[dict], ts: str) -> str:
    lines = [
        "# INT Zone Validation Report — Client Deliverable",
        "",
        f"**Report date:** {ts}  ",
        "**Source:** DXF processing pipeline (`build_int_zone_pipeline`)  ",
        "**Evidence directory:** `output/geometry_validation/`  ",
        "",
        "---",
        "",
        "## Summary — All Files",
        "",
        "| File | Source DXF | Polygons Detected | INT Zones | Flagged INT Zones | Orphan Faces | Overall Gate |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for r in rows:
        lines.append(
            f"| {r['file_key']} | {r['source_dxf']} | {r['polygons_detected']} | "
            f"{r['int_zones']} | {r['flagged_int_zones']} | {r['orphan_faces']} | **{r['overall_gate']}** |"
        )

    lines.extend(["", "---", ""])

    for r in rows:
        lines.extend(
            [
                f"## {r['file_key']}",
                "",
                f"**Source DXF:** `{r['source_dxf']}`  ",
                f"**Manifest:** `{r['manifest']}`  ",
                "",
                "### 1. Computed metrics",
                "",
                "| # | Metric | Value |",
                "| ---: | --- | ---: |",
                f"| 1 | Total source polygons/faces detected | {r['polygons_detected']} |",
                f"| 2 | Slivers filtered (< threshold) | {r['slivers_filtered']} |",
                f"| 3 | Non-sliver faces | {r['faces_non_sliver']} |",
                f"| 4 | Faces assigned to INT zones | {r['faces_assigned']} |",
                f"| 5 | Total INT zones generated | {r['int_zones']} (expected {r['expected_zones']}) |",
                f"| 6 | Total flagged INT zones | {r['flagged_int_zones']} |",
                f"| 7 | Orphan / unassigned faces (no bay match) | {r['orphan_faces']} |",
                f"| 8 | Non-sliver faces not assigned (excl. orphans) | {r['unassigned_non_orphan_faces']} |",
                "",
                "### 2. Gate results",
                "",
                f"**Overall gate:** **{r['overall_gate']}**  ",
                f"**Reason:** {r['overall_reason']}",
                "",
                "| Gate | Result | Detail |",
                "| --- | --- | --- |",
            ]
        )
        for name, status, detail in r["gates"]:
            lines.append(f"| {name} | **{status}** | {detail} |")

        lines.extend(
            [
                "",
                "### 3. Flagged INT zones",
                "",
            ]
        )
        if r["flagged_rows"]:
            lines.extend(
                [
                    "| INT ID | Area (m²) | Face Count | Classification | Triggering Gate(s) |",
                    "| --- | ---: | ---: | --- | --- |",
                ]
            )
            for fr in r["flagged_rows"]:
                lines.append(
                    f"| {fr['label']} | {fr['area_m2']:.4f} | {fr['face_count']} | "
                    f"{fr['classification']} | {fr['triggering_gates']} |"
                )
        else:
            lines.append("No flagged INT zones.")

        lines.extend(
            [
                "",
                "### 4. Evidence files",
                "",
                f"**Full overlay:** `{r['overlay']}`",
                "",
                "**Flagged zone zoom images:**",
                "",
            ]
        )
        if r["flagged_rows"]:
            for fr in r["flagged_rows"]:
                lines.append(f"- {fr['label']}: `{fr['zoom']}`")
        else:
            lines.append("- None")

        lines.extend(["", "---", ""])

    lines.extend(
        [
            "## Metric definitions",
            "",
            "| Term | Definition |",
            "| --- | --- |",
            "| Polygons detected | Count of micro-face polygons from Stage 1 polygonize (`FaceAssignmentSummary.total_faces`). |",
            "| Slivers filtered | Faces below `sliver_max_m2` threshold, excluded from assignment. |",
            "| Orphan faces | Faces with no bay intersection above minimum threshold. |",
            "| Flagged INT zone | INT label referenced in at least one REVIEW or FAIL gate detail string. |",
            "| Overall gate | FAIL if any gate FAIL; else REVIEW if any gate REVIEW; else PASS. |",
            "",
            "## Classification key",
            "",
            "| Classification | Meaning |",
            "| --- | --- |",
            "| empty | Zero faces assigned; union area 0.00 m². |",
            "| overlap | `face_sum_vs_union` gate: sum of assigned face areas differs from union area by >2%. |",
            "| low_bay_coverage | `union_vs_clipped_bay` gate: union area <5% of clipped bay cell area. |",
            "| manifest_variance | `manifest_area` gate: computed area outside 0.05% of manifest value. |",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    config = load_yaml(PROJECT_ROOT / "config.yaml")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = [process(item, config) for item in DRAWINGS]
    REPORT_PATH.write_text(render_report(rows, ts), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
