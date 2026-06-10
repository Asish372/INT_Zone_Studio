#!/usr/bin/env python3
"""Verification phase: batch run + metrics table (no new product features)."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.converter import ensure_dxf
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.validation_diagnostics import diagnose_drawing


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


def main() -> int:
    config = load_config()
    input_dir = PROJECT_ROOT / "input"
    cache_dir = PROJECT_ROOT / "output" / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print("=== Step 2: Batch pipeline (main.py) ===\n")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), str(input_dir), "--batch"],
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    if result.returncode != 0:
        print(f"main.py exited with code {result.returncode}")

    cad_files = collect_cad_files(input_dir)
    metrics_rows: list[list[str]] = []

    for cad_path in cad_files:
        try:
            if cad_path.suffix.lower() == ".dwg":
                dxf_path = ensure_dxf(cad_path, cache_dir)
                note = "DWG via ODA"
            else:
                dxf_path = cad_path
                note = "native DXF"
            doc = load_dxf(dxf_path)
            msp = get_modelspace(doc)
            resolution = resolve_wall_layers(msp, config, auto_fallback=True)
            diag, _ = diagnose_drawing(cad_path, dxf_path, doc, config, note)
            metrics_rows.append(
                [
                    cad_path.name,
                    resolution.source,
                    str(diag.regions_detected),
                    f"{diag.total_detected_area_m2:.2f}",
                    str(diag.open_endpoints_after_close),
                    str(diag.invalid_polygon_count),
                    str(diag.gaps_closed),
                ]
            )
        except Exception as exc:
            metrics_rows.append([cad_path.name, "error", "—", "—", "—", "—", str(exc)])

    lines = [
        "# Batch Verification Summary",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Pipeline metrics (detector)",
        "",
        format_md_table(
            [
                "Drawing",
                "Layer source",
                "Detected regions",
                "Total area (m²)",
                "Open endpoints (after close)",
                "Invalid polygons",
                "Gaps closed",
            ],
            metrics_rows,
        ),
        "## Step 3 — Recall measurement (manual)",
        "",
        "Fill **AutoCAD Regions** after manual boundary count / client reference.",
        "Target: **Recall > 90%**.",
        "",
        format_md_table(
            ["Drawing", "AutoCAD Regions", "Detected", "Recall %"],
            [
                ["S111_A.dwg", "?", str(next((r[2] for r in metrics_rows if "S111_A" in r[0]), "?")), "?"],
                ["S111_J.dwg", "?", str(next((r[2] for r in metrics_rows if "S111_J" in r[0]), "?")), "?"],
                [
                    "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg",
                    "?",
                    str(
                        next(
                            (r[2] for r in metrics_rows if "WAREHOUSE" in r[0] or "6276" in r[0]),
                            "?",
                        )
                    ),
                    "?",
                ],
            ],
        ),
        "",
        "## Step 5 — Area benchmark (manual)",
        "",
        "See `area_benchmark_template.md` — measure 5–10 regions in AutoCAD vs detector Excel.",
        "",
    ]

    out_path = PROJECT_ROOT / "verification_summary.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
