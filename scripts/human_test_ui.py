#!/usr/bin/env python3
"""Browser-level civil engineer workflow via Playwright."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = (
    PROJECT_ROOT
    / "output"
    / ".dxf_cache"
    / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
UI = "http://localhost:1420"
ENGINE = "http://127.0.0.1:8765"

FRICTION: list[str] = []
STEPS: dict[str, dict] = {}


def friction(step: str, note: str) -> None:
    FRICTION.append(f"{step}: {note}")
    print(f"  FRICTION {step}: {note}")


def record(step: str, ok: bool, detail: str) -> None:
    STEPS[step] = {"ok": ok, "detail": detail}
    print(f"  {'PASS' if ok else 'FAIL'} — {detail}")


def _read_total(page) -> int | None:
    text = page.locator("text=Total:").first.inner_text(timeout=5000)
    m = re.search(r"Total:\s*(\d+)", text)
    return int(m.group(1)) if m else None


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed — run: pip install playwright && playwright install chromium")
        return 1

    if not WAREHOUSE_DXF.is_file():
        print(f"Missing {WAREHOUSE_DXF}")
        return 1

    save_path = Path(tempfile.gettempdir()) / "int_zone_pilot_human_test.pjson"
    session_id: str | None = None
    import_count = 0
    passed = True

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        def on_request(request):
            nonlocal session_id
            if "/upload" in request.url:
                sid = request.headers.get("x-session-id")
                if sid:
                    session_id = sid

        def on_response(response):
            nonlocal session_id
            if "/upload" in response.url and response.status == 200:
                try:
                    body = response.json()
                    session_id = body.get("session_id") or session_id
                except Exception:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)

        print("\n=== UI 0 — Load welcome ===")
        page.goto(UI, wait_until="networkidle", timeout=60_000)
        record("welcome", page.get_by_role("button", name="Import Drawing").count() > 0, "Welcome screen loaded")

        print("\n=== UI 1 — Import drawing ===")
        friction("1", "Welcome has two similar buttons: 'Open Project' vs 'Import Drawing'")
        with page.expect_file_chooser() as fc:
            page.get_by_role("button", name="Import Drawing").first.click()
        fc.value.set_files(str(WAREHOUSE_DXF))
        page.wait_for_selector("text=Polygon Table", timeout=180_000)
        import_count = _read_total(page) or 0
        record("import", import_count > 0, f"Workspace loaded — {import_count} polygons")

        print("\n=== UI 2 — Run Detection (ribbon) ===")
        page.get_by_role("button", name="Run", exact=True).first.click()
        page.wait_for_timeout(1000)
        after_detect = _read_total(page) or 0
        record(
            "detect_run",
            after_detect == import_count,
            f"Run Detection refreshed scene; count {after_detect} (unchanged expected)",
        )

        print("\n=== UI 2b — Select polygon via table ===")
        friction("2", "Large table — scroll needed; canvas click harder at fit zoom")
        row = page.locator("tr[data-polygon-id]").first
        row.wait_for(timeout=30_000)
        row.click()
        page.wait_for_timeout(500)
        record("select_polygon", True, "Clicked first polygon table row")

        print("\n=== UI 3 — Manual polygon (API-assisted after Draw tool) ===")
        if not session_id:
            passed = False
            record("manual_polygon", False, "Could not capture session id from upload")
        else:
            import httpx

            client = httpx.Client(timeout=120.0)
            scene = client.get(f"{ENGINE}/scene", headers={"X-Session-Id": session_id}).json()
            polys = scene["scene"]["polygons"]
            minx = miny = 1e18
            maxx = maxy = -1e18
            for poly in polys:
                for pt in poly.get("ring") or []:
                    x, y = float(pt[0]), float(pt[1])
                    minx, miny = min(minx, x), min(miny, y)
                    maxx, maxy = max(maxx, x), max(maxy, y)
            x0, y0 = maxx + 10_000.0, miny + 10_000.0
            size = 5000.0
            ring = [[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size]]
            page.get_by_role("button", name="Draw", exact=True).first.click()
            page.wait_for_timeout(300)
            manual = client.post(
                f"{ENGINE}/polygon/manual",
                headers={"X-Session-Id": session_id, "Content-Type": "application/json"},
                json={"ring": ring},
            )
            client.close()
            if manual.status_code == 200:
                page.get_by_role("button", name="Run", exact=True).first.click()
                page.wait_for_timeout(1500)
                after_manual = _read_total(page) or int(manual.json()["counts"]["total"])
                ok = after_manual == import_count + 1
                record(
                    "manual_polygon",
                    ok,
                    f"Manual polygon added via API after Draw tool; total {after_manual}",
                )
                import_count = after_manual
                if not ok:
                    passed = False
            else:
                passed = False
                record("manual_polygon", False, manual.text[:200])

        print("\n=== UI 4 — Save project ===")
        page.get_by_role("button", name="Save", exact=True).click()
        modal = page.locator(".modal-card").filter(has_text="Save Workspace")
        modal.wait_for(timeout=10_000)
        friction("4", "Modal requires typing full Windows path — no file picker")
        path_input = modal.locator("input[type='text']")
        path_input.fill(str(save_path))
        modal.get_by_role("button", name="Save", exact=True).click()
        page.wait_for_selector("text=Workspace saved", timeout=30_000)
        record("save", save_path.is_file(), f"Saved {save_path}")

        print("\n=== UI 5 — Close app (reload) ===")
        page.goto(UI, wait_until="networkidle")
        friction("5", "Reload returns to welcome — no recent projects list")

        print("\n=== UI 6 — Reopen project ===")
        with page.expect_file_chooser() as fc:
            page.get_by_role("button", name="Open Project").first.click()
        fc.value.set_files(str(save_path))
        page.wait_for_selector("text=Polygon Table", timeout=120_000)
        reopen_count = _read_total(page) or 0
        review_only = page.locator("text=review-only").count() > 0 or page.locator("text=Review-only").count() > 0
        ok_reopen = reopen_count == import_count and not review_only
        record(
            "reopen",
            ok_reopen,
            f"Reopened with {reopen_count} polygons; review_only={review_only}",
        )
        if not ok_reopen:
            passed = False

        print("\n=== UI 7 — Export package (bonus) ===")
        try:
            page.get_by_role("button", name="Export", exact=True).click()
            export_modal = page.locator(".modal-card").filter(has_text="Export")
            export_modal.wait_for(timeout=10_000)
            friction("7", "Multiple export options — 'Export Project Package' is the pilot path")
            export_modal.get_by_text("Export Project Package").click()
            page.wait_for_selector("text=Export complete", timeout=120_000)
            record("export", True, "Export Project Package completed")
        except Exception as exc:
            record("export", False, str(exc))
            friction("7", "Export step failed — non-blocking for core workflow")

        browser.close()

    report_path = PROJECT_ROOT / "output" / "human_test_ui_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "passed": passed,
                "steps": STEPS,
                "friction": FRICTION,
                "counts": {"final": import_count},
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nReport: {report_path}")
    print(f"\n=== UI RESULT: {'PASS' if passed else 'FAIL'} ===")
    for f in FRICTION:
        print(f"  • {f}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
