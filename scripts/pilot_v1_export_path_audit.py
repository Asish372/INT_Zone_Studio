#!/usr/bin/env python3
"""Pilot-v1 export path audit — reproduces/closes DEF-ENV-002."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
PILOT = REPO / "release" / "INT-Zone-Studio-Pilot-v1"
WAREHOUSE = REPO / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf"
ENGINE = "http://127.0.0.1:8765"


def port_open() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 8765), timeout=1):
            return True
    except OSError:
        return False


def kill_port_holder() -> None:
    import subprocess as sp

    out = sp.check_output(
        ["powershell", "-NoProfile", "-Command",
         "(Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess"],
        text=True,
    ).strip()
    if out.isdigit() and int(out) > 0:
        sp.run(["taskkill", "/F", "/PID", out], check=False)


def start_pilot() -> subprocess.Popen:
    py = REPO / ".venv" / "Scripts" / "python.exe"
    if not py.is_file():
        py = Path(sys.executable)
    proc = subprocess.Popen(
        [str(py), str(PILOT / "scripts" / "run_polygon_workspace.py")],
        cwd=str(PILOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(80):
        if port_open():
            r = httpx.get(f"{ENGINE}/scope/config", timeout=2)
            if r.status_code == 404:
                return proc
        time.sleep(0.25)
    proc.kill()
    raise RuntimeError("Pilot engine did not start")


def main() -> int:
    if not WAREHOUSE.is_file():
        print("Missing warehouse DXF")
        return 1

    kill_port_holder()
    time.sleep(1)
    proc = start_pilot()
    client = httpx.Client(timeout=300, base_url=ENGINE)
    try:
        sid = client.post("/session").json()["session_id"]
        h = {"X-Session-Id": sid}
        with WAREHOUSE.open("rb") as fh:
            client.post("/upload", headers=h, files={"file": (WAREHOUSE.name, fh, "application/octet-stream")}).raise_for_status()
        r = client.post("/export", headers={**h, "Content-Type": "application/json"}, json={"formats": ["package"], "use_timestamp": True})
        r.raise_for_status()
        export = r.json()

        checks = []
        for key, rel in export.get("paths", {}).items():
            repo_p = REPO / rel.replace("/", "\\")
            pilot_p = PILOT / rel.replace("/", "\\")
            abs_p = Path((export.get("absolute_paths") or {}).get(key, pilot_p))
            checks.append({
                "format": key,
                "relative": rel,
                "repo_exists": repo_p.is_file() and repo_p.stat().st_size > 0,
                "pilot_exists": pilot_p.is_file() and pilot_p.stat().st_size > 0,
                "absolute_exists": abs_p.is_file() and abs_p.stat().st_size > 0,
                "pilot_path": str(pilot_p),
            })

        false_missing = [c for c in checks if not c["repo_exists"] and c["pilot_exists"]]
        report = {
            "def_env_002_reproduced": bool(false_missing),
            "verdict": (
                "FALSE POSITIVE — export files exist under pilot-v1 PROJECT_ROOT; "
                "QA checked repo root paths only."
                if false_missing
                else "Files missing under both roots — investigate export failure."
            ),
            "export_folder": export.get("folder"),
            "checks": checks,
        }
        out = REPO / "output" / "pilot_v1_export_path_audit.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        print(f"\nReport: {out}")
        return 0
    finally:
        client.close()
        proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
