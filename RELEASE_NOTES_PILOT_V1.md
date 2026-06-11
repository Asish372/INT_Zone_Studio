# Release Notes — INT Zone Studio · Pilot Evaluation Build v1

**Version:** `0.1.0-pilot.1`  
**Tag:** `pilot-v1`  
**Status:** Pilot Validation — not a production or commercial release

---

## What this build is

INT Zone Studio is offered as a **Pilot Evaluation Build** for real slab-drawing workflows with structural engineers. The goal is to validate the core workflow and collect structured feedback — not to ship a finished product.

**Client language:** INT Zone Studio · Pilot Evaluation Build v1

---

## Supported workflow

```
Import Drawing → Automatic Detection → Review → Recovery → Save Project → Reopen Project → Export Package
```

---

## Detection workflow

1. **Import Drawing** — DXF or DWG from Welcome screen or Home → Import.
2. **Automatic Detection** — Detection → Run Detection. Polygons are detected from CAD geometry and shown on the canvas and in the Polygon Table.
3. **Review** — Select polygons, set review status (Approve / Reject / Needs Review), and run Validation when the original CAD source is available.
4. **Statistics** — Detection menu shows detected count, missing count (when expected count is set), and coverage %.

**Re-run Detection — read carefully:** Re-run refreshes the **current session view**. It does **not** re-import the drawing from disk and does **not** discard manual review work or recoveries already in the session. If you need a fresh import, use Import Drawing again.

---

## Suspected gaps workflow

1. Run **Validation** (Detection or Review tab) when CAD is available.
2. Open the **Suspected Gaps** panel from the validation results.
3. Click a gap entry to pan/zoom to the suspected missing region.
4. Use **Seed Recovery** (Detection → Seed Recovery, or tool **A**) and click on the canvas to recover a missing polygon.
5. **Primary pilot signal:** Did the gap list get you to the right cell, and was recovery useful?

---

## Save / Open workflow

| Action | How |
|--------|-----|
| **Save Workspace** | Home → Save Workspace (Ctrl+S). A dialog asks for the **full file path** (example: `C:\Projects\MyDrawing.pjson`). |
| **Save Workspace As** | Home → Save Workspace As — same path entry pattern. |
| **Open Project** | Welcome or Home → Open Project — uses a file picker for saved `.pjson` workspace files. |

**Open Project ≠ Import Drawing.** Import starts a new session from CAD. Open restores a saved workspace.

**Expected pilot friction (#1):** Save has no browse button — engineers must type or paste the full path. Facilitator should brief this before the first save. Note all confusion verbatim in `PILOT_FEEDBACK.md`; do not treat this as a pilot failure by itself.

---

## Export workflow

1. Home → **Export** (or Export button in workspace).
2. For pilot sessions, prefer **Export Project Package** — PDF, DXF, CSV, and Excel in one output folder.
3. Use **Open folder** on the success panel to locate files.

Other export formats (DXF only, Excel only, etc.) are available but not required for Round 1 metrics.

---

## Pilot feedback

- **Help → Export Pilot Feedback Template** — opens or downloads `PILOT_FEEDBACK.md` for per-drawing notes.
- **Metrics CSV** — `pilot_metrics_template.csv` for quantitative session capture (one row per drawing).

No in-app analytics, telemetry, tracking, or cloud sync in this build.

### Top 5 questions (Round 1 — answer these before collecting feature requests)

1. Was the **detection count believable**?
2. Were **suspected gaps useful**?
3. Did **recovery** lead to a missing cell?
4. Was **save/reopen** understandable?
5. Was the **export package** useful as a deliverable?

If you get 20 feature requests but no clear answers to these five, Round 1 has not yet validated the product.

---

## Known limitations

| Area | Limitation |
|------|------------|
| Save | No browse button — full path must be typed or pasted (expected friction #1) |
| Re-run Detection | Refreshes current session view only; does not re-import CAD or wipe manual work |
| Recent Projects | Not available — use Open Project |
| Search | No global search bar |
| AI recovery | Not included |
| Cloud sync | Not included |
| Scale display | Status bar shows static `1:100` — not drawing-derived |
| DWG | Depends on local CAD conversion support |
| Menu scope | Only shipped commands appear; no “coming soon” stubs in menus |

---

## Round 1 exit criteria

| Criterion | Target |
|-----------|--------|
| Crashes | 0 |
| Data loss | 0 |
| Save/Reopen success | ≥ 90% |
| Export success | ≥ 90% |
| Useful gap-guided recovery | ≥ 1 per pilot round |

---

## During pilot

**Learn, not build.** Note feature requests (Recent Projects, search, AI recovery, save picker) in feedback — do not expect them in v1.

---

*Frozen at `pilot-v1`. Allowed changes: crash fixes, data-loss fixes, pilot feedback fixes, small UX polish, client language corrections.*
