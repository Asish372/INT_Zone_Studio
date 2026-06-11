#!/usr/bin/env python3
"""Smoke-test the bundled detection engine before shipping the installer."""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_EXE = (
    REPO_ROOT
    / "desktop"
    / "studio"
    / "src-tauri"
    / "resources"
    / "engine"
    / "int-zone-engine"
    / "int-zone-engine.exe"
)
ODA_EXE = (
    REPO_ROOT
    / "desktop"
    / "studio"
    / "src-tauri"
    / "resources"
    / "oda"
    / "ODAFileConverter.exe"
)


def main() -> int:
    if not ENGINE_EXE.exists():
        print(f"ERROR: engine not built at {ENGINE_EXE}")
        return 1

    env = dict(**__import__("os").environ)
    env["INT_ZONE_DATA_DIR"] = str(REPO_ROOT / "output" / "_engine_bundle_test")
    if ODA_EXE.is_file():
        env["INT_ZONE_ODA_PATH"] = str(ODA_EXE)
        oda_dir = str(ODA_EXE.parent)
        env["PATH"] = oda_dir + __import__("os").pathsep + env.get("PATH", "")

    proc = subprocess.Popen(
        [str(ENGINE_EXE)],
        cwd=ENGINE_EXE.parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    deadline = time.time() + 45
    while time.time() < deadline:
        if proc.poll() is not None:
            out = (proc.stdout.read() if proc.stdout else b"").decode("utf-8", "replace")
            err = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", "replace")
            print("ERROR: engine exited early")
            if out.strip():
                print(out)
            if err.strip():
                print(err)
            return 1
        try:
            with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as resp:
                if resp.status == 200:
                    print("OK: engine health check passed")
                    proc.terminate()
                    proc.wait(timeout=10)
                    return 0
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)

    proc.kill()
    print("ERROR: engine did not become healthy in time")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
