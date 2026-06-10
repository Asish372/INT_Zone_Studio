#!/usr/bin/env python3
"""Generate PDF INT zone verification reports for the three production drawings."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
VERIFY = OUTPUT / "verification_run"

REPORTS = [
    {
        "title": "S111_A — INT Zone Detection Report",
        "md": OUTPUT / "S111_A_int_zone_report.md",
        "preview": VERIFY / "S111_A_int_zones_preview.png",
        "pdf": OUTPUT / "S111_A_int_zone_report.pdf",
    },
    {
        "title": "S111_J (J33B) — INT Zone Detection Report",
        "md": OUTPUT / "S111_J_int_zone_report.md",
        "preview": VERIFY / "S111_J_int_zones_preview.png",
        "pdf": OUTPUT / "S111_J_int_zone_report.pdf",
    },
    {
        "title": "6276.S111-WAREHOUSE (J33A) — INT Zone Detection Report",
        "md": OUTPUT / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F_int_zone_report.md",
        "preview": VERIFY / "6276.png",
        "pdf": OUTPUT / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F_int_zone_report.pdf",
    },
]


def _parse_md_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    i = start
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|"):
            break
        if re.match(r"^\|\s*---", line):
            i += 1
            continue
        cells = [c.strip().replace("**", "") for c in line.strip("|").split("|")]
        rows.append(cells)
        i += 1
    return rows, i


def _status_color(status: str):
    status = status.upper()
    if status == "PASS":
        return colors.HexColor("#1e7e34")
    if status == "FAIL":
        return colors.HexColor("#c0392b")
    if status == "REVIEW":
        return colors.HexColor("#d68910")
    return colors.HexColor("#555555")


def _make_table(rows: list[list[str]], col_widths: list[float] | None = None) -> Table:
    if not rows:
        return Table([["—"]])
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if rows and rows[0] and "Status" in rows[0]:
        status_col = rows[0].index("Status")
        for r in range(1, len(rows)):
            if status_col < len(rows[r]):
                style.append(
                    ("TEXTCOLOR", (status_col, r), (status_col, r), _status_color(rows[r][status_col]))
                )
                style.append(("FONTNAME", (status_col, r), (status_col, r), "Helvetica-Bold"))
    table.setStyle(TableStyle(style))
    return table


def md_to_pdf(md_path: Path, pdf_path: Path, title: str, preview_path: Path | None) -> None:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=8,
        textColor=colors.HexColor("#1a252f"),
    )
    h2_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#2c3e50"),
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontSize=8,
        leftIndent=12,
        spaceAfter=2,
    )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    story: list = []

    story.append(Paragraph(title, title_style))

    for line in lines[:6]:
        if line.startswith("**") and ":" in line:
            story.append(Paragraph(line.replace("**", ""), meta_style))

    story.append(Spacer(1, 6))

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("## "):
            story.append(Paragraph(line[3:], h2_style))
            i += 1
            continue

        if line.startswith("### "):
            story.append(Paragraph(line[4:], h2_style))
            i += 1
            continue

        if line.startswith("|"):
            rows, i = _parse_md_table(lines, i)
            if rows:
                story.append(_make_table(rows))
                story.append(Spacer(1, 6))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"• {line[2:]}", bullet_style))
            i += 1
            continue

        if line.startswith("**") and not line.startswith("|"):
            plain = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
            plain = plain.replace("`", "")
            story.append(Paragraph(plain, meta_style))
            i += 1
            continue

        i += 1

    if preview_path and preview_path.is_file():
        story.append(Spacer(1, 10))
        story.append(Paragraph("Grid Frame Preview", h2_style))
        img = Image(str(preview_path))
        max_w = A4[0] - 28 * mm
        max_h = 180 * mm
        scale = min(max_w / img.drawWidth, max_h / img.drawHeight, 1.0)
        img.drawWidth *= scale
        img.drawHeight *= scale
        story.append(img)

    doc.build(story)


def main() -> None:
    generated: list[Path] = []
    for item in REPORTS:
        md = item["md"]
        if not md.is_file():
            raise SystemExit(f"Missing report markdown: {md}")
        preview = item["preview"] if item["preview"].is_file() else None
        md_to_pdf(md, item["pdf"], item["title"], preview)
        generated.append(item["pdf"])
        print(f"Generated: {item['pdf']}")

        verify_copy = VERIFY / item["pdf"].name
        if verify_copy != item["pdf"]:
            import shutil

            shutil.copy2(item["pdf"], verify_copy)
            print(f"Copied: {verify_copy}")

    print(f"\nDone — {len(generated)} PDF report(s).")


if __name__ == "__main__":
    main()
