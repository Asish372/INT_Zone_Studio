# V2 North Star — INT Zones as Primary Product Object

**Status:** Strategic conclusion (research complete; no implementation during pilot-v1)  
**Date:** 2026-06-10  
**Evidence base:** Warehouse 24 vs 18 analysis, `studio_zone_engine_alignment.md`, `scope_vs_polygon_detection_analysis.md`

---

## Verdict (data-backed)

| Question | Answer |
|----------|--------|
| Is warehouse detection broken? | **No** — Stage 1 identical (618 faces CLI = Studio) |
| Is 24 vs 18 a regression? | **No** — architectural divergence, not detection failure |
| Is Studio zone generation authoritative? | **No** — `workspace_zones.py` is a placeholder |
| Is CLI / `build_int_zone_pipeline` authoritative? | **Yes** — manifest, exports, readiness gates |
| Are polygons the final product? | **No** — internal micro-faces (Stage 1) |
| Are INT zones the final product? | **Yes** — schedule-aligned pour partitions (Stage 2) |
| Should pilot-v1 freeze continue? | **Yes** — learn from engineers; do not integrate yet |

---

## What the warehouse evidence proved

### Stage 1 (Detection) — aligned

```
CLI    → 618 faces
Studio → 618 faces
```

Not a gap-closing problem. Not polygonize. Not CAD parsing. Not warehouse regression.

### Stage 2 (Zone generation) — divergent

**Authoritative engine (CLI):**

```
CAD grid layers (S-GRID-*)
  → 24 structural bays (manifest-aligned)
  → face assignment (247 assigned, 369 slivers, 0 orphans)
  → unary_union per bay
  → 24 INT zones (INT-1 … INT-24)
```

**Studio placeholder:**

```
618 polygons
  → all participate (no sliver filter)
  → centroid → bounding-box bucket
  → 18 occupied cells only
  → INT-10 … INT-15 missing vs schedule
```

The mature business logic already lives in `src/zone_engine/`. Studio runs prototype-level aggregation in `workspace_zones.py`.

---

## Business risk (why this matters)

If an engineer sees **INT Zones = 18** in Studio and **INT Zones = 24** on the slab schedule, trust in Studio erodes — even when detection is correct.

**Pilot instruction:** Treat Studio **Generate Zones** count as **non-authoritative**. Use CLI `*_int_zone_report.md` / `run_int_zone_pipeline.py` for INT zone validation metrics.

---

## Product hypothesis — confirmed

> **Polygons are implementation. INT zones are product.**

| Artifact | Centric on |
|----------|------------|
| CLI exports (`*_int_zones.dxf`, `*_int_schedule.xlsx`) | INT zones |
| `reference/j33a_zones_manifest.yaml` | 24 INT rows |
| Readiness gates (`zone_count`, `manifest_area`) | INT zones |
| Client validation reports | INT zones |
| Pilot engineer mental model (slab schedule) | INT-1 … INT-N |

Stage 1 polygon count (618) is an engine diagnostic, not the deliverable engineers sign off on.

---

## V2 North Star goal

**Replace Studio heuristic zone generation with authoritative `build_int_zone_pipeline` integration.**

| Target | Success criterion |
|--------|-------------------|
| Zone count | Studio INT count **==** CLI INT count **==** manifest expected |
| Labels | Studio labels **==** manifest labels (`INT-1`, not `INT-01`) |
| Exports | Studio package exports **==** CLI exports (union geometry, INT schedule) |
| Polygons | Remain editable recovery layer; feed pipeline as `FaceData` input |

**Do not maintain `workspace_zones.py` long-term** — retire after adapter ships.

**Complexity:** Medium (achievable post-pilot; see `studio_zone_engine_alignment.md`).

---

## Future UX (north star, not pilot-v1)

### Today (pilot)

- **Polygon table** — 618 rows (primary review surface)
- **INT Zones** — optional; count may disagree with schedule

### V2 (target)

- **INT Zone table** — 24 rows (primary review surface)

```
INT-1   0.00 m²   0 faces
INT-2   5.13 m²   3 faces
…
INT-24  661.17 m² 23 faces
```

- **Expand zone → Show faces** — drill-down to micro-faces only when needed
- **Gap recovery** — still adds/edits faces; triggers zone rebuild
- **Validation** — zone count + manifest area gates surfaced per INT row

Engineer-friendly: schedule-shaped primary object, geometry detail on demand.

---

## What stays in pilot-v1 (unchanged)

```
Import → Detect → Review → Recovery → Save → Reopen → Export
```

**Primary validation signal (unchanged):**

```
Suspected Gap → engineer clicked → recovered successfully → useful?
```

Do **not** break freeze for zone-engine integration now. Integration introduces:

- New bugs in save/open
- Export format changes
- Recovery → zone invalidation semantics
- Label migration (`INT-01` → `INT-1`)

All of that belongs **after** Round 1 engineer feedback.

---

## Research complete — open questions for engineers

Research is closed. The remaining question is **product-market**, not technical:

> *"Kya unhe 618 polygons chahiye ya 24 INT zones?"*

Capture verbatim in `pilot_metrics_template.csv` / session notes:

- Did engineer look at polygon count or INT zone count?
- Did they compare Studio zones to schedule?
- Would INT-first table reduce confusion?
- Was gap list useful despite zone count mismatch?

Hypothesis: engineers want **24 INT zones** matching schedule; polygons are means, not ends.

---

## Post-pilot implementation sequence (reference only)

1. **Sidecar adapter** — `zone_pipeline_adapter.py`; wire `/zones/generate`, `/zones/rebuild`
2. **Bundle manifests** — ship `reference/*_zones_manifest.yaml` in standalone build
3. **Export parity** — `export_int_pipeline_outputs` in workspace package
4. **Save v3** — pipeline-backed zones + `zones_stale` after recovery
5. **Deprecate** — `workspace_zones.py`, heuristic merge/rename
6. **UX shift** — INT zone table primary (V2 UI; separate from step 1–5)

---

## Related documents

| Doc | Purpose |
|-----|---------|
| `docs/research/studio_zone_engine_alignment.md` | Integration architecture, migration, complexity |
| `docs/research/scope_vs_polygon_detection_analysis.md` | Scope vs polygon semantics |
| `zone_detection_design.md` | Original T0–T3 tier design |
| `PILOT_V1.md` | Freeze rules + non-authoritative zone count note |

---

## One-line strategy

**Pilot learns on polygons + gaps; V2 ships INT zones from the engine that already passes manifest validation.**
