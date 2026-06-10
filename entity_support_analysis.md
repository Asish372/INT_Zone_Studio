# Entity Support Analysis — `unsupported_entity_miss`

**Generated:** 2026-06-05  
**Phase:** Pre-P2 prioritization review  
**Sources:** `detection_coverage_report.md`, `coverage_metrics.xlsx`, `output/entity_support_analysis_data.json`  
**Drawings:** `6276.S111-WAREHOUSE SLAB PLAN-Rev_F`, `S111_A`, `S111_J`

---

## Executive conclusion

**Entity-support expansion should NOT be prioritized ahead of gap-closure improvements** for the current S111 drawing family.

The `unsupported_entity_miss` category (387 P1 records) is **misleadingly large**. It is almost entirely driven by a proximity heuristic (INSERT within 1500 units of an unresolved gap endpoint), not by confirmed missing boundary geometry. Spatial analysis shows:

- Slab/block boundaries are already represented by **1,012–1,524 LINE segments** on structural layers (`S-FNDN-1`, `S-BEAM-*`, `A-WALL-*`).
- Unsupported entities are predominantly **annotation** (MTEXT, HATCH) or **point features** (column/footing/grid INSERTs), not missing pour-boundary loops.
- Actionable miss drivers remain **gap-closure failures** (`bearing_mismatch_miss`: 169, `pairing_conflict_miss`: 25, `gap_blocked_closure`: 60).

**Recommended priority:** Proceed with **P2 gap-closure work** first. Defer broad INSERT/MTEXT/HATCH support; consider **selective HATCH-on-slab-layer** support only as a future per-project option.

---

## 1. P1 `unsupported_entity_miss` breakdown

### 1.1 Miss record composition (from `coverage_metrics.xlsx`)

| Record type | Count | Entity type field | Meaning |
| --- | ---: | --- | --- |
| `entity-miss-insert-near-gap-*` | **384** | `INSERT` | Gap endpoint within 1500 units of an INSERT |
| `entity-miss-unsupported-summary` | **3** | Multi-type comma list | Drawing-level exposure summary |
| **Total** | **387** | | |

**Per drawing:**

| Drawing | `unsupported_entity_miss` records |
| --- | ---: |
| Warehouse Rev_F | 76 |
| S111_A | 102 |
| S111_J | 209 |

**Important:** No individual miss records are emitted for MTEXT, HATCH, CIRCLE, or DIMENSION. Those types appear only in the 3 summary rows. The category total is **not** 387 independent boundary misses — it is **384 INSERT-proximity flags + 3 summaries**.

### 1.2 Modelspace entity inventory (unsupported types)

| Entity type | Warehouse | S111_A | S111_J | **Total** |
| --- | ---: | ---: | ---: | ---: |
| **INSERT** | 271 | 286 | 153 | **710** |
| **MTEXT** | 249 | 269 | 221 | **739** |
| **HATCH** | 16 | 7 | 32 | **55** |
| **CIRCLE** | 8 | 1 | 10 | **19** |
| **DIMENSION** | 0 | 0 | 3 | **3** |
| **Other unsupported** | — | — | — | **0** |

---

## 2. Boundary contribution vs annotation-only

### 2.1 Classification method

Each unsupported entity was classified using:

1. **Layer role** — annotation hints (`ANNO`, `TEXT`, `NOTE`, `DIM`, `IDEN`, `GRID`, `GENF`, `COLS`, etc.)
2. **Spatial proximity** — distance to active detection segment network (≤ 500 units) and to unresolved gap/free endpoints (≤ 1500 units)
3. **INSERT block inspection** — whether block definition contains LINE/LWPOLYLINE/ARC geometry
4. **HATCH path presence** — whether hatch has boundary paths and which layer it sits on

### 2.2 Summary by entity type

| Entity type | Total entities | On annotation layers | On boundary-candidate layers | Near segment network | Near gap endpoint | **Boundary role** |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **INSERT** | 710 | 530 (75%) | 180 (25%) | 501 (71%) | 199 (28%) | **Point features** (columns, footings, grids) — not pour loops |
| **MTEXT** | 739 | 739 (100%) | 0 | 154 (21%) | 85 (11%) | **Annotation only** |
| **HATCH** | 55 | 55 (100%) | 0 | 0 | 0 | **Annotation / finish shading** |
| **CIRCLE** | 19 | 15 (79%) | 4 (21%) | 8 (42%) | 7 (37%) | **Annotation / detail markers** |
| **DIMENSION** | 3 | 3 (100%) | 0 | 3 | 1 | **Annotation only** |

### 2.3 INSERT deep dive

INSERT is the only type with meaningful geometric content in block definitions:

| Drawing | INSERT count | Block has LINE/ARC geometry | Block has no geometry | Near gap | Near segment |
| --- | ---: | ---: | ---: | ---: | ---: |
| Warehouse Rev_F | 271 | 247 (91%) | 24 | 33 | 148 |
| S111_A | 286 | 257 (90%) | 29 | 91 | 241 |
| S111_J | 153 | 129 (84%) | 24 | 75 | 112 |
| **Total** | **710** | **633 (89%)** | **77** | **199** | **501** |

**Dominant INSERT layers:**

| Layer | INSERT count (all drawings) | Role |
| --- | ---: | --- |
| `S-COLS` | 295 | Column symbols — interior point obstacles |
| `S-COLS-1` | 113 | Column symbols |
| `S-COLS-IDEN-1` | (MTEXT, not INSERT) | Labels |
| `S-GRID-IDEN` | 66 | Grid identification markers |
| `S-FNDN-1` | 100 | Footing/column placement on slab layer |
| `S-FNDN-HDLN-1` | 59 | Footing symbols near pour-break lines (S111_A) |
| `A-DETL-GENF` | 49 | Detail/finish graphics |

**Dominant block families:** `SGE_SCL-Column-*`, `SGE Footing-*`, `Grid - 1_Project Grid`, `SGE Door Column - DC1`.

These are **Revit-exported structural families** placed at grid/column intersections. They sit near gap endpoints because columns and door openings coincide with wall line breaks — correlation, not causation.

**Critical finding:** INSERT geometry describes **column/footing footprints**, not the **missing edges of slab pour regions**. The pour boundary lines are already present as native LINE entities on `S-FNDN-1` / `S-BEAM-*` / `A-WALL-*`.

### 2.4 MTEXT deep dive

| Drawing | MTEXT | Annotation layers | Near gap | Near segment |
| --- | ---: | ---: | ---: | ---: |
| Warehouse | 249 | 249 (100%) | 13 | 61 |
| S111_A | 269 | 269 (100%) | 17 | 29 |
| S111_J | 221 | 221 (100%) | 55 | 64 |

Layers: `G-ANNO-TEXT-*`, `S-COLS-IDEN-1`, `A-ANNO-NOTE`, `S-GRID-IDEN-1`.

MTEXT entities are **grid IDs, column IDs, and general notes**. They have no closed boundary geometry and cannot form blocks.

### 2.5 HATCH deep dive

| Drawing | HATCH | Has paths | On boundary layer | On annotation layer |
| --- | ---: | ---: | ---: | ---: |
| Warehouse | 16 | 16 | 0 | 16 |
| S111_A | 7 | 7 | 0 | 7 |
| S111_J | 32 | 32 | 0 | 32 |

Layers: `G-ANNO-TEXT-2`, `A-DETL-GENF-*` (finish/shading hatches).

**Zero hatches** sit on slab/foundation boundary layers in these drawings. HATCH support would not recover any missed block on this dataset.

### 2.6 Others (CIRCLE, DIMENSION)

- **CIRCLE** (19): predominantly `G-ANNO-TEXT-*` annotation bubbles; 4 on `A-DETL` in S111_J.
- **DIMENSION** (3): all on `A-ANNO-DIMS-1`.

No evidence of boundary-defining circles or dimensions.

---

## 3. Expected recall gain by entity type

Estimates are for **block detection recall** (finding enclosed pour regions), not area accuracy. No ground-truth FN count exists; ranges are based on spatial correlation and gap-miss overlap.

| Entity type | Expected recall gain | Rationale |
| --- | --- | --- |
| **INSERT (full explosion)** | **0–2%** | Columns/footings may add micro-polygons around point features; unlikely to close existing gap misses. 633/710 blocks already contain lines but represent interior obstacles. |
| **INSERT (selective: footing on HDLN only)** | **0–1%** | 59 INSERT on `S-FNDN-HDLN-1` (S111_A); HDLN lines already extracted as LINE (67 segments). Redundant. |
| **HATCH (all layers)** | **0%** | All 55 hatches on annotation/detail layers on these drawings. |
| **HATCH (slab layers only, future)** | **0% here; 5–15% on other projects** | Would help only when CAD encodes pours as closed hatches on `S-FNDN-*` / slab layers. Not present in S111 family. |
| **MTEXT** | **0%** | Pure labels; no geometry. |
| **CIRCLE** | **0%** | Annotation markers. |
| **DIMENSION** | **0%** | Annotation. |

### Comparison: gap-closure expected gain

| Miss driver | P1 miss events | Expected recall gain | Evidence strength |
| --- | ---: | --- | --- |
| `bearing_mismatch_miss` | 169 | **5–12%** | Within-threshold pairs not bridged; direct topology break |
| `pairing_conflict_miss` | 25 | **2–5%** | Greedy pairing leaves valid closures open |
| `gap_blocked_closure` | 60 | **3–8%** | Above-threshold and large gaps |
| `unknown_unresolved` | 40 | **2–5%** | Orphan endpoints after close |
| **`unsupported_entity_miss`** | **387** (384 INSERT proximity) | **0–2%** | Correlation with gaps, not missing boundaries |

Gap-closure addresses **254 topology-classified miss events** with direct causal links to unclosed loops. Entity support addresses **0 confirmed missing boundary loops** on these drawings.

---

## 4. Implementation complexity and false-positive risk

| Entity type | Implementation complexity | False-positive risk | Recommendation |
| --- | --- | --- | --- |
| **INSERT explosion** | **High** — block transform, nested blocks, unit scale, layer inheritance, performance on 700+ inserts | **High** — column footprints subdivide bays into spurious micro-blocks; over-segmentation already 16–26× vs INT zones | **Defer** |
| **INSERT selective** (column layers excluded) | **Medium** | **Medium** — footing symbols may still bisect regions incorrectly | **Defer** unless project-specific need |
| **HATCH (boundary layers)** | **Medium** — path extraction, arc bulges, island holes | **Low–Medium** on correct layers; **High** if all layers enabled | **Future per-project toggle only** |
| **MTEXT** | **Low** technically | **Very High** — would create nonsense boundaries from text boxes | **Do not implement** |
| **CIRCLE / DIMENSION** | **Low** | **High** — annotation noise | **Do not implement** |

---

## 5. Why P1 over-counts `unsupported_entity_miss`

The P1 instrumentation uses two rules:

1. **Summary rule** — one record per drawing if any unsupported type exists (counts MTEXT/HATCH/INSERT exposure).
2. **INSERT proximity rule** — one record per unique gap endpoint within 1500 units of any INSERT.

This produces **384 INSERT records** from only **199 INSERT entities** actually near gaps, because multiple gap endpoints can cluster around the same column opening. The category ranks #1 (387) in the coverage report but does **not** represent 387 missing blocks.

**P1 instrumentation refinement (recommended, not blocking P2):**

- Split `unsupported_entity_miss` into `unsupported_entity_exposure` (inventory) vs `unsupported_entity_correlated` (spatial correlation with confirmed open topology).
- Deduplicate INSERT proximity by INSERT handle, not gap endpoint.
- Exclude annotation layers from INSERT proximity scoring.

---

## 6. Prioritization decision

### Should entity-support expansion precede gap-closure?

| Criterion | Entity support | Gap closure (P2) |
| --- | --- | --- |
| Confirmed missing boundaries | **No** — boundaries exist as LINE | **Yes** — 101 open endpoints, 194 within-threshold unclosed |
| P1 miss signal quality | **Low** — proximity heuristic inflated | **High** — direct gap failure reasons |
| Expected recall gain | **0–2%** | **10–20%** (combined topology fixes) |
| Implementation complexity | **High** (INSERT) | **Medium** (algorithm change) |
| False-positive risk | **High** (INSERT/HATCH all layers) | **Low–Medium** (bridge quality tuning) |
| Dataset fit (S111 family) | **Poor** — Revit column/grid exports | **Strong** — door/opening gaps documented |

### Decision: **Gap-closure first (P2)**

Entity-support work should be limited to:

1. **Refine P1 taxonomy** — separate exposure from correlated misses (low effort).
2. **Optional future HATCH tier** — config-gated `hatch_boundary_layers` for projects that encode pours as hatches (not S111).
3. **No MTEXT/CIRCLE/DIMENSION support** — no boundary value.
4. **No broad INSERT explosion** — risks over-segmentation; columns are not missing slab boundaries.

---

## 7. Per-drawing quick reference

### Warehouse Rev_F

| Metric | Value |
| --- | ---: |
| P1 `unsupported_entity_miss` | 76 |
| INSERT near gap (spatial) | 33 |
| MTEXT / HATCH | 249 / 16 (100% annotation) |
| Open endpoints after close | 31 |
| Dominant gap miss | `bearing_mismatch_miss` (30) |

### S111_A

| Metric | Value |
| --- | ---: |
| P1 `unsupported_entity_miss` | 102 |
| INSERT near gap (spatial) | 91 |
| MTEXT / HATCH | 269 / 7 (100% annotation) |
| Open endpoints after close | 20 |
| Dominant gap miss | `bearing_mismatch_miss` (60) |

### S111_J

| Metric | Value |
| --- | ---: |
| P1 `unsupported_entity_miss` | 209 |
| INSERT near gap (spatial) | 75 |
| MTEXT / HATCH | 221 / 32 (100% annotation) |
| Open endpoints after close | 50 |
| Dominant gap miss | `bearing_mismatch_miss` (79) + `pairing_conflict_miss` (24) |

---

## 8. Next steps

1. **Proceed with P2 gap-closure** — global min-cost endpoint matching, iterative close loop, pair-level audit.
2. **Refine P1 `unsupported_entity_miss` scoring** — dedupe and split exposure vs correlated (parallel, low risk).
3. **Park INSERT/HATCH expansion** — revisit only if a future drawing family encodes boundaries exclusively in blocks or slab-layer hatches.
4. **Do not add MTEXT support** under any current scope.

---

*Analysis script: `scripts/analyze_entity_support.py` — raw data: `output/entity_support_analysis_data.json`*
