# Changelog

All notable releases of **INT Zone Studio** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versioning for the pilot line: `0.1.0-pilot.N`.

---

## [0.1.0-pilot.1] — 2026-06-11

**Tag:** `pilot-v1` · **Pilot Evaluation Build v1**

### Added

- Desktop app (Tauri + React) with bundled detection engine — no Python install for end users
- Import DXF and DWG slab drawings
- Automatic pour-cell polygon detection from CAD geometry
- Interactive CAD viewer (pan, zoom, minimap, layer visibility)
- Polygon table with review status (Approve / Reject / Needs Review)
- Validation workflow with **Suspected Gaps** panel
- Seed recovery — click on canvas to recover missing polygons
- Save / reopen workspace projects (`.pjson`)
- Export: DXF, CSV, JSON, Excel, and **Export Project Package**
- CLI batch processing via `main.py`
- Pilot feedback template and metrics CSV
- Windows NSIS standalone installer

### Pilot workflow (supported)

```
Import Drawing → Automatic Detection → Review → Recovery → Save Project → Reopen Project → Export Package
```

### Known limitations

- Save workspace requires typing full file path (no browse dialog)
- Re-run Detection refreshes session view only
- No Recent Projects, search, AI recovery, or cloud sync
- Local-only — no telemetry

### Downloads

- **Windows installer:** [GitHub Release v0.1.0-pilot.1](https://github.com/Asish372/INT_Zone_Studio/releases/tag/v0.1.0-pilot.1)
- Full notes: [RELEASE_NOTES_PILOT_V1.md](RELEASE_NOTES_PILOT_V1.md)

---

## Upcoming

Items noted during pilot — **not committed to v1**:

- Save dialog with file browser
- Recent projects list
- Drawing-derived scale in status bar

See [docs/V2_ROADMAP.md](docs/V2_ROADMAP.md) for post-pilot direction (internal).
