# User Guide — INT Zone Studio

**Pilot Evaluation Build v1** · `0.1.0-pilot.1`

This guide covers the **only supported workflow** in the pilot build.

---

## Workflow overview

```
Import Drawing
      ↓
Automatic Detection
      ↓
Review
      ↓
Recovery (when needed)
      ↓
Save Project
      ↓
Reopen Project
      ↓
Export Package
```

---

## 1. Import drawing

**Welcome screen** or **Home → Import Drawing**

- Choose a slab plan in **DXF** or **DWG**.
- Wait for the drawing to load. Large files may take up to a minute.

> **Open Project** is different: it restores a saved `.pjson` workspace, not a new CAD file.

---

## 2. Run detection

**Detection → Run Detection**

- The engine finds enclosed pour-cell polygons from wall/beam geometry.
- Results appear on the canvas and in the **Polygon Table**.
- Check **Detection** menu for counts: detected, missing (if expected count set), coverage %.

### Re-run detection

**Detection → Re-run Detection** refreshes the **current session view**. It does **not**:

- Re-import the file from disk
- Discard manual review or recoveries already in the session

For a fresh import, use **Import Drawing** again.

---

## 3. Review polygons

1. Select polygons on the canvas or in the **Polygon Table**.
2. Set review status: **Approve**, **Reject**, or **Needs Review**.
3. Inspect properties in the side panel.

When the original CAD source is available, run **Validation** (Detection or Review tab) to compare detected cells against the drawing.

---

## 4. Suspected gaps and recovery

Primary pilot question: *Did the gap list get you to the right missing cell, and was recovery useful?*

1. Run **Validation** when CAD is available.
2. Open **Suspected Gaps** from validation results.
3. Click a gap entry — the viewer pans/zooms to the suspected region.
4. Use **Seed Recovery** (**Detection → Seed Recovery**, or tool **A**).
5. Click on the canvas where a cell should be; confirm the preview, then accept.

Repeat until the slab layout matches your engineering judgment.

---

## 5. Save project

| Action | Menu | Shortcut |
|--------|------|----------|
| Save Workspace | Home → Save Workspace | Ctrl+S |
| Save Workspace As | Home → Save Workspace As | — |

**Pilot note:** You must type or paste the **full file path**, for example:

```
C:\Projects\Warehouse-S111.pjson
```

There is no browse button in pilot v1. Plan the folder before your first save.

---

## 6. Reopen project

**Welcome** or **Home → Open Project**

- Uses a file picker for `.pjson` workspace files.
- Restores polygons, review state, and session data from your last save.

---

## 7. Export

**Home → Export**

For pilot sessions, prefer **Export Project Package** — PDF, DXF, CSV, and Excel in one output folder.

Use **Open folder** on the success panel to locate deliverables.

Individual formats (DXF only, Excel only, etc.) are available but not required for pilot metrics.

---

## Pilot feedback

Help improve the product:

- **Help → Export Pilot Feedback Template** — session notes template
- [`pilot_metrics_template.csv`](../../pilot_metrics_template.csv) — one row per drawing

---

## Keyboard shortcuts (common)

| Shortcut | Action |
|----------|--------|
| Ctrl+S | Save Workspace |
| A | Seed Recovery tool (when active) |

See in-app menus for the full list shipped in pilot v1.

---

## What is out of scope in v1

- Recent Projects list
- Global search
- AI-assisted recovery
- Cloud sync or telemetry

Note these in feedback; they are tracked for post-pilot planning only.

---

## More help

- [FAQ](FAQ.md)
- [Installation](INSTALLATION.md)
- [Release notes](../../RELEASE_NOTES_PILOT_V1.md)
