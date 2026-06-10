# INT Zone Engine — Design Specification

**Version:** 1.0  
**Date:** June 1, 2026  
**Status:** Design only (no implementation)  
**Related:** `reference_pdf_analysis.md`, `zone_detection_design.md`, `acceptance_readiness_report.md`

---

## 1. Executive summary

The geometric detector is **working as designed**: it finds hundreds of valid closed polygons from structural linework. The QS deliverables in **J33A** and **J33B** do not report those polygons. They report **INT zones** — roughly **24** (warehouse grid) or **17** (irregular layout) engineering pour regions with labels `INT-1`, `INT-2`, …, plus a **SLAB SUMMARY SCHEDULE** (area SQM, volume CUM).

| Drawing | Raw polygons (Stage 1) | INT zones (PDF) | Over-segmentation |
|---------|------------------------:|----------------:|------------------:|
| `6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg` | 618 | 24 (J33A) | ~26× |
| `S111_J.dwg` | 331 | 17 (J33B) | ~19× |
| `S111_A.dwg` | 397 | ~24 (grid-class, no INT PDF) | ~17× |

The **INT Zone Engine** is a new Stage 2 layer that sits **after** polygon detection and **before** business reporting. It does not replace Stage 1; it **consumes** micro-polygons and structural context to emit the partition the quantity surveyor uses.

**Target pipeline (QS workflow):**

```text
Raw polygons (Stage 1)
  → Structural frame (grid / major joints)
  → INT zone partition
  → Area (union per zone)
  → Volume (area × thickness)
  → Schedule (INT-n, SQM, CUM)
```

**Out of scope for this document:** GUI, export format changes, and code changes.

---

## 2. Review of PDF analysis findings

Full analysis: `reference_pdf_analysis.md`. Summary for engine design:

### 2.1 Deliverable types

| PDF | Role | INT labels | Extractable text |
|-----|------|------------|------------------|
| `J33A-MODSCAPE-INTERNALS.pdf` | **QS output** (Modscape) | `INT-1` … `INT-24` | None (raster) |
| `J33B BTR-INTERNALS.pdf` | **QS output** (V&G) | `INT-1` … `INT-17` | None (raster) |
| `S111-WAREHOUSE-SLAB-PLAN-Rev.C.pdf` | Engineering **source** | — | DCJ, PC1–PC3 |
| `S111_J.pdf` | Engineering **source** | — | DCJ, PC1–PC4, RSCJ, grid |

**Critical finding:** `INT-*` strings exist on yellow callouts and schedule tables in INTERNALS PDFs only. They are **not** greppable from DXF. Labels must come from **grid indexing**, **manifest**, or future OCR — not from assuming TEXT entities in CAD.

### 2.2 How J33A defines a zone (24 INT)

- **Layout:** Structural grid **1–24** (one axis) × **A–D** (other axis).
- **Geometry:** One **bay** = one rectangle between **adjacent** grid lines (e.g. between grid 4–5 and lines B–C).
- **Boundaries:** **Major grid / pour breaks** — not every interior saw-cut, beam stiffener, or detail hatch inside the bay.
- **Report:** “SLAB SUMMARY SCHEDULE - VBC USE ONLY” — Pour No. (= INT), Concrete Area (SQM), Concrete Volume (CUM).
- **Business rule:** Quantity is **per grid bay**, not per minimal closed loop.

### 2.3 How J33B defines a zone (17 INT)

- **Layout:** Irregular warehouse; **not** a uniform 24-cell grid.
- **Boundaries:** Prominent **red** lines on INTERNALS PDF = construction / pour joints (aligned with DCJ / major breaks on source plan where applicable).
- **Zone types:** Few large central pours, narrow perimeter strips, smaller zones near entries — **semantic** grouping, not equal-area cells.
- **Report:** “V&G USE ONLY” — Pour No., Estimated SF, Estimated CY.
- **Business rule:** Zones follow **major joint polygons**; column blockouts and minor internal geometry are **ignored** for partitioning.

### 2.4 Source-plan labels vs INT semantics

| Label on structural PDF | Typical meaning | Use in INT engine |
|-------------------------|-----------------|-------------------|
| Grid **1–24**, **A–D** | Structural grid axes | **Primary** bay frame (J33A) |
| **S-GRID-1**, **S-GRID-IDEN** | Grid linework in DXF | Extract axis lines → bay cells |
| **DCJ** | Dowelled construction joint | **Hard** zone boundary when aligned with INT breaks |
| **PC1–PC4** | Pour / panel codes | Finer than INT on source; **do not** use all as zone walls |
| **RSCJ** | Reinforced saw-cut joint | Usually **within** a pour — not a separate INT |
| **S-FNDN-HDLN** | Foundation / pour headline | Often **hard** boundary |
| **S-BEAM-***, **S-BEAM-HDLN-*** | Beams | **Subdivide** geometric faces; **must not** subdivide INT zones by default |

### 2.5 Scale alignment (detector vs INT)

- Largest detector faces (~**747–881 m²** warehouse, **~810 m²** repeated on S111_A) match **one structural bay** in order of magnitude.
- Detector total area (sum of all micro-faces) should approximate sum of INT schedule areas once scope matches (internal slab only).
- Average **~20–26 micro-polygons per INT zone** explains the count gap: polygonize is correct at the **face** level, wrong at the **pour** level.

### 2.6 Acceptance shift (from PDFs)

| Metric | Current geometric acceptance | INT-zone acceptance |
|--------|---------------------------|---------------------|
| Region count | 618 / 331 / 397 = success | **24 / 17 / ~24** |
| Label | `Room 1` … `Room N` | **`INT-1` … `INT-n`** |
| Area check | Per micro-face vs AutoCAD | Per **INT zone** (union) vs schedule SQM |
| Recall | Maximize closed loops | **Cover all INT zones**; micro-faces optional debug |

---

## 3. Problem statement

### 3.1 What is not broken

- DWG → DXF conversion, layer auto-fallback, gap closing, polygonize, area/volume math, zero invalid polygons on sample drawings.
- Detection **recall of geometry** in the planar subdivision sense.

### 3.2 What is missing

A **semantic aggregation** step that maps:

```text
{ face_1, face_2, … face_618 }  →  { INT-1, … INT-24 }
```

without discarding Stage 1 for engineering QA (gaps, open endpoints, layer diagnostics).

### 3.3 Root cause of over-segmentation (ordered by impact)

1. **Wrong unit of report** — `polygonize` emits every minimal face; QS emits one face per bay or major pour.
2. **Secondary linework as walls** — beams, details, and HDLN segments in auto-fallback split bays into many cells.
3. **Exhaustive mode** — retains slivers (0.01 m² floor); INT zones have no sub–m² entries.
4. **DCJ/PC density** — source plan has many joint labels; INT deliverable **aggregates** across them.
5. **No post-polygonize grouping** — pipeline stops at `detect_regions` → `compute_all` on raw polygons.

---

## 4. Concepts: grid lines, structural bays, major joints

### 4.1 Grid lines

**Definition:** Infinite or long construction lines (usually on `S-GRID-1`, `S-GRID-IDEN`, or equivalent) that encode the structural **column/grid module**. On J33A they appear as numbered axes **1–24** and lettered axes **A–D** on the PDF overlay.

**Role in INT engine:**

- Provide a **regular partition frame** when the project matches “grid warehouse” class.
- Define **orthogonal cutting planes** between adjacent parallel grid lines.
- Supply **stable naming** (`INT-k` ↔ grid cell index) when manifest or OCR order is known.

**Extraction approach (design):**

1. Collect LINE / LWPOLYLINE / XLINE on configured `grid_layers`.
2. Cluster by orientation (within angular tolerance) → two families (e.g. “along 1–24” vs “along A–D”).
3. Sort parallel lines by position → ordered axis list.
4. Adjacent axis pairs bound one **bay strip**; cross product of strips yields **bay cells**.

**Caveats:**

- Grid text (MTEXT “12”, “C”) may be on annotation layers — use for **validation**, not sole geometry source.
- `layer_resolver` currently treats `GRID` as ignore hint for **wall** ranking; grid layers must be **explicitly enabled** for zone framing, separate from polygonize wall set.

### 4.2 Structural bays

**Definition:** The **smallest regular pour module** implied by the structural grid — one cell between four grid intersections (or between grid line and slab edge for perimeter bays).

**Relationship to detector output:**

- One bay often corresponds to **one** of the largest repeated detector faces (~810 m² on S111_A).
- The same bay typically contains **many smaller** faces from beam intersections and details **inside** the cell.

**Role in INT engine:**

- **J33A profile:** 1 bay = 1 INT zone (24 bays → 24 INT zones).
- Bay polygon = `intersection(slab_outline, cell_rectangle)` where slab outline comes from `S-FNDN-1` / perimeter walls.

### 4.3 Major joints

**Definition:** Construction or pour breaks that the QS treats as **zone boundaries** — not every labeled joint on the source plan.

**Hierarchy:**

| Class | Examples | INT boundary? (default) |
|-------|----------|-------------------------|
| **Major pour joint** | Red lines on J33B INTERNALS, `S-FNDN-HDLN`, aligned DCJ | **Yes** |
| **Dowelled construction joint (DCJ)** | On source PDF | **Yes** when on HDLN / manifest |
| **Panel code (PC*)** | PC1–PC4 | **No** (merge across) unless project config |
| **Saw-cut (RSCJ)** | Fine shrinkage joints | **No** (merge across) |
| **Beam line** | `S-BEAM-*` | **No** for INT partition |

**Role in INT engine:**

- **J33B profile:** Build a **planar graph** from major-joint linework only → polygonize or extract closed regions → expect **~17** components; assign `INT-1` … `INT-17` by manifest order or area sort mapped to PDF.
- **J33A profile:** Major joints **coincide** with grid; grid frame is primary, joints validate edges.

### 4.4 Slab scope (outline)

**Definition:** The **internal slab** region to which INT zones must be a partition (mutually exclusive, collectively exhaustive within scope).

**Sources (priority):**

1. Union of Stage 1 faces whose centroids fall inside primary envelope (T3 assignment).
2. Closed polyline on `S-FNDN-1` + perimeter `A-WALL-*`.
3. Manifest / PDF traced outline (acceptance only).

Exclude from scope per note on source PDF: external aprons, mezzanine, “dry sump detail only” unless labelled as separate INT.

---

## 5. INT Zone Engine — architecture

### 5.1 Position in the system

```text
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1 — Geometric Face Detector (existing, frozen baseline)    │
│  extract → layer tiers → snap → gap_close → polygonize → faces F │
└───────────────────────────────┬─────────────────────────────────┘
                                │ F + DXF context
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2 — INT Zone Engine (NEW)                                  │
│  profile detect → frame (grid | joints) → assign/merge → zones Z │
└───────────────────────────────┬─────────────────────────────────┘
                                │ Z
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3 — Quantity & schedule (existing calculator, new binding) │
│  area = union(Z_i), volume = area × thickness, schedule rows     │
└─────────────────────────────────────────────────────────────────┘
```

Stage 1 output remains available as **debug faces** (`Room 1` … `Room N`). Stage 2 output is the **official QS partition** (`INT-1` … `INT-n`).

### 5.2 Engine modules (logical)

| Module | Responsibility |
|--------|----------------|
| **Profile classifier** | Choose J33A-grid vs J33B-joint vs manifest-only from layer set, grid line count, manifest presence |
| **Grid frame builder** | Axes → bay cells → cell polygons clipped to slab outline |
| **Joint frame builder** | Major-joint segments → noded graph → coarse regions |
| **Face assigner** | Map each micro-face in F to exactly one zone (by centroid-in-cell or max intersection area) |
| **Zone aggregator** | `unary_union` of assigned faces → zone polygon; sum validation |
| **Labeler** | `INT-{n}` from grid index, manifest row, or sequential pour order |
| **Schedule builder** | Rows: Pour No., SQM, CUM, thickness, face_count, tier metadata |
| **Validator** | Count vs manifest, total area vs schedule, orphan faces, gaps in partition |

### 5.3 Project profiles

| Profile | Trigger signals | Zone count target | Frame source | Label source |
|---------|-----------------|-------------------|--------------|--------------|
| **GRID_WAREHOUSE** | ≥2 grid layer families, ~24 axis modules, DWG maps to J33A | 24 | Grid bay cells | Row-major grid index or manifest |
| **JOINT_WAREHOUSE** | Irregular outline, rich DCJ/HDLN, maps to J33B | 17 | Major joint polygonize | Manifest / OCR order |
| **MANIFEST_OVERRIDE** | `reference/*_zones_manifest.yaml` present | manifest.n | Manifest polygons or grid+manifest labels | Manifest |
| **FALLBACK_MERGE** | No grid, weak joints | config or area-driven | Face adjacency merge only | `Zone 1` … `Zone n` |

Classifier should **log** chosen profile and allow YAML override per project template.

### 5.4 Detection tiers (reuse from zone_detection_design)

Run tiers until validation passes; record `detection_tier` on each zone.

| Tier | Source | When |
|------|--------|------|
| **T0** | PDF schedule manifest (SQM, CUM) | Acceptance / sign-off |
| **T0b** | Structural grid → bay cells | Default J33A / S111_A class |
| **T1** | HATCH / closed LWPOLYLINE on slab layers | CAD encodes pours |
| **T2** | Primary-boundary-only polygonize | Few coarse faces before assign |
| **T3** | Assign + union micro-faces per cell | **618 → 24** bridge |
| **T4** | MTEXT `INT-\d+` in DXF | Rare; validate positions |
| **T5** | Seed-assisted recovery | Missing INT cell only |

**Recommended default path for warehouse:** **T0b + T3** (grid frame + face assignment). **J33B:** **T2 (joint-only) + T3** or joint polygonize with merge to 17.

---

## 6. Micro-polygon merge and assignment

Two complementary mechanisms: **(A) assign-to-frame** (preferred for J33A) and **(B) graph merge** (required for J33B and fallback).

### 6.1 Assign-to-frame (primary for grid warehouses)

**Input:** Face list `F` from Stage 1; bay cell polygons `{C_1 … C_24}` from grid frame.

**Algorithm:**

1. **Filter noise faces** before assignment:
   - Drop slivers: `area_m2 < sliver_max_m2` (default **1.0 m²**, not 0.01).
   - Optional: drop faces with centroid outside slab outline.
2. For each face `f ∈ F`:
   - Let `C* = argmax_{C_j} area(f ∩ C_j)` (or centroid ∈ C_j with tie-break by intersection).
   - If no intersection: flag `orphan_face` for QA; optionally assign to nearest cell by centroid distance.
3. For each cell `C_j`:
   - `zone_polygon_j = unary_union({ f.polygon : f assigned to j })`
   - If union empty: **missing zone** → trigger T5 seed or manifest review.
4. **Area:** `area(zone_j) = area(zone_polygon_j)` in m² (not sum of overlapping micro-areas — faces are disjoint in planar subdivision).
5. **Volume:** `volume = area × slab_thickness` (same as current `calculator.compute_volume`).

**Properties:**

- Micro-polygons **inside** a bay never create extra INT rows — they **roll up** to the parent bay.
- Beam-created faces straddling a grid line: assign by **majority intersection**; document edge cases in validation report.

### 6.2 Graph merge (J33B and fallback)

**Input:** Face list `F`; classification of segments into **barrier** vs **mergeable** edges.

**Build dual graph:**

- Nodes = faces.
- Edge between faces if they share a boundary segment longer than `min_shared_length_m` AND the shared segment is **not** on a barrier layer (`S-FNDN-HDLN`, configured DCJ layers, manifest “do not merge” polylines).

**Merge passes:**

1. Remove slivers (same as 6.1).
2. **Agglomerative merge:** repeatedly union adjacent faces with highest shared **mergeable** boundary length until:
   - `count(zones) ≤ target_zone_count` (17 for J33B), OR
   - `min(zone_area_m2) ≥ zone_min_m2` (default **500–2000 m²** project-dependent), OR
   - no mergeable pairs remain.
3. If count still **>** target: merge pair that least increases perimeter/area ratio (smallest “cost” pour break).
4. If count **<** target: stop and flag — likely missing barrier lines; use manifest or seed.

**Barrier vs mergeable (default config):**

```yaml
zone_engine:
  barrier_layers:      # shared edge blocks merge
    - S-FNDN-HDLN-1
    - S-FNDN-HDLN
  mergeable_layers:    # shared edge allows merge
    - S-BEAM-1
    - S-BEAM-2
    - S-BEAM-HDLN-1
    - A-DETL-1
    - A-DETL-2
    - A-FLOR
  primary_outline_layers:
    - S-FNDN-1
    - A-WALL-1
    - A-WALL-2
```

### 6.3 Hybrid: grid assign then merge cells (optional)

For drawings where **24 grid cells** exist but QS wants **fewer** INT zones (e.g. multiple bays per pour):

- Start with 24 cells from T0b.
- Merge **adjacent cells** across non-barrier grid lines only when manifest specifies `INT-1` spans grids 1–3.
- Requires **manifest grouping** — do not infer from geometry alone.

J33A evidence points to **1:1 bay:INT**; hybrid merge is for future projects, not default Modscape warehouse.

### 6.4 Labelling INT-n

| Method | Order rule | Use when |
|--------|------------|----------|
| **Manifest** | Exact `INT-n` from YAML | Acceptance, OCR transcription |
| **Grid index** | Row-major: increasing grid number, then letter (validate against PDF preview) | J33A default |
| **Area sort** | Largest zone → `INT-1` | Only if manifest missing; **risky** vs PDF order |
| **Joint traverse** | Follow pour sequence on J33B red lines | J33B with manual manifest mapping |

**Do not** reuse `Room 1` area-sort labels as INT IDs — PDF pour sequence is **not** strictly area-descending.

### 6.5 Schedule output (logical schema)

Match QS PDF columns (units converted to metric in engine):

| Column | J33A (VBC) | J33B (V&G) | Source |
|--------|------------|------------|--------|
| Pour No. / Zone ID | INT-n | INT-n | Labeler |
| Concrete Area | SQM | SF → convert | `compute_area(zone_polygon)` |
| Concrete Volume | CUM | CY → convert | `area × thickness` |
| Face count | optional QA | optional QA | \|assigned faces\| |
| Detection tier | audit | audit | T0b/T3/… |
| Centroid X, Y | optional | optional | zone polygon centroid |

Grand total: `sum(INT area)` ≈ detector total internal slab area ± scope tolerance.

---

## 7. Data model (design)

```python
@dataclass
class FaceData:
    """Stage 1 micro-polygon (existing RegionData without zone binding)."""
    face_id: int
    polygon: Polygon
    area_m2: float
    source_layers: set[str]  # layers contributing boundary segments

@dataclass
class IntZoneData:
    """Stage 2 QS pour zone."""
    zone_id: int              # 1..n
    label: str                # INT-1
    polygon: Polygon          # unary_union of member faces
    area_m2: float
    volume_m3: float
    face_ids: list[int]
    profile: str              # GRID_WAREHOUSE | JOINT_WAREHOUSE | ...
    detection_tier: str       # T0b, T3, ...
    grid_ref: str | None      # e.g. "12-C" for audit
    source_file: str

@dataclass
class IntScheduleRow:
    """Stage 3 schedule line matching PDF."""
    pour_no: str              # INT-1
    area_sqm: float
    volume_cum: float
    thickness_m: float
    face_count: int
```

Existing `RegionData` remains for **face debug** export; `IntZoneData` becomes the object passed to zone-level area validation against manifest.

---

## 8. Validation and acceptance

### 8.1 Zone-level gates (replace face-count gates for QS sign-off)

| Check | Rule | Source |
|-------|------|--------|
| Zone count | \|Z\| within ±1 of manifest / PDF | J33A: 24; J33B: 17 |
| Zone area | \|A_auto − A_manifest\| / A_manifest ≤ 0.05% per INT-n | Transcribed schedule (P0) |
| Total area | \|Σ A_zones − Σ A_manifest\| ≤ project tolerance | Schedule footer |
| Coverage | Every manifest INT has ≥1 assigned face; no duplicate assignment | Assigner |
| Orphans | orphan_face count = 0 or documented | QA sheet |

### 8.2 P0 ground truth

Transcribe **24 rows** from J33A “SLAB SUMMARY SCHEDULE” into `reference/j33a_zones_manifest.yaml`:

```yaml
# Example structure (values to be filled from PDF)
project: J33A
drawing_ref: 6226-S111
zones:
  - label: INT-1
    area_sqm: null   # from PDF
    volume_cum: null
    grid_ref: null   # e.g. "1-A" if known
  # ... INT-24
```

Same for J33B (17 rows) as `reference/j33b_zones_manifest.yaml`.

### 8.3 Debug vs official outputs

| Output | Audience | Content |
|--------|----------|---------|
| **Official** | QS / client | INT schedule + zone polygons only |
| **Debug** | Engineering | All micro-faces, gap report, layer diagnostics |

Keep Stage 1 metrics in `acceptance_readiness_report.md` as **geometry QA**; add parallel **INT zone acceptance** section driven by manifest.

---

## 9. Configuration (design)

```yaml
zone_engine:
  enabled: true
  profile: auto              # auto | GRID_WAREHOUSE | JOINT_WAREHOUSE
  manifest_path: null        # reference/j33a_zones_manifest.yaml

  grid_layers:
    - S-GRID-1
    - S-GRID-IDEN
  grid_angle_tolerance_deg: 2.0
  min_grid_lines_per_axis: 3

  slab_outline_layers:
    - S-FNDN-1
    - A-WALL-1
    - A-WALL-2

  sliver_max_m2: 1.0
  zone_min_m2: 500
  target_zone_count: null    # 24 or 17 when known

  assignment_method: centroid_in_cell   # or max_intersection_area
  merge_across_beam_layers: false
```

Stage 1 `wall_layers` / auto-fallback **unchanged** for feature-freeze compatibility; zone engine **does not** depend on reducing Stage 1 face count.

---

## 10. Implementation phases (reference only)

| Phase | Deliverable | Success signal |
|-------|-------------|----------------|
| **P0** | Manifest YAML from J33A/J33B PDF schedules | Ground-truth INT count + areas |
| **P1** | Grid frame builder (T0b) + cell polygons | 24 cells on warehouse DXF |
| **P2** | Face assigner + zone union (T3) | 618 faces → 24 zones; areas vs manifest |
| **P3** | Joint profile for S111_J (T2+merge) | ~17 zones |
| **P4** | Schedule builder + validation report | Matches PDF column semantics |
| **P5** | OCR / label anchoring (optional) | Raster PDF → manifest assist |

**Explicit non-goals in P1–P4:** GUI changes, Excel/DXF export layout (design only here), modifications to `polygonize` behavior.

---

## 11. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Grid lines missing or on ignored layers | Wrong cell count | Manifest override; manual axis seed |
| 1:1 bay:INT assumption wrong for S111_A | Mislabeled zones | Confirm with client; manifest |
| Faces span grid line | Split assignment | Max-intersection rule; QA flag |
| Merging across real DCJ | Overstated pour | Barrier layer config |
| No INT text in DXF | Wrong labels | Manifest / grid index only |
| Raster PDF only | No automated label positions | OCR P5; manual manifest P0 |
| Double-count area | Wrong schedule | Union geometry, not sum of micro-areas |

---

## 12. Relation to existing work

| Artifact | Relationship |
|----------|--------------|
| `reference_pdf_analysis.md` | Evidence base for profiles and counts |
| `zone_detection_design.md` | Broader zone strategy; this doc narrows to **INT workflow** |
| `seed_assisted_fallback_design.md` | Fills **missing** INT cells only — not over-segmentation fix |
| `acceptance_readiness_report.md` | Face recall pending; add INT zone acceptance when manifest ready |
| `src/detector.py` | Stage 1 — unchanged role |
| `src/calculator.py` | Reuse area/volume math on **zone polygons** |

---

## 13. Summary

| Question | Answer |
|----------|--------|
| What is an INT zone? | QS **pour quantity region** (`INT-n`), not every closed polygon |
| Why 618 vs 24? | ~26 micro-faces per bay from beam/detail linework inside each grid cell |
| Grid lines? | Extract axes → **bay cells** → one INT per cell (J33A) |
| Structural bays? | Regular module ~800 m²; aggregator for all faces inside cell |
| Major joints? | **Hard boundaries** for irregular layouts (J33B); selective DCJ/HDLN |
| How to merge micro-polygons? | **Assign to frame** (grid) or **merge graph** (joints); `unary_union` per zone |
| Pipeline? | Raw polygons → frame → INT zones → area → volume → schedule |
| Next step? | P0 manifest transcription; then P1 grid + P2 assign on warehouse DWG |

---

*End of INT Zone Engine design specification*
