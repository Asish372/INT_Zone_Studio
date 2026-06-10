from __future__ import annotations

import datetime
import hashlib
import shutil
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
DELIVERY = OUTPUT / "client_delivery"
DETECTION_DIR = OUTPUT / "detection_visualization"


def copy_files() -> None:
    for sub in ["J33A", "J33B", "S111_A", "QA_evidence"]:
        (DELIVERY / sub).mkdir(parents=True, exist_ok=True)

    # Primary client artifacts — schedules, DXF exports (no gate/validation reports)
    copy_map: dict[str, list[str]] = {
        "J33A": [
            "6276.S111-WAREHOUSE SLAB PLAN-Rev_F_int_schedule.xlsx",
            "6276.S111-WAREHOUSE SLAB PLAN-Rev_F_int_schedule.pdf",
            "6276.S111-WAREHOUSE SLAB PLAN-Rev_F_int_zones.dxf",
            "6276.S111-WAREHOUSE SLAB PLAN-Rev_F_annotated.dxf",
        ],
        "J33B": [
            "S111_J_int_schedule.xlsx",
            "S111_J_int_schedule.pdf",
            "S111_J_int_zones.dxf",
            "S111_J_annotated.dxf",
        ],
        "S111_A": [
            "S111_A_int_schedule.xlsx",
            "S111_A_int_schedule.pdf",
            "S111_A_int_zones.dxf",
            "S111_A_annotated.dxf",
        ],
    }

    for folder, files in copy_map.items():
        for name in files:
            source = OUTPUT / name
            if source.exists():
                shutil.copy2(source, DELIVERY / folder / source.name)

    # Primary visual deliverable — PDF only (PNGs are internal build artifacts)
    detection_pdf = DETECTION_DIR / "DETECTION_VISUALIZATION_REPORT.pdf"
    if detection_pdf.is_file():
        shutil.copy2(detection_pdf, DELIVERY / "DETECTION_VISUALIZATION_REPORT.pdf")

    # Internal QA only — gate tables, metrics, validation reports
    qa_internal = [
        "acceptance_readiness_report.md",
        "area_benchmark_template.md",
        "verification_summary.md",
    ]
    for name in qa_internal:
        src = ROOT / name
        if src.is_file():
            shutil.copy2(src, DELIVERY / "QA_evidence" / name)

    for pattern in [
        "*_int_zone_report.md",
        "*_results.xlsx",
        "*_semantic_validation_signoff.md",
    ]:
        for src in OUTPUT.glob(pattern):
            shutil.copy2(src, DELIVERY / "QA_evidence" / src.name)

    validation_dir = OUTPUT / "geometry_validation"
    if validation_dir.is_dir():
        qa_val = DELIVERY / "QA_evidence" / "geometry_validation"
        if qa_val.is_dir():
            shutil.rmtree(qa_val)
        shutil.copytree(
            validation_dir,
            qa_val,
            ignore=shutil.ignore_patterns("package"),
        )


def write_export_verification() -> None:
    lines = [
        "# Export Verification Evidence",
        "",
        f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| File | Headers | Data rows |",
        "| --- | --- | ---: |",
    ]
    for xlsx in sorted(OUTPUT.glob("*_int_schedule.xlsx")):
        sheet = openpyxl.load_workbook(xlsx, data_only=True).active
        headers = ", ".join(str(c.value) for c in sheet[1])
        rows = max(sheet.max_row - 1, 0)
        lines.append(f"| {xlsx.name} | {headers} | {rows} |")
    (DELIVERY / "QA_evidence" / "export_verification.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def build_manifest() -> None:
    entries: list[tuple[str, str, str]] = []
    for path in sorted(DELIVERY.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(DELIVERY).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        gate = "DB-5"
        if "_int_schedule.pdf" in rel:
            gate = "PDF/G7"
        elif "_int_schedule.xlsx" in rel or "_results.xlsx" in rel:
            gate = "DB-4/G4"
        elif "_int_zones.dxf" in rel or "_annotated.dxf" in rel:
            gate = "DB-4/DXF"
        elif "detection_visual" in rel or "DETECTION_VISUALIZATION" in rel:
            gate = "Primary visual deliverable"
        elif "_int_zone_report.md" in rel:
            gate = "Internal QA"
        elif "semantic_validation" in rel:
            gate = "Internal QA"
        elif "geometry_validation" in rel:
            gate = "Internal QA"
        elif "area_benchmark_template" in rel:
            gate = "DB-4/G5"
        elif "verification_summary" in rel:
            gate = "DB-4/G6"
        elif "acceptance_readiness_report" in rel:
            gate = "DB-5/G9"
        elif "export_verification" in rel:
            gate = "DB-4 evidence"
        entries.append((rel, digest, gate))

    lines = [
        "# DELIVERY_MANIFEST",
        "",
        f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Files",
        "",
        "| File | SHA-256 | Gate |",
        "| --- | --- | --- |",
    ]
    for rel, digest, gate in entries:
        lines.append(f"| {rel} | `{digest}` | {gate} |")

    lines.extend(
        [
            "",
            "## Release Notes",
            "",
            "- Product Owner sign-off: proxy baseline accepted for this environment run and recorded in acceptance report addendum.",
        ]
    )

    (DELIVERY / "DELIVERY_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    copy_files()
    write_export_verification()
    build_manifest()
    print("Delivery package assembled.")
