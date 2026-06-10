# Delivery Closure Plan

**Role:** CAD QA Lead  
**Date:** 2026-06-02  
**Project:** DXF CAD Room Detection & INT Zone Area Calculation System  
**Drawings in scope:** `6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg` (J33A), `S111_J.dwg` (J33B), `S111_A.dwg`  
**Architecture / code:** FROZEN — no new features, no refactors  

---

## Current system status (snapshot)

| Area | State | Gate status |
| --- | --- | --- |
| Detection pipeline (3 drawings) | Runs clean; 618 / 331 / 397 regions; 0 invalid polygons | Automated: PASS |
| Unit test suite | 20/20 passed | PASS |
| Export outputs (Excel + DXF) | Present in `output/` | PASS |
| INT zone engine (P2/P3/P4/P5) | Wired; milestone report PASS on all 3 drawings | PASS |
| INT zone count vs manifest expected | 24/24 (J33A), 17/17 (J33B), 24/24 (S111_A) | PASS |
| **Manifest transcription (P0)** | Both YAML files are `status: template`; all `area_sqm = null` | **BLOCKED** |
| **Manifest area gate (0.05%)** | 100% SKIP — cannot execute until P0 complete | **BLOCKED** |
| **Detection recall vs AutoCAD** | AutoCAD region counts not recorded; recall % unknown | **BLOCKED** |
| **Area benchmark vs AutoCAD** | 0 / 30 benchmark regions measured | **BLOCKED** |
| **Empty zone investigation** | INT-1, INT-8, INT-10 (J33A); INT-16 (J33B) — root cause not documented | **OPEN** |
| **J33B semantic validation** | J33B YAML empty; INT zone SQM/CUM values unverified against PDF | **BLOCKED** |
| Client delivery package | Not assembled | **NOT STARTED** |

---

## Delivery blockers — detail

### DB-1 · Manifest transcription workflow (P0)

**What is missing:** Both `reference/j33a_zones_manifest.yaml` and `reference/j33b_zones_manifest.yaml` have `transcription.status: template` and every `area_sqm` / `volume_cum` field is `null`. The manifest area gate in `manifest_reconciliation.py` is unconditionally SKIP when status = `template`. No area delta comparison can be produced.

**Source PDFs to transcribe:**

| Manifest | Source PDF | Schedule title | Zones |
| --- | --- | --- | --- |
| `j33a_zones_manifest.yaml` | `J33A-MODSCAPE-INTERNALS.pdf` | "SLAB SUMMARY SCHEDULE - VBC USE ONLY" | INT-1 … INT-24 |
| `j33b_zones_manifest.yaml` | `J33B BTR-INTERNALS.pdf` | "V&G USE ONLY" (may be imperial SF/CY — convert) | INT-1 … INT-17 |

**Remaining tasks:**

| # | Task | Owner |
| --- | --- | --- |
| DB-1.1 | Locate and open `J33A-MODSCAPE-INTERNALS.pdf`; extract area_sqm and volume_cum for INT-1 … INT-24 from the slab summary schedule | QA |
| DB-1.2 | Enter values into `reference/j33a_zones_manifest.yaml`; set `transcription.status: complete`, fill `transcribed_by` and `transcribed_at` | QA |
| DB-1.3 | Locate and open `J33B BTR-INTERNALS.pdf`; extract values for INT-1 … INT-17; convert SF → m² (÷ 10.7639) and CY → m³ (× 0.7646) if schedule is imperial | QA |
| DB-1.4 | Enter values into `reference/j33b_zones_manifest.yaml`; set `transcription.status: complete` | QA |
| DB-1.5 | Re-run INT zone pipeline on J33A: `python main.py --zones -i input/6276.S111-WAREHOUSE\ SLAB\ PLAN-Rev_F.dwg --manifest reference/j33a_zones_manifest.yaml` | QA |
| DB-1.6 | Re-run INT zone pipeline on J33B: `python main.py --zones -i input/S111_J.dwg --manifest reference/j33b_zones_manifest.yaml` | QA |
| DB-1.7 | Confirm `manifest_area` gate changes from SKIP → PASS or FAIL in both `*_int_zone_report.md` files | QA |

**Evidence required:** Updated YAML files with all `area_sqm` populated; regenerated `*_int_zone_report.md` with `manifest_area` gate = PASS (not SKIP, not FAIL).

**Pass criterion:** Every INT zone shows `Δ % ≤ 0.05%` against manifest value; gate = PASS. If any zone FAIL, log root cause (document only — no code change).

**Estimated effort:** 2–4 hours (manual transcription) + 30 min (pipeline re-runs and review).

---

### DB-2 · Empty zone investigation

**What is missing:** Three zones in J33A (INT-1, INT-8, INT-10) and one in J33B (INT-16) have zero faces assigned. The pipeline reports `REVIEW` for `zone_face_coverage` but no root cause has been documented. Client-deliverable reports must explain each empty zone — whether it is a legitimate structural boundary (e.g., edge strip, drainage pit, column line bay) or a detection gap.

**Current data:**

| Drawing | Empty zone | Clipped bay area (m²) | Grid position |
| --- | --- | --- | --- |
| J33A | INT-1 | 17.37 (low coverage, 16.3%) | Row 0, Col 0 |
| J33A | INT-8 | 2.61 (clipped bay very small) | Row 1, Col 1 |
| J33A | INT-10 | 89.04 (full-size bay, 100% coverage) | Row 1, Col 3 |
| J33B | INT-16 | Unknown | Row varies |

**Remaining tasks:**

| # | Task | Owner |
| --- | --- | --- |
| DB-2.1 | Open `output/6276.S111-WAREHOUSE SLAB PLAN-Rev_F_int_zones.dxf` in AutoCAD/DXF viewer; locate INT-1, INT-8, INT-10 bay boundaries on the drawing | QA |
| DB-2.2 | For INT-10 (full-size bay, 0 faces): determine whether the bay is genuinely blank on the slab plan (no internal pour boundary geometry) or whether the micro-face filter excluded all geometry inside it | QA |
| DB-2.3 | For INT-1 and INT-8 (very small clipped areas): confirm whether these are edge bays with minimal slab coverage; document as expected behaviour if confirmed | QA |
| DB-2.4 | Repeat for J33B INT-16 using `output/S111_J_int_zones.dxf` (if generated) or re-run pipeline | QA |
| DB-2.5 | Write a 1-paragraph root-cause note for each empty zone; attach to `*_int_zone_report.md` under a new "## Empty zone root cause" section (append only — no code change) | QA |

**Evidence required:** Written root-cause note per empty zone confirming either (a) structurally empty bay or (b) known detection gap with documented coordinates.

**Pass criterion:** Each empty zone has a recorded disposition: `EXPECTED_EMPTY` or `DETECTION_GAP_DOCUMENTED`. No empty zone may remain `unexplained` at delivery.

**Estimated effort:** 1–2 hours.

---

### DB-3 · J33B semantic validation

**What is missing:** J33B (`S111_J.dwg`) has 17 INT zones produced but the manifest YAML (`j33b_zones_manifest.yaml`) has never been transcribed. Beyond the area gate (covered by DB-1), the zone semantics — which INT label maps to which named pour in the structural schedule — have not been verified. The INT labels are assigned deterministically row-major from the grid, but the grid for J33B uses profile `JOINT_WAREHOUSE` which may have an irregular layout. The zone-to-schedule mapping must be confirmed before the client can use the schedule export.

**Remaining tasks:**

| # | Task | Owner |
| --- | --- | --- |
| DB-3.1 | Open `J33B BTR-INTERNALS.pdf`; identify how pours are named in the "V&G USE ONLY" schedule (Pour No. / label convention) | QA |
| DB-3.2 | Open `output/S111_J_int_zones.dxf` (or re-run pipeline to generate it); overlay INT-1 … INT-17 labels against the PDF pour layout | QA |
| DB-3.3 | Confirm each INT-n maps to the correct pour; record any label mismatch as a `grid_ref` or `notes` entry in `j33b_zones_manifest.yaml` | QA |
| DB-3.4 | If INT label order does not match PDF pour numbering, record the remapping table in the manifest `notes` field (do not renumber in code — architecture frozen) | QA |
| DB-3.5 | Re-run INT schedule export for J33B after YAML is complete (DB-1.6 satisfies this if done in order) | QA |

**Evidence required:** `j33b_zones_manifest.yaml` with `grid_ref` populated per zone; a written sign-off note confirming INT-n ↔ PDF pour-n correspondence or documenting any known reordering.

**Pass criterion:** All 17 zones have confirmed pour identification; any label-order discrepancy is documented with a remapping table.

**Estimated effort:** 1–2 hours.

---

### DB-4 · Export verification

**What is missing:** The export outputs exist in `output/` but have not been formally verified against the acceptance criteria. Specifically:

1. **Excel schedule** (`*_int_schedule.xlsx`): Pour No., SQM, CUM, face_count columns must be present and non-empty for all non-empty zones.
2. **Annotated DXF** (`*_int_zones.dxf`): Zones must be visually inspectable and layer-correct.
3. **Detection Excel** (`*_results.xlsx`): Must be present for all 3 drawings.
4. **Area accuracy benchmark**: 0 of 30 target regions have been measured in AutoCAD. PRD NFR-02 / TRD T-03 require area error ≤ 0.05% on real drawing regions.
5. **Detection recall**: AutoCAD ground-truth region counts have not been entered; PRD NFR-02a / TRD T-08 recall > 90% cannot be confirmed.

**Remaining tasks:**

| # | Task | Owner |
| --- | --- | --- |
| DB-4.1 | Open `output/6276.S111-WAREHOUSE SLAB PLAN-Rev_F_int_schedule.xlsx`; verify columns: Pour No. (INT-n), SQM, CUM, face_count; check all 24 rows populated (empty zones may show 0.00) | QA |
| DB-4.2 | Open `output/6276.S111-WAREHOUSE SLAB PLAN-Rev_F_int_zones.dxf` in AutoCAD or eZDraw; confirm zone polygons are visible and correctly layered | QA |
| DB-4.3 | Confirm `output/S111_J_int_schedule.xlsx` and `output/S111_A_int_schedule.xlsx` (or equivalents) exist; repeat column check for 17 and 24 zones respectively | QA |
| DB-4.4 | **Area benchmark (manual):** Using `acceptance_readiness_report.md §4.1` as the worksheet, open each drawing in AutoCAD, trace the boundary of the top 10 regions per drawing (30 total), run AREA command, record m² | QA |
| DB-4.5 | Enter AutoCAD AREA values into `area_benchmark_template.md`; compute Error % = |Detector − AutoCAD| ÷ AutoCAD × 100; flag any > 0.05% | QA |
| DB-4.6 | **Recall benchmark (manual):** For each of the 3 drawings, count closed regions in AutoCAD using same boundary layers as `auto_fallback` (S-FNDN-1, S-BEAM-2/1, A-WALL-1/2/3); enter counts into `verification_summary.md §Step 3` | QA |
| DB-4.7 | Compute recall % = (Detected ÷ AutoCAD) × 100; confirm > 90% for each drawing; document in `acceptance_readiness_report.md §3.1` | QA |

**Evidence required:**
- Screenshot or export of each verified Excel file (column headers + row count visible)
- DXF visual confirmation (screenshot with zones visible)
- Completed `area_benchmark_template.md` with all 30 rows filled and Error % computed
- Completed `verification_summary.md §Step 3` with recall % per drawing

**Pass criteria:**
- All Excel outputs have expected columns and correct row count
- Area Error % ≤ 0.05% on all 30 benchmark regions
- Detection recall > 90% on each of the 3 drawings
- No missing output files

**Estimated effort:** 3–5 hours (area and recall measurements are the dominant cost; each requires AutoCAD work on real geometry).

---

### DB-5 · Client delivery package

**What is missing:** No delivery package directory or manifest exists. The client receives a defined set of output artifacts, not the full repository.

**Remaining tasks:**

| # | Task | Owner |
| --- | --- | --- |
| DB-5.1 | Create `output/client_delivery/` directory | QA |
| DB-5.2 | Copy final outputs (after DB-1 through DB-4 pass): all `*_int_schedule.xlsx`, all `*_annotated.dxf`, all `*_int_zones.dxf`, all `*_results.xlsx`, both `*_int_zone_report.md` files | QA |
| DB-5.3 | Copy acceptance evidence: `acceptance_readiness_report.md` (updated with completed tables), `area_benchmark_template.md` (completed), `verification_summary.md` (completed recall table) | QA |
| DB-5.4 | Write `output/client_delivery/DELIVERY_MANIFEST.md` listing every file, its SHA-256 hash, and the gate it satisfies | QA |
| DB-5.5 | Run a final completeness check: confirm every INT zone in both schedule XLSXs has SQM > 0 or `EXPECTED_EMPTY` disposition; confirm no SKIP gates remain in either `*_int_zone_report.md` | QA |
| DB-5.6 | Obtain sign-off from Product Owner / Engineering Lead on `acceptance_readiness_report.md` Criteria A and B verdicts before releasing package | Product Owner |

**Evidence required:** `output/client_delivery/DELIVERY_MANIFEST.md` with file list + hashes; signed acceptance report (Criteria A and B filled as PASS or documented exception).

**Pass criterion:** Delivery package directory contains all required artifacts; no gate is SKIP or FAIL without a written exception; product owner sign-off recorded.

**Estimated effort:** 1 hour (assembly) + sign-off lead time.

---

## Gate dependency chain

```
DB-1 (transcription)
    └─► DB-3 (J33B semantic)
    └─► manifest_area gate: SKIP → PASS

DB-2 (empty zone investigation)
    └─► empty zone dispositions documented

DB-4 (export verification)
    ├─► DB-1 must complete first (INT schedule values depend on manifest)
    └─► Area + recall benchmarks are independent of DB-1

DB-5 (delivery package)
    └─► ALL of DB-1, DB-2, DB-3, DB-4 must reach PASS
```

No gate in DB-5 can close until DB-1 through DB-4 are individually resolved.

---

## Summary table

| Blocker | Estimated effort | Prerequisite | Current status | Delivery gate |
| --- | --- | --- | --- | --- |
| DB-1 Manifest transcription (J33A + J33B) | 2.5–4.5 h | PDF source files present | BLOCKED — YAML template | **HARD BLOCKER** |
| DB-2 Empty zone investigation | 1–2 h | DXF viewer access | OPEN — undocumented | **HARD BLOCKER** |
| DB-3 J33B semantic validation | 1–2 h | DB-1 YAML + PDF | BLOCKED — no values | **HARD BLOCKER** |
| DB-4 Export verification (Excel/DXF + benchmarks) | 3–5 h | AutoCAD + DB-1 complete | PARTIALLY OPEN — files exist, not verified | **HARD BLOCKER** |
| DB-5 Client delivery package assembly | 1 h + sign-off | DB-1–DB-4 all PASS | NOT STARTED | **FINAL GATE** |
| **Total estimated effort** | **8.5–14.5 h** | | | |

---

## What can be approved today (without further work)

| Item | Evidence on record | Verdict |
| --- | --- | --- |
| DWG → DXF conversion pipeline | Validation report 2026-06-01 — 3/3 drawings converted clean | **APPROVED** |
| Region detection (candidate layer auto-fallback) | 618 / 397 / 331 regions; 0 invalid polygons | **APPROVED** |
| INT zone count vs manifest expected | 24/24 (J33A), 17/17 (J33B) — milestone report 2026-06-02 | **APPROVED** |
| Zone geometry (no overlaps, no orphans, stable labels) | Milestone report all criteria ✓ | **APPROVED** |
| Area math on synthetic geometry (0.05% test) | `tests/test_accuracy.py` — 20/20 pass | **APPROVED** |
| Excel + DXF export produced | Files present in `output/` | **APPROVED (structure only — content unverified)** |

## What cannot be approved without completing the blockers above

| Item | Reason |
| --- | --- |
| INT zone area accuracy (0.05% vs manifest) | Manifest is `template`; all values null — DB-1 required |
| J33B zone semantic correctness | No pour-to-INT mapping confirmed — DB-3 required |
| Empty zone acceptability | No root cause on record — DB-2 required |
| Detection recall > 90% | AutoCAD ground-truth count not recorded — DB-4 required |
| Real-drawing area benchmark (30 regions) | No AutoCAD measurements taken — DB-4 required |
| Client delivery package | Upstream blockers unresolved — DB-5 required |

---

## Recommended execution order

1. **Immediately:** DB-1 (transcription) — this unblocks DB-3 and the manifest gate in DB-4.
2. **In parallel with DB-1:** DB-2 (empty zone investigation) — independent of transcription.
3. **After DB-1 complete:** DB-3 (J33B semantic) — verify zone labelling against PDF.
4. **After DB-1 + DB-3:** DB-4 (export verification + benchmarks) — full evidence collection.
5. **Last:** DB-5 (package assembly + sign-off) — only when DB-1–DB-4 all closed.

---

*End of delivery closure plan*
