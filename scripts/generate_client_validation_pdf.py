#!/usr/bin/env python3
"""Build uniform client validation PDF and ZIP package."""

from __future__ import annotations

import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT_DIR = PROJECT_ROOT / "output" / "geometry_validation"
PACKAGE_DIR = OUT_DIR / "package"
MD_PATH = OUT_DIR / "CLIENT_VALIDATION_REPORT.md"
PDF_PATH = OUT_DIR / "CLIENT_VALIDATION_REPORT.pdf"
PACKAGE_PDF = PACKAGE_DIR / "CLIENT_VALIDATION_REPORT.pdf"
ZIP_PATH = OUT_DIR / "CLIENT_VALIDATION_PACKAGE.zip"

PAGE_W, PAGE_H = A4
MARGIN = 14 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

# Uniform package IDs (same folder name in ZIP for every drawing)
DRAWING_PACKAGE = [
    {
        "package_id": "S111_A",
        "legacy_key": "S111_A",
        "title": "S111_A",
    },
    {
        "package_id": "S111_J",
        "title": "S111_J (J33B)",
        "legacy_key": "S111_J",
    },
    {
        "package_id": "J33A_WAREHOUSE",
        "title": "6276.S111-WAREHOUSE (J33A)",
        "legacy_key": "6276.S111-WAREHOUSE_SLAB_PLAN-Rev_F",
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
    s = status.upper()
    if s == "PASS":
        return colors.HexColor("#1e7e34")
    if s == "FAIL":
        return colors.HexColor("#c0392b")
    if s == "REVIEW":
        return colors.HexColor("#d68910")
    return colors.HexColor("#333333")


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _cell_styles() -> tuple[ParagraphStyle, ParagraphStyle, ParagraphStyle]:
    styles = getSampleStyleSheet()
    header = ParagraphStyle(
        "CellHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    body = ParagraphStyle(
        "CellBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#222222"),
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    body_center = ParagraphStyle(
        "CellBodyCenter",
        parent=body,
        alignment=TA_CENTER,
    )
    return header, body, body_center


def _infer_col_widths(header: list[str]) -> list[float]:
    """Column widths that fit CONTENT_W and match table semantics."""
    h = [c.lower() for c in header]
    n = len(header)

    if n == 7 and "overall gate" in h:
        # Executive summary — must sum to CONTENT_W
        return [30 * mm, 26 * mm, 20 * mm, 14 * mm, 20 * mm, 16 * mm, CONTENT_W - 126 * mm]

    if n == 3 and h[0] in ("#", "no", "no.") or h[1] == "metric":
        # Computed metrics: # | Metric | Value
        return [12 * mm, CONTENT_W - 44 * mm, 32 * mm]

    if n == 3 and h[0] == "gate":
        # Gate | Result | Detail
        return [36 * mm, 22 * mm, CONTENT_W - 58 * mm]

    if n == 3 and h[0] == "term":
        return [42 * mm, CONTENT_W - 42 * mm]

    if n == 2 and h[0] == "classification":
        return [36 * mm, CONTENT_W - 36 * mm]

    if n == 5 and h[0] == "int id":
        return [16 * mm, 18 * mm, 18 * mm, 28 * mm, CONTENT_W - 80 * mm]

    if n == 2:
        return [48 * mm, CONTENT_W - 48 * mm]

    if n == 3:
        return [40 * mm, 30 * mm, CONTENT_W - 70 * mm]

    if n == 5:
        return [18 * mm, 22 * mm, 18 * mm, 30 * mm, CONTENT_W - 88 * mm]

    # Fallback: equal split
    w = CONTENT_W / n
    return [w] * n


def _styled_table(rows: list[list[str]], col_widths: list[float] | None = None) -> Table:
    if not rows:
        return Table([[Paragraph("—", _cell_styles()[1])]])

    header_style, body_style, body_center = _cell_styles()
    if col_widths is None:
        col_widths = _infer_col_widths(rows[0])

    # Normalise row width
    ncols = len(rows[0])
    norm_rows: list[list[str]] = []
    for row in rows:
        cells = list(row) + [""] * (ncols - len(row))
        norm_rows.append(cells[:ncols])

    para_rows: list[list] = []
    header = norm_rows[0]
    result_col = header.index("Result") if "Result" in header else -1
    gate_col = header.index("Overall Gate") if "Overall Gate" in header else -1

    for r_idx, row in enumerate(norm_rows):
        style = header_style if r_idx == 0 else body_style
        para_row = []
        for c_idx, cell in enumerate(row):
            text = _escape_xml(cell)
            if r_idx == 0:
                para_row.append(Paragraph(text, header_style))
            elif c_idx == 0 and header[0] in ("#", "INT ID"):
                para_row.append(Paragraph(text, body_center))
            elif c_idx == result_col or c_idx == gate_col:
                color = _status_color(cell)
                para_row.append(
                    Paragraph(
                        f'<font color="{color.hexval()}"><b>{text}</b></font>',
                        body_center,
                    )
                )
            elif c_idx == 1 and header[1] == "Metric":
                para_row.append(Paragraph(text, body_style))
            elif c_idx == 2 and len(header) == 3 and header[2] in ("Value", "Detail"):
                align_style = body_center if header[2] == "Value" else body_style
                para_row.append(Paragraph(text, align_style))
            else:
                para_row.append(Paragraph(text, body_style))
        para_rows.append(para_row)

    table = Table(para_rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    table.setStyle(TableStyle(style_cmds))
    return table


def _scaled_image(path: Path, max_w: float, max_h: float) -> Image:
    img = Image(str(path))
    scale = min(max_w / img.drawWidth, max_h / img.drawHeight, 1.0)
    img.drawWidth *= scale
    img.drawHeight *= scale
    img.hAlign = "CENTER"
    return img


def _page_footer(canvas, doc):
    canvas.saveState()
    ts = getattr(doc, "generation_timestamp", "")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(PAGE_W / 2, 8 * mm, f"Page {canvas.getPageNumber()}")
    canvas.drawRightString(PAGE_W - MARGIN, 8 * mm, ts)
    canvas.drawString(MARGIN, 8 * mm, "INT Zone Validation Report")
    canvas.restoreState()


def _legacy_overlay(legacy_key: str) -> Path:
    return OUT_DIR / legacy_key / f"{legacy_key}_full_overlay.png"


def _legacy_flagged(legacy_key: str, int_label: str) -> Path:
    return OUT_DIR / legacy_key / f"{legacy_key}_{int_label.replace('-', '_')}_flagged.png"


def _package_overlay(package_id: str) -> Path:
    return PACKAGE_DIR / package_id / "full_overlay.png"


def _package_flagged(package_id: str, int_label: str) -> Path:
    return PACKAGE_DIR / package_id / "flagged" / f"{int_label}.png"


def _clean_old_outputs() -> None:
    if ZIP_PATH.is_file():
        ZIP_PATH.unlink()
    if PDF_PATH.is_file():
        PDF_PATH.unlink()
    if PACKAGE_DIR.is_dir():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)


def _parse_flagged_from_md(text: str) -> dict[str, list[str]]:
    """Return {section_title: [INT-2, INT-3, ...]}."""
    result: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("## ") and line[3:].strip() not in (
            "Summary — All Files",
            "Metric definitions",
            "Classification key",
        ):
            current = line[3:].strip()
            result.setdefault(current, [])
        m = re.match(r"- (INT-\d+):", line.strip())
        if m and current:
            result.setdefault(current, []).append(m.group(1))
    return result


def _section_to_package_id(section: str) -> str | None:
    for item in DRAWING_PACKAGE:
        if item["title"] == section or item["package_id"] == section:
            return item["package_id"]
        if item["legacy_key"] in section:
            return item["package_id"]
    if section == "S111_A":
        return "S111_A"
    if section == "S111_J":
        return "S111_J"
    if "6276" in section or "WAREHOUSE" in section:
        return "J33A_WAREHOUSE"
    return None


def stage_uniform_package(md_text: str) -> dict[str, dict]:
    """Copy legacy PNGs into uniform package layout. Returns manifest per drawing."""
    flagged_map = _parse_flagged_from_md(md_text)
    manifest: dict[str, dict] = {}

    for item in DRAWING_PACKAGE:
        pid = item["package_id"]
        legacy = item["legacy_key"]
        dest_dir = PACKAGE_DIR / pid
        flagged_dir = dest_dir / "flagged"
        flagged_dir.mkdir(parents=True, exist_ok=True)

        src_overlay = _legacy_overlay(legacy)
        dest_overlay = _package_overlay(pid)
        if src_overlay.is_file():
            shutil.copy2(src_overlay, dest_overlay)
        else:
            dest_overlay = Path()

        flagged_labels: list[str] = []
        flagged_files: list[Path] = []
        for section, labels in flagged_map.items():
            sid = _section_to_package_id(section)
            if sid != pid:
                continue
            for label in labels:
                src = _legacy_flagged(legacy, label)
                dest = _package_flagged(pid, label)
                if src.is_file():
                    shutil.copy2(src, dest)
                    flagged_labels.append(label)
                    flagged_files.append(dest)

        manifest[pid] = {
            "title": item["title"],
            "overlay": dest_overlay if dest_overlay.is_file() else None,
            "flagged": list(zip(flagged_labels, flagged_files)),
        }

    if MD_PATH.is_file():
        shutil.copy2(MD_PATH, PACKAGE_DIR / "CLIENT_VALIDATION_REPORT.md")

    readme = PACKAGE_DIR / "README.txt"
    readme.write_text(
        "\n".join(
            [
                "INT Zone Validation Package",
                "===========================",
                "",
                "Contents:",
                "  CLIENT_VALIDATION_REPORT.pdf  — Client report with embedded evidence",
                "  CLIENT_VALIDATION_REPORT.md   — Source markdown report",
                "  S111_A/                       — Drawing evidence",
                "  S111_J/                       — Drawing evidence",
                "  J33A_WAREHOUSE/               — Drawing evidence",
                "",
                "Each drawing folder contains:",
                "  full_overlay.png              — Full-plan overlay",
                "  flagged/INT-XX.png            — Zoom evidence per flagged zone",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return manifest


def build_pdf(md_path: Path, pdf_path: Path, manifest: dict[str, dict], generation_ts: str) -> None:
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    styles = getSampleStyleSheet()
    cover_title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=26,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.HexColor("#1a252f"),
    )
    cover_sub = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=6,
    )
    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=14,
        spaceBefore=8,
        spaceAfter=8,
        textColor=colors.HexColor("#1a252f"),
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#2c3e50"),
    )
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=12, spaceAfter=4)
    reason = ParagraphStyle(
        "Reason", parent=styles["Normal"], fontSize=8, leading=11, spaceAfter=6
    )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="INT Zone Validation Report",
        author="INT Zone Engine",
    )
    doc.generation_timestamp = generation_ts

    story: list = []

    story.append(Spacer(1, 35 * mm))
    story.append(Paragraph("INT Zone Validation Report", cover_title))
    story.append(Paragraph("Client Deliverable", cover_sub))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"Generated: {generation_ts}", cover_sub))
    story.append(Paragraph("Source: DXF processing pipeline (build_int_zone_pipeline)", cover_sub))
    story.append(Spacer(1, 14 * mm))
    story.append(Paragraph("Executive Summary", h1))

    summary_rows: list[list[str]] = []
    for idx, line in enumerate(lines):
        if line.strip() == "## Summary — All Files":
            summary_rows, _ = _parse_md_table(lines, idx + 2)
            break
    if summary_rows:
        story.append(_styled_table(summary_rows))
    story.append(PageBreak())

    skip_sections = {"Summary — All Files"}
    current_section = ""
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line in ("---", "") or line.startswith("# INT Zone Validation Report"):
            i += 1
            continue
        if line.startswith("**Report date:") or line.startswith("**Source:") or line.startswith("**Evidence"):
            i += 1
            continue

        if line.startswith("## "):
            section = line[3:].strip()
            if section in skip_sections:
                i += 1
                while i < len(lines) and not lines[i].startswith("## "):
                    i += 1
                continue
            if section in ("Metric definitions", "Classification key"):
                story.append(PageBreak())
                story.append(Paragraph(section, h1))
                current_section = section
                i += 1
                continue
            current_section = section
            story.append(Paragraph(section, h1))
            i += 1
            continue

        if line.startswith("### "):
            story.append(Paragraph(line[4:], h2))
            i += 1
            continue

        if line.startswith("|"):
            rows, i = _parse_md_table(lines, i)
            if rows:
                story.append(_styled_table(rows))
                story.append(Spacer(1, 6))
            continue

        if line.startswith("**Overall gate:"):
            story.append(Paragraph(line.replace("**", ""), body))
            i += 1
            continue
        if line.startswith("**Reason:"):
            story.append(
                Paragraph(f"<b>Reason:</b> {line.replace('**Reason:**', '').strip()}", reason)
            )
            i += 1
            continue
        if line.startswith("**Source DXF:") or line.startswith("**Manifest:"):
            story.append(Paragraph(line.replace("`", ""), body))
            i += 1
            continue

        if line.startswith("**Full overlay:**") or line.startswith("**Flagged zone"):
            i += 1
            continue
        if line.startswith("- INT-"):
            i += 1
            continue

        i += 1

    # Embed full overlays per drawing (uniform paths)
    for item in DRAWING_PACKAGE:
        pid = item["package_id"]
        info = manifest.get(pid, {})
        overlay = info.get("overlay")
        story.append(PageBreak())
        story.append(Paragraph(f"{item['title']} — Full Overlay", h1))
        if overlay and overlay.is_file():
            story.append(_scaled_image(overlay, CONTENT_W, 170 * mm))
        else:
            story.append(Paragraph("Metric not available from current run.", body))
        story.append(Spacer(1, 8))

    # Appendix — flagged zones (uniform order: by drawing, then INT number)
    story.append(PageBreak())
    story.append(Paragraph("Appendix — Flagged Zone Evidence", h1))
    story.append(
        Paragraph(
            "Zoomed overlay images for each INT zone referenced in a REVIEW or FAIL gate.",
            body,
        )
    )
    story.append(Spacer(1, 6))

    for item in DRAWING_PACKAGE:
        pid = item["package_id"]
        flagged = manifest.get(pid, {}).get("flagged", [])
        if not flagged:
            continue
        story.append(Paragraph(item["title"], h2))
        for label, img_path in sorted(flagged, key=lambda x: int(x[0].split("-")[1])):
            story.append(Paragraph(label, h2))
            if img_path.is_file():
                story.append(_scaled_image(img_path, CONTENT_W, 115 * mm))
            else:
                story.append(Paragraph("Metric not available from current run.", body))
            story.append(Spacer(1, 6))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)


def build_zip(package_dir: Path, zip_path: Path) -> int:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_dir.rglob("*")):
            if path.is_file():
                arc = path.relative_to(package_dir).as_posix()
                zf.write(path, arcname=arc)
                count += 1
    return count


def main() -> int:
    if not MD_PATH.is_file():
        print(f"Missing: {MD_PATH}")
        print("Run: python scripts/generate_client_validation_report.py")
        return 1

    generation_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md_text = MD_PATH.read_text(encoding="utf-8")

    _clean_old_outputs()
    manifest = stage_uniform_package(md_text)

    build_pdf(MD_PATH, PACKAGE_PDF, manifest, generation_ts)
    shutil.copy2(PACKAGE_PDF, PDF_PATH)

    file_count = build_zip(PACKAGE_DIR, ZIP_PATH)

    print(f"Generated: {PDF_PATH}")
    print(f"Generated: {PACKAGE_PDF}")
    print(f"Generated: {ZIP_PATH} ({file_count} files, uniform layout)")
    print("Package layout:")
    for item in DRAWING_PACKAGE:
        pid = item["package_id"]
        n_flagged = len(manifest.get(pid, {}).get("flagged", []))
        print(f"  {pid}/full_overlay.png + flagged/ ({n_flagged} images)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
