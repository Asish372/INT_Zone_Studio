#!/usr/bin/env python3
"""Aggressive QA harness — break INT Zone Studio engine/API."""

from __future__ import annotations

import copy
import json
import mimetypes
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BASE = "http://127.0.0.1:8765"
WAREHOUSE = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
QA_DIR = PROJECT_ROOT / "output" / "qa_fixtures"
ENGINE_PROC: subprocess.Popen | None = None


@dataclass
class Bug:
    id: str
    severity: str  # critical, high, medium, low
    category: str  # crash, freeze, corruption, message, validation
    title: str
    steps: str
    expected: str
    actual: str
    component: str = "engine"


@dataclass
class QAResult:
    name: str
    passed: bool
    detail: str
    duration_ms: float = 0.0
    bugs: list[Bug] = field(default_factory=list)


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def ensure_engine() -> None:
    global ENGINE_PROC
    if _port_open("127.0.0.1", 8765):
        return
    py = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if not py.is_file():
        py = Path(sys.executable)
    ENGINE_PROC = subprocess.Popen(
        [str(py), str(PROJECT_ROOT / "scripts" / "run_polygon_workspace.py")],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        if _port_open("127.0.0.1", 8765):
            return
        time.sleep(0.25)
    raise RuntimeError("Engine sidecar failed to start on :8765")


def req(
    method: str,
    path: str,
    data: Any = None,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any], float]:
    import urllib.error
    import urllib.request

    t0 = time.perf_counter()
    url = BASE + path
    body: bytes | None = None
    h = dict(headers or {})
    if data is not None and not isinstance(data, (bytes, bytearray)):
        body = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    elif isinstance(data, (bytes, bytearray)):
        body = bytes(data)
    request = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read()
            payload = json.loads(raw) if raw else {}
            return resp.status, payload, (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return e.code, payload, (time.perf_counter() - t0) * 1000
    except Exception as exc:
        return 0, {"error": str(exc)}, (time.perf_counter() - t0) * 1000


def upload_bytes(
    session_id: str,
    filename: str,
    content: bytes,
    timeout: float = 120.0,
) -> tuple[int, dict[str, Any], float]:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "X-Session-Id": session_id,
    }
    return req("POST", "/upload", data=body, headers=headers, timeout=timeout)


def new_session() -> str:
    st, data, _ = req("POST", "/session")
    assert st == 200, data
    return data["session_id"]


def run_tests() -> list[QAResult]:
    results: list[QAResult] = []
    QA_DIR.mkdir(parents=True, exist_ok=True)

    def record(name: str, passed: bool, detail: str, ms: float = 0.0, bugs: list[Bug] | None = None):
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {name} ({ms:.0f}ms): {detail}")
        results.append(QAResult(name, passed, detail, ms, bugs or []))

    # --- 1. Invalid DWG ---
    sid = new_session()
    invalid_dwg = QA_DIR / "invalid.dwg"
    invalid_dwg.write_bytes(b"NOT_A_REAL_DWG_HEADER\x00\x01\x02")
    st, up, ms = upload_bytes(sid, "invalid.dwg", invalid_dwg.read_bytes())
    bugs: list[Bug] = []
    if st not in (400, 422):
        bugs.append(
            Bug(
                "BUG-001",
                "high",
                "validation",
                "Invalid DWG accepted or wrong status",
                "Upload garbage bytes with .dwg extension",
                "HTTP 422 with clear conversion/parse error",
                f"HTTP {st}: {up.get('detail', up)}",
            )
        )
    elif st == 422 and "ODA" not in str(up.get("detail", "")):
        bugs.append(
            Bug(
                "BUG-002",
                "low",
                "message",
                "Invalid DWG error omits ODA install hint",
                "Upload invalid.dwg without ODA or with bad file",
                "Message mentions ODA File Converter when relevant",
                str(up.get("detail")),
            )
        )
    record("Invalid DWG", st in (400, 422) and st != 200, f"status={st} detail={up.get('detail', '')[:120]}", ms, bugs)

    # --- 2. Empty file ---
    sid = new_session()
    st, up, ms = upload_bytes(sid, "empty.dxf", b"")
    bugs = []
    if st == 200:
        bugs.append(
            Bug(
                "BUG-003",
                "critical",
                "validation",
                "Empty DXF file accepted",
                "Upload 0-byte .dxf",
                "Reject with 400/422",
                f"Accepted with {up.get('polygon_count')} polygons",
            )
        )
    elif st not in (400, 422):
        bugs.append(
            Bug(
                "BUG-004",
                "medium",
                "validation",
                "Empty file returns unexpected status",
                "Upload empty.dxf",
                "400 or 422",
                f"HTTP {st}",
            )
        )
    record("Empty DXF", st in (400, 422), f"status={st} detail={str(up.get('detail', ''))[:100]}", ms, bugs)

    # --- 3. Corrupted DXF ---
    sid = new_session()
    corrupt = b"0\nSECTION\nHEADER\nBAD\x00\xff\xfe\n"
    st, up, ms = upload_bytes(sid, "corrupt.dxf", corrupt)
    bugs = []
    if st == 200:
        bugs.append(
            Bug(
                "BUG-005",
                "critical",
                "validation",
                "Corrupted DXF accepted",
                "Upload truncated/garbage DXF",
                "422 parse error",
                f"polygon_count={up.get('polygon_count')}",
            )
        )
    record("Corrupted DXF", st in (400, 422), f"status={st}", ms, bugs)

    # --- 4. Wrong extension ---
    sid = new_session()
    st, up, ms = upload_bytes(sid, "notes.txt", b"hello")
    record("Wrong file type", st == 400, f"status={st} detail={up.get('detail')}", ms)

    # --- 5. 10,000 polygons (synthetic session stress) ---
    sid = new_session()
    if WAREHOUSE.is_file():
        st, up, ms = upload_bytes(sid, WAREHOUSE.name, WAREHOUSE.read_bytes(), timeout=180)
        if st == 200:
            polys = up.get("scene", {}).get("polygons", [])
            base = polys[:1] if polys else []
            if base:
                synthetic = []
                for i in range(10_000):
                    p = copy.deepcopy(base[0])
                    p["id"] = i + 1
                    c = p.get("centroid") or [0, 0]
                    ring = p.get("ring") or []
                    offset = (i % 100) * 10.0
                    p["centroid"] = [c[0] + offset, c[1] + offset]
                    p["ring"] = [[pt[0] + offset, pt[1] + offset] for pt in ring]
                    synthetic.append(p)
                # Direct session manipulation via repeated delete + scene fetch
                t0 = time.perf_counter()
                st_scene, scene, ms_scene = req("GET", "/scene", headers={"X-Session-Id": sid})
                # Inject via many recoveries isn't practical; test scene build at module level
                from desktop.engine_sidecar.scene_builder import build_scene

                t_build = time.perf_counter()
                built = build_scene(
                    source_file="stress.dxf",
                    cad_segments=[],
                    polygons=synthetic,
                )
                build_ms = (time.perf_counter() - t_build) * 1000
                bugs = []
                if build_ms > 5000:
                    bugs.append(
                        Bug(
                            "BUG-006",
                            "high",
                            "freeze",
                            "Scene build >5s with 10k polygons",
                            "Load workspace with 10,000 polygon records",
                            "Interactive render prep <2s",
                            f"build_scene took {build_ms:.0f}ms",
                            component="scene_builder",
                        )
                    )
                payload_size = len(json.dumps(built))
                if payload_size > 50_000_000:
                    bugs.append(
                        Bug(
                            "BUG-007",
                            "high",
                            "freeze",
                            "Scene JSON exceeds 50MB for 10k polygons",
                            "GET /scene with 10k polygons",
                            "Paginate or simplify geometry",
                            f"~{payload_size // 1_000_000}MB JSON",
                        )
                    )
                record(
                    "10,000 polygons (scene build)",
                    build_ms < 10_000,
                    f"polygons={len(built['polygons'])} build_ms={build_ms:.0f} json_mb={payload_size/1e6:.1f}",
                    build_ms,
                    bugs,
                )
            else:
                record("10,000 polygons", False, "warehouse upload had no polygons", ms)
        else:
            record("10,000 polygons", False, f"warehouse upload failed st={st}", ms)
    else:
        record("10,000 polygons", False, f"missing warehouse dxf: {WAREHOUSE}", 0)

    # --- 6. Polygon deletion ---
    sid = new_session()
    if WAREHOUSE.is_file():
        st, up, ms = upload_bytes(sid, WAREHOUSE.name, WAREHOUSE.read_bytes(), timeout=180)
        if st == 200:
            pid = up["scene"]["polygons"][0]["id"]
            before = up["counts"]["total"]
            st_del, del_res, ms_del = req(
                "POST",
                f"/polygon/{pid}/delete",
                headers={"X-Session-Id": sid},
            )
            after = del_res.get("counts", {}).get("total", -1)
            bugs = []
            if st_del != 200 or after != before - 1:
                bugs.append(
                    Bug(
                        "BUG-008",
                        "high",
                        "corruption",
                        "Delete did not decrement active count",
                        f"DELETE polygon {pid}",
                        f"total {before} -> {before-1}",
                        f"status={st_del} total={after}",
                    )
                )
            # Double delete
            st2, up2, _ = req("POST", f"/polygon/{pid}/delete", headers={"X-Session-Id": sid})
            if st2 == 200 and up2.get("counts", {}).get("deleted", 0) < 1:
                bugs.append(
                    Bug(
                        "BUG-009",
                        "medium",
                        "validation",
                        "Double-delete silently succeeds without idempotency message",
                        "Delete same polygon twice",
                        "409 or no-op with warning",
                        f"status={st2}",
                    )
                )
            record("Polygon deletion", st_del == 200 and after == before - 1, f"before={before} after={after}", ms_del, bugs)
        else:
            record("Polygon deletion", False, "upload failed", ms)

    # --- 7. Undo / Redo spam ---
    sid = new_session()
    if WAREHOUSE.is_file():
        st, up, ms = upload_bytes(sid, WAREHOUSE.name, WAREHOUSE.read_bytes(), timeout=180)
        if st == 200:
            pid = up["scene"]["polygons"][0]["id"]
            for _ in range(5):
                req("POST", f"/polygon/{pid}/delete", headers={"X-Session-Id": sid})
            undo_ok = redo_ok = 0
            undo_fail = redo_fail = 0
            t0 = time.perf_counter()
            for _ in range(200):
                st_u, _, _ = req("POST", "/undo", headers={"X-Session-Id": sid})
                if st_u == 200:
                    undo_ok += 1
                else:
                    undo_fail += 1
            for _ in range(200):
                st_r, _, _ = req("POST", "/redo", headers={"X-Session-Id": sid})
                if st_r == 200:
                    redo_ok += 1
                else:
                    redo_fail += 1
            spam_ms = (time.perf_counter() - t0) * 1000
            st_f, final, _ = req("GET", "/scene", headers={"X-Session-Id": sid})
            bugs = []
            if spam_ms > 30_000:
                bugs.append(
                    Bug(
                        "BUG-010",
                        "high",
                        "freeze",
                        "Undo/redo spam causes multi-second lockup",
                        "200 undo + 200 redo rapid fire",
                        "All requests <30s total",
                        f"{spam_ms:.0f}ms",
                    )
                )
            if undo_ok == 0 and redo_ok == 0:
                bugs.append(
                    Bug(
                        "BUG-011",
                        "medium",
                        "validation",
                        "Undo never succeeds after delete spam",
                        "Delete then undo 200x",
                        "At least one undo restores state",
                        f"undo_ok={undo_ok} redo_ok={redo_ok}",
                    )
                )
            record(
                "Undo/redo spam",
                st_f == 200 and spam_ms < 60_000,
                f"undo_ok={undo_ok} undo_fail={undo_fail} redo_ok={redo_ok} redo_fail={redo_fail} ms={spam_ms:.0f}",
                spam_ms,
                bugs,
            )

    # --- 8. Export without detection ---
    sid = new_session()
    st, exp, ms = req(
        "POST",
        "/export",
        {"formats": ["json", "dxf"]},
        headers={"X-Session-Id": sid},
    )
    bugs = []
    if st != 404:
        bugs.append(
            Bug(
                "BUG-012",
                "high",
                "validation",
                "Export allowed on empty session",
                "POST /export with no upload",
                "404 No polygons to export",
                f"HTTP {st} paths={exp.get('paths')}",
            )
        )
    record("Export without detection", st == 404, f"status={st} detail={exp.get('detail')}", ms, bugs)

    # --- 9. Export with all polygons deleted ---
    sid = new_session()
    if WAREHOUSE.is_file():
        st, up, ms = upload_bytes(sid, WAREHOUSE.name, WAREHOUSE.read_bytes(), timeout=180)
        if st == 200:
            for p in up["scene"]["polygons"][:20]:
                req("POST", f"/polygon/{p['id']}/delete", headers={"X-Session-Id": sid})
            st2, counts, _ = req("GET", "/summary", headers={"X-Session-Id": sid})
            total = counts.get("counts", {}).get("total", 0)
            st_exp, exp2, ms_exp = req(
                "POST",
                "/export",
                {"formats": ["json"]},
                headers={"X-Session-Id": sid},
            )
            bugs = []
            # API checks `if not session.polygons` not active count — still exports if records exist
            if total < 618 and st_exp == 200:
                exported = exp2.get("polygon_count", -1)
                if exported != total:
                    bugs.append(
                        Bug(
                            "BUG-013",
                            "medium",
                            "corruption",
                            "Export polygon_count mismatch after deletions",
                            "Delete some polygons then export",
                            "polygon_count matches active total",
                            f"summary total={total} export count={exported}",
                        )
                    )
            record(
                "Export after partial delete",
                st_exp == 200,
                f"active={total} export_st={st_exp}",
                ms_exp,
                bugs,
            )

    # --- 10. Save while detection running (concurrent upload) ---
    sid_a = new_session()
    sid_b = new_session()
    if WAREHOUSE.is_file():
        import threading

        upload_result: dict[str, Any] = {}
        save_result: dict[str, Any] = {}

        def do_upload():
            st, data, ms = upload_bytes(sid_a, WAREHOUSE.name, WAREHOUSE.read_bytes(), timeout=300)
            upload_result.update(status=st, data=data, ms=ms)

        def do_save():
            time.sleep(0.05)
            st, data, ms = req("POST", "/save", headers={"X-Session-Id": sid_b})
            save_result.update(status=st, data=data, ms=ms)

        t = threading.Thread(target=do_upload)
        t.start()
        do_save()
        t.join(timeout=300)
        bugs = []
        if save_result.get("status") == 200:
            bugs.append(
                Bug(
                    "BUG-014",
                    "medium",
                    "validation",
                    "Save succeeds on empty session during other upload",
                    "Concurrent upload on session A, save on empty session B",
                    "404 on B",
                    f"B save status={save_result.get('status')}",
                )
            )
        record(
            "Save while detection running",
            upload_result.get("status") == 200,
            f"upload_st={upload_result.get('status')} upload_ms={upload_result.get('ms',0):.0f} "
            f"parallel_save_st={save_result.get('status')}",
            float(upload_result.get("ms", 0)),
            bugs,
        )

    # --- 11. Save interrupt / partial write check ---
    sid = new_session()
    if WAREHOUSE.is_file():
        st, up, ms = upload_bytes(sid, WAREHOUSE.name, WAREHOUSE.read_bytes(), timeout=180)
        if st == 200:
            st_s, saved, ms_s = req("POST", "/save", headers={"X-Session-Id": sid})
            paths = saved.get("paths", {})
            bugs = []
            for fmt, rel in paths.items():
                p = PROJECT_ROOT / rel.replace("/", "\\")
                if not p.is_file() or p.stat().st_size == 0:
                    bugs.append(
                        Bug(
                            "BUG-015",
                            "critical",
                            "corruption",
                            f"Save produced empty/missing {fmt} file",
                            "POST /save after valid upload",
                            "Non-zero output files",
                            f"{p} exists={p.is_file()}",
                        )
                    )
                else:
                    # JSON must be valid
                    if fmt == "json":
                        try:
                            payload = json.loads(p.read_text(encoding="utf-8"))
                            if payload.get("polygon_count", 0) <= 0:
                                bugs.append(
                                    Bug(
                                        "BUG-016",
                                        "high",
                                        "corruption",
                                        "Saved JSON has zero polygon_count",
                                        "Save after detection",
                                        "polygon_count > 0",
                                        str(payload.get("polygon_count")),
                                    )
                                )
                        except json.JSONDecodeError as exc:
                            bugs.append(
                                Bug(
                                    "BUG-017",
                                    "critical",
                                    "corruption",
                                    "Saved JSON is invalid",
                                    "POST /save",
                                    "Valid JSON",
                                    str(exc),
                                )
                            )
            record("Save integrity", st_s == 200 and not bugs, f"paths={list(paths.keys())}", ms_s, bugs)

    # --- 12. Seed recovery on invalid area ---
    sid = new_session()
    if WAREHOUSE.is_file():
        st, up, ms = upload_bytes(sid, WAREHOUSE.name, WAREHOUSE.read_bytes(), timeout=180)
        if st == 200:
            # Far outside drawing
            st_p, prev, ms_p = req(
                "POST",
                "/recover/preview",
                {"x": 9.9e9, "y": 9.9e9},
                headers={"X-Session-Id": sid},
            )
            bugs = []
            if st_p == 200:
                bugs.append(
                    Bug(
                        "BUG-018",
                        "high",
                        "validation",
                        "Seed preview succeeds far outside drawing",
                        "Click seed at (9.9e9, 9.9e9)",
                        "422 no_boundary or outside_walls",
                        "preview returned ok",
                    )
                )
            elif st_p == 422:
                msg = str(prev.get("detail", ""))
                if "no_boundary" not in msg.lower() and "could not recover" not in msg.lower():
                    bugs.append(
                        Bug(
                            "BUG-019",
                            "low",
                            "message",
                            "Seed failure message not user-friendly",
                            "Seed outside drawing",
                            "Clear 'no closed region' message",
                            msg[:200],
                        )
                    )
            # NaN coordinates
            st_nan, nan_res, _ = req(
                "POST",
                "/recover/preview",
                {"x": "nan", "y": 0},
                headers={"X-Session-Id": sid},
            )
            if st_nan not in (400, 422):
                bugs.append(
                    Bug(
                        "BUG-020",
                        "medium",
                        "validation",
                        "Non-numeric seed coordinates not rejected at API",
                        "POST recover with x='nan'",
                        "400 validation error",
                        f"HTTP {st_nan}",
                    )
                )
            record(
                "Seed recovery invalid area",
                st_p in (404, 409, 422),
                f"far_point status={st_p} nan_status={st_nan}",
                ms_p,
                bugs,
            )

    # --- 13. Scene without upload ---
    sid = new_session()
    st, scene, ms = req("GET", "/scene", headers={"X-Session-Id": sid})
    record("Scene without upload", st == 404, f"status={st}", ms)

    # --- 14. Delete nonexistent polygon ---
    sid = new_session()
    st, res, ms = req("POST", "/polygon/999999/delete", headers={"X-Session-Id": sid})
    record("Delete missing polygon", st == 404, f"status={st}", ms)

    return results


def write_bug_report(results: list[QAResult], out_path: Path) -> None:
    all_bugs: list[Bug] = []
    for r in results:
        all_bugs.extend(r.bugs)

    passed = sum(1 for r in results if r.passed)
    lines = [
        "# INT Zone Studio — Aggressive QA Bug Report",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Tests run:** {len(results)} | **Passed:** {passed} | **Failed:** {len(results) - passed}",
        f"**Bugs found:** {len(all_bugs)}",
        "",
        "## Executive Summary",
        "",
    ]

    if not all_bugs:
        lines.append("No confirmed defects from automated harness. Manual UI tests still recommended for close-during-save and canvas rendering at scale.")
    else:
        sev = {}
        for b in all_bugs:
            sev[b.severity] = sev.get(b.severity, 0) + 1
        lines.append(
            f"Automated testing found **{len(all_bugs)}** issues: "
            + ", ".join(f"{k}: {v}" for k, v in sorted(sev.items()))
        )

    lines.extend(["", "## Test Results", "", "| Test | Result | Detail |", "| --- | --- | --- |"])
    for r in results:
        lines.append(f"| {r.name} | {'PASS' if r.passed else '**FAIL**'} | {r.detail[:120]} |")

    if all_bugs:
        lines.extend(["", "## Bug Details", ""])
        for b in all_bugs:
            lines.extend(
                [
                    f"### {b.id}: {b.title}",
                    "",
                    f"- **Severity:** {b.severity}",
                    f"- **Category:** {b.category}",
                    f"- **Component:** {b.component}",
                    f"- **Steps:** {b.steps}",
                    f"- **Expected:** {b.expected}",
                    f"- **Actual:** {b.actual}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Manual / Not Automated",
            "",
            "| Scenario | Notes |",
            "| --- | --- |",
            "| Close application during save | Requires Tauri process kill; risk of partial DXF if killed mid-write |",
            "| Canvas freeze at 10k polygons | Frontend CadCanvas must be profiled separately |",
            "| Invalid DWG without ODA | User-facing message depends on ODA install state |",
            "",
            "## Recommendations",
            "",
            "1. Block export UI when `counts.total === 0` (mirror API 404).",
            "2. Reject empty uploads before parsing (check `len(content)==0`).",
            "3. Cap undo history memory for large drawings (deepcopy of 600+ polygons × 30).",
            "4. Add scene pagination or ring simplification for >2000 polygons.",
            "5. Atomic save: write to `.tmp` then rename.",
            "",
        ]
    )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nBug report written to {out_path}")


def main() -> int:
    try:
        ensure_engine()
    except RuntimeError as exc:
        print(f"FATAL: {exc}")
        return 2

    print("=== Aggressive QA Test Suite ===\n")
    results = run_tests()
    report_path = PROJECT_ROOT / "output" / "qa_bug_report.md"
    write_bug_report(results, report_path)

    all_bugs = [b for r in results for b in r.bugs]
    failed = [r for r in results if not r.passed]
    print(f"\n=== Summary: {len(results) - len(failed)}/{len(results)} tests passed, {len(all_bugs)} bugs ===")
    return 1 if failed or all_bugs else 0


if __name__ == "__main__":
    sys.exit(main())
