"""PyInstaller entrypoint for the bundled detection engine."""

from __future__ import annotations

from desktop.engine_sidecar.api import main

if __name__ == "__main__":
    main()
