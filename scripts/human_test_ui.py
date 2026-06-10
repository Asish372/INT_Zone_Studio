#!/usr/bin/env python3
"""Browser-level naive-user simulation via Playwright."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = (
    PROJECT_ROOT
    / "output"
    / ".dxf_cache"
    / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
UI = "http://localhost:1420"

FRICTION: list[str] = []


def friction(step: str, note: str) -> None:
    FRICTION.append(f"{step}: {note}")
    print(f"  FRICTION {step}: {note}")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed")
        return 1

    if not WAREHOUSE_DXF.is_file():
        print(f"Missing {WAREHOUSE_DXF}")
        return 1

    save_path = Path(tempfile.gettempdir()) / "int_zone_pilot_human_test.pjson"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(UI, wait_until="networkidle", timeout=60_000)

        # Step 1 — Open drawing
        print("\n=== UI 1 — Import drawing ===")
        friction("1", "Welcome has two similar buttons: 'Open Project' vs 'Import Drawing'")
        with page.expect_file_chooser() as fc:
            page.get_by_role("button", name="Import Drawing").first.click()
        fc.value.set_files(str(WAREHOUSE_DXF))
        page.wait_for_selector("text=Polygon Table", timeout=120_000)
        print("  Workspace loaded")

        # Step 2 — Find polygon (table, not canvas — naive path)
        print("\n=== UI 2 — Find polygon via table ===")
        friction("2", "618-row table — user may not know to scroll; canvas click needs zoom")
        row = page.locator("tr[data-polygon-id]").first
        row.wait_for(timeout=30_000)
        row.click()
        page.wait_for_timeout(500)
        print("  Clicked first table row")

        # Step 3 — Save
        print("\n=== UI 3 — Save project ===")
        page.get_by_role("button", name="Save", exact=True).click()
        modal = page.locator(".modal-card").filter(has_text="Save Workspace")
        modal.wait_for(timeout=10_000)
        friction("3", "Modal requires typing full Windows path — no file picker")
        path_input = modal.locator("input[type='text']")
        path_input.fill(str(save_path))
        modal.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_selector("text=Workspace saved", timeout=30_000)
        print(f"  Saved {save_path}")

        # Step 4 — Close (reload)
        print("\n=== UI 4 — Close app (reload) ===")
        page.goto(UI, wait_until="networkidle")
        friction("4", "Reload returns to welcome — no 'recent projects' list")

        # Step 5 — Reopen
        print("\n=== UI 5 — Reopen project ===")
        with page.expect_file_chooser() as fc:
            page.get_by_role("button", name="Open Project").first.click()
        fc.value.set_files(str(save_path))
        page.wait_for_selector("text=Polygon Table", timeout=60_000)
        count_text = page.locator("text=Polygon Table").first.inner_text()
        print(f"  Reopened — {count_text}")

        # Step 6 — Export package
        print("\n=== UI 6 — Export package ===")
        page.get_by_role("button", name="Export", exact=True).click()
        export_modal = page.locator(".modal-card").filter(has_text="Export")
        export_modal.wait_for(timeout=10_000)
        friction("6", "8 export options — 'Export Project Package' not obviously the right one")
        export_modal.get_by_text("Export Project Package").click()
        page.wait_for_selector("text=Export complete", timeout=120_000)
        print("  Package exported")

        browser.close()

    print("\n=== UI RESULT: PASS (no crash) ===")
    for f in FRICTION:
        print(f"  • {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
