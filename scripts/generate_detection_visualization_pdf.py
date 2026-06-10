#!/usr/bin/env python3
"""Build civil-engineer Detection Visualization PDF — PDF-only client deliverable."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT_DIR = PROJECT_ROOT / "output" / "detection_visualization"
PACKAGE_DIR = OUT_DIR / "package"
MANIFEST_JSON = OUT_DIR / "detection_visualization_manifest.json"
PDF_PATH = OUT_DIR / "DETECTION_VISUALIZATION_REPORT.pdf"
PACKAGE_PDF = PACKAGE_DIR / "DETECTION_VISUALIZATION_REPORT.pdf"

PAGE_W, PAGE_H = landscape(A3)
MARGIN = 12 * mm
CONTENT_W = PAGE_W - 2 * MARGIN
CONTENT_H = PAGE_H - 2 * MARGIN - 14 * mm

# Civil engineer sheet order per drawing
PAGE_ORDER = [
    ("page1_storyboard", "Overview — input plan to INT zones"),
    ("page2_detected", "Detected pour areas"),
    ("page2b_context", "Detection coverage (pour areas vs not used)"),
    ("page3_detail_1", "Zone detail — callout A"),
    ("page3_detail_2", "Zone detail — callout B"),
    ("page3_detail_3", "Zone detail — callout C"),
    ("page3_summary", "Additional zone detail — callouts D & E"),
    ("page4_zones", "INT zone map with areas (m²)"),
    ("page5_boundaries", "Final pour boundaries"),
]


def _scaled_image(path: Path) -> Image:
    img = Image(str(path))
    scale = min(CONTENT_W / img.drawWidth, CONTENT_H / img.drawHeight, 1.0)
    img.drawWidth *= scale
    img.drawHeight *= scale
    img.hAlign = "CENTER"
    return img


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(PAGE_W / 2, 8 * mm, f"Page {canvas.getPageNumber()}")
    canvas.drawRightString(PAGE_W - MARGIN, 8 * mm, getattr(doc, "generation_timestamp", ""))
    canvas.drawString(MARGIN, 8 * mm, "INT Zone Detection Visualization")
    canvas.restoreState()


def build_pdf(manifest: list[dict], pdf_path: Path, generation_ts: str) -> None:
    styles = getSampleStyleSheet()
    cover_title = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontSize=26,
        leading=30,
        alignment=TA_CENTER,
        spaceAfter=16,
        textColor=colors.HexColor("#1a252f"),
    )
    cover_sub = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontSize=13,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceAfter=10,
    )
    body = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#333333"),
        spaceAfter=8,
    )
    drawing_head = ParagraphStyle(
        "DrawingHead",
        parent=styles["Heading1"],
        fontSize=18,
        spaceBefore=4,
        spaceAfter=8,
        textColor=colors.HexColor("#1a252f"),
    )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=landscape(A3),
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="INT Zone Detection Visualization",
        author="INT Zone Engine",
    )
    doc.generation_timestamp = generation_ts

    story: list = []
    story.append(Spacer(1, 45 * mm))
    story.append(Paragraph("INT Zone Detection Visualization", cover_title))
    story.append(Spacer(1, 10 * mm))
    story.append(
        Paragraph(
            "Detected pour areas on original slab plans — grouped into INT zones",
            cover_sub,
        )
    )
    story.append(Spacer(1, 14 * mm))
    story.append(Paragraph(f"Issued: {generation_ts}", cover_sub))
    story.append(Spacer(1, 20 * mm))
    story.append(
        Paragraph(
            "<b>Contents per drawing:</b><br/>"
            "1. Overview storyboard<br/>"
            "2. Detected pour areas on plan<br/>"
            "3. Detection coverage<br/>"
            "4–7. Zone detail views<br/>"
            "8. INT zone map with areas (m²)<br/>"
            "9. Final pour boundaries",
            body,
        )
    )
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph("<b>Drawings included:</b>", body))
    for entry in manifest:
        story.append(Paragraph(f"• {entry['title']} — {entry['source_dxf']}", body))
    story.append(PageBreak())

    for entry in manifest:
        story.append(Paragraph(entry["title"], drawing_head))
        story.append(Paragraph(f"Source drawing: {entry['source_dxf']}", body))
        story.append(Spacer(1, 4))

        pages = entry["pages"]
        for page_key, sheet_label in PAGE_ORDER:
            rel = pages.get(page_key)
            if not rel:
                continue
            img_path = PROJECT_ROOT / rel
            if not img_path.is_file():
                continue
            story.append(_scaled_image(img_path))
            story.append(PageBreak())

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)


def stage_package(manifest: list[dict]) -> None:
    """Package dir holds PDF only for client handoff."""
    if PACKAGE_DIR.is_dir():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PDF_PATH, PACKAGE_DIR / "DETECTION_VISUALIZATION_REPORT.pdf")
    (PACKAGE_DIR / "README.txt").write_text(
        "\n".join(
            [
                "INT Zone Detection Visualization",
                "================================",
                "",
                "Client deliverable: DETECTION_VISUALIZATION_REPORT.pdf",
                "",
                "Shows detected pour areas on the original slab plan,",
                "how they group into INT zones, and final pour boundaries.",
                "",
                "Open in any PDF viewer or print at A3 landscape.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    if not MANIFEST_JSON.is_file():
        print(f"Missing {MANIFEST_JSON}")
        print("Run: python scripts/generate_detection_visualization.py")
        return 1

    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    generation_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    build_pdf(manifest, PDF_PATH, generation_ts)
    stage_package(manifest)

    print(f"Generated: {PDF_PATH}")
    print(f"Generated: {PACKAGE_DIR / 'DETECTION_VISUALIZATION_REPORT.pdf'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
