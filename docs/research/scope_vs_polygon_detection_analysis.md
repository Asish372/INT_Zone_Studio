# Scope vs Polygon Detection — Research Analysis

**Status:** Discovery / evidence gathering (no implementation)  
**Date:** 2026-06-10  
**Classification:** Core product-direction signal (accepted pilot feedback)  
**Related design:** Approved discovery doc — slab scope + pillar obstacles (session 2026-06-10)

---

## Executive summary

Internal documentation has **long identified** a semantic gap between Stage 1 polygon detection (hundreds of micro-faces) and business INT zones (17–24 pour partitions). Pilot feedback now states the same gap in engineer language: **pillars should be obstacles inside a user-defined slab scope, not slab separators.**

Evidence shows **over-segmentation is real and quantified** on all three reference drawings, but **pillars are not the primary numeric driver** of the 20–26× count inflation. **Beams, detail linework, and exhaustive polygonize** dominate. Pillars remain a **valid product signal** for scope/obstacle semantics, export clarity, and engineer mental model.

**Recommendation:** Treat **Option B (scope + obstacle workflow)** as core product direction; keep Option A as an internal/debug path. If adopted, **INT Zones become the primary user-facing object**; polygon detection becomes an internal engine step (already partially true in CLI delivery and domain model, not yet in Pilot Studio UI).

---

## 1. Search methodology

Searched repository artifacts for:

`slab boundary`, `slab scope`, `pour boundary`, `outer perimeter`, `obstacle`, `pillar`, `column`, `blockout`, `void`, `net area`, `gross area`, `INT zone count`, `over-segmentation`

**Sources reviewed:**

| Category | Files |
|----------|-------|
| Design / architecture | `zone_detection_design.md`, `int_zone_engine_design.md`, `01_Software_Flow.md`, `04_DOMAIN_MODEL.md`, `ARCHITECTURE_DESKTOP_APPLICATION.md`, `seed_assisted_fallback_design.md` |
| Audits / verification | `verification_summary.md`, `acceptance_readiness_report.md`, `entity_support_analysis.md`, `block_detection_improvement_plan.md`, `delivery_closure_plan.md`, `client_validation_package.md`, `grid_frame_report.md`, `area_benchmark_template.md` |
| Product / PRD | `prd.md`, `PRD_Desktop_Application.md`, `PILOT_V1.md` |
| Pilot capture | `pilot_feedback_log.csv`, `pilot_metrics_template.csv`, `pilot/SESSION_SCHEDULE.md`, `pilot/ROUND1_EXIT_EVALUATION.md`, `PILOT_FEEDBACK.md` |
| Engine / export | `src/zone_engine/slab_outline.py`, `src/zone_engine/int_schedule_export.py` |

**Not in repo yet:** Verbatim pillar/scope feedback text is accepted in product direction (2026-06-10) but **not logged** in `pilot_feedback_log.csv` (that file only contains founder prep confusion items as of this analysis).

---

## 2. Existing evidence by concept

### 2.1 Slab boundary / slab scope / outer perimeter

| Evidence | Source | Finding |
|----------|--------|---------|
| Slab outline extraction | `src/zone_engine/slab_outline.py`, `01_Software_Flow.md` §9.3 | Auto outline from `S-FNDN-1`: polygonize large regions, else **concave hull** fallback |
| Warehouse slab area | `grid_frame_report.md` | Concave hull on `S-FNDN-1` → **11,065.64 m²**; 33 small polygonize regions below 100 m² threshold |
| Slab scope definition | `int_zone_engine_design.md` §4.4 | INT zones must partition **internal slab**; sources: primary envelope, `S-FNDN-1` + `A-WALL-*`, manifest |
| Clipping | `grid_frame_report.md` | Raw bay area 11,238 m² → clipped **10,878.86 m²** (96.8% retained); mean per-bay coverage **85.9%** |
| User-defined scope | Approved discovery doc (2026-06-10) | **Requested** — not implemented; current outline is engine-only |

### 2.2 Pour boundary / partition semantics

| Evidence | Source | Finding |
|----------|--------|---------|
| Business vs geometric unit | `zone_detection_design.md` §1.3, §3.1 | QS uses **pour breaks** (grid, HDLN, major joints); detector uses **every minimal closed loop** |
| Layer tiering proposal | `zone_detection_design.md` §4.3 | `primary_boundary` vs `secondary_subdivision` (beams) vs `exclude_from_faces` (details) |
| Major joints | `int_zone_engine_design.md` §4.3 | Beams **subdivide** geometric faces but **must not** subdivide INT zones by default (`merge_across_beam_layers: false`) |
| J33A model | `int_zone_engine_design.md` §2.2 | 1 grid bay = 1 INT zone (24 cells) |
| J33B model | `int_zone_engine_design.md` §2.3 | ~17 zones from **major pour joints**, not every internal line |

### 2.3 Obstacle / pillar / column / blockout / void

| Evidence | Source | Finding |
|----------|--------|---------|
| INSERT inventory | `entity_support_analysis.md` §2.3 | **710 INSERT** entities; **295 on `S-COLS`**, 113 on `S-COLS-1` — classified as **interior point obstacles**, not pour loops |
| INSERT explosion gain | `entity_support_analysis.md` §3 | Full INSERT support → **0–2%** recall gain; may add micro-polygons at column locations |
| Pour lines vs column symbols | `entity_support_analysis.md` §2.3 | Pour boundaries already on `S-FNDN-1` / `S-BEAM-*` / `A-WALL-*` LINE entities |
| PRD precision goal | `prd.md` §10 | Long-term: minimize **false regions (columns, hatching noise)** |
| min_area filter intent | `01_Software_Flow.md` Stage 5 | `filter_polygons(min_area)` removes **column cross-sections** — but `exhaustive_min_area_m2: 0.01` in config overrides for recall |
| Seed resolver | `seed_assisted_fallback_design.md` §5.1 | Multiple nested faces (incl. columns) → pick **smallest containing face** |
| Pilot feedback (accepted) | Session 2026-06-10 | Engineer request: pillars as **internal obstacles/voids**, not slab separators |

### 2.4 Net area / gross area

| Evidence | Source | Finding |
|----------|--------|---------|
| Export columns | `src/zone_engine/int_schedule_export.py` | **`Concrete Area (SQM)`** only — no gross/net split today |
| Zone area semantics | `int_zone_engine_design.md`, `client_validation_package.md` §5 | Zone area = **union of assigned micro-faces** in bay; INT-8 example **87.27 m²** computed vs **87.45 m²** manifest |
| Slab vs detector totals | `zone_detection_design.md` §2.1 | Detector sum **10,091–16,348 m²** across drawings; INT schedule targets **business partition** of that scope |
| Blockout deduction | Not implemented | Discovery doc proposes **gross − obstacle deduction = net pour** — requires client confirmation of schedule convention |

### 2.5 INT zone count / over-segmentation

| Evidence | Source | Finding |
|----------|--------|---------|
| Quantified gap | `zone_detection_design.md` §2.1 | **618 / 331 / 397** raw polygons vs **24 / 17 / ~24** INT zones |
| Over-segmentation factor | `zone_detection_design.md` §2.1 | **~16.5× – 25.8×** micro-polygons per INT zone |
| Root causes (ordered) | `zone_detection_design.md` §3, `int_zone_engine_design.md` §3.3 | (1) polygonize minimal faces, (2) secondary linework in auto_fallback, (3) exhaustive mode, (4) gap chords, (5) no aggregation |
| Domain language | `04_DOMAIN_MODEL.md` §2 | **Micro-face** → many roll up to one **INT zone** |
| INT engine bridge | `int_zone_engine_design.md` §5 | Stage 1 faces → Stage 2 zone assembly → Stage 3 schedule |
| Delivery gate | `delivery_closure_plan.md` | INT zone count **24/24, 17/17, 24/24** PASS (CLI pipeline) |
| Pilot Studio dry-run | `pilot/SESSION_SCHEDULE.md` | **618 polygons** detected; **18 INT zones** shown (discrepancy vs CLI 24 — see §4.3) |

---

## 3. Drawings where over-segmentation occurs

All three reference drawings in scope show over-segmentation relative to QS INT deliverables:

| Drawing | DWG counterpart | Raw polygons (Stage 1) | Total detected area (m²) | Dominant face size (m²) | Expected INT zones | Over-seg. factor | Layers in auto_fallback (sample) |
|---------|-----------------|------------------------:|-------------------------:|------------------------:|-------------------:|-----------------:|----------------------------------|
| Warehouse | `6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg` | **618** | 10,091.19 | ~747 (top rooms); grid bays ~810 class | **24** (J33A) | **25.8×** | `S-FNDN-1`, `S-BEAM-2`, `A-WALL-*`, `A-DETL-*`, `A-FLOR` |
| Challenger | `S111_J.dwg` | **331** | 5,320.03 | ~881 max | **17** (J33B) | **19.5×** | 11 candidate layers |
| Grid-class | `S111_A.dwg` | **397** | 16,348.58 | **810** (repeated) | **~24** | **~16.5×** | `S-FNDN-1`, `S-BEAM-*`, `S-BEAM-HDLN-1`, `S-FNDN-HDLN-1`, `A-DETL-1` |

**Pattern:** Largest repeated faces (~**747–881 m²**, often **810 m²**) match **structural bay modules**, not column footprints. The detector is finding **cells**; QS reports **aggregated pour zones**.

**Supporting diagnostics:**

- `verification_summary.md`: 618 / 397 / 331 regions; 0 invalid polygons; open endpoints 31 / 20 / 50
- `area_benchmark_template.md`: Top regions are bay-scale (e.g. six consecutive **810.0000 m²** rooms on S111_A)
- `grid_frame_report.md` (warehouse): Grid frame resolves **136 raw bays → 24** target cells after manifest-aware subsampling

---

## 4. Expected INT zone counts vs detected polygon counts

| Drawing | Stage 1 polygons | INT zones (manifest / PDF) | INT zones (CLI engine) | INT zones (Pilot dry-run) | Face Count column meaning |
|---------|-------------------:|---------------------------:|-----------------------:|--------------------------:|---------------------------|
| Warehouse / J33A | 618 | 24 | 24 (`delivery_closure_plan.md`) | **18** (`pilot/SESSION_SCHEDULE.md`) | Micro-faces assigned per zone in `*_int_schedule.xlsx` |
| S111_J / J33B | 331 | 17 | 17 | — | Same |
| S111_A | 397 | ~24 | 24 | — | Same |

**Export row counts today:**

- **Polygon-first (Stage 1):** 618 / 331 / 397 rows if exporting `Room N` results (`prd.md` exhaustive philosophy)
- **INT schedule export:** 24 / 17 / 24 data rows + TOTAL row (`INT_EXCEL_COLUMNS` in `int_schedule_export.py`)

**Pilot metrics capture** (`pilot_metrics_template.csv`) records `total_polygons_detected` only — not INT zone count — reinforcing polygon-first UX in Pilot v1.

### 4.1 Pilot dry-run anomaly (618 vs 18)

Founder dry-run on warehouse drawing reports **618 polygons** but **18 INT zones** (not 24). Possible causes (not fully diagnosed in repo):

- Studio sidecar may expose partial zone framing vs full CLI `--zones` pipeline
- Grid axis subsampling / profile mismatch in embedded run
- UI count source may differ from `delivery_closure_plan.md` CLI gate

**Research gap:** Reconcile Pilot Studio INT zone count with CLI `24/24` before using Studio metrics for scope-workflow ROI.

---

## 5. Are pillars the primary cause of over-segmentation?

### 5.1 Short answer

**No — not the primary cause** of the 20–26× count inflation on reference drawings. **Beams and secondary structural/detail linework** are the dominant drivers in existing audits.

**Yes — as a product semantics issue:** Engineers correctly describe pillar/column geometry as something that should **not** define pour partitions. That aligns with obstacle modeling even when numeric impact is secondary.

### 5.2 Evidence breakdown

| Hypothesis | Support | Strength |
|------------|---------|----------|
| Beams subdivide bays | `zone_detection_design.md` §3.2; repeated ~810 m² faces; `S-BEAM-*` in every auto_fallback set | **Strong** |
| Exhaustive mode retains slivers | `exhaustive_min_area_m2: 0.01`; validation notes sub-m² artifacts | **Strong** |
| Polygonize enumerates all minimal faces | `zone_detection_design.md` §3.1 grid diagram (9 faces from cross grid) | **Strong** |
| Columns create boundary loops | `entity_support_analysis.md`: INSERTs are point features; explosion **0–2%** gain, micro-polygons at columns | **Weak–Medium** |
| Columns engineer sees as “separators” | Pilot feedback (accepted); PRD mentions column false regions | **Qualitative Strong** |
| Gap closing adds chords | `zone_detection_design.md` §3.4; 37–110 gaps closed per drawing | **Medium** |

### 5.3 Interpretation

1. **Numeric over-segmentation** on S111 family is explained mainly by **beam grid + detail layers** participating equally in polygonize — not by 295 `S-COLS` INSERT symbols (which are not LINE-extracted today).
2. **Perceived pillar problem** may arise when: (a) column footing linework on `S-FNDN-1` forms small closed loops, (b) engineers review **618 polygon rows** in Pilot Studio and see column-adjacent cells, (c) mental model expects **scope → obstacles → zones** but UI shows **flat polygon list**.
3. **Scope + obstacle workflow** addresses both the dominant cause (partition inside scope, ignore obstacle loops) and the pilot signal (pillar voids), even if pillars alone would not reduce 618 → 24.

---

## 6. Estimated impact on export schedules

### 6.1 Current export behavior

| Artifact | Primary object | Typical row count (warehouse) | Area semantics |
|----------|----------------|------------------------------:|----------------|
| `*_results.xlsx` (Stage 1) | `Room N` / polygon | **618** | Per micro-face |
| `*_int_schedule.xlsx` (Stage 2) | `INT-n` pour | **24** + TOTAL | Union area per zone; **Face Count** exposes rollup |
| `*_annotated.dxf` | Micro-face overlay | 618 regions | Debug / QA |
| `*_int_zones.dxf` | INT boundaries | 24 zones | Business deliverable |
| Pilot **Export Project Package** | Workspace polygons | **618** in dry-run | Pilot path is polygon-first |

### 6.2 If scope + obstacle workflow is adopted (estimate)

| Dimension | Impact | Notes |
|-----------|--------|-------|
| **Row count** | Unchanged at INT layer (still 17–24) | Scope workflow changes **how** zones are built, not manifest cardinality |
| **Concrete Area (SQM)** | **Medium change risk** | May shift if obstacles subtracted (net) vs included (gross); needs client rule |
| **Face Count** | **Likely decreases** per zone | Fewer spurious micro-faces inside bays after obstacle exclusion |
| **New columns (potential)** | `Gross SQM`, `Obstacle Deduction SQM`, `Net SQM`, `Scope Source` | Not in `INT_EXCEL_COLUMNS` today; would be contract change |
| **Manifest reconciliation** | **Improved interpretability** | Δ% vs PDF may improve if scope matches QS envelope; concave hull distortion reduced |
| **Pilot package** | **High UX impact** | Engineers would export **INT schedule** not 618-row polygon dump |
| **Empty zones** | **Indirect** | `delivery_closure_plan.md` / `client_validation_package.md`: INT-1, INT-8, INT-10 (J33A), INT-16 (J33B) — scope clarity may help explain legitimate empties vs detection gaps |

### 6.3 Quantitative schedule area reference (warehouse)

| Metric | Value | Source |
|--------|------:|--------|
| Detector total (all micro-faces) | 10,091.19 m² | `verification_summary.md` |
| Slab outline (concave hull) | 11,065.64 m² | `grid_frame_report.md` |
| Clipped bay total | 10,878.86 m² | `grid_frame_report.md` |
| INT zone areas (manifest template) | Mostly placeholder / pipeline-derived | `reference/j33a_zones_manifest.yaml` — PDF transcription **BLOCKED** per `delivery_closure_plan.md` |

**Conclusion:** Export schedule **structure** (Pour No., SQM, CUM) is already INT-centric in CLI delivery. Scope + obstacle mainly affects **area correctness**, **face rollup**, and **which object Pilot users review/export** — not the 24-row shape of the QS schedule.

---

## 7. Recommendation matrix

| Criterion | Option A: Polygon-first workflow | Option B: Scope + obstacle workflow |
|-----------|----------------------------------|-------------------------------------|
| **Engineering accuracy (vs QS INT deliverables)** | **Low–Medium** for business task. High for geometric completeness. Optimizes 618 faces; QS expects 24 zones (`zone_detection_design.md`) | **High** when scope and partition rules match project. Aligns with J33A/J33B semantics (`int_zone_engine_design.md`) |
| **User effort** | **Lower upfront** — import and auto-detect only in Pilot v1 | **Higher upfront** — define/confirm scope, confirm obstacles; **lower review** — 24 rows vs 618 |
| **Implementation complexity** | **Low** — shipped in Stage 1 + Pilot Studio | **High** — scope UI, layer role classification, obstacle extraction, partition graph, persistence, migration |
| **Recovery workflow impact** | **Central** in Pilot v1 — suspected gaps → seed recovery on micro-face graph (`PILOT_V1.md`, `suspected_gaps.py`) | **Reframed** — gaps on **partition boundaries inside scope**; obstacle gaps deprioritized; recovery targets missing **pour cells**, not column loops |
| **Export workflow impact** | Pilot exports **polygon workspace** (618 rows); CLI can export INT schedule separately | **Unified** — primary export = `*_int_schedule.xlsx` / INT zones DXF; micro-faces → debug layer only |
| **Pilot v1 compatibility** | **Full** — frozen workflow | **None without flag** — violates pilot freeze if shipped mid-Round 1 |
| **Evidence maturity** | Production for Stage 1; recall vs AutoCAD **BLOCKED** (`acceptance_readiness_report.md`) | Design docs mature; **user-defined scope unbuilt**; CLI INT engine partial (P2–P5 PASS) |
| **Risk** | Engineers drown in polygons; false confidence from high counts | Wrong scope → wrong totals; gross/net ambiguity; engineering change management |

### 7.1 Recommendation

| Audience | Recommendation |
|----------|----------------|
| **Product direction** | **Option B** — core direction, consistent with accepted pilot feedback and `int_zone_engine_design.md` |
| **Pilot Round 1** | **Stay Option A** — log feedback only (`PILOT_V1.md`); complete gap-recovery validation |
| **Pilot Round 2 / post-pass** | **Option B MVP** — auto scope + select polyline + `S-COLS` obstacles; behind feature flag |
| **Engine internals** | Retain Option A as **Stage 1 diagnostic** regardless |

---

## 8. Primary user-facing object — decision question

> If this workflow is adopted, does polygon detection become an internal engine step and INT Zones become the primary user-facing object?

### Answer: **Yes.**

**Already true in parts of the system:**

| Layer | Primary object today | Evidence |
|-------|---------------------|----------|
| Domain model | INT zone + micro-face distinction | `04_DOMAIN_MODEL.md` |
| CLI client delivery | INT schedule + `*_int_zones.dxf` as deliverable; annotated DXF = Stage 1 debug | `client_validation_package.md` §6.1 |
| Desktop PRD / architecture | Map shows **INT boundaries**; export contract is INT schedule columns | `PRD_Desktop_Application.md`, `ARCHITECTURE_DESKTOP_APPLICATION.md` §7.4 |
| INT engine | Stage 1 → Stage 2 → schedule explicit | `int_zone_engine_design.md` §5 |

**Still polygon-first (gap to close):**

| Layer | Current state | Evidence |
|-------|---------------|----------|
| Pilot Studio UX | Polygon table, `total_polygons_detected` in metrics | `pilot_metrics_template.csv`, `pilot/SESSION_SCHEDULE.md` (618) |
| PRD Stage 1 philosophy | “Prefer missing nothing”; export **all** detected regions | `prd.md` §10 |
| Recovery | Operates on micro-face / seed resolution | `suspected_gaps.py`, `seed_assisted_fallback_design.md` |

**Adoption model:**

```text
User-facing:     Slab Scope → INT Zones (17–24) → Export schedule
Internal/debug:  Polygonize → micro-faces → gap diagnostics → face assignment rollup
Obstacles:       Shown as voids/deductions; not rows in zone list
```

Polygon detection does **not** disappear — it becomes **input** to zone assembly and QA, analogous to how compiler IR is not the programmer's primary artifact.

---

## 9. Open research gaps

1. **Reconcile Pilot Studio 18 vs CLI 24 INT zones** on warehouse drawing.
2. **Quantify pillar-only polygon count** — isolate micro-faces whose centroid falls inside `S-COLS` INSERT bounding boxes vs beam-induced cells (requires scripted analysis; not in repo).
3. **Client rule for gross vs net pour area** — QS PDFs do not document blockout deduction in extracted evidence.
4. **Transcribe J33A/J33B manifest areas** — `delivery_closure_plan.md` P0 still BLOCKED; limits schedule impact quantification.
5. **Log accepted pillar/scope feedback** into `pilot_feedback_log.csv` with category `product_direction`.

---

## 10. Source index

| Document | Relevance |
|----------|-----------|
| `zone_detection_design.md` | Over-segmentation quantification, root causes, layer tiering |
| `int_zone_engine_design.md` | Slab scope, grid/bay/joint semantics, two-stage architecture |
| `entity_support_analysis.md` | Column INSERT role; explosion impact 0–2% |
| `verification_summary.md` | 618/397/331 polygon counts |
| `grid_frame_report.md` | 24 INT cells, slab hull, clip statistics |
| `delivery_closure_plan.md` | 24/24, 17/17 gates; empty zones |
| `client_validation_package.md` | Export artifacts; INT-8 area variance |
| `04_DOMAIN_MODEL.md` | Micro-face vs INT zone language |
| `prd.md` | Column false-region precision goal; exhaustive export |
| `PILOT_V1.md` | Frozen workflow; gap recovery primary signal |
| `pilot/SESSION_SCHEDULE.md` | 618 polygons / 18 INT zones dry-run |
| Approved discovery doc (2026-06-10) | Scope + obstacle workflow proposal |

---

*Research only. No code, UI, or feature implementation.*
