#!/usr/bin/env python3
"""Phase 1 slab boundary verification (API + persistence)."""

from __future__ import annotations

import json
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_DXF = (
    PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
)
BASE = "http://127.0.0.1:8765"


class Check:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        line = f"[{mark}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)

    def all_passed(self) -> bool:
        return all(ok for _, ok, _ in self.results)


def _request(
    method: str,
    path: str,
    *,
    session_id: str | None = None,
    body: dict | None = None,
    files: dict | None = None,
) -> tuple[int, dict]:
    headers: dict[str, str] = {}
    if session_id:
        headers["X-Session-Id"] = session_id
    data: bytes | None = None
    if files:
        import uuid

        boundary = uuid.uuid4().hex
        parts: list[bytes] = []
        for name, (filename, content, ctype) in files.items():
            parts.append(f"--{boundary}\r\n".encode())
            parts.append(
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
            )
            parts.append(f"Content-Type: {ctype}\r\n\r\n".encode())
            parts.append(content)
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def scene_bounds(scene: dict) -> tuple[float, float, float, float]:
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for line in scene.get("cad_lines") or []:
        for i in (0, 2):
            min_x = min(min_x, line[i])
            max_x = max(max_x, line[i])
        for i in (1, 3):
            min_y = min(min_y, line[i])
            max_y = max(max_y, line[i])
    for poly in scene.get("polygons") or []:
        for x, y in poly.get("ring") or []:
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
    return min_x, min_y, max_x, max_y


def rings_equal(a: list, b: list, tol: float = 1e-6) -> bool:
    if len(a) != len(b):
        return False
    for (x1, y1), (x2, y2) in zip(a, b):
        if abs(x1 - x2) > tol or abs(y1 - y2) > tol:
            return False
    return True


def main() -> int:
    check = Check()

    code, health = _request("GET", "/health")
    check.record("Engine reachable", code == 200 and health.get("status") == "ok", str(health))

    code, cfg = _request("GET", "/scope/config")
    scope_on = code == 200 and cfg.get("enabled") is True
    check.record(
        "scope.enabled in config",
        scope_on,
        "Set scope.enabled: true and restart sidecar" if not scope_on else "",
    )
    if not scope_on:
        check.print_summary()
        return 1

    if not WAREHOUSE_DXF.is_file():
        check.record("Warehouse DXF present", False, str(WAREHOUSE_DXF))
        check.print_summary()
        return 1
    check.record("Warehouse DXF present", True, WAREHOUSE_DXF.name)

    code, sess = _request("POST", "/session")
    session_a = sess.get("session_id", "")
    check.record("Create session A", code == 200 and bool(session_a))

    content = WAREHOUSE_DXF.read_bytes()
    code, upload = _request(
        "POST",
        "/upload",
        session_id=session_a,
        files={"file": (WAREHOUSE_DXF.name, content, "application/dxf")},
    )
    scene = upload.get("scene") or {}
    poly_count = len([p for p in scene.get("polygons", []) if p.get("status") != "deleted"])
    check.record(
        "Upload warehouse (618 polygons)",
        code == 200 and poly_count == 618,
        f"got {poly_count}",
    )

    min_x, min_y, max_x, max_y = scene_bounds(scene)
    pad_x = (max_x - min_x) * 0.02
    pad_y = (max_y - min_y) * 0.02
    ring = [
        [min_x + pad_x, min_y + pad_y],
        [max_x - pad_x, min_y + pad_y],
        [max_x - pad_x, max_y - pad_y],
        [min_x + pad_x, max_y - pad_y],
    ]

    code, preview = _request(
        "POST",
        "/scope/boundary/preview",
        session_id=session_a,
        body={"ring": ring},
    )
    preview_ring = (preview.get("preview") or {}).get("ring")
    check.record("Boundary preview (draw equivalent)", code == 200 and bool(preview_ring))

    code, committed = _request(
        "PUT",
        "/scope/boundary",
        session_id=session_a,
        body={"ring": ring, "source": "drawn"},
    )
    boundary = (committed.get("scope") or {}).get("boundary") or {}
    area_saved = boundary.get("area_m2")
    ring_saved = boundary.get("ring") or []
    scene_boundary = (committed.get("scene") or {}).get("scope_boundary") or {}
    check.record(
        "Commit boundary to session",
        code == 200 and rings_equal(ring_saved, ring) and bool(scene_boundary.get("ring")),
        f"area={area_saved} m²",
    )

    with tempfile.TemporaryDirectory() as tmp:
        save_path = Path(tmp) / "warehouse_boundary_test.pjson"
        code, save_resp = _request(
            "POST",
            "/workspace/save",
            session_id=session_a,
            body={"path": str(save_path)},
        )
        check.record("Save workspace", code == 200 and save_path.is_file())

        # Simulate app restart: new session, load project file
        code, sess_b = _request("POST", "/session")
        session_b = sess_b.get("session_id", "")
        code, loaded = _request(
            "POST",
            "/workspace/load-project",
            session_id=session_b,
            files={
                "file": (
                    save_path.name,
                    save_path.read_bytes(),
                    "application/json",
                )
            },
        )
        loaded_boundary = ((loaded.get("scene") or {}).get("scope_boundary")) or {}
        loaded_ring = loaded_boundary.get("ring") or []
        loaded_area = loaded_boundary.get("area_m2")
        check.record(
            "Reopen: same vertices after save/load",
            code == 200 and rings_equal(loaded_ring, ring_saved),
            f"{len(loaded_ring)} vertices",
        )
        check.record(
            "Reopen: same area after save/load",
            code == 200 and loaded_area == area_saved,
            f"saved={area_saved} loaded={loaded_area}",
        )

    # Undo removes committed boundary; redo restores it
    code, undo_resp = _request("POST", "/undo", session_id=session_a)
    scene_after_undo = undo_resp.get("scene") or {}
    boundary_after_undo = scene_after_undo.get("scope_boundary")
    check.record(
        "Undo removes boundary",
        code == 200 and boundary_after_undo in (None, {}),
        "boundary cleared after Ctrl+Z equivalent",
    )

    code, redo_resp = _request("POST", "/redo", session_id=session_a)
    scene_after_redo = redo_resp.get("scene") or {}
    redo_ring = (scene_after_redo.get("scope_boundary") or {}).get("ring") or []
    check.record(
        "Redo restores boundary",
        code == 200 and rings_equal(redo_ring, ring_saved),
        f"{len(redo_ring)} vertices",
    )

    # Delete boundary → save → reopen
    code, cleared = _request("DELETE", "/scope/boundary", session_id=session_a)
    check.record("Delete boundary", code == 200 and cleared.get("scope", {}).get("boundary") is None)

    with tempfile.TemporaryDirectory() as tmp2:
        save_path2 = Path(tmp2) / "warehouse_no_boundary.pjson"
        code, _ = _request(
            "POST",
            "/workspace/save",
            session_id=session_a,
            body={"path": str(save_path2)},
        )
        code, sess_c = _request("POST", "/session")
        session_c = sess_c.get("session_id", "")
        code, reloaded = _request(
            "POST",
            "/workspace/load-project",
            session_id=session_c,
            files={
                "file": (
                    save_path2.name,
                    save_path2.read_bytes(),
                    "application/json",
                )
            },
        )
        gone = ((reloaded.get("scene") or {}).get("scope_boundary")) in (None, {})
        scope_null = (json.loads(save_path2.read_text()).get("scope") or {}).get("boundary") is None
        check.record(
            "Delete, save, reopen: boundary gone",
            code == 200 and gone and scope_null,
        )

    check.print_summary()
    return 0 if check.all_passed() else 1


# Monkey-patch helper for summary
def _print_summary(self: Check) -> None:
    passed = sum(1 for _, ok, _ in self.results if ok)
    total = len(self.results)
    print(f"\n=== {passed}/{total} checks passed ===")


Check.print_summary = _print_summary  # type: ignore[method-assign]

if __name__ == "__main__":
    sys.exit(main())
