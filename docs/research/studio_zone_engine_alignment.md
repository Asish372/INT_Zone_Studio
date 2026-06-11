# Studio ↔ Authoritative INT Zone Engine Alignment

**Status:** Architecture research (no implementation)  
**Date:** 2026-06-10  
**Trigger:** Warehouse drawing — CLI **24** manifest-aligned INT zones vs Studio **18** heuristic clusters; **618** detection faces identical  
**Related:** `docs/research/scope_vs_polygon_detection_analysis.md`, `zone_detection_design.md`

---

## Executive summary

Pilot Studio’s **Generate Zones** path does not call `build_int_zone_pipeline`. It uses a placeholder in `desktop/engine_sidecar/workspace_zones.py` (bounding-box centroid grid). The authoritative zone engine already exists in `src/zone_engine/` and is what CLI scripts, validation reports, and manifest gates use.

**Alignment** means: after polygon detection (unchanged), the sidecar runs the same P2+P3 pipeline the CLI uses, serializes results into the existing session/workspace model, and retires the heuristic grouper.

**Complexity estimate: Medium** (sidecar-only wiring is Low; preserving edit round-trip, save compatibility, and export parity across pilot builds is what raises it).

---

## 1. What is required for Studio to consume the authoritative INT Zone Pipeline?

### 1.1 Minimal integration contract

Studio already has everything needed to *invoke* the pipeline after import:

| Input | Studio today | Pipeline needs |
|-------|--------------|----------------|
| Modelspace | `session.dxf_path` → `load_dxf` → `get_modelspace` | `Modelspace` |
| Config | `_load_config()` → `config.yaml` | `dict` with `zone_engine` block |
| Micro-faces | `session.polygons` (618 records) | `list[FaceData]` |
| Source name | `session.source_file` | `source_file` str |
| Unit scale | `session.unit_scale_m` | `unit_scale_m` |
| Manifest | Not loaded | `manifest_path` → `reference/j33a_zones_manifest.yaml` (per drawing/profile) |
| Profile | Not resolved | `resolve_zone_profile()` → `GRID_WAREHOUSE` |

**Required call shape** (mirrors `zone_mode.process_file_zones` and `scripts/run_int_zone_pipeline.py`):

```python
faces = polygon_records_to_faces(session.polygons)  # new adapter
profile, manifest = resolve_zone_profile(config, manifest_path=resolved_manifest)
zone_cfg = {**config["zone_engine"], "profile": profile}

result = build_int_zone_pipeline(
    msp,
    config,
    source_file=session.source_file,
    unit_scale_m=session.unit_scale_m,
    expected_int_count=manifest.get("zone_count_expected"),
    manifest_path=resolved_manifest,
    faces=faces,
    zone_cfg=zone_cfg,
    auto_detect_faces=False,  # use workspace polygons, not re-detect
)
session.zones = int_zones_to_api_records(result)
apply_face_assignments_to_polygons(session.polygons, result.assignment)
session.zone_pipeline = serialize_pipeline_snapshot(result)  # optional cache for export/gates
```

### 1.2 New sidecar module (replaces `workspace_zones.py` logic)

A thin adapter layer — e.g. `desktop/engine_sidecar/zone_pipeline_adapter.py` — should own:

1. **`polygon_records_to_faces`** — rebuild `FaceData` from workspace polygon rings (respect `status != deleted`).
2. **`int_zones_to_api_records`** — map `IntZoneData` → JSON-safe `ZoneRecord` for API/UI/save.
3. **`apply_face_assignments_to_polygons`** — set `polygon["int_zone"]` from `FaceAssignmentSummary` (authoritative labels `INT-1`…`INT-N`, not `INT-01`).
4. **`run_zone_pipeline_for_session(session)`** — resolve manifest, load msp, call `build_int_zone_pipeline`, update session.
5. **`zone_union_ring(zone: IntZoneData)`** — exterior coords for DXF/scene (replace per-polygon stitching in `save_zones_dxf`).

### 1.3 API surface (unchanged routes, different implementation)

Keep existing endpoints so pilot UI needs no redesign for v1 alignment:

| Endpoint | Today | After alignment |
|----------|-------|-----------------|
| `POST /zones/generate` | `generate_int_zones(polygons)` | `run_zone_pipeline_for_session(session)` |
| `POST /zones/rebuild` | same | same (re-run after polygon edits) |
| `GET /zones` | heuristic list | pipeline-backed list |
| `POST /zones/merge` | heuristic label merge | **defer or gate** — merging structural bays breaks manifest alignment |
| `POST /zones/rename` | string rename | **defer or gate** — labels are manifest-schedule IDs |

### 1.4 Bundled runtime assets

Standalone / PyInstaller sidecar must ship:

- `config.yaml` (already in `src-tauri/resources/`)
- `reference/j33a_zones_manifest.yaml` (and j33b / per-drawing manifests as pilot set grows)
- Optional: drawing→manifest routing table (e.g. warehouse filename → `j33a_zones_manifest.yaml`)

### 1.5 Frontend (out of scope for this doc, but implied)

No UI redesign required for count/label correctness if API record shape is extended compatibly:

```typescript
// Extend IntZone — additive fields only
interface IntZone {
  label: string;           // "INT-1" (not "INT-01")
  area_m2: number;
  volume_m3?: number;
  face_count: number;
  polygon_ids: number[];
  empty?: boolean;
  bay_coverage_pct?: number;
  manifest_status?: "PASS" | "REVIEW" | "FAIL" | "SKIP";
}
```

Scene rendering can continue showing per-polygon fills; zone highlight = filter `polygons where int_zone === label`.

### 1.6 Invalidation rules

Pipeline must re-run when micro-face set changes:

- Import / re-detect
- Seed recovery (`POST /recover`)
- Polygon delete
- Manual polygon edit (if added later)

Today recovery **does not** touch `session.zones` — stale zones are silent. Alignment requires either auto-rebuild or a `zones_stale: true` flag until user runs **Rebuild Zones**.

---

## 2. Dependencies that currently prevent `build_int_zone_pipeline` from the workspace workflow

### 2.1 Architectural / intentional

| Blocker | Detail |
|---------|--------|
| **Placeholder zone module** | `workspace_zones.py` was written as a fast pilot grouper with no CAD grid, slab, or assignment logic. `api.py` imports it directly. |
| **Two-stage product split** | Studio optimized for polygon review + gap recovery; zone engine optimized for CLI delivery. No bridge was built. |
| **Pilot freeze** | No new features — but correcting authoritative zone output is a **data correctness** fix aligned with manifest validation, not a new workflow. |

### 2.2 Session and data model gaps

| Blocker | Detail |
|---------|--------|
| **No `FaceData` round-trip** | `polygon_records.py` converts `FaceData` → record, not the reverse. Recovered/edited polygons exist only as records. |
| **No manifest resolution** | Sidecar never calls `resolve_zone_profile` or `load_manifest`. Expected zone count defaults to `len(polygons)` on import (`expected_polygon_count = len(records)`), conflating faces with zones. |
| **No pipeline result cache** | Session stores `zones: list[dict]` only — no `assignment`, `readiness`, `manifest`, or union geometries for export. |
| **Zones cleared on import** | `session.zones = []` after upload; user must manually Generate. Even then, heuristic runs. |
| **Label namespace mismatch** | Heuristic uses `INT-{cell:02d}`; engine uses `INT-{n}` from `assign_int_labels`. Saved `int_zone` on polygons incompatible across systems. |

### 2.3 Geometry / export mismatches

| Blocker | Detail |
|---------|--------|
| **`save_zones_dxf` draws member polygons** | Iterates `zone.polygon_ids` and exports each micro-face on `INT_ZONES` layer — not `IntZoneData.polygon` union. CLI `export_int_zones_dxf` exports true zone boundaries. |
| **No INT schedule Excel in workspace export** | Package export has polygons xlsx/csv/dxf; CLI has `export_int_schedule_excel`. |
| **Merge/rename semantics** | `merge_zones` / `rename_zone` assume heuristic labels. Incompatible with fixed structural bay grid without override manifest. |

### 2.4 Detection path divergence (secondary)

| Blocker | Detail |
|---------|--------|
| **Stage 1 prep differs** | `detect_pipeline._prepare_segments` uses iterative + tier2 gap close; `int_zone_pipeline.detect_faces_from_modelspace` uses single-pass close. Warehouse both yield 618 today — but edited sessions that re-detect in-engine could diverge. |
| **Recommendation** | When calling pipeline, always pass `faces=` from workspace polygons (`auto_detect_faces=False`) so zone assignment matches what the engineer reviewed. |

### 2.5 Deployment

| Blocker | Detail |
|---------|--------|
| **Manifest not in release bundle** | `reference/*.yaml` exist in repo; pilot zip / tauri resources may not include them. Pipeline gates need bundled manifests or embedded defaults. |
| **Drawing→manifest routing** | CLI uses `--manifest` flag; Studio has no equivalent selection logic. |

---

## 3. Data structures that would replace `workspace_zones.py`

### 3.1 Retire

| File / symbol | Role today |
|---------------|------------|
| `generate_int_zones` | Bbox centroid grid, occupied cells only |
| `merge_zones` | Heuristic merge |
| `rename_zone` | Heuristic rename |

These should be **removed or deprecated** once the adapter is live. Pilot menu entries for merge/rename should be gated until override semantics are defined.

### 3.2 Adopt from `src/zone_engine/models.py`

| Type | Purpose in Studio |
|------|-------------------|
| `FaceData` | Canonical micro-face geometry for assignment input |
| `FaceAssignment` / `FaceAssignmentSummary` | Polygon→bay mapping; drives `int_zone` on records |
| `IntZoneData` | Authoritative zone union, areas, face membership |
| `IntZonePipelineResult` | Full snapshot: geometry, zones, assignment, manifest, readiness |
| `ManifestReconciliation` | Per-zone PASS/REVIEW for UI badges |
| `ProductionReadinessGate` | Console / validation panel |

### 3.3 New API / persistence DTO: `ZoneRecord`

JSON-safe serializable form for session, workspace save, and TypeScript `IntZone`:

```python
@dataclass
class ZoneRecord:
    label: str              # "INT-1"
    zone_id: int
    area_m2: float
    volume_m3: float
    face_count: int
    polygon_ids: list[int]
    face_sum_area_m2: float
    clipped_bay_area_m2: float
    bay_coverage_pct: float
    empty: bool
    ring: list[list[float]] | None   # union boundary for DXF/map
    profile: str
    detection_tier: str
    # Optional manifest overlay
    manifest_area_sqm: float | None
    manifest_delta_pct: float | None
    manifest_status: str | None
```

**Mapping:**

- `IntZoneData` → `ZoneRecord` via `int_zone_data_to_record()`
- `ZoneRecord` is a superset of current frontend `IntZone` (additive migration)

### 3.4 Session extensions

```python
@dataclass
class WorkspaceSession:
    # existing...
    zones: list[dict[str, Any]]           # ZoneRecord as dict
    zone_pipeline_version: int | None       # e.g. 1
    zones_stale: bool = False
    zone_profile: str | None = None
    manifest_path: str | None = None
    readiness: list[dict[str, str]] | None = None  # gate name/status/detail
```

### 3.5 Polygon record linkage

Keep `polygon["int_zone"]` as denormalized cache from `FaceAssignmentSummary`:

- Set by `apply_face_assignments_to_polygons` after each pipeline run
- Used by polygon table filter, properties panel, xlsx export column
- Orphans: surface in validation (`assignment.orphans`) — not hidden

---

## 4. Migration path preserving pilot workflow

Pilot workflow (frozen): **Import → Detect → Review → Recovery → Save → Reopen → Export**

### Phase 0 — Document & measure (done)

- CLI vs Studio discrepancy documented (24 vs 18, same 618 faces).
- This alignment spec.

### Phase 1 — Sidecar swap (invisible to engineers)

**Scope:** Replace implementation behind `POST /zones/generate` and `/zones/rebuild` only.

| Pilot step | Preservation |
|------------|--------------|
| Import | Unchanged — still `detect_from_cad_path` → 618 polygons |
| Detect | Unchanged |
| Review | Unchanged — polygon table, approve/reject |
| Recovery | Unchanged — `POST /recover` adds seed polygon; set `zones_stale=true` |
| Generate Zones | Now returns **24** zones; polygon `int_zone` from assignment |
| Save | `zones` in workspace JSON now pipeline-backed; **version 2** loader accepts both |
| Reopen | Load zones + polygons; if `zones_stale`, show rebuild prompt in actions log |
| Export | `zones_dxf` uses union rings; optional add `int_schedule.xlsx` to package |

**Backward compatibility:**

- v2 saves with heuristic zones: on reopen, first Rebuild replaces with pipeline zones.
- `int_zone` label change `INT-01` → `INT-1`: one-time migration on rebuild (acceptable in pilot).

### Phase 2 — Export parity

Wire `export_int_pipeline_outputs` (or subset) into `POST /export` package:

- `*_int_zones.dxf` — union geometry (matches CLI)
- `*_int_schedule.xlsx` — QS columns
- Keep existing `*_corrected_polygons.*` as micro-face debug exports

### Phase 3 — Validation overlay (optional, still pilot-safe)

Surface `readiness` gates in existing validation panel — informational only, no new menus:

- `zone_count` PASS/FAIL
- `orphan_faces`
- Empty zones list (INT-1, INT-8, INT-10)

Gap recovery **unchanged** — operates on segments + `session.polygons`; suspected gaps remain polygon-workflow tools.

### Phase 4 — Deprecate heuristic helpers

Remove `workspace_zones.py` or leave stubs that raise `RuntimeError("use zone_pipeline_adapter")`.

Disable or hide merge/rename until manifest override design exists.

### What NOT to change in pilot

- No new menus or workflow steps (Rebuild already exists).
- No replacement of gap list / recovery UX.
- No polygon table removal.
- No AI / cloud / architecture refactors.

### Save format evolution

| Version | Content |
|---------|---------|
| v2 (current) | `polygons`, `zones` (heuristic), `validation` |
| v3 (proposed) | + `zone_pipeline_version`, `zone_profile`, `readiness`, `zones_stale`; `zones` = `ZoneRecord[]` |

Loader: `version > WORKSPACE_VERSION` still errors; v2 loads with `zones_stale=true` if `zone_pipeline_version` absent.

---

## 5. Complexity estimate

### Rating: **Medium**

| Work package | Effort | Notes |
|--------------|--------|-------|
| `zone_pipeline_adapter.py` + wire `/zones/generate` | **Low** | ~1 module, existing pipeline API |
| `polygon_records_to_faces` + assignment writeback | **Low** | Straightforward Shapely rebuild |
| Manifest routing + bundle manifests | **Low–Medium** | Per-drawing lookup; release script update |
| `save_zones_dxf` / export parity | **Medium** | Union rings vs polygon_ids |
| Save v3 + v2 compat | **Medium** | Migration + stale flag |
| Recovery invalidation + rebuild UX | **Low** | Flag + log message; no UI redesign |
| Merge/rename deprecation policy | **Low** | Disable or noop with warning |
| Stage 1 prep unification (if ever re-detect in pipeline) | **Medium** | Optional; bypass with `faces=` for now |
| Full readiness UI + manifest badges | **Medium–High** | Optional phase 3 |

**Why not Low:** Export formats, persistence versioning, bundled manifests, and label migration touch multiple release artifacts.

**Why not High:** Core engine exists and is tested; no new algorithms; frontend types are additive; pilot workflow routes stay the same.

**Raises to High if:** Real-time zone refresh after every recovery, engineer-facing bay geometry editor, or manifest override merge/rename are in scope.

---

## Appendix A — File touch map (implementation reference only)

| File | Action |
|------|--------|
| `desktop/engine_sidecar/zone_pipeline_adapter.py` | **Create** |
| `desktop/engine_sidecar/workspace_zones.py` | **Deprecate / remove** |
| `desktop/engine_sidecar/api.py` | Wire generate/rebuild/recover/export |
| `desktop/engine_sidecar/session_store.py` | Add stale flag, readiness cache |
| `desktop/engine_sidecar/workspace_save.py` | v3 format, union DXF export |
| `desktop/engine_sidecar/polygon_records.py` | Add `records_to_faces` |
| `src/zone_engine/int_zone_pipeline.py` | **No change** (consume as-is) |
| `desktop/studio/src-tauri/resources/reference/` | **Add** manifest YAMLs |
| `desktop/studio/src/types/index.ts` | Extend `IntZone` (additive) |

## Appendix B — Warehouse verification baseline

Reproduced 2026-06-10 on `6276.S111-WAREHOUSE SLAB PLAN-Rev_F`:

| Metric | CLI `build_int_zone_pipeline` | Studio `generate_int_zones` |
|--------|--------------------------------|-----------------------------|
| Micro-faces | 618 | 618 |
| INT zones | **24** | **18** |
| Grid basis | S-GRID CAD axes + manifest | Bbox 8×3 centroid grid |
| Empty zones | INT-1, INT-8, INT-10 (0 m²) | Omitted entirely |
| Missing vs CLI | — | INT-10 … INT-15 (bbox row with no centroids) |

---

## Decision record

| Question | Answer |
|----------|--------|
| Authoritative zone source? | `build_int_zone_pipeline` in `src/zone_engine/` |
| Replace `workspace_zones.py`? | Yes — with `zone_pipeline_adapter` + engine models |
| Break pilot workflow? | No — same steps; Generate/Rebuild become correct |
| Complexity? | **Medium** |
