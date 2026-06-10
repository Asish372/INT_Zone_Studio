# INT Zone Studio

Professional CAD workspace for slab pour-cell polygon detection and review.

## Prerequisites

- Python 3.10+ with project dependencies (`pip install -r requirements.txt` from repo root)
- Node.js 18+
- Rust toolchain (optional, for `tauri dev` / `tauri build`)

## Development (web + sidecar)

Terminal 1 — start the Python detection engine:

```bash
cd ../..
python scripts/run_polygon_workspace.py
```

Terminal 2 — start the React UI:

```bash
cd desktop/studio
npm install
npm run dev
```

Open http://localhost:1420

## Tauri desktop

Requires Rust. The Tauri host spawns the Python sidecar on launch.

```bash
npm run tauri:dev
```

## Features (Level 1 MVP)

- DXF/DWG upload with auto polygon detection
- Interactive CAD viewer (pan, zoom, wheel, fit, window zoom, minimap)
- Polygon selection and properties panel
- Seed recovery with preview + confirm
- Layer visibility and polygon table
- Export DXF, CSV, JSON, `.pjson`
- Light / dark theme (follows system by default)

## Theme

Settings → Appearance: System / Light / Dark. Canvas stays white in both modes.
