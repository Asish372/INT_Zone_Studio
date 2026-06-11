# INT Zone Studio — V2 Roadmap (Planning Only)

**Status:** Planning document — **no implementation during `pilot-v1`**  
**Date:** 2026-06-10  
**Freeze tag:** `pilot-v1` remains authoritative until Round 1 exit evaluation passes  
**Audience:** Product, engineering, pilot facilitators

---

## Purpose

This roadmap defines what V2 means after pilot validation — without changing pilot-v1 code or workflow.

**V2 thesis (evidence-backed):**

> Polygons are implementation. INT zones are product.

Pilot-v1 learns whether engineers think in polygons or zones. V2 ships the engine that already passes manifest validation in CLI, with Studio as the primary surface.

---

## What V2 is not

| Out of scope for initial V2 | Notes |
|------------------------------|-------|
| Pilot-v1 workflow redesign | Same 7 steps: Import → Detect → Review → Recovery → Save → Reopen → Export |
| New menus during pilot | Note feedback only |
| AI recovery / cloud sync | Post-V2 or never |
| Full slab-scope editor (user-drawn boundary) | V2.1+ — see §6 |
| Real-time zone rebuild on every polygon edit | Deferred unless pilot proves necessity |

---

## Current state (baseline)

### Two-stage architecture today

```
Stage 1 — Detection (aligned)
  CAD → gap close → polygonize → micro-faces (e.g. 618)
  CLI and Studio produce identical face counts.

Stage 2 — Zone aggregation (divergent)
  CLI:  build_int_zone_pipeline → 24 manifest-aligned INT zones  ✓ authoritative
  Studio: workspace_zones.py heuristic → 18 bbox clusters         ✗ placeholder
```

### Authoritative vs placeholder

| Component | Location | Role |
|-----------|----------|------|
| `build_int_zone_pipeline` | `src/zone_engine/int_zone_pipeline.py` | **Authoritative** — grid bays, face assignment, union geometry, readiness gates |
| `workspace_zones.py` | `desktop/engine_sidecar/` | **Placeholder** — centroid bbox grid; retire in V2 |
| `polygon_records.py` | `desktop/engine_sidecar/` | Face persistence for review/recovery/save |
| `suspected_gaps.py` | `desktop/engine_sidecar/` | Gap list → recovery (pilot primary signal) |
| `workspace_save.py` | `desktop/engine_sidecar/` | Save/open + export package |
| `workspace_validation.py` | `desktop/engine_sidecar/` | Gap + workspace validation |

### Business risk if unchanged

Engineer sees **18 INT zones** in Studio and **24** on slab schedule → trust erodes even when detection (618 faces) is correct.

---

## V2 goals (four pillars)

### 1. Authoritative INT Zone Engine integration

**Objective:** Studio calls the same `build_int_zone_pipeline` the CLI uses. No parallel zone logic.

**Integration contract** (sidecar adapter — planning reference only):

| Input | Source |
|-------|--------|
| Modelspace | `session.dxf_path` → `load_dxf` |
| Config | `config.yaml` → `zone_engine` block |
| Micro-faces | `session.polygons` → `FaceData` adapter |
| Manifest | `reference/*_zones_manifest.yaml` (bundled per drawing profile) |
| Profile | `resolve_zone_profile()` → e.g. `GRID_WAREHOUSE` |

**Critical rule:** Pass workspace polygons as `faces=` with `auto_detect_faces=False` so zone assignment matches what the engineer reviewed — not a silent re-detect.

**Endpoints to rewire (same routes, new implementation):**

| Endpoint | V2 behavior |
|----------|-------------|
| `POST /zones/generate` | `run_zone_pipeline_for_session()` |
| `POST /zones/rebuild` | Re-run after polygon set changes |
| `GET /zones` | Pipeline-backed `ZoneRecord[]` |

**Deprecate:** `generate_int_zones`, heuristic `merge_zones`, `rename_zone` until manifest-override semantics exist.

**New sidecar module (future):** `zone_pipeline_adapter.py` — owns polygon↔face conversion, assignment writeback, union rings for export.

**Bundled assets:** Manifest YAMLs + drawing→manifest routing table in standalone release.

**Success criteria:**

- Studio INT count == CLI INT count == manifest `zone_count_expected`
- Labels `INT-1` … `INT-N` (not `INT-01`)
- Empty zones (0 m²) visible — not omitted
- `manifest_status` per zone available for validation UI

---

### 2. INT Zones as primary user-facing object

**Objective:** Engineer opens Studio and sees **schedule-shaped** data first — not 618 rows.

#### Information architecture shift

| Surface | Pilot-v1 (today) | V2 (target) |
|---------|------------------|-------------|
| Primary table | Polygon table (618 rows) | **INT Zone table** (24 rows) |
| Primary count in status/footer | "618 polygons detected" | "24 INT zones · N faces" |
| Review unit | Individual micro-face | Zone area, coverage %, manifest match |
| Drill-down | — | Expand zone → show assigned faces |
| Gap recovery entry | Suspected Gaps panel | **Unchanged** — still gap-driven |

#### INT Zone table columns (target)

| Column | Source |
|--------|--------|
| Label | `IntZoneData.label` |
| Area (m²) | Union geometry |
| Face count | Assigned micro-faces |
| Coverage % | `bay_coverage_pct` |
| Manifest status | PASS / REVIEW / FAIL |
| Empty flag | 0 m² pour cells |

#### Scenario A vs B (pilot signal → V2 UX)

| Pilot observation | V2 implication |
|-------------------|----------------|
| Engineer cites polygon count first | Keep polygon drill-down prominent; zone table secondary until habit forms |
| Engineer asks "INT zones kitne bane?" | Zone-first default; polygons under "Show faces" |
| Engineer compares Studio zones to schedule | V2 integration is **blocking** for that persona |

**UX principle:** Default to what engineers sign off on (slab schedule / QS deliverable). Polygons remain accessible but not the headline.

---

### 3. Faces / Polygons as secondary diagnostic objects

**Objective:** Micro-faces stay in the engine and in recovery — they are not removed, only demoted in UI hierarchy.

#### Role clarity

| Object | Role | User action |
|--------|------|-------------|
| **INT Zone** | Business deliverable; export primary | Review area, manifest match, approve package |
| **Face / Polygon** | Detection artifact; gap target | Recover missing cell; approve/reject individual face |
| **Suspected Gap** | Navigation aid | Click → recover → new face |

#### What stays polygon-centric (by design)

- Seed-assisted recovery (`POST /recover`, `POST /recover/preview`)
- Suspected gaps list (`suspected_gaps.py`)
- Polygon approve/reject/delete
- `*_corrected_polygons.*` debug exports in package

#### What changes

- Polygon table: secondary panel or zone drill-down — not default landing
- Status messaging: "618 faces" → diagnostic detail, not hero metric
- `int_zone` on polygon record: denormalized cache from `FaceAssignmentSummary` (authoritative after rebuild)

#### Orphans and slivers

Surface engine diagnostics without hiding them:

- Orphan faces → validation warning + filter in face view
- Sliver faces (unassigned) → informational; do not inflate zone count
- Empty zones (INT-1, INT-8, INT-10 on warehouse) → visible in zone table with 0 m²

---

### 4. Migration path — preserve pilot workflows

Pilot workflow is frozen. V2 must preserve every step engineers are validating now.

```
Import → Detect → Review → Recovery → Save → Reopen → Export
```

#### Per-step preservation map

| Step | Pilot-v1 behavior | V2 change | Preserved? |
|------|-------------------|-----------|------------|
| **Import** | `detect_from_cad_path` → polygons | Unchanged | ✓ |
| **Detect** | Same detection pipeline | Unchanged | ✓ |
| **Review** | Polygon table primary | Zone table primary; faces on drill-down | ✓ (shifted focus, same data) |
| **Recovery** | Gap click → seed recover → new polygon | Same API; set `zones_stale=true` after recover | ✓ |
| **Save** | Workspace JSON v2 | v3 adds pipeline metadata; v2 loader still works | ✓ |
| **Reopen** | Load polygons + zones | Load v2 heuristic zones → prompt Rebuild; v3 loads pipeline zones | ✓ |
| **Export** | Package: polygons dxf/xlsx/csv + zones dxf | Add `int_schedule.xlsx`, union `int_zones.dxf`; keep polygon exports as debug | ✓ (enhanced) |

#### Recovery → zone invalidation

Today recovery does not update `session.zones` — silent staleness.

**V2 rule:**

1. Recovery adds/edits polygon → `zones_stale = true`
2. Actions log: "Zones out of date — run Rebuild Zones"
3. Export package uses last rebuilt zones OR blocks with clear message (product choice at implementation time)
4. Gap list and recovery UX unchanged

#### Save format evolution

| Version | Contents | Migration |
|---------|----------|-----------|
| **v2** (pilot) | `polygons`, heuristic `zones`, `validation` | Baseline |
| **v3** (V2) | + `zone_pipeline_version`, `zone_profile`, `manifest_path`, `readiness`, `zones_stale`; `zones` = `ZoneRecord[]` | v2 opens normally; first Rebuild upgrades zone data |
| **Label migration** | `INT-01` → `INT-1` | One-time on rebuild; acceptable post-pilot |

**Backward compatibility requirement:** Projects saved during pilot-v1 must open in V2 without data loss. Polygons always authoritative for face geometry.

#### Export parity

| Artifact | Pilot-v1 | V2 target | Matches CLI? |
|----------|----------|-----------|--------------|
| Corrected polygons DXF/XLSX/CSV | ✓ | ✓ (debug/diagnostic) | Partial |
| Zones DXF | Member polygons per zone | **Union boundary** per INT zone | ✓ |
| INT schedule Excel | ✗ | ✓ `export_int_schedule_excel` | ✓ |
| Validation report in package | ✓ | ✓ + readiness gates | ✓ |
| PDF summary | If in package | ✓ zone-first narrative | TBD |

#### Validation preservation

`POST /validation` and gap summary stay. V2 **adds** informational overlays — no new required steps.

| Check | Pilot-v1 | V2 additive |
|-------|----------|-------------|
| Recoverable gaps | ✓ | ✓ |
| Open endpoints | ✓ | ✓ |
| Polygon count vs expected | ✓ | Demote; zone count gate replaces for schedule |
| Zone count vs manifest | ✗ (heuristic) | ✓ `zone_count` PASS/FAIL |
| Orphan faces | ✗ | ✓ from assignment summary |
| Empty zones list | ✗ | ✓ INT-1, INT-8, INT-10 visible |
| Per-zone manifest area delta | ✗ | ✓ REVIEW/FAIL badges |

Validation remains **informational** during early V2 — does not block export unless product explicitly gates commercial release.

---

## Implementation phases (post-pilot only)

Gated on Round 1 exit: 0 crashes · 0 data loss · ≥90% save/reopen · ≥90% export · ≥1 useful gap→recovery.

### Phase 0 — Pilot learning (now)

- No code. Real engineer sessions.
- Capture Scenario A vs B (polygon-centric vs zone-centric language).
- Log SDE-2 feedback as `product_direction` — do not build.

### Phase 1 — Engine integration (invisible correctness)

**Goal:** Generate/Rebuild returns authoritative zones; workflow steps unchanged.

| Work package | Effort |
|--------------|--------|
| `zone_pipeline_adapter.py` | Low |
| Wire `/zones/generate`, `/zones/rebuild` | Low |
| `polygon_records_to_faces` + assignment writeback | Low |
| Bundle manifests in release | Low–Medium |
| Recovery → `zones_stale` flag | Low |

**Exit:** Warehouse drawing → Studio 24 zones == CLI 24 zones.

### Phase 2 — Export parity

**Goal:** Export package matches CLI deliverables.

| Work package | Effort |
|--------------|--------|
| Union `int_zones.dxf` | Medium |
| `int_schedule.xlsx` in package | Low |
| Keep polygon exports as diagnostic tier | Low |

**Exit:** Side-by-side diff of Studio export vs `run_int_zone_pipeline` output passes.

### Phase 3 — Save v3 + reopen compat

**Goal:** Pipeline metadata persists; v2 projects open cleanly.

| Work package | Effort |
|--------------|--------|
| Workspace schema v3 | Medium |
| v2 loader + stale rebuild prompt | Medium |
| Label migration on rebuild | Low |

**Exit:** Save pilot-v1 project → open in V2 → Rebuild → identical zone set to fresh import.

### Phase 4 — UX: zone-first surfaces

**Goal:** INT Zone table primary; polygons secondary.

| Work package | Effort |
|--------------|--------|
| Zone table component (primary dock) | Medium |
| Zone expand → faces drill-down | Medium |
| Status footer zone-first copy | Low |
| Deprecate heuristic merge/rename UI | Low |

**Exit:** Engineer completes full workflow without opening polygon table unless recovering.

### Phase 5 — Validation overlay

**Goal:** Readiness gates visible per zone; gap validation unchanged.

| Work package | Effort |
|--------------|--------|
| Readiness panel / per-zone badges | Medium |
| Orphan / empty zone surfacing | Low |

**Exit:** Validation panel shows zone_count PASS and manifest REVIEW rows without new menu items.

### Phase 6 — Retire placeholder

- Remove or stub `workspace_zones.py`
- Document `zone_pipeline_adapter` as sole zone path

**Overall complexity:** Medium (engine exists; risk is save/export/versioning, not algorithms).

---

## V2.1+ horizon (not initial V2)

Captured from pilot / SDE-2 feedback — **note only until V2 core ships:**

| Theme | Description | Depends on |
|-------|-------------|------------|
| User-defined slab boundary | Engineer draws or picks pour perimeter | Zone engine integration |
| Pillars as obstacles | Columns as voids inside scope, not partition lines | Slab scope model |
| Gross vs net area | Export columns for obstacle deductions | Obstacle geometry |
| Manifest override merge/rename | Engineer adjusts bay labels vs schedule | Authoritative zones + policy design |
| Tiered detection mode | Business partition mode vs exhaustive debug | Pilot signal on polygon noise |

---

## Decision gates (when to start V2)

| Gate | Criterion |
|------|-----------|
| **G0 — Pilot complete** | Round 1 exit criteria met |
| **G1 — Persona signal** | ≥1 engineer zone-centric (Scenario B) OR schedule mismatch blocks trust |
| **G2 — No pilot regressions** | Crash/data-loss fixes only during pilot; no feature creep |
| **G3 — Phase 1 ready** | Manifest routing table for pilot drawing set finalized |

If Round 1 fails on gap→recovery usefulness, **fix recovery/gap UX before zone integration** — zone count correctness does not substitute for pilot primary signal.

---

## Success metrics (V2 done)

| Metric | Target |
|--------|--------|
| Studio INT count vs CLI | 100% match on reference drawings |
| Studio INT count vs manifest | 100% match |
| Save → Reopen → zone count | Unchanged |
| Recovery → Rebuild → zone count | Stable; no silent staleness |
| Export package vs CLI | Union DXF + schedule Excel match |
| Pilot workflow steps | 7 steps unchanged |
| Gap→recovery usefulness | ≥ pilot-v1 baseline (must not regress) |

---

## Related documents

| Document | Contents |
|----------|----------|
| `docs/research/studio_zone_engine_alignment.md` | Integration architecture, blockers, file touch map |
| `docs/research/v2_north_star_int_zones.md` | Strategic verdict, warehouse evidence |
| `docs/research/scope_vs_polygon_detection_analysis.md` | Scope/obstacle/pillar product direction |
| `PILOT_V1.md` | Freeze rules, non-authoritative zone count note |
| `.cursor/rules/pilot-validation-mode.mdc` | Agent constraints during pilot |

---

## One-line strategy

**Pilot validates gap→recovery on polygons. V2 makes INT zones the face of the product by wiring Studio to the engine that already passes manifest validation — without breaking save, recovery, or export.**
