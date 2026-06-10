"""Golden workflow verification against engine sidecar API."""
from __future__ import annotations

import json
import mimetypes
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8765"
WAREHOUSE = PROJECT_ROOT / "output" / "polygon_workspace" / "uploads" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"


def req(method: str, path: str, data=None, headers: dict | None = None):
    url = BASE + path
    body = None
    h = dict(headers or {})
    if data is not None and not isinstance(data, bytes):
        body = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(request, timeout=180) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return e.code, payload
    except Exception as e:
        return 0, {"error": str(e)}


def upload_file(session_id: str, file_path: Path):
    try:
        import httpx  # type: ignore
    except ImportError:
        httpx = None

    if httpx is not None:
        with httpx.Client(timeout=180.0) as client:
            with file_path.open("rb") as fh:
                response = client.post(
                    f"{BASE}/upload",
                    headers={"X-Session-Id": session_id},
                    files={"file": (file_path.name, fh, "application/dxf")},
                )
            try:
                payload = response.json()
            except json.JSONDecodeError:
                payload = {"detail": response.text}
            return response.status_code, payload

    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + file_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "X-Session-Id": session_id,
    }
    return req("POST", "/upload", data=body, headers=headers)


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str):
        results.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")

    st, health = req("GET", "/health")
    check("Engine health", st == 200, str(health))

    st, sess = req("POST", "/session")
    session_id = sess.get("session_id", "")
    check("Create session", st == 200 and bool(session_id), session_id or str(sess))

    if not WAREHOUSE.is_file():
        check("Warehouse file exists", False, str(WAREHOUSE))
        _print_summary(results)
        return 1

    st, up = upload_file(session_id, WAREHOUSE)
    counts = up.get("counts", {})
    total = counts.get("total", 0)
    upload_detail = up.get("detail") or up.get("error") or ""
    check(
        "Upload Warehouse DXF",
        st == 200 and total >= 600,
        f"status={st} total={total} detected={counts.get('detected')} detail={upload_detail}",
    )

    st, scene = req("GET", "/scene", headers={"X-Session-Id": session_id})
    polys = scene.get("scene", {}).get("polygons", [])
    check("Scene polygons renderable", st == 200 and len(polys) >= 600, f"count={len(polys)}")

    if polys:
        pid = polys[0]["id"]
        st, sel = req(
            "POST",
            "/select",
            {"polygon_id": pid},
            headers={"X-Session-Id": session_id},
        )
        check("Polygon select", st == 200 and sel.get("selected_id") == pid, str(sel.get("selected_id")))

    # Use first polygon centroid as a realistic seed probe.
    cx, cy = 0.0, 0.0
    if polys and polys[0].get("centroid"):
        cx, cy = polys[0]["centroid"]
    st, prev = req(
        "POST",
        "/recover/preview",
        {"x": cx + 5000.0, "y": cy + 5000.0},
        headers={"X-Session-Id": session_id},
    )
    check(
        "Seed recovery preview",
        st in (200, 409, 422),
        f"status={st} detail={prev.get('detail', prev.get('message', 'ok'))}",
    )

    st, proj = req("POST", "/projects", {"name": "GoldenTest"})
    project_id = proj.get("project", {}).get("id", "")
    check("Create project", st == 200 and bool(project_id), project_id or str(proj))

    st, saved = req(
        "POST",
        f"/projects/{project_id}/versions",
        {"label": "golden-v1"},
        headers={"X-Session-Id": session_id},
    )
    ver_id = saved.get("version", {}).get("id", "")
    check("Save version", st == 200 and bool(ver_id), ver_id or str(saved))

    st, loaded = req(
        "POST",
        "/projects/load-version",
        {"project_id": project_id, "version_id": ver_id},
        headers={"X-Session-Id": session_id},
    )
    loaded_count = loaded.get("counts", {}).get("total", 0)
    check("Reopen version", st == 200 and loaded_count >= 600, f"total={loaded_count}")

    st, exp = req(
        "POST",
        "/export",
        {"formats": ["dxf", "csv", "pdf", "package"]},
        headers={"X-Session-Id": session_id},
    )
    paths = exp.get("paths", {})
    check(
        "Export DXF/CSV/PDF/package",
        st == 200 and all(k in paths for k in ("dxf", "csv", "pdf")),
        f"paths={list(paths.keys())}",
    )

    for key, rel in paths.items():
        p = PROJECT_ROOT / rel.replace("/", "\\")
        check(f"Export file exists: {key}", p.is_file() and p.stat().st_size > 0, str(p))

    return _print_summary(results)


def _print_summary(results: list[tuple[str, bool, str]]) -> int:
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n=== Golden Workflow: {passed}/{total} passed ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
