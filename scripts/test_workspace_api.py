#!/usr/bin/env python3
"""Quick HTTP smoke test for polygon workspace API."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
BASE = "http://127.0.0.1:8765"


def main() -> int:
    req = Request(f"{BASE}/session", method="POST")
    with urlopen(req, timeout=30) as resp:
        session = json.loads(resp.read().decode())["session_id"]

    boundary = "----boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{WAREHOUSE.name}"\r\n'
        "Content-Type: application/dxf\r\n\r\n"
    ).encode() + WAREHOUSE.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = Request(f"{BASE}/upload", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("X-Session-Id", session)
    with urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    print("upload count:", data["polygon_count"])
    assert data["polygon_count"] == 618
    assert data["counts"]["total"] == 618

    export_req = Request(
        f"{BASE}/export",
        data=json.dumps({"formats": ["json", "dxf", "csv"], "use_timestamp": True}).encode(),
        method="POST",
    )
    export_req.add_header("Content-Type", "application/json")
    export_req.add_header("X-Session-Id", session)
    with urlopen(export_req, timeout=60) as resp:
        save = json.loads(resp.read().decode())
    print("export:", save["paths"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
