#!/usr/bin/env python3
"""P1 — Block detection coverage baseline and miss taxonomy report."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.converter import ensure_dxf, find_oda_converter
from src.detection_coverage import (
    analyze_drawing_coverage,
    render_coverage_report_markdown,
    write_coverage_excel,
    write_coverage_log,
)
from src.parser import load_dxf


def load_config() -> dict:
    path = PROJECT_ROOT / "config.yaml"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def collect_cad_files(input_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.dwg", "*.DWG", "*.dxf", "*.DXF"):
        files.extend(input_dir.glob(pattern))
    return sorted({f.resolve() for f in files})


def setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"coverage_run_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_path


def main() -> int:
    config = load_config()
    input_dir = PROJECT_ROOT / config.get("input", {}).get("input_dir", "./input")
    output_dir = PROJECT_ROOT / config.get("output", {}).get("output_dir", "./output")
    cache_dir = output_dir / ".dxf_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    log_dir = PROJECT_ROOT / config.get("logging", {}).get("log_dir", "./logs")
    log_path = setup_logging(Path(log_dir))
    logger = logging.getLogger(__name__)

    cad_files = collect_cad_files(input_dir)
    if not cad_files:
        logger.error("No DWG/DXF files in %s", input_dir)
        return 1

    results = []
    for cad_path in cad_files:
        logger.info("Analyzing coverage: %s", cad_path.name)
        try:
            if cad_path.suffix.lower() == ".dwg":
                oda = find_oda_converter()
                if not oda:
                    logger.error("ODA File Converter not found for %s", cad_path.name)
                    continue
                dxf_path = ensure_dxf(cad_path, cache_dir)
            else:
                dxf_path = cad_path

            doc = load_dxf(dxf_path)
            result = analyze_drawing_coverage(
                drawing_name=cad_path.name,
                source_path=str(cad_path),
                dxf_path=str(dxf_path),
                doc=doc,
                config=config,
            )
            results.append(result)
            logger.info(
                "  detected=%d missed=%d at_risk=%d open_after=%d",
                result.detected_count,
                result.missed_count,
                result.at_risk_count,
                result.open_endpoints_after_close,
            )
        except Exception as exc:
            logger.exception("Failed %s: %s", cad_path.name, exc)

    if not results:
        logger.error("No coverage results produced")
        return 1

    report_path = PROJECT_ROOT / "detection_coverage_report.md"
    excel_path = PROJECT_ROOT / "coverage_metrics.xlsx"
    json_log_path = Path(log_dir) / f"coverage_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report_path.write_text(
        render_coverage_report_markdown(results, config), encoding="utf-8"
    )
    write_coverage_excel(excel_path, results)
    write_coverage_log(json_log_path, results, config)

    print(f"\nWrote {report_path}")
    print(f"Wrote {excel_path}")
    print(f"Wrote {json_log_path}")
    print(f"Log saved to: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
