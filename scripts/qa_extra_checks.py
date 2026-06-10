#!/usr/bin/env python3
"""Supplementary QA checks."""
from __future__ import annotations

import copy
import json
import sys
import time
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from desktop.engine_sidecar.session_store import create_session  # noqa: E402
from desktop.engine_sidecar.workspace_history import HistoryStack  # noqa: E402

BASE = "http://127.0.0.1:8765"
WAREHOUSE = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"


def req(method, path, data=None, headers=None):
    import urllib.error
    import urllib.request

    h = dict(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    r = urllib.request.Request(BASE + path, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=180) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def upload(session_id, path: Path):
    import mimetypes

    boundary = f"----b{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mimetypes.guess_type(path.name)[0] or 'application/octet-stream'}\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    import urllib.request

    r = urllib.request.Request(
        BASE + "/upload",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Session-Id": session_id,
        },
    )
    import urllib.error

    try:
        with urllib.request.urlopen(r, timeout=300) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def main():
    _, sess = req("POST", "/session")
    sid = sess["session_id"]

    # Export when all polygons soft-deleted
    st, up = upload(sid, WAREHOUSE)
    print("upload", st, up.get("counts"))
    for p in up["scene"]["polygons"]:
        req("POST", f"/polygon/{p['id']}/delete", headers={"X-Session-Id": sid})
    _, summary = req("GET", "/summary", headers={"X-Session-Id": sid})
    print("after delete all:", summary.get("counts"))
    st_exp, exp = req("POST", "/export", {"formats": ["json"]}, headers={"X-Session-Id": sid})
    print("export all-deleted:", st_exp, exp.get("detail"), exp.get("polygon_count"))

    # Undo history memory
    session = create_session()
    big = [{"id": i, "status": "active", "ring": [[0, 0], [1, 0], [1, 1], [0, 1]]} for i in range(618)]
    session.polygons = big
    hist = HistoryStack(max_depth=30)
    hist.seed(big)
    t0 = time.perf_counter()
    for _ in range(30):
        session.polygons = copy.deepcopy(big)
        hist.push(session.polygons)
    print(f"history push 30x618 polys: {(time.perf_counter()-t0)*1000:.0f}ms")

    # DXF with no geometry - minimal valid dxf
    minimal = PROJECT_ROOT / "output" / "qa_fixtures" / "minimal.dxf"
    minimal.write_text(
        "0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n1\n"
        "0\nLAYER\n2\n0\n70\n0\n62\n7\n6\nCONTINUOUS\n0\nENDTAB\n0\nENDSEC\n"
        "0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n",
        encoding="ascii",
    )
    _, s2 = req("POST", "/session")
    st2, up2 = upload(s2["session_id"], minimal)
    print("minimal dxf:", st2, up2.get("polygon_count"), up2.get("detail"))


if __name__ == "__main__":
    main()
