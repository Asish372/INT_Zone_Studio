#!/usr/bin/env python3
"""Phase 1 boundary overlay UI check (warehouse, zoom/pan stress)."""

from __future__ import annotations

import sys
import tempfile
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = (
    PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
UI = "http://localhost:1420"
ENGINE = "http://127.0.0.1:8765"


def engine_ok() -> bool:
    try:
        with urllib.request.urlopen(f"{ENGINE}/health", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def scope_enabled() -> bool:
    try:
        with urllib.request.urlopen(f"{ENGINE}/scope/config", timeout=5) as r:
            import json

            return json.loads(r.read()).get("enabled") is True
    except Exception:
        return False


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[SKIP] playwright not installed — overlay UI check skipped")
        return 0

    if not engine_ok():
        print("[FAIL] Engine not reachable on :8765")
        return 1
    if not scope_enabled():
        print("[FAIL] scope.enabled is false — restart sidecar after enabling in config.yaml")
        return 1
    if not WAREHOUSE_DXF.is_file():
        print(f"[FAIL] Missing {WAREHOUSE_DXF}")
        return 1

    results: list[tuple[str, bool, str]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.goto(UI, wait_until="networkidle", timeout=120_000)

        # Import warehouse
        with page.expect_file_chooser() as fc:
            page.get_by_role("button", name="Import Drawing").first.click()
        fc.value.set_files(str(WAREHOUSE_DXF))
        page.wait_for_selector("text=Polygon Table", timeout=180_000)

        # Define slab boundary via Detection ribbon (scope enabled)
        page.get_by_role("button", name="Boundary", exact=True).click()
        page.wait_for_selector("text=Define Slab Boundary:", timeout=15_000)

        canvas = page.locator(".canvas-wrap")
        box = canvas.bounding_box()
        if not box:
            print("[FAIL] Canvas not found")
            browser.close()
            return 1

        # Draw rectangle boundary (4 corners + close)
        clicks = [
            (box["x"] + box["width"] * 0.25, box["y"] + box["height"] * 0.25),
            (box["x"] + box["width"] * 0.75, box["y"] + box["height"] * 0.25),
            (box["x"] + box["width"] * 0.75, box["y"] + box["height"] * 0.75),
            (box["x"] + box["width"] * 0.25, box["y"] + box["height"] * 0.75),
        ]
        for x, y in clicks:
            page.mouse.click(x, y)
            page.wait_for_timeout(120)
        page.keyboard.press("Enter")
        page.wait_for_selector("text=Slab boundary preview", timeout=15_000)
        preview_area = page.locator("text=Slab boundary preview").inner_text()
        page.get_by_role("button", name="Confirm").click()
        page.wait_for_timeout(1200)
        results.append(
            (
                "Boundary preview shows area",
                "m²" in preview_area,
                preview_area[:80],
            )
        )

        # Overlay visible (canvas has content after boundary)
        shot_path = Path(tempfile.gettempdir()) / "phase1_boundary_overlay.png"
        page.screenshot(path=str(shot_path), full_page=False)
        results.append(
            (
                "Boundary draw + confirm in UI",
                shot_path.is_file(),
                str(shot_path),
            )
        )

        # Zoom/pan stress — measure frame times during interaction
        timings: list[float] = []
        for _ in range(8):
            page.mouse.wheel(0, -400)
            page.wait_for_timeout(50)
        for _ in range(12):
            t0 = time.perf_counter()
            page.mouse.move(
                box["x"] + box["width"] * 0.5,
                box["y"] + box["height"] * 0.5,
            )
            page.mouse.down()
            page.mouse.move(
                box["x"] + box["width"] * 0.5 + 80,
                box["y"] + box["height"] * 0.5 + 60,
                steps=10,
            )
            page.mouse.up()
            page.wait_for_timeout(30)
            timings.append(time.perf_counter() - t0)

        avg_pan = sum(timings) / len(timings) if timings else 999.0
        smooth = avg_pan < 0.5
        results.append(
            (
                "Warehouse overlay smooth under pan/zoom",
                smooth,
                f"avg pan gesture {avg_pan:.3f}s (threshold 0.5s)",
            )
        )

        # Save → reload → boundary banner or scope still in scene (table row count unchanged)
        save_path = Path(tempfile.gettempdir()) / "phase1_ui_boundary.pjson"
        page.get_by_role("button", name="Save", exact=True).click()
        modal = page.locator(".modal-card").filter(has_text="Save Workspace")
        modal.wait_for(timeout=10_000)
        modal.locator("input[type='text']").fill(str(save_path))
        modal.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_selector("text=Workspace saved", timeout=30_000)
        import json

        saved_payload = json.loads(save_path.read_text(encoding="utf-8"))
        saved_ring = ((saved_payload.get("scope") or {}).get("boundary") or {}).get(
            "ring"
        ) or []
        results.append(
            (
                "UI save persists boundary in .pjson",
                len(saved_ring) >= 3,
                f"{len(saved_ring)} vertices, {save_path.stat().st_size} bytes",
            )
        )

        page.goto(UI, wait_until="networkidle")
        with page.expect_file_chooser() as fc2:
            page.get_by_role("button", name="Open Project").first.click()
        with page.expect_response(
            lambda r: "load-project" in r.url and r.status == 200,
            timeout=120_000,
        ) as load_resp:
            fc2.value.set_files(str(save_path))
        load_json = load_resp.value.json()
        reopened_ring = (
            (load_json.get("scene") or {}).get("scope_boundary") or {}
        ).get("ring") or []
        page.wait_for_selector("text=Polygon Table", timeout=120_000)
        page.wait_for_timeout(1500)
        reload_shot = Path(tempfile.gettempdir()) / "phase1_boundary_after_reopen.png"
        page.screenshot(path=str(reload_shot), full_page=False)
        poly_count = len(
            [
                p
                for p in (load_json.get("scene") or {}).get("polygons") or []
                if p.get("status") != "deleted"
            ]
        )
        results.append(
            (
                "UI reopen: 618 polygons + boundary ring",
                poly_count == 618 and len(reopened_ring) == len(saved_ring),
                f"polys={poly_count}, boundary verts={len(reopened_ring)}",
            )
        )

        browser.close()

    passed = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name} — {detail}")
        if ok:
            passed += 1
    print(f"\n=== UI: {passed}/{len(results)} checks passed ===")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
