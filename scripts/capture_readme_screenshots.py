#!/usr/bin/env python3
"""Capture README screenshots for GitHub (Playwright)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "docs" / "images"
WAREHOUSE_DXF = (
    PROJECT_ROOT
    / "output"
    / ".dxf_cache"
    / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
UI = "http://localhost:1420"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium")
        return 1

    if not WAREHOUSE_DXF.is_file():
        print(f"Missing sample drawing: {WAREHOUSE_DXF}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.set_default_timeout(180_000)

        print("1/4 Welcome screen...")
        page.goto(UI, wait_until="networkidle")
        page.wait_for_selector("text=Import Drawing", timeout=60_000)
        time.sleep(0.5)
        page.screenshot(path=str(OUT_DIR / "welcome-screen.png"))

        print("2/4 Import drawing -> workspace...")
        with page.expect_file_chooser() as fc:
            page.get_by_role("button", name="Import Drawing").first.click()
        fc.value.set_files(str(WAREHOUSE_DXF))
        page.wait_for_selector("text=Polygon Table", timeout=180_000)
        page.wait_for_timeout(2000)
        page.evaluate("window.dispatchEvent(new CustomEvent('studio:fit-view'))")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT_DIR / "workspace-detection.png"))

        print("3/4 Polygon table + selection...")
        row = page.locator("tr[data-polygon-id]").first
        row.wait_for(timeout=60_000)
        row.click(force=True)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT_DIR / "workspace-review.png"))

        print("4/4 Validation / gaps panel...")
        for label in ("Validate", "Validation", "Suspected Gaps"):
            try:
                page.get_by_role("button", name=label, exact=False).first.click(timeout=3000)
                page.wait_for_timeout(2000)
                break
            except Exception:
                continue
        page.screenshot(path=str(OUT_DIR / "workspace-validation.png"))

        browser.close()

    files = sorted(OUT_DIR.glob("*.png"))
    print(f"\nSaved {len(files)} screenshots to {OUT_DIR}")
    for f in files:
        print(f"  {f.name} ({f.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
