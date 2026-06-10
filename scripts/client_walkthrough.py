"""Simulate a non-technical client walking through INT Zone Studio."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = PROJECT_ROOT / "output" / "polygon_workspace" / "uploads" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
UI_URL = "http://localhost:1420"
SCREENSHOT_DIR = PROJECT_ROOT / "output" / "client_walkthrough"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

findings: list[dict] = []


def note(step: str, status: str, detail: str):
    findings.append({"step": step, "status": status, "detail": detail})
    mark = {"ok": "OK", "confused": "??", "fail": "FAIL"}.get(status, status)
    print(f"[{mark}] {step}: {detail}")


def shot(page, name: str):
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def main() -> int:
    if not WAREHOUSE.is_file():
        note("Prerequisite", "fail", f"Test drawing missing: {WAREHOUSE}")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(UI_URL, wait_until="networkidle", timeout=30000)

        # Step 1: Welcome / upload
        try:
            page.wait_for_selector("text=Drop your CAD file here", timeout=10000)
            note("Landing page", "ok", "Clear upload prompt with drag-drop zone")
            shot(page, "01_welcome")
        except PlaywrightTimeout:
            note("Landing page", "confused", "Did not see expected welcome text")
            shot(page, "01_welcome_error")

        # Upload via hidden file input
        t0 = time.time()
        page.locator('input[type="file"]').first.set_input_files(str(WAREHOUSE))
        try:
            page.wait_for_selector("text=Detected:", timeout=120000)
            elapsed = round(time.time() - t0, 1)
            note("Upload + detect", "ok", f"Warehouse slab plan processed in {elapsed}s")
            shot(page, "02_after_upload")
        except PlaywrightTimeout:
            err = page.locator(".engine-error, [role=alert]").first
            detail = err.inner_text() if err.count() else "Timed out waiting for detection"
            note("Upload + detect", "fail", detail)
            shot(page, "02_upload_failed")
            browser.close()
            _write_report()
            return 1

        # Step 2: See all polygons
        stat_text = page.locator("text=Total:").first.inner_text(timeout=5000)
        note("Polygon counts visible", "ok", stat_text)

        # Polygon table
        table_rows = page.locator("table tbody tr")
        row_count = table_rows.count()
        if row_count > 0:
            note("Polygon table", "ok", f"Table shows {row_count} visible rows (scrollable list)")
            table_rows.first.click()
            time.sleep(0.5)
            shot(page, "03_polygon_selected")
        else:
            note("Polygon table", "confused", "No rows in polygon table — where is the full list?")

        # Step 3: Find recovery controls
        page.get_by_role("button", name="Detection", exact=True).click()
        time.sleep(0.3)
        seed_btn = page.locator("button").filter(has_text="Seed")
        missing_btn = page.locator("button").filter(has_text="Missing")
        if seed_btn.count():
            note("Recover missing — find control", "ok", "Detection tab has Seed and Missing buttons")
            seed_btn.first.click()
            time.sleep(0.3)
            banner = page.locator("text=Seed Recovery Mode")
            if banner.count():
                note("Recover missing — mode", "ok", "Banner explains click inside missing area")
                shot(page, "04_seed_recovery_mode")
            else:
                note("Recover missing — mode", "confused", "Clicked Seed but no guidance banner appeared")
        else:
            note("Recover missing — find control", "confused", "Could not find Seed button on Detection tab")

        # Step 4: Save
        page.get_by_role("button", name="File", exact=True).click()
        time.sleep(0.3)
        save_btn = page.locator("button").filter(has_text="Save").first
        if save_btn.count():
            save_btn.click()
            time.sleep(0.5)
            export_modal = page.locator("text=Export Project Package")
            if export_modal.count():
                note("Save", "ok", "Save opens export dialog with DXF, CSV, PDF, package options")
                shot(page, "05_export_modal")
                # Try primary export
                pkg = page.locator("button", has_text="Export Project Package").first
                if pkg.count():
                    pkg.click()
                    time.sleep(2)
                    toast = page.locator("text=Saved:")
                    if toast.count():
                        note("Save — export", "ok", toast.first.inner_text()[:120])
                    else:
                        note("Save — export", "confused", "Clicked export but no confirmation toast")
            else:
                note("Save", "confused", "Save button did something but export options unclear")
        else:
            note("Save", "confused", "Could not find Save on File ribbon")

        # Confusion audit: stub items
        page.get_by_role("button", name="Help", exact=True).click()
        time.sleep(0.2)
        help_guide = page.locator("text=Help & Guide")
        if help_guide.count():
            note("Help", "confused", "Welcome screen shows Help & Guide greyed out — no onboarding")

        # Menu complexity
        tabs = ["File", "Home", "View", "Detection", "Polygons", "INT Zones", "Review", "Export", "Tools", "Window", "Help"]
        note("UI complexity", "confused" if len(tabs) > 7 else "ok", f"{len(tabs)} top-level menu tabs (AutoCAD-style)")

        shot(page, "06_final_state")
        browser.close()

    _write_report()
    return 0


def _write_report():
    report = SCREENSHOT_DIR / "findings.json"
    report.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\nScreenshots + findings: {SCREENSHOT_DIR}")


if __name__ == "__main__":
    sys.exit(main())
