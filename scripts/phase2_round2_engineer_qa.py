#!/usr/bin/env python3
"""Phase 2 / Pilot Round 2 — full engineer workflow QA via engine API.

Workflow:
  Import → Detect → Draw Boundary → Apply Boundary → Generate Zones →
  Recover Missing Face → Draw Manual Polygon → Save → Close → Reopen →
  Rebuild Zones → Export Package

Output: defect list JSON + markdown (defects only; no feature work).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = (
    PROJECT_ROOT
    / "output"
    / ".dxf_cache"
    / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
ENGINE = os.environ.get("INT_ZONE_ENGINE", "http://127.0.0.1:8765")
DRAWING = WAREHOUSE_DXF.name


@dataclass
class Defect:
    id: str
    severity: str  # P0 crash/data-loss/zone-mismatch | P1 step-fail | P2 friction
    step: str
    summary: str
    expected: str
    actual: str


@dataclass
class QAState:
    defects: list[Defect] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    steps: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add(
        self,
        defect_id: str,
        severity: str,
        step: str,
        summary: str,
        expected: str,
        actual: str,
    ) -> None:
        self.defects.append(
            Defect(defect_id, severity, step, summary, expected, actual)
        )

    def step_ok(self, name: str, detail: str, **extra: Any) -> None:
        self.steps[name] = {"ok": True, "detail": detail, **extra}

    def step_fail(self, name: str, detail: str, **extra: Any) -> None:
        self.steps[name] = {"ok": False, "detail": detail, **extra}


def _polygon_bbox(polygons: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    minx = miny = 1e18
    maxx = maxy = -1e18
    for poly in polygons:
        for pt in poly.get("ring") or []:
            x, y = float(pt[0]), float(pt[1])
            minx, miny = min(minx, x), min(miny, y)
            maxx, maxy = max(maxx, x), max(maxy, y)
    return minx, miny, maxx, maxy


def _scene_bounds(scene: dict[str, Any]) -> tuple[float, float, float, float]:
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for line in scene.get("cad_lines") or []:
        for i in (0, 2):
            min_x = min(min_x, float(line[i]))
            max_x = max(max_x, float(line[i]))
        for i in (1, 3):
            min_y = min(min_y, float(line[i]))
            max_y = max(max_y, float(line[i]))
    for poly in scene.get("polygons") or []:
        for x, y in poly.get("ring") or []:
            min_x, max_x = min(min_x, float(x)), max(max_x, float(x))
            min_y, max_y = min(min_y, float(y)), max(max_y, float(y))
    return min_x, min_y, max_x, max_y


def _boundary_ring(scene: dict[str, Any]) -> list[list[float]]:
    min_x, min_y, max_x, max_y = _scene_bounds(scene)
    pad_x = (max_x - min_x) * 0.02
    pad_y = (max_y - min_y) * 0.02
    return [
        [min_x + pad_x, min_y + pad_y],
        [max_x - pad_x, min_y + pad_y],
        [max_x - pad_x, max_y - pad_y],
        [min_x + pad_x, max_y - pad_y],
    ]


def _empty_manual_ring(polygons: list[dict[str, Any]], size: float = 5000.0) -> list[list[float]]:
    minx, miny, maxx, maxy = _polygon_bbox(polygons)
    x0 = maxx + 10_000.0
    y0 = miny + 10_000.0
    return [
        [x0, y0],
        [x0 + size, y0],
        [x0 + size, y0 + size],
        [x0, y0 + size],
    ]


def _zone_signature(zones: list[dict[str, Any]]) -> list[tuple[str, int, float]]:
    sig: list[tuple[str, int, float]] = []
    for z in zones:
        label = str(z.get("label") or z.get("int_label") or "")
        face_ids = z.get("face_ids") or z.get("polygon_ids") or []
        area = float(z.get("area_m2") or 0.0)
        sig.append((label, len(face_ids), round(area, 4)))
    return sorted(sig)


def run_qa() -> QAState:
    qa = QAState()
    t0 = time.time()
    headers: dict[str, str] = {}
    session_id = ""
    save_path: Path | None = None
    zones_before_reopen: list[dict[str, Any]] = []
    zone_sig_before: list[tuple[str, int, float]] = []
    counts_at_save: dict[str, Any] = {}

    client = httpx.Client(timeout=600.0, base_url=ENGINE)

    try:
        # --- Preflight ---
        r = client.get("/health")
        if r.status_code != 200:
            qa.step_fail("preflight", f"Engine health HTTP {r.status_code}")
            qa.add("DEF-001", "P0", "preflight", "Engine unreachable", "HTTP 200", str(r.status_code))
            return qa
        qa.step_ok("preflight", "Engine health OK")

        r = client.get("/scope/config")
        scope_on = r.status_code == 200 and r.json().get("enabled") is True
        if not scope_on:
            qa.step_fail("preflight", "scope.enabled is false")
            qa.add(
                "DEF-002",
                "P1",
                "preflight",
                "Slab boundary feature disabled in config",
                "scope.enabled: true",
                str(r.json() if r.is_success else r.text[:120]),
            )
        else:
            qa.step_ok("preflight_scope", "scope.enabled=true")

        if not WAREHOUSE_DXF.is_file():
            qa.add("DEF-003", "P0", "preflight", "Test drawing missing", str(WAREHOUSE_DXF), "not found")
            return qa

        # --- Import ---
        r = client.post("/session")
        r.raise_for_status()
        session_id = r.json()["session_id"]
        headers = {"X-Session-Id": session_id}

        with WAREHOUSE_DXF.open("rb") as fh:
            r = client.post(
                "/upload",
                headers=headers,
                files={"file": (WAREHOUSE_DXF.name, fh, "application/octet-stream")},
            )
        if r.status_code != 200:
            qa.step_fail("import", f"HTTP {r.status_code}: {r.text[:200]}")
            qa.add("DEF-010", "P0", "import", "Import failed", "HTTP 200", r.text[:200])
            return qa
        upload = r.json()
        import_count = int(upload["counts"]["total"])
        obstacle_n = int(upload["counts"].get("obstacles", 0))
        qa.metrics["after_import"] = import_count
        qa.metrics["obstacles_after_import"] = obstacle_n
        qa.step_ok(
            "import",
            f"{import_count} polygons ({obstacle_n} obstacles) in {r.elapsed.total_seconds():.1f}s",
        )
        if import_count <= 0:
            qa.add("DEF-011", "P0", "import", "Zero polygons after import", ">0 polygons", "0")

        scene = upload.get("scene") or {}

        # --- Detect refresh ---
        r = client.get("/scene", headers=headers)
        r.raise_for_status()
        detect_count = int(r.json()["summary"]["counts"]["total"])
        qa.metrics["after_detect"] = detect_count
        if detect_count != import_count:
            qa.step_fail("detect", f"Count changed {import_count} → {detect_count}")
            qa.add(
                "DEF-012",
                "P1",
                "detect",
                "Detect refresh changed polygon count unexpectedly",
                str(import_count),
                str(detect_count),
            )
        else:
            qa.step_ok("detect", f"Refresh unchanged at {detect_count}")

        # --- Draw boundary ---
        ring = _boundary_ring(scene)
        r = client.post("/scope/boundary/preview", headers=headers, json={"ring": ring})
        if r.status_code != 200:
            qa.step_fail("draw_boundary", r.text[:200])
            qa.add("DEF-020", "P1", "draw_boundary", "Boundary preview failed", "HTTP 200", r.text[:200])
        else:
            qa.step_ok("draw_boundary_preview", "Preview OK")

        r = client.put(
            "/scope/boundary",
            headers=headers,
            json={"ring": ring, "source": "drawn"},
        )
        if r.status_code != 200:
            qa.step_fail("draw_boundary", r.text[:200])
            qa.add("DEF-021", "P1", "draw_boundary", "Boundary commit failed", "HTTP 200", r.text[:200])
        else:
            boundary = (r.json().get("scope") or {}).get("boundary") or {}
            qa.step_ok(
                "draw_boundary",
                f"Committed boundary area={boundary.get('area_m2')} m²",
                area_m2=boundary.get("area_m2"),
            )

        # --- Apply boundary ---
        pre_apply = import_count
        r = client.post("/scope/boundary/apply", headers=headers)
        if r.status_code != 200:
            qa.step_fail("apply_boundary", r.text[:200])
            qa.add("DEF-030", "P1", "apply_boundary", "Apply boundary failed", "HTTP 200", r.text[:200])
        else:
            apply_body = r.json()
            scoped_count = int(apply_body["counts"]["total"])
            clip = apply_body.get("clip_stats") or {}
            obstacle_after = int(apply_body["counts"].get("obstacles", 0))
            qa.metrics["after_apply_boundary"] = scoped_count
            qa.metrics["obstacles_after_apply"] = obstacle_after
            qa.metrics["clip_stats"] = clip
            qa.step_ok(
                "apply_boundary",
                f"{scoped_count} polygons inside boundary (excluded={clip.get('excluded', '?')}, obstacles={obstacle_after})",
            )
            if scoped_count >= pre_apply:
                qa.add(
                    "DEF-031",
                    "P2",
                    "apply_boundary",
                    "Apply boundary did not reduce polygon count (may be OK if boundary covers full slab)",
                    f"< {pre_apply}",
                    str(scoped_count),
                )

        polys = (apply_body.get("scene") or {}).get("polygons") if r.status_code == 200 else scene.get("polygons") or []

        # --- Generate zones (first pass) ---
        r = client.post("/zones/generate", headers=headers)
        if r.status_code != 200:
            qa.step_fail("generate_zones", r.text[:300])
            qa.add("DEF-040", "P1", "generate_zones", "Zone generation failed", "HTTP 200", r.text[:300])
            zones_first: list[dict[str, Any]] = []
        else:
            zones_first = r.json().get("zones") or []
            qa.metrics["zones_after_generate"] = len(zones_first)
            qa.step_ok("generate_zones", f"{len(zones_first)} INT zones generated")
            if len(zones_first) == 0:
                qa.add(
                    "DEF-041",
                    "P1",
                    "generate_zones",
                    "No INT zones generated for warehouse drawing",
                    ">0 zones",
                    "0",
                )

        # --- Recover missing face (via validation gaps) ---
        r = client.post("/validate", headers=headers)
        recovery_done = False
        recovered_id: int | None = None
        if r.status_code != 200:
            qa.step_fail("recover_gap", r.text[:200])
            qa.add("DEF-050", "P1", "recover_gap", "Validation/gap scan failed", "HTTP 200", r.text[:200])
        else:
            validation = r.json().get("validation") or {}
            gaps = validation.get("suspected_gaps") or []
            gap_summary = validation.get("gap_summary") or {}
            qa.metrics["suspected_gaps"] = gap_summary.get("total", len(gaps))
            qa.metrics["recoverable_gaps"] = gap_summary.get("recoverable", 0)
            recoverable = [g for g in gaps if g.get("recoverable")]
            qa.step_ok(
                "recover_gap_scan",
                f"{len(gaps)} suspected gaps ({len(recoverable)} recoverable)",
            )
            for gap in recoverable[:1]:
                sx, sy = gap["seed_point"]
                rr = client.post("/recover", headers=headers, json={"x": sx, "y": sy})
                if rr.status_code == 200:
                    recovery_done = True
                    recovered_id = rr.json().get("polygon", {}).get("id")
                    qa.metrics["after_recovery"] = int(rr.json()["counts"]["total"])
                    qa.step_ok(
                        "recover_gap",
                        f"Recovered polygon #{recovered_id} at gap {gap.get('id')}",
                    )
                    break
                qa.add(
                    "DEF-051",
                    "P1",
                    "recover_gap",
                    f"Recovery failed for gap {gap.get('id')}",
                    "HTTP 200",
                    f"HTTP {rr.status_code}: {rr.text[:160]}",
                )
            if not recoverable:
                qa.step_ok("recover_gap", "No recoverable gaps — skipped recovery attempt")

        # --- Manual polygon ---
        active_polys = polys
        if recovery_done:
            r = client.get("/scene", headers=headers)
            if r.is_success:
                active_polys = r.json().get("polygons") or polys
        manual_ring = _empty_manual_ring(active_polys)
        r = client.post("/polygon/manual/preview", headers=headers, json={"ring": manual_ring})
        if r.status_code != 200:
            qa.add("DEF-060", "P1", "manual_polygon", "Manual preview failed", "HTTP 200", r.text[:200])
        r = client.post("/polygon/manual", headers=headers, json={"ring": manual_ring})
        if r.status_code != 200:
            qa.step_fail("manual_polygon", r.text[:200])
            qa.add("DEF-061", "P1", "manual_polygon", "Manual polygon commit failed", "HTTP 200", r.text[:200])
            count_before_save = qa.metrics.get("after_recovery") or qa.metrics.get("after_apply_boundary") or import_count
        else:
            manual = r.json()
            count_before_save = int(manual["counts"]["total"])
            manual_id = manual["polygon"]["id"]
            qa.metrics["after_manual"] = count_before_save
            qa.step_ok("manual_polygon", f"Added manual #{manual_id}; total {count_before_save}")

        zones_before_reopen = zones_first
        zone_sig_before = _zone_signature(zones_first)

        # --- Save ---
        save_path = Path(tempfile.gettempdir()) / "phase2_round2_engineer_qa.pjson"
        r = client.post(
            "/workspace/save",
            headers=headers,
            json={"path": str(save_path)},
        )
        if r.status_code != 200 or not save_path.is_file():
            qa.step_fail("save", r.text[:200] if r.status_code != 200 else "file missing")
            qa.add("DEF-070", "P0", "save", "Save project failed", "valid .pjson", r.text[:200])
        else:
            payload = json.loads(save_path.read_text(encoding="utf-8"))
            saved_manual = any(p.get("source") == "manual" for p in payload.get("polygons", []))
            saved_boundary = bool((payload.get("scope") or {}).get("boundary"))
            saved_zones = payload.get("zones") or []
            counts_at_save = {
                "total": len([p for p in payload.get("polygons", []) if p.get("status") != "deleted"]),
                "zones": len(saved_zones),
            }
            qa.step_ok(
                "save",
                f"Saved {save_path.name}; boundary={saved_boundary} manual={saved_manual} zones={len(saved_zones)}",
            )
            if not saved_boundary:
                qa.add("DEF-071", "P0", "save", "Boundary not persisted in .pjson", "boundary in scope", "missing")
            if not saved_manual:
                qa.add("DEF-072", "P0", "save", "Manual polygon not persisted in .pjson", "source=manual row", "missing")

        # --- Close (new session) ---
        r = client.post("/session")
        r.raise_for_status()
        new_session = r.json()["session_id"]
        new_headers = {"X-Session-Id": new_session}
        qa.step_ok("close", f"New session {new_session}")

        # --- Reopen ---
        assert save_path is not None
        with save_path.open("rb") as fh:
            r = client.post(
                "/workspace/load-project",
                headers=new_headers,
                files={"file": (save_path.name, fh, "application/json")},
            )
        if r.status_code != 200:
            qa.step_fail("reopen", r.text[:200])
            qa.add("DEF-080", "P0", "reopen", "Load project failed", "HTTP 200", r.text[:200])
            return qa
        loaded = r.json()
        reopen_count = int(loaded["counts"]["total"])
        qa.metrics["after_reopen"] = reopen_count
        cad_ok = bool(loaded.get("cad_available", True))
        restored_manual = any(p.get("source") == "manual" for p in loaded["scene"]["polygons"])
        reopened_boundary = (loaded.get("scene") or {}).get("scope_boundary") or {}
        zones_on_reopen = loaded.get("zones") or loaded.get("scene", {}).get("zones") or []
        qa.metrics["zones_after_reopen"] = len(zones_on_reopen)
        qa.step_ok(
            "reopen",
            f"{reopen_count} polygons; manual={restored_manual}; cad={cad_ok}; zones={len(zones_on_reopen)}",
        )
        if reopen_count != count_before_save:
            qa.add(
                "DEF-081",
                "P0",
                "reopen",
                "Polygon count mismatch after reopen",
                str(count_before_save),
                str(reopen_count),
            )
        if not restored_manual:
            qa.add("DEF-082", "P0", "reopen", "Manual polygon lost after reopen", "manual present", "missing")
        if not cad_ok:
            qa.add("DEF-083", "P0", "reopen", "CAD source unavailable after reopen", "cad_available=true", "false")
        if not reopened_boundary.get("ring"):
            qa.add("DEF-084", "P0", "reopen", "Boundary lost after reopen", "scope_boundary.ring", "missing")

        # --- Rebuild zones ---
        r = client.post("/zones/rebuild", headers=new_headers)
        if r.status_code != 200:
            qa.step_fail("rebuild_zones", r.text[:300])
            qa.add("DEF-090", "P1", "rebuild_zones", "Rebuild zones failed", "HTTP 200", r.text[:300])
            zones_rebuilt: list[dict[str, Any]] = []
        else:
            zones_rebuilt = r.json().get("zones") or []
            qa.metrics["zones_after_rebuild"] = len(zones_rebuilt)
            qa.step_ok("rebuild_zones", f"{len(zones_rebuilt)} zones after rebuild")
            sig_rebuild = _zone_signature(zones_rebuilt)
            sig_reopen = _zone_signature(zones_on_reopen)
            if zone_sig_before and sig_rebuild != zone_sig_before:
                qa.add(
                    "DEF-091",
                    "P0",
                    "rebuild_zones",
                    "Zone mismatch: rebuild differs from pre-save generation",
                    json.dumps(zone_sig_before[:5]),
                    json.dumps(sig_rebuild[:5]),
                )
            if zones_on_reopen and sig_rebuild != sig_reopen:
                qa.add(
                    "DEF-092",
                    "P0",
                    "rebuild_zones",
                    "Zone mismatch: rebuild differs from zones restored on reopen",
                    json.dumps(sig_reopen[:5]),
                    json.dumps(sig_rebuild[:5]),
                )
            if len(zones_rebuilt) == 0 and len(zones_before_reopen) > 0:
                qa.add(
                    "DEF-093",
                    "P0",
                    "rebuild_zones",
                    "Rebuild produced zero zones after successful pre-save generation",
                    str(len(zones_before_reopen)),
                    "0",
                )

        # --- Export package ---
        r = client.post(
            "/export",
            headers={**new_headers, "Content-Type": "application/json"},
            json={"formats": ["package"], "use_timestamp": True},
        )
        if r.status_code != 200:
            qa.step_fail("export", r.text[:200])
            qa.add("DEF-100", "P1", "export", "Export package failed", "HTTP 200", r.text[:200])
        else:
            paths = r.json().get("paths") or {}
            required = ("json", "dxf", "pdf", "xlsx")
            missing = [k for k in required if k not in paths]
            qa.step_ok("export", f"Package files: {list(paths.keys())}")
            if missing:
                qa.add(
                    "DEF-101",
                    "P1",
                    "export",
                    "Export package missing expected artifacts",
                    ", ".join(required),
                    f"missing {missing}",
                )
            for fmt, rel in paths.items():
                p = PROJECT_ROOT / rel.replace("/", "\\") if not Path(rel).is_absolute() else Path(rel)
                if not p.is_file() or p.stat().st_size == 0:
                    qa.add(
                        "DEF-102",
                        "P0",
                        "export",
                        f"Export artifact empty or missing: {fmt}",
                        "non-zero file",
                        str(p),
                    )

    except Exception as exc:
        qa.add(
            "DEF-999",
            "P0",
            "crash",
            "Unhandled exception during workflow",
            "clean completion",
            f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-400:]}",
        )
        qa.step_fail("crash", str(exc))
    finally:
        client.close()
        qa.metrics["elapsed_seconds"] = round(time.time() - t0, 1)
        qa.metrics["drawing"] = DRAWING
        qa.metrics["engine"] = ENGINE

    return qa


def write_reports(qa: QAState) -> tuple[Path, Path]:
    out_dir = PROJECT_ROOT / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    json_path = out_dir / f"phase2_round2_qa_{ts}.json"
    md_path = out_dir / f"phase2_round2_defects_{ts}.md"

    payload = {
        "workflow": "Import→Detect→Boundary→Apply→Zones→Recover→Manual→Save→Reopen→Rebuild→Export",
        "drawing": DRAWING,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "passed": len(qa.defects) == 0,
        "defect_count": len(qa.defects),
        "p0_count": sum(1 for d in qa.defects if d.severity == "P0"),
        "metrics": qa.metrics,
        "steps": qa.steps,
        "defects": [asdict(d) for d in qa.defects],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Phase 2 / Pilot Round 2 — Defect List",
        "",
        f"**Drawing:** `{DRAWING}`  ",
        f"**Run:** {payload['timestamp']}  ",
        f"**Defects:** {len(qa.defects)} (P0: {payload['p0_count']})  ",
        "",
    ]
    if not qa.defects:
        lines.append("No defects recorded — workflow completed cleanly.")
    else:
        lines.append("| ID | Sev | Step | Summary | Expected | Actual |")
        lines.append("|----|-----|------|---------|----------|--------|")
        for d in qa.defects:
            lines.append(
                f"| {d.id} | {d.severity} | {d.step} | {d.summary} | {d.expected} | {d.actual} |"
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    print("=== Phase 2 / Pilot Round 2 Engineer Workflow QA ===\n")
    qa = run_qa()
    json_path, md_path = write_reports(qa)
    print(f"\nDefects: {len(qa.defects)}")
    for d in qa.defects:
        print(f"  [{d.severity}] {d.id} {d.step}: {d.summary}")
    print(f"\nJSON: {json_path}")
    print(f"Markdown: {md_path}")
    print(f"RESULT: {'PASS' if not qa.defects else 'FAIL'}")
    return 0 if not qa.defects else 1


if __name__ == "__main__":
    sys.exit(main())
