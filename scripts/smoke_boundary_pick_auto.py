#!/usr/bin/env python3
"""Smoke test for boundary pick/auto API endpoints."""

from __future__ import annotations

import json
import sys
import uuid
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765"
WAREHOUSE = Path("output/.dxf_cache/6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf")


def main() -> int:
    req = urllib.request.Request(f"{BASE}/session", method="POST")
    sid = json.load(urllib.request.urlopen(req, timeout=30))["session_id"]
    content = WAREHOUSE.read_bytes()
    boundary = uuid.uuid4().hex
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{WAREHOUSE.name}"\r\n'.encode(),
        b"Content-Type: application/dxf\r\n\r\n",
        content,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request(
        f"{BASE}/upload",
        data=b"".join(parts),
        headers={
            "X-Session-Id": sid,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=300)

    req = urllib.request.Request(
        f"{BASE}/scope/boundary/candidates",
        headers={"X-Session-Id": sid},
    )
    cands = json.load(urllib.request.urlopen(req, timeout=60))["candidates"]
    print(f"candidates={len(cands)}")

    req = urllib.request.Request(
        f"{BASE}/scope/boundary/auto",
        headers={"X-Session-Id": sid},
        method="POST",
    )
    auto = json.load(urllib.request.urlopen(req, timeout=120))["preview"]
    print(f"auto area={auto['area_m2']} source={auto['source']}")

    if cands:
        ring = cands[0]["ring"]
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        req = urllib.request.Request(
            f"{BASE}/scope/boundary/pick",
            data=json.dumps({"x": cx, "y": cy}).encode(),
            headers={"X-Session-Id": sid, "Content-Type": "application/json"},
            method="POST",
        )
        pick = json.load(urllib.request.urlopen(req, timeout=60))["preview"]
        print(f"pick area={pick['area_m2']} source={pick['source']}")

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
