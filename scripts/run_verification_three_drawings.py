#!/usr/bin/env python3
"""Fresh verification run for the three production drawings."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from src.converter import ensure_dxf
from src.parser import get_modelspace, load_dxf
from src.units import scale_factor
from src.zone_engine import build_int_zone_pipeline, render_grid_frame_preview
from src.zone_engine.zone_coverage_report import write_int_zone_report

DRAWINGS = [
    {
        "label": "S111_A",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_A.dxf",
        "manifest": PROJECT_ROOT / "reference" / "s111_a_zones_manifest.yaml",
    },
    {
        "label": "S111_J (J33B)",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_J.dxf",
        "manifest": PROJECT_ROOT / "reference" / "j33b_zones_manifest.yaml",
    },
    {
        "label": "6276.S111-WAREHOUSE (J33A)",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf",
        "manifest": PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml",
    },
]

OUT_DIR = PROJECT_ROOT / "output" / "verification_run"


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def gate_summary(readiness) -> str:
    counts = {"PASS": 0, "REVIEW": 0, "FAIL": 0, "SKIP": 0}
    for gate in readiness:
        counts[gate.status] = counts.get(gate.status, 0) + 1
    parts = [f"{k}={v}" for k, v in counts.items() if v]
    return ", ".join(parts)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    config = load_yaml(PROJECT_ROOT / "config.yaml")
    zone_cfg = config.get("zone_engine", {})
    unit_scale = scale_factor(config.get("geometry", {}).get("drawing_unit", "mm"))

    rows: list[str] = []
    exit_code = 0

    for item in DRAWINGS:
        dxf_path = item["dxf"]
        manifest_path = item["manifest"]
        label = item["label"]

        print(f"\n{'=' * 60}\nProcessing: {label}\n{'=' * 60}")

        if not dxf_path.is_file():
            print(f"MISSING: {dxf_path}")
            rows.append(f"| {label} | MISSING | — | — | — | — |")
            exit_code = 1
            continue

        manifest = load_yaml(manifest_path)
        expected = manifest.get("zone_count_expected")

        # Also run via main.py for full export artifacts
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            str(dxf_path),
            "--zones",
            "--manifest",
            str(manifest_path),
        ]
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        if proc.returncode != 0:
            exit_code = max(exit_code, proc.returncode)

        doc = load_dxf(dxf_path)
        msp = get_modelspace(doc)
        result = build_int_zone_pipeline(
            msp,
            config,
            source_file=dxf_path.name,
            unit_scale_m=unit_scale,
            expected_int_count=int(expected) if expected is not None else None,
            manifest_path=manifest_path,
            zone_cfg=zone_cfg,
        )

        stem = dxf_path.stem.replace(" ", "_")
        report_path = OUT_DIR / f"{stem}_int_zone_report.md"
        preview_path = OUT_DIR / f"{stem}_int_zones_preview"
        write_int_zone_report(result, report_path)
        preview_files = render_grid_frame_preview(result.geometry, preview_path)

        assignment = result.assignment
        micro_faces = assignment.total_faces + assignment.sliver_count
        gates = gate_summary(result.readiness)
        gate_lines = "\n".join(
            f"  - **{g.status}** `{g.name}`: {g.detail}" for g in result.readiness
        )

        rows.append(
            "| "
            + " | ".join(
                [
                    label,
                    str(micro_faces),
                    str(assignment.total_faces),
                    str(len(result.zones)),
                    str(assignment.orphan_count),
                    gates,
                    "OK" if proc.returncode == 0 else f"exit {proc.returncode}",
                ]
            )
            + " |"
        )

        section = f"""## {label}

**Source:** `{dxf_path.name}`  
**Manifest:** `{manifest_path.name}`  
**Run:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

| Metric | Value |
| --- | ---: |
| Micro-faces detected (Stage 1) | {micro_faces} |
| Faces after sliver filter | {assignment.total_faces} |
| Slivers filtered | {assignment.sliver_count} |
| Faces assigned | {assignment.assigned_count} |
| **Orphan faces** | **{assignment.orphan_count}** |
| **INT zones generated** | **{len(result.zones)}** |
| Expected INT count | {expected or '—'} |

### Gate summary ({gates})

{gate_lines}

### Artifacts

- Report: `{report_path.relative_to(PROJECT_ROOT)}`
- Preview PNG: `{preview_files[1].relative_to(PROJECT_ROOT) if len(preview_files) > 1 else '—'}`
- Preview SVG: `{preview_files[0].relative_to(PROJECT_ROOT) if preview_files else '—'}`
- INT zone DXF: `output/{dxf_path.stem}_int_zones.dxf`
- INT schedule: `output/{dxf_path.stem}_int_schedule.xlsx`

"""
        (OUT_DIR / f"{stem}_summary.md").write_text(section, encoding="utf-8")
        print(section)

    summary = f"""# Three-Drawing Verification Results

**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  
**Python:** {sys.version.split()[0]}

| Drawing | Micro-faces | Faces (post-sliver) | INT zones | Orphans | Gates | Pipeline |
| --- | ---: | ---: | ---: | ---: | --- | --- |
{chr(10).join(rows)}

## Notes

- **Micro-faces** = total polygonized regions before sliver filtering.
- **Faces (post-sliver)** = regions used for INT assignment.
- Gate statuses: PASS / REVIEW / FAIL / SKIP per production readiness checks.
- Source DXF files from `output/.dxf_cache/` (original DWG not present in `input/`).

"""
    summary_path = OUT_DIR / "VERIFICATION_RESULTS.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"\nWrote {summary_path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
