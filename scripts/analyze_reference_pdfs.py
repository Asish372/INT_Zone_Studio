"""Deep analysis of reference PDFs: text dict, drawings, render previews."""
from __future__ import annotations

import re
from pathlib import Path

import fitz

PDF_DIR = Path(r"C:\Users\Administrator\OneDrive\Desktop\freelancing project")
OUT_DIR = Path(r"c:\Users\Administrator\OneDrive\Desktop\Strtup\output\pdf_analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LABEL_RE = re.compile(
    r"\b(INT[- ]?\d+|PC\d+|DCJ|DDCJ|RSCJ|DC\d+|EXT[- ]?\d+|ZONE[- ]?\d+)\b",
    re.I,
)


def analyze_pdf(path: Path) -> None:
    doc = fitz.open(path)
    print("\n" + "=" * 80)
    print(f"{path.name}  pages={len(doc)}  size={path.stat().st_size}")
    print("=" * 80)

    all_labels: list[str] = []
    for i, page in enumerate(doc):
        # Render preview
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
        img_path = OUT_DIR / f"{path.stem}_p{i+1}.png"
        pix.save(str(img_path))

        text = page.get_text("text") or ""
        blocks = page.get_text("blocks")
        words = page.get_text("words")

        labels = LABEL_RE.findall(text)
        all_labels.extend(labels)

        print(f"\n  Page {i+1}: blocks={len(blocks)} words={len(words)} text_len={len(text)}")
        print(f"    Preview: {img_path.name}")

        if text.strip():
            for line in text.splitlines():
                if LABEL_RE.search(line) or any(
                    k in line.upper() for k in ("INTERNAL", "SLAB", "AREA", "M2", "M²")
                ):
                    print(f"    | {line.strip()[:120]}")

        # Unique word strings that look like zone codes
        word_texts = sorted({w[4].strip() for w in words if w[4].strip()})
        zone_words = [w for w in word_texts if LABEL_RE.search(w) or re.match(r"^[A-Z]{2,4}\d*$", w)]
        if zone_words:
            print(f"    Zone-like words: {zone_words[:40]}")

        drawings = page.get_drawings()
        print(f"    Vector drawings paths: {len(drawings)}")

    unique = sorted(set(all_labels), key=str.upper)
    print(f"\n  All label tokens in extractable text: {unique}")
    doc.close()


def main() -> None:
    for pdf in sorted(PDF_DIR.glob("*.pdf")):
        analyze_pdf(pdf)
    print(f"\nPreviews saved under {OUT_DIR}")


if __name__ == "__main__":
    main()
