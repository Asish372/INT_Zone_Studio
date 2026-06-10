# Reference PDF Analysis — INT Zones vs Detector Output

**Date:** June 1, 2026  
**Source folder:** `C:\Users\Administrator\OneDrive\Desktop\freelancing project`  
**Previews:** `output/pdf_analysis/*.png`

---

## 1. PDF inventory and DWG mapping

| PDF | Size | Pages | Extractable text | Maps to Strtup DWG |
|-----|------|-------|------------------|-------------------|
| `J33A-MODSCAPE-INTERNALS.pdf` | 1.37 MB | 1 | **None** (raster/flattened) | `6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg` (drawing **6226-S111**) |
| `J33B BTR-INTERNALS.pdf` | 671 KB | 1 | **None** (raster/flattened) | Likely `S111_J.dwg` (Challenger / Stage 2 layout) |
| `S111-WAREHOUSE-SLAB-PLAN-Rev.C.pdf` | 298 KB | 1 | Yes — notes + **DCJ**, **PC1–PC3** | Same family as warehouse; **not** the INT overlay deliverable |
| `S111_J.pdf` | 310 KB | 1 | Yes — **DCJ**, **PC1–PC4**, **DC1**, **RSCJ** | `S111_J.dwg` — **source** structural plan |

**Important:** `INT-*` labels appear only on the **J33A / J33B INTERNALS** deliverables (yellow callouts + quantity table). They are **not** in the structural PDF text layer or in cached DXF grep.

---

## 2. How example regions are defined (from PDFs)

### 2.1 `J33A-MODSCAPE-INTERNALS.pdf` (warehouse — 24 zones)

| Attribute | Definition |
|-----------|------------|
| **Zone IDs** | `INT-1` … `INT-24` (yellow labels, centred in each bay) |
| **Layout** | Structural grid **1–24** (vertical) × **A–D** (horizontal) |
| **Zone geometry** | One **bay = one pour zone** = rectangle between adjacent grid lines (e.g. between grid 4–5 and B–C) |
| **Boundaries** | **Major grid / pour breaks** — not every internal saw-cut or detail line inside the bay |
| **Internal linework** | Dense detail inside each INT cell (joints, dots, annotations) → causes **many** geometric faces **inside** one INT zone |
| **Report** | **“SLAB SUMMARY SCHEDULE - VBC USE ONLY”** — columns include zone ID, **Concrete Area (SQM)**, **Concrete Volume (CUM)** |
| **Drawing title** | WAREHOUSE SLAB PLAN, **6226-S111**, scale 1:250 |

**Business rule:** Quantity is reported **per grid bay (INT-n)**, not per minimal closed loop.

### 2.2 `J33B BTR-INTERNALS.pdf` (17 zones)

| Attribute | Definition |
|-----------|------------|
| **Zone IDs** | `INT-1` … `INT-17` (visible) |
| **Layout** | Irregular warehouse; **not** a uniform 24-cell grid |
| **Boundaries** | Prominent **red** lines = construction / pour joints (align with structural grid where applicable) |
| **Zone types** | Large central pours (INT-1,2,3,5,6,7), narrow perimeter strips (INT-4,8,13–16), smaller zones near entry (INT-9–12,17) |
| **Report** | Table **“V&G USE ONLY”**: Pour No. (= INT), **Estimated SF**, **Estimated CY** |
| **Detail** | “TYPICAL DRY SUMP DETAIL” — local feature, not a separate INT unless labelled |

**Business rule:** Zones follow **major joint polygons**, ignoring column blockouts and minor internal geometry.

### 2.3 `S111-WAREHOUSE-SLAB-PLAN-Rev.C.pdf` & `S111_J.pdf` (engineering source)

These are **inputs**, not the client QS output:

| Label on plan | Meaning (typical) | Role in zone logic |
|---------------|-------------------|-------------------|
| **DCJ** | Dowelled construction joint | **Should** subdivide or define pour boundaries when aligned with INT breaks |
| **PC1 / PC2 / PC3 / PC4** | Pour / panel codes | Finer subdivision than INT on J33B; **over-segment** if all used as walls |
| **DC1** | Construction joint variant | Same family as DCJ |
| **RSCJ** | Reinforced saw-cut joint | Often **within** a pour, not a separate QS zone |
| Grid **1–10**, **A–C** | Structural grid | **Primary** merge frame for naming and boundaries |

Text extract: *“FOR ALL INTERNAL SLAB AREAS PROVIDE MINIMUM 100mm OF CLASS 3 CRUSHED ROCK…”* — scope is **internal slab**, matching INT zones.

---

## 3. Expected zones vs detector (quantitative)

| DWG (Strtup pipeline) | Detector polygons | Expected INT zones (PDF) | Ratio (detector ÷ zones) | Micro-polygons per INT (avg) |
|------------------------|------------------:|-------------------------:|-------------------------:|-----------------------------:|
| `6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg` | **618** | **24** (J33A) | **25.8×** | ~26 |
| `S111_J.dwg` | **331** | **17** (J33B) | **19.5×** | ~19 |
| `S111_A.dwg` | **397** | **~24** (assume same grid class as J33A until transcribed) | **~16.5×** | ~17 |

**Detector largest faces (~810 m² on S111_A)** ≈ **one structural bay**; **INT zone** on J33A = **one bay** (same scale). The detector is largely finding **bay cells** plus hundreds of **smaller** faces from beams, details, and joints inside/between bays.

**Area totals (detector, entire drawing):**

| Drawing | Detector total area (m²) | Notes |
|---------|---------------------------:|-------|
| Warehouse | 10,091.19 | Sum of **all** disjoint faces — should ≈ sum of INT-1…24 areas from schedule once transcribed |
| S111_A | 16,348.58 | |
| S111_J | 5,320.03 | Smaller footprint / Stage 2 |

---

## 4. Why over-segmentation happens (PDF-confirmed)

| # | Cause | Evidence from PDFs |
|---|--------|-------------------|
| 1 | **Wrong unit of report** | J33A defines **24** regions; detector emits **618** |
| 2 | **Internal lines treated as walls** | Inside each yellow INT box, drawing shows many interior lines; polygonize creates one face per cell |
| 3 | **All fallback layers polygonized** | `S-BEAM-*`, `A-DETL-*` split bays further (validation_report candidate layers) |
| 4 | **Exhaustive mode** | Keeps slivers; PDF zones have **no** 0.01 m² regions |
| 5 | **DCJ/PC vs INT semantics** | Source plan has **many** DCJ/PC labels; INT deliverable **aggregates** to grid bays (J33A) or major red joints (J33B) |
| 6 | **Deliverable ≠ DXF** | INT labels exist only on raster INTERNALS PDFs — cannot grep from DXF |

---

## 5. Strategy to reach business-level zones (updated)

### 5.1 Target definition per project type

| Project pattern | Zone count | Boundary rule | Label source |
|-----------------|-----------|---------------|--------------|
| **Grid warehouse (J33A)** | 24 = (grid1..24) × (A..D bays) | Cells between **S-GRID-*** / major foundations; **ignore** interior beam mesh as zone walls | INT-1…24 from grid index or OCR table |
| **Irregular warehouse (J33B)** | 17 | **DCJ / major joint** network + merge small faces | INT-1…17 from OCR / manifest |
| **Debug / QA** | 331–618 | Current polygonize | Room 1…N |

### 5.2 Recommended pipeline

```text
1. Parse structural grid (S-GRID-1, S-GRID-IDEN layers) → grid lines
2. Build bay cells = rectangle between adjacent grid lines (24 for warehouse)
3. Optional: clip cells to slab outline (S-FNDN-1 perimeter)
4. Assign label INT-{sequential} row-major or match OCR label positions from J33 PDF
5. Area_zone = union of all detector faces whose centroid ∈ cell (or intersection area)
6. Volume = area × thickness from config
7. Export schedule matching “SLAB SUMMARY SCHEDULE” columns
```

**Alternative for J33B:** Merge faces across **non-DCJ** edges until ≈17 components; validate count against manifest.

### 5.3 Transcription task (P0)

Manually or OCR transcribe from J33A schedule:

- `INT-n` → Area (SQM), Volume (CUM) for acceptance vs aggregated detector zones.

Store as `reference/j33a_zones_manifest.yaml`.

---

## 6. File cross-reference (freelancing folder)

```
freelancing project/
  6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg  ←→  J33A-MODSCAPE-INTERNALS.pdf (24 INT)
  S111_J.dwg                               ←→  J33B BTR-INTERNALS.pdf (17 INT)
                                              S111_J.pdf (source)
  S111_A.dwg                               ←→  (no INT PDF in folder; infer J33A-style grid)
  S111-WAREHOUSE-SLAB-PLAN-Rev.C.pdf       ←→  engineering issue (Rev C)
```

---

## 7. Acceptance criteria shift

| Metric | Old (geometric) | New (business, from PDFs) |
|--------|-----------------|---------------------------|
| Region count | 618 = success | **24** (warehouse) / **17** (J33B) |
| Label | Room 1…N | **INT-n** |
| Area check | Per micro-face vs AutoCAD | Per **INT zone** vs schedule SQM |
| Recall | Maximize faces | **Cover all INT zones**; micro-faces optional debug sheet |

---

## 8. Next steps

1. Copy PDFs into `Strtup/input/reference/` for version control.
2. Transcribe **SLAB SUMMARY SCHEDULE** from J33A (24 rows) into YAML.
3. Implement **grid-cell zone builder** (Phase P1) before generic face merge.
4. Use `seed_assisted_fallback_design.md` only for **missing** INT cells, not for fixing over-count.

See also: `zone_detection_design.md` (architecture).
