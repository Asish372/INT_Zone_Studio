from __future__ import annotations

from pathlib import Path

import openpyxl
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"


def excel_to_pdf(xlsx_path: Path, pdf_path: Path) -> None:
    workbook = openpyxl.load_workbook(xlsx_path, data_only=True)
    sheet = workbook.active

    page_width, page_height = landscape(A4)
    c = canvas.Canvas(str(pdf_path), pagesize=landscape(A4))

    left_margin = 24
    top_margin = page_height - 28
    row_height = 16

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_margin, top_margin, f"INT Schedule Export - {xlsx_path.name}")
    y = top_margin - 24

    headers = [cell.value or "" for cell in sheet[1]]
    col_width = (page_width - (2 * left_margin)) / max(len(headers), 1)

    def draw_row(values: list[str], y_pos: float, bold: bool = False) -> None:
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 8)
        for idx, value in enumerate(values):
            txt = str(value)[:26]
            x = left_margin + (idx * col_width)
            c.drawString(x, y_pos, txt)

    draw_row(headers, y, bold=True)
    y -= row_height

    for row in sheet.iter_rows(min_row=2, values_only=True):
        values = ["" if value is None else value for value in row]
        draw_row(values, y, bold=False)
        y -= row_height
        if y <= 30:
            c.showPage()
            y = page_height - 30
            draw_row(headers, y, bold=True)
            y -= row_height

    c.save()


def main() -> None:
    schedules = sorted(OUTPUT_DIR.glob("*_int_schedule.xlsx"))
    if not schedules:
        raise SystemExit("No *_int_schedule.xlsx files found in output/")

    for schedule in schedules:
        pdf_out = schedule.with_suffix(".pdf")
        excel_to_pdf(schedule, pdf_out)
        print(f"Generated PDF: {pdf_out}")


if __name__ == "__main__":
    main()
