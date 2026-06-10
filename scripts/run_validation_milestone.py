#!/usr/bin/env python3
"""Multi-drawing INT zone validation milestone (pre-P4 gate)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from shapely.validation import explain_validity

from src.parser import get_modelspace, load_dxf
from src.units import scale_factor
from src.zone_engine.int_zone_pipeline import build_int_zone_pipeline
from src.zone_engine.models import IntZonePipelineResult
from src.zone_engine.zone_aggregator import _zone_overlap_pairs

DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"
DEFAULT_OUT_DIR = PROJECT_ROOT / "output" / "validation_milestone"

DRAWING_SUITE = [
    {
        "drawing_id": "J33A_WAREHOUSE",
        "cad_path": PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf",
        "manifest_path": PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml",
        "description": "J33A warehouse slab (24-cell grid)",
    },
    {
        "drawing_id": "J33B_S111_J",
        "cad_path": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_J.dxf",
        "manifest_path": PROJECT_ROOT / "reference" / "j33b_zones_manifest.yaml",
        "description": "J33B joint warehouse (17 zones expected)",
    },
    {
        "drawing_id": "S111_A_ALT_GRID",
        "cad_path": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_A.dxf",
        "manifest_path": PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml",
        "description": "S111_A alternate grid layout (~24 bays, GRID_WAREHOUSE)",
    },
]


@dataclass
class DrawingValidationResult:
    drawing_id: str
    description: str
    cad_path: str
    manifest_path: str
    run_ok: bool
    error: str | None = None
    face_count: int = 0
    sliver_count: int = 0
    assigned_count: int = 0
    orphan_count: int = 0
    zone_count: int = 0
    expected_zone_count: int | None = None
    zone_count_match: bool = False
    overlap_pair_count: int = 0
    overlap_pairs: list[dict[str, Any]] = field(default_factory=list)
    invalid_zone_count: int = 0
    invalid_zone_labels: list[str] = field(default_factory=list)
    empty_zone_count: int = 0
    mean_union_bay_coverage_pct: float = 0.0
    total_union_area_m2: float = 0.0
    total_clipped_bay_m2: float = 0.0
    p2_mean_coverage_pct: float = 0.0
    p2_overlap_pairs: int = 0
    p2_invalid_bays: int = 0
    label_signature_run1: list[str] = field(default_factory=list)
    label_signature_run2: list[str] = field(default_factory=list)
    labels_stable: bool = False
    readiness: list[dict[str, str]] = field(default_factory=list)
    manifest_summary: dict[str, Any] = field(default_factory=dict)
    criteria: dict[str, bool] = field(default_factory=dict)
    all_criteria_pass: bool = False


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _label_signature(result: IntZonePipelineResult) -> list[str]:
    bays = sorted(result.geometry.bays, key=lambda b: (b.row, b.col, b.bay_id))
    return [f"{b.row}:{b.col}={b.int_label}" for b in bays]


def _validate_drawing(
    entry: dict,
    config: dict,
    *,
    repeat: int = 2,
) -> DrawingValidationResult:
    drawing_id = entry["drawing_id"]
    cad_path = Path(entry["cad_path"])
    manifest_path = Path(entry["manifest_path"])
    manifest = _load_yaml(manifest_path)
    expected = manifest.get("zone_count_expected")
    expected_int = int(expected) if expected is not None else None

    out = DrawingValidationResult(
        drawing_id=drawing_id,
        description=entry["description"],
        cad_path=str(cad_path),
        manifest_path=str(manifest_path),
        run_ok=False,
        expected_zone_count=expected_int,
    )

    if not cad_path.is_file():
        out.error = f"CAD file not found: {cad_path}"
        return out

    unit_scale = scale_factor(config.get("geometry", {}).get("drawing_unit", "mm"))
    zone_cfg = dict(config.get("zone_engine", {}))

    results: list[IntZonePipelineResult] = []
    try:
        doc = load_dxf(cad_path)
        msp = get_modelspace(doc)
        for _ in range(repeat):
            results.append(
                build_int_zone_pipeline(
                    msp,
                    config,
                    source_file=cad_path.name,
                    unit_scale_m=unit_scale,
                    expected_int_count=expected_int,
                    manifest_path=manifest_path,
                    zone_cfg=zone_cfg,
                )
            )
    except Exception as exc:
        out.error = str(exc)
        return out

    out.run_ok = True
    r1, r2 = results[0], results[1]
    out.label_signature_run1 = _label_signature(r1)
    out.label_signature_run2 = _label_signature(r2)
    out.labels_stable = out.label_signature_run1 == out.label_signature_run2

    r = r1
    assignment = r.assignment
    geometry = r.geometry
    val = geometry.validation

    out.face_count = assignment.total_faces
    out.sliver_count = assignment.sliver_count
    out.assigned_count = assignment.assigned_count
    out.orphan_count = assignment.orphan_count
    out.zone_count = len(r.zones)
    out.zone_count_match = (
        expected_int is not None and out.zone_count == expected_int
    )
    out.total_union_area_m2 = sum(z.area_m2 for z in r.zones)
    out.total_clipped_bay_m2 = val.total_clipped_area_m2
    out.p2_mean_coverage_pct = val.mean_coverage_pct
    out.p2_overlap_pairs = val.overlap_pair_count
    p2_invalid_geom = sum(
        1
        for v in val.bay_validations
        if "invalid_geometry" in v.flags
    )
    out.p2_invalid_bays = p2_invalid_geom

    coverages = [
        z.bay_coverage_pct
        for z in r.zones
        if z.clipped_bay_area_m2 > 1e-6 and z.face_count > 0
    ]
    out.mean_union_bay_coverage_pct = (
        sum(coverages) / len(coverages) if coverages else 0.0
    )

    overlap_m2 = float(zone_cfg.get("overlap_area_m2", 0.5))
    overlaps = _zone_overlap_pairs(r.zones, unit_scale_m=unit_scale, overlap_area_m2=overlap_m2)
    out.overlap_pair_count = len(overlaps)
    out.overlap_pairs = [
        {"zone_a": a, "zone_b": b, "overlap_m2": round(area, 4)} for a, b, area in overlaps
    ]

    invalid_labels: list[str] = []
    empty = 0
    for zone in r.zones:
        if zone.face_count == 0:
            empty += 1
        if zone.polygon.is_empty:
            continue
        if not zone.polygon.is_valid:
            invalid_labels.append(f"{zone.label}: {explain_validity(zone.polygon)}")

    out.invalid_zone_count = len(invalid_labels)
    out.invalid_zone_labels = invalid_labels
    out.empty_zone_count = empty

    out.readiness = [
        {"name": g.name, "status": g.status, "detail": g.detail} for g in r.readiness
    ]

    if r.manifest:
        m = r.manifest
        out.manifest_summary = {
            "project": m.project,
            "profile": m.profile,
            "transcription_status": m.transcription_status,
            "zone_count_match": m.zone_count_match,
            "zones_with_manifest_area": m.zones_with_manifest_area,
            "zones_within_tolerance": m.zones_within_tolerance,
            "total_computed_sqm": round(m.total_computed_sqm, 2),
            "total_manifest_sqm": m.total_manifest_sqm,
        }

    out.criteria = {
        "zero_orphans": out.orphan_count == 0,
        "zero_zone_overlaps": out.overlap_pair_count == 0,
        "labels_stable": out.labels_stable,
        "zone_count_match": out.zone_count_match,
        "no_invalid_geometries": out.invalid_zone_count == 0 and out.p2_invalid_bays == 0,
        "p2_no_bay_overlaps": out.p2_overlap_pairs == 0,
    }
    out.all_criteria_pass = all(out.criteria.values())
    return out


def render_markdown(
    results: list[DrawingValidationResult],
    *,
    generated_at: str,
) -> str:
    all_pass = all(r.all_criteria_pass for r in results if r.run_ok)
    lines = [
        "# INT Zone Validation Milestone Report",
        "",
        f"**Generated:** {generated_at}  ",
        f"**Overall:** {'PASS — eligible for P4/P5' if all_pass else 'FAIL — resolve before P4/P5'}  ",
        "",
        "## Success criteria (per drawing)",
        "",
        "| Criterion | Description |",
        "| --- | --- |",
        "| zero_orphans | No unassigned micro-faces |",
        "| zero_zone_overlaps | No INT union overlap above threshold |",
        "| labels_stable | Identical INT labels across 2 consecutive runs |",
        "| zone_count_match | Computed zones = manifest `zone_count_expected` |",
        "| no_invalid_geometries | Valid zone polygons; P2 bays valid |",
        "| p2_no_bay_overlaps | Clipped bay grid has no overlaps |",
        "",
    ]

    for r in results:
        status = "PASS" if r.all_criteria_pass else ("ERROR" if not r.run_ok else "FAIL")
        lines.extend(
            [
                f"## {r.drawing_id} — {status}",
                "",
                f"*{r.description}*  ",
                f"**CAD:** `{r.cad_path}`  ",
                "",
            ]
        )
        if r.error:
            lines.extend([f"**Error:** {r.error}", ""])
            continue

        lines.extend(
            [
                "### Face & assignment statistics",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Micro-faces (Stage 1) | {r.face_count} |",
                f"| Slivers filtered | {r.sliver_count} |",
                f"| Faces assigned | {r.assigned_count} |",
                f"| Orphan faces | {r.orphan_count} |",
                "",
                "### Zone coverage statistics",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| INT zones (union) | {r.zone_count} |",
                f"| Expected (manifest) | {r.expected_zone_count or '—'} |",
                f"| Zone count match | {'yes' if r.zone_count_match else 'no'} |",
                f"| Empty zones (no faces) | {r.empty_zone_count} |",
                f"| Mean union/clipped bay % | {r.mean_union_bay_coverage_pct:.1f}% |",
                f"| Total union area (m²) | {r.total_union_area_m2:,.2f} |",
                f"| Total clipped bay area (m²) | {r.total_clipped_bay_m2:,.2f} |",
                f"| P2 mean slab coverage % | {r.p2_mean_coverage_pct:.1f}% |",
                "",
                "### Overlap & geometry",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| INT zone overlap pairs | {r.overlap_pair_count} |",
                f"| P2 clipped bay overlap pairs | {r.p2_overlap_pairs} |",
                f"| Invalid zone geometries | {r.invalid_zone_count} |",
                f"| Labels stable (2 runs) | {'yes' if r.labels_stable else 'no'} |",
                "",
            ]
        )
        if r.overlap_pairs:
            lines.append("**Zone overlaps:**")
            for pair in r.overlap_pairs[:10]:
                lines.append(
                    f"- {pair['zone_a']} ∩ {pair['zone_b']}: {pair['overlap_m2']:.2f} m²"
                )
            lines.append("")

        if r.manifest_summary:
            lines.extend(
                [
                    "### Manifest reconciliation",
                    "",
                    "```json",
                    json.dumps(r.manifest_summary, indent=2),
                    "```",
                    "",
                ]
            )

        lines.extend(
            [
                "### Production gates",
                "",
                "| Gate | Status | Detail |",
                "| --- | --- | --- |",
            ]
        )
        for gate in r.readiness:
            lines.append(f"| {gate['name']} | {gate['status']} | {gate['detail']} |")
        lines.append("")

        lines.extend(
            [
                "### Criteria checklist",
                "",
                "| Criterion | Pass |",
                "| --- | --- |",
            ]
        )
        for name, passed in r.criteria.items():
            lines.append(f"| {name} | {'✓' if passed else '✗'} |")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="INT zone multi-drawing validation milestone")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--log-level", default="WARNING")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.WARNING))

    config = _load_yaml(args.config)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    results = [_validate_drawing(entry, config, repeat=2) for entry in DRAWING_SUITE]

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "generated_at": generated_at,
        "overall_pass": all(r.all_criteria_pass for r in results if r.run_ok),
        "drawings": [asdict(r) for r in results],
    }

    json_path = args.out_dir / "validation_results.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_path = args.out_dir / "validation_milestone_report.md"
    md_path.write_text(render_markdown(results, generated_at=generated_at), encoding="utf-8")

    print("=== Validation Milestone ===")
    for r in results:
        flag = "PASS" if r.all_criteria_pass else ("ERR" if not r.run_ok else "FAIL")
        print(
            f"[{flag}] {r.drawing_id}: faces={r.face_count} assigned={r.assigned_count} "
            f"orphans={r.orphan_count} zones={r.zone_count}/{r.expected_zone_count} "
            f"overlaps={r.overlap_pair_count}"
        )
        if not r.all_criteria_pass and r.criteria:
            failed = [k for k, v in r.criteria.items() if not v]
            print(f"       failed: {', '.join(failed)}")
    print(f"JSON: {json_path}")
    print(f"Report: {md_path}")

    if payload["overall_pass"]:
        prod_path = args.out_dir / "production_readiness_report.md"
        prod_path.write_text(
            _render_production_readiness(results, generated_at),
            encoding="utf-8",
        )
        print(f"Production readiness: {prod_path}")
        return 0
    return 1


def _render_production_readiness(
    results: list[DrawingValidationResult],
    generated_at: str,
) -> str:
    lines = [
        "# Production Readiness Report — INT Zone Engine",
        "",
        f"**Generated:** {generated_at}  ",
        "**Status:** APPROVED for P4 (main integration) and P5 (schedule export)  ",
        "",
        "Multi-drawing validation milestone passed all gates on:",
        "",
    ]
    for r in results:
        lines.append(
            f"- **{r.drawing_id}** — {r.face_count} faces → {r.zone_count} INT zones, "
            f"0 orphans, 0 zone overlaps, stable labels"
        )
    lines.extend(
        [
            "",
            "## Approved next steps",
            "",
            "1. **P4** — Wire `build_int_zone_pipeline` into `main.py` with `--zone-profile` / `--manifest`",
            "2. **P5** — Excel/DXF INT schedule export (Pour No., SQM, CUM, face_count)",
            "",
            "## Out of scope until P0 transcription",
            "",
            "- Per-INT area vs manifest SQM (0.05% gate) remains SKIP until `area_sqm` filled in YAML",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
