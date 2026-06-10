# Implementation Plan
## DXF CAD Room Detection & Grid-Based Zone Detection Engine

| Document section | Version | Scope |
|------------------|---------|--------|
| §1–§7 below | **1.0** (historical) | Original 10-phase room detection plan |
| §8–§12 below | **2.0** (current) | Zone Engine phases and remaining roadmap |

**Version:** 2.0 | **Date:** June 2026

---

## 1. Overview

| Item | Detail |
|---|---|
| Total Duration | 22 working days (≈ 4.5 weeks) |
| Approach | Phase-by-phase — each phase independently testable |
| Tech Stack | Python 3.10+, ezdxf, Shapely, pandas, openpyxl |
| Tools | Cursor IDE (AI-assisted), ChatGPT, Antigravity |
| Milestone Rule | Never move to next phase unless current phase passes verification |

---

## 2. Pre-Work Checklist (Day 0 — Before Coding)

```
☐  Python 3.10+ installed and verified  (python --version)
☐  Cursor IDE installed and opened
☐  Sample DXF files placed in input/ folder
☐  config.yaml created with correct layer names from client DXF
☐  All dependencies installed (pip install -r requirements.txt)
☐  test_setup.py runs and prints "Setup OK"
☐  output/ and logs/ folders created
```

**Setup verification command:**
```bash
python test_setup.py
# Expected output:
# ✓ Python 3.10+
# ✓ ezdxf imported
# ✓ shapely imported
# ✓ pandas imported
# ✓ openpyxl imported
# Setup OK — ready to build
```

---

## 3. Phase-by-Phase Plan

---

### PHASE 1 — DXF Parser
**Duration:** 1–2 days
**Goal:** Read any DXF file and print what's inside

#### Tasks

| # | Task | File | Done |
|---|---|---|---|
| 1.1 | Write `load_dxf(filepath)` — open file, handle errors | `src/parser.py` | ☐ |
| 1.2 | Write `get_modelspace(doc)` — return model space | `src/parser.py` | ☐ |
| 1.3 | Write `list_layers(doc)` — print all layer names | `src/parser.py` | ☐ |
| 1.4 | Add `if __name__ == "__main__"` test block | `src/parser.py` | ☐ |
| 1.5 | Write `test_parser.py` unit test | `tests/` | ☐ |

#### Cursor Prompt for This Phase
```
Create src/parser.py for a DXF processing project.

Functions needed:
1. load_dxf(filepath: str) -> ezdxf.Document
   - Open DXF file using ezdxf.readfile()
   - If FileNotFoundError: print clear message and exit
   - If ezdxf.DXFStructureError: print "Corrupted DXF" and exit

2. get_modelspace(doc) -> Modelspace
   - Return doc.modelspace()

3. list_layers(doc) -> List[str]
   - Return list of all layer names in the file
   - Print them in a clean format

Add test block at bottom:
if __name__ == "__main__":
    import sys
    doc = load_dxf(sys.argv[1])
    print("Layers:", list_layers(doc))
    msp = get_modelspace(doc)
    count = sum(1 for _ in msp)
    print(f"Total entities: {count}")
```

#### Verification Checklist
```
☐  python src/parser.py input/S111_A.dxf  → runs without crash
☐  Layer names printed (e.g. WALL, BEAM, TEXT...)
☐  Entity count > 0
☐  Wrong path tested → clear error message, not Python traceback
☐  pytest tests/test_parser.py → all pass
```

---

### PHASE 2 — Entity Extractor
**Duration:** 1–2 days
**Goal:** Filter relevant entities and convert to Shapely geometry

#### Tasks

| # | Task | File | Done |
|---|---|---|---|
| 2.1 | Write `extract_entities(msp, layers)` | `src/extractor.py` | ☐ |
| 2.2 | Write `entity_to_segments(entity, arc_points=64)` | `src/extractor.py` | ☐ |
| 2.3 | Handle LINE → LineString | `src/extractor.py` | ☐ |
| 2.4 | Handle LWPOLYLINE → List[LineString] | `src/extractor.py` | ☐ |
| 2.5 | Handle ARC → 64-point LineString | `src/extractor.py` | ☐ |
| 2.6 | Skip unknown types with warning log | `src/extractor.py` | ☐ |
| 2.7 | Write `test_extractor.py` | `tests/` | ☐ |

#### Cursor Prompt for This Phase
```
Create src/extractor.py for a DXF processing project.

Functions needed:

1. extract_entities(msp, layers: List[str]) -> List
   - Iterate through modelspace
   - Keep only entities on specified layers
   - Keep only types: LINE, LWPOLYLINE, ARC
   - Skip everything else (TEXT, HATCH, INSERT, etc.)
   - Print count of each type found

2. entity_to_segments(entity, arc_points=64) -> List[LineString]
   - LINE: return [LineString([(x1,y1),(x2,y2)])]
   - LWPOLYLINE: return list of LineStrings between each vertex pair
     Use entity.get_points() to get vertices
   - ARC: approximate with arc_points equally spaced points
     Use start_angle, end_angle, center, radius from entity.dxf
   - Unknown: print warning and return []

3. extract_all_segments(entities, arc_points=64) -> List[LineString]
   - Call entity_to_segments on every entity
   - Flatten results into one list
   - Print total: "X segments extracted"

Use: from shapely.geometry import LineString, Point
```

#### Verification Checklist
```
☐  Segments extracted > 0 from sample DXF
☐  LINE entities correctly become single LineStrings
☐  LWPOLYLINE with 5 vertices becomes 4-5 LineStrings
☐  ARC entities become smooth curves (64 points)
☐  No crash on TEXT or HATCH entities
☐  pytest tests/test_extractor.py → all pass
```

---

### PHASE 3 — Geometry Builder
**Duration:** 1–2 days
**Goal:** Prepare segments for polygonization — snap and union

#### Tasks

| # | Task | File | Done |
|---|---|---|---|
| 3.1 | Write `snap_endpoints(segments, tolerance)` | `src/geometry.py` | ☐ |
| 3.2 | Write `build_multilinestring(segments)` | `src/geometry.py` | ☐ |
| 3.3 | Apply `unary_union` to node intersections | `src/geometry.py` | ☐ |
| 3.4 | Print segment count before and after merge | `src/geometry.py` | ☐ |
| 3.5 | Write `test_geometry.py` | `tests/` | ☐ |

#### Cursor Prompt for This Phase
```
Create src/geometry.py for a DXF processing project.

Functions needed:

1. snap_endpoints(segments: List[LineString], tolerance: float) -> List[LineString]
   - For each segment endpoint, if another endpoint is within tolerance:
     snap them to the same coordinate
   - Use shapely.ops.snap() for snapping
   - This removes tiny gaps caused by drafting imprecision

2. build_multilinestring(segments: List[LineString]) -> MultiLineString
   - Combine all segments into one MultiLineString
   - Apply shapely.ops.unary_union() to properly node intersections
   - Print: "MultiLineString built: X individual lines"
   - Return the unioned geometry

Use: from shapely.ops import unary_union, snap
Use: from shapely.geometry import MultiLineString
```

#### Verification Checklist
```
☐  MultiLineString created without error
☐  Segment count after snap ≤ before snap (some merged)
☐  unary_union runs in under 10 seconds on sample file
☐  No empty geometry returned
```

---

### PHASE 4 — Gap Handler ⚠️ Most Critical Phase
**Duration:** 3–5 days
**Goal:** Auto-close door/shutter gaps so polygonization works

#### Tasks

| # | Task | File | Done |
|---|---|---|---|
| 4.1 | Write `find_dangling_endpoints(geometry)` | `src/gap_handler.py` | ☐ |
| 4.2 | Cluster endpoints by distance | `src/gap_handler.py` | ☐ |
| 4.3 | Write `close_gaps(geometry, threshold)` | `src/gap_handler.py` | ☐ |
| 4.4 | Insert synthetic LineStrings for closed gaps | `src/gap_handler.py` | ☐ |
| 4.5 | Log every gap with coordinates and distance | `src/gap_handler.py` | ☐ |
| 4.6 | Flag unresolved gaps for human review | `src/gap_handler.py` | ☐ |
| 4.7 | Tune threshold on actual client DXF files | manual tuning | ☐ |
| 4.8 | Write `test_gap_handler.py` | `tests/` | ☐ |

#### Cursor Prompt for This Phase
```
Create src/gap_handler.py for a DXF processing project.

Context: DXF files have gaps at door and shutter locations.
These gaps break room boundaries and prevent polygon detection.
We need to automatically close gaps smaller than a threshold.

Functions needed:

1. find_dangling_endpoints(geometry: MultiLineString) -> List[Point]
   - Extract all line endpoints from the MultiLineString
   - Find endpoints that appear only ONCE (dangling = open end)
   - These are the gap endpoints
   - Return list of Point objects

2. close_gaps(geometry: MultiLineString, threshold: float) 
   -> Tuple[MultiLineString, List[dict]]
   - Call find_dangling_endpoints()
   - For each pair of dangling points within threshold distance:
     * Create new LineString connecting them
     * Record it as a "closed gap" with coordinates + distance
   - For pairs beyond threshold:
     * Record as "unresolved gap"
     * Print warning with coordinates
   - Return (updated_geometry, list_of_gap_reports)
   - gap_report dict: {id, start, end, distance, closed: bool}

3. print_gap_summary(gap_reports: List[dict]) -> None
   - Print table: Total gaps | Closed | Unresolved
   - Print each unresolved gap coordinate for manual fixing

Use: from shapely.geometry import LineString, Point
Use: from shapely.ops import unary_union
Use: scipy.spatial.distance.cdist for distance calculations
```

#### Gap Threshold Tuning Guide
```
Problem: gap_threshold affects everything.
Too low  → gaps not closed → 0 rooms detected
Too high → wrong gaps closed → false rooms detected

How to tune:
1. Start with threshold = 500 (drawing units)
2. Run: python main.py --input input/S111_A.dxf
3. Check: how many rooms detected vs expected?
4. If too few: increase threshold to 800, 1000, 1500
5. If false rooms: decrease threshold to 300, 200
6. Check gap log — are the right gaps being closed?

For warehouse drawings in mm:
  Typical door width = 900–1200 mm
  Typical shutter width = 3000–4500 mm
  Recommended: gap_threshold = 500 for doors only
               gap_threshold = 5000 to also close shutters
```

#### Verification Checklist
```
☐  Dangling endpoints found > 0 on real DXF
☐  At least some gaps closed (closed_gaps > 0)
☐  Unresolved gaps printed with coordinates
☐  After gap closing: more regions detected than before
☐  Gap log saved to logs/ folder
☐  pytest tests/test_gap_handler.py → all pass
```

---

### PHASE 5 — Region Detector
**Duration:** 2–3 days
**Goal:** Polygonize and get clean list of rooms

#### Tasks

| # | Task | File | Done |
|---|---|---|---|
| 5.1 | Write `detect_regions(geometry, min_area, scale)` | `src/detector.py` | ☐ |
| 5.2 | Apply `shapely.ops.polygonize()` | `src/detector.py` | ☐ |
| 5.3 | Apply min_area filter | `src/detector.py` | ☐ |
| 5.4 | Remove duplicate/overlapping polygons | `src/detector.py` | ☐ |
| 5.5 | Sort by area descending | `src/detector.py` | ☐ |
| 5.6 | Print room count and size range | `src/detector.py` | ☐ |
| 5.7 | Write `test_detector.py` | `tests/` | ☐ |

#### Cursor Prompt for This Phase
```
Create src/detector.py for a DXF processing project.

Functions needed:

1. detect_regions(geometry: MultiLineString, min_area_m2: float, 
                  scale_factor: float) -> List[Polygon]
   - Run shapely.ops.polygonize(geometry)
   - Convert each polygon area to m²: area_m2 = poly.area * scale_factor**2
   - Filter: keep only polygons where area_m2 >= min_area_m2
   - Remove duplicates: if two polygons overlap >90%, keep larger one
   - Sort by area descending (largest room = Room 1)
   - Print: "X regions detected (Y removed by area filter)"
   - Return list of Polygon objects

2. filter_by_area(polygons: List[Polygon], min_m2: float, 
                  scale: float) -> List[Polygon]
   - Keep only polygons with area >= min_m2 in m²

3. remove_overlapping(polygons: List[Polygon]) -> List[Polygon]
   - For each pair, compute intersection area / smaller area
   - If > 0.9: remove the smaller one

Use: from shapely.ops import polygonize
Use: from shapely.geometry import Polygon
```

#### Verification Checklist
```
☐  polygonize() returns > 0 polygons on real DXF with gaps closed
☐  All detected areas are > min_area (1 m²)
☐  No obvious duplicate rooms in output
☐  Largest room is listed first
☐  Areas look realistic for the building type
```

---

### PHASE 6 — Calculator + Labeler
**Duration:** 1–2 days
**Goal:** Compute all metrics and assign room labels

#### Tasks

| # | Task | File | Done |
|---|---|---|---|
| 6.1 | Write `compute_metrics(polygons, config)` | `src/calculator.py` | ☐ |
| 6.2 | Compute area_m2, perimeter_m, volume_m3 | `src/calculator.py` | ☐ |
| 6.3 | Compute centroid for each polygon | `src/calculator.py` | ☐ |
| 6.4 | Write `assign_labels(regions, prefix)` | `src/labeler.py` | ☐ |
| 6.5 | Handle concave rooms (centroid outside polygon) | `src/labeler.py` | ☐ |
| 6.6 | Write `test_calculator.py` | `tests/` | ☐ |

#### Cursor Prompt for This Phase
```
Create src/calculator.py and src/labeler.py.

calculator.py — compute_metrics(polygons, scale_factor, thickness, prefix) 
-> List[RegionData]
For each polygon:
  area_m2     = polygon.area * (scale_factor ** 2)
  perimeter_m = polygon.length * scale_factor
  volume_m3   = area_m2 * thickness
  centroid    = polygon.centroid  (Shapely Point)

Return list of RegionData objects (use Python dataclass).

labeler.py — assign_labels(regions, prefix="Room") -> List[RegionData]
For each region (already sorted by area desc):
  label = f"{prefix} {i+1}"   e.g. "Room 1"
  label_text = f"{label}\n{area_m2:.1f} m²\nVol: {volume_m3:.1f} m³"
  label_pos = centroid
  BUT: if centroid is not inside the polygon (concave rooms):
    use polygon.representative_point() instead

RegionData dataclass fields:
  region_id, label, polygon, centroid, area_m2, 
  perimeter_m, volume_m3, label_text, label_pos, source_file
```

#### Verification Checklist
```
☐  area_m2 values match AutoCAD within 0.05% on test polygons
☐  volume_m3 = area_m2 × 0.15 (verify with manual calc)
☐  Label "Room 1" assigned to largest polygon
☐  Labels placed inside room boundaries (even for L-shaped rooms)
☐  All RegionData fields populated (no None values)
```

**Area Accuracy Test:**
```python
# Known test: 10m × 12m rectangle in mm drawing
# In DXF: 10000 × 12000 units
# Expected area: 120.000 m²
# Your result must be between: 119.940 m² and 120.060 m²  (0.05% tolerance)
```

---

### PHASE 7 — Exporter
**Duration:** 2–3 days
**Goal:** Write annotated DXF and Excel report

#### Tasks

| # | Task | File | Done |
|---|---|---|---|
| 7.1 | Write `export_dxf(source, regions, config)` | `src/exporter.py` | ☐ |
| 7.2 | Add DETECTED_REGIONS layer with boundaries | `src/exporter.py` | ☐ |
| 7.3 | Add ROOM_LABELS layer with text entities | `src/exporter.py` | ☐ |
| 7.4 | Write `export_excel(regions, path)` | `src/exporter.py` | ☐ |
| 7.5 | Format Excel with headers, totals, colors | `src/exporter.py` | ☐ |
| 7.6 | Never overwrite source DXF | `src/exporter.py` | ☐ |
| 7.7 | Write `test_exporter.py` | `tests/` | ☐ |

#### Verification Checklist
```
☐  output/ folder has annotated .dxf file
☐  Open DXF in AutoCAD → DETECTED_REGIONS layer visible in red
☐  Room labels visible at correct positions in green
☐  Original DXF unchanged (compare timestamps)
☐  Excel has all 8 columns
☐  TOTALS row at bottom with correct sum
☐  No #DIV/0! or #REF! errors in Excel
```

---

### PHASE 8 — main.py + CLI
**Duration:** 1–2 days
**Goal:** Wire everything together into a single command

#### Tasks

| # | Task | File | Done |
|---|---|---|---|
| 8.1 | Wire full pipeline in `main.py` | `main.py` | ☐ |
| 8.2 | Add argparse CLI (--input, --thickness, --gap, --prefix, --batch) | `main.py` | ☐ |
| 8.3 | Add config loading + CLI override logic | `main.py` | ☐ |
| 8.4 | Add logging setup (file + console) | `main.py` | ☐ |
| 8.5 | Add startup banner and settings display | `main.py` | ☐ |
| 8.6 | Add final summary table | `main.py` | ☐ |
| 8.7 | Test end-to-end on all 3 sample DXF files | manual | ☐ |

#### Cursor Prompt for This Phase
```
Wire together the full pipeline in main.py.

Import and call in order:
  1. load config (config.yaml + argparse overrides)
  2. parser.load_dxf()
  3. parser.list_layers()
  4. extractor.extract_entities()
  5. extractor.extract_all_segments()
  6. geometry.snap_endpoints()
  7. geometry.build_multilinestring()
  8. gap_handler.close_gaps()
  9. detector.detect_regions()
  10. calculator.compute_metrics()
  11. labeler.assign_labels()
  12. exporter.export_dxf()
  13. exporter.export_excel()
  14. Print final summary table

CLI args using argparse:
  --input PATH         required
  --thickness FLOAT    optional, default from config
  --gap FLOAT          optional, default from config
  --prefix TEXT        optional, default "Room"
  --unit TEXT          optional, default "mm"
  --batch              flag for batch mode
  --preview            flag to show matplotlib preview

Print progress after each step with ✓ or ✗
Use try/except around each step — log error and continue if possible
```

---

### PHASE 9 — Error Handling + Polish
**Duration:** 2–3 days
**Goal:** Make it production-ready — no crashes, clear messages

#### Tasks

| # | Task | Done |
|---|---|---|
| 9.1 | Add try/except around every module call in main.py | ☐ |
| 9.2 | Test with corrupted DXF file → clean error message | ☐ |
| 9.3 | Test with wrong layer names → helpful suggestion | ☐ |
| 9.4 | Test with 0 gaps → correct behavior | ☐ |
| 9.5 | Test batch mode with 3 DXF files | ☐ |
| 9.6 | Create COMBINED_report.xlsx in batch mode | ☐ |
| 9.7 | Verify log file written after every run | ☐ |
| 9.8 | Add --preview matplotlib visualization | ☐ |
| 9.9 | Run pytest on all test files | ☐ |

---

### PHASE 10 — Accuracy Validation
**Duration:** 2–3 days
**Goal:** Prove ≤ 0.05% area deviation against AutoCAD

#### Tasks

| # | Task | Done |
|---|---|---|
| 10.1 | Pick 5–10 rooms from sample DXF | ☐ |
| 10.2 | Manually measure each in AutoCAD (AREA command) | ☐ |
| 10.3 | Run tool on same DXF | ☐ |
| 10.4 | Compare: `deviation = abs(tool - autocad) / autocad * 100` | ☐ |
| 10.5 | All deviations must be < 0.05% | ☐ |
| 10.6 | Document results in Accuracy_Test_Report.xlsx | ☐ |
| 10.7 | If deviation > 0.05%: increase arc_points to 128 and re-test | ☐ |

#### Accuracy Test Template

| Room | AutoCAD (m²) | Tool (m²) | Deviation % | Pass? |
|---|---|---|---|---|
| Room 1 | 120.000 | 119.998 | 0.002% | ✓ |
| Room 2 | 87.500 | 87.496 | 0.005% | ✓ |
| Room 3 | 580.000 | 579.710 | 0.050% | ✓ |

---

## 4. Full Timeline

```
Day 01-02  ████  Phase 1 — Parser
Day 02-04  ████  Phase 2 — Extractor
Day 04-06  ████  Phase 3 — Geometry Builder
Day 06-11  ██████████  Phase 4 — Gap Handler (most time here)
Day 11-14  ██████  Phase 5 — Detector
Day 14-16  ████  Phase 6 — Calculator + Labeler
Day 16-19  ██████  Phase 7 — Exporter
Day 19-21  ████  Phase 8 — main.py + CLI
Day 21-22  ████  Phase 9 — Error Handling
Day 22     ██  Phase 10 — Accuracy Validation
────────────────────────────────────────────
Total:    ~22 days
```

---

## 5. Testing Strategy Per Phase

| Phase | What to Test | Tool |
|---|---|---|
| 1 | File load, layer list, bad file | pytest |
| 2 | LINE/LWPOLYLINE/ARC conversion, segment count | pytest |
| 3 | Snap, union, segment count reduction | pytest |
| 4 | Gap finding, gap closing, unresolved gap logging | pytest + manual |
| 5 | Polygon count, area range, filter behavior | pytest |
| 6 | Area accuracy (0.05%), volume calc, label position | pytest + AutoCAD |
| 7 | DXF layers created, Excel columns correct, totals | pytest |
| 8 | End-to-end on all 3 DXF files | manual |
| 9 | Edge cases: corrupted file, 0 rooms, batch | manual |
| 10 | Area accuracy vs AutoCAD on 10 known rooms | manual + Excel |

---

## 6. Risk Register

| Risk | When | Mitigation |
|---|---|---|
| Gap threshold wrong for client files | Phase 4 | Tune on each DXF; add --gap flag for easy override |
| 0 rooms detected after gap handling | Phase 4-5 | Check layer names; increase threshold; check geometry in matplotlib |
| Area deviation > 0.05% | Phase 10 | Increase arc_points to 128; check scale_factor |
| Client DXF layers use different names | Phase 2 | Print all layer names at startup; user updates config.yaml |
| Large DXF files slow (>60 sec) | Phase 5 | Add Shapely STRtree spatial index in gap_handler |
| False rooms (tiny artifacts) | Phase 5 | Increase min_area from 1.0 to 5.0 m² |

---

## 7. Definition of Done

A phase is "done" when:
```
✓  All tasks in that phase are complete
✓  Verification checklist fully checked
✓  pytest tests pass (where applicable)
✓  No Python tracebacks in normal operation
✓  Progress logged clearly to console
✓  Next phase's input is available and correct
```

The full project is "done" when:
```
✓  All 10 phases complete
✓  python main.py input/S111_A.dxf  runs end-to-end without error
✓  Excel report has correct rooms, areas, volumes
✓  Annotated DXF shows room labels in AutoCAD
✓  Area deviation < 0.05% on 10 tested rooms
✓  Batch mode works on all 3 sample DXF files
✓  Log file created for every run
✓  All pytest tests passing
```

---

# Version 2.0 — Grid-Based Zone Detection Engine

> **NEW (v2.0):** Stage 1 (Phases 1–10 below) is **implemented and frozen** for geometric face detection. Stage 2 Zone Engine work is tracked in Phases P0–P6. Status reflects the repository as of June 2026.

---

## 8. Zone Engine — Status Overview (v2.0)

| Component | Phase | Status | Module / entry |
|-----------|-------|--------|----------------|
| Grid Frame Builder | P1 | **Done** | `src/zone_engine/grid_frame.py` |
| Axis Clustering | P1 | **Done** | `_cluster_lines_into_families`, `_cluster_positions` |
| Manifest-Aware Bay Generation | P1 | **Done** | `_resolve_target_axes`, manifest `zone_count_expected` |
| Slab Boundary Extraction | P2 | **Done** | `src/zone_engine/slab_outline.py` |
| Slab Boundary Clipping | P2 | **Done** | `src/zone_engine/bay_geometry.py` |
| INT Zone Mapping | P2 | **Done** | `src/zone_engine/int_labels.py` |
| Validation Reporting | P2 | **Done** | `geometry_validation.py`, `grid_frame_report.py` |
| Preview visualization | P2 | **Done** | `grid_frame_visualize.py`, `output/grid_frame_preview.svg` |
| Manifest transcription (T0) | P0 | **In progress** | `reference/j33a_zones_manifest.yaml` (template) |
| Face assigner + zone union (T3) | P3 | **Done** | `face_assigner.py`, `zone_aggregator.py` |
| Profile classifier (J33A vs J33B) | P3 | **Not started** | Roadmap |
| Joint frame builder | P4 | **Not started** | J33B / 17 zones |
| `main.py` integration | P4 | **Not started** | Single CLI for Stage 1+2 |
| INT schedule Excel/DXF export | P5 | **Not started** | Stage 3 |
| Manifest area acceptance (≤0.05%) | P6 | **Blocked on P0** | QA |

**Verified acceptance example (warehouse DWG):** `grid_frame_report.md` — 24 bays, `frame_mode: target_24`, bay count matches expected INT count.

---

## 9. Zone Engine Phase Plan (v2.0)

### PHASE P0 — Manifest ground truth (T0)

**Goal:** Transcribe QS PDF schedules into YAML for acceptance.

| # | Task | Artifact | Status |
|---|------|----------|--------|
| P0.1 | Transcribe J33A 24 rows (SQM, CUM) | `reference/j33a_zones_manifest.yaml` | ☐ template only |
| P0.2 | Transcribe J33B 17 rows | `reference/j33b_zones_manifest.yaml` | ☐ |
| P0.3 | Document transcription audit fields | `transcription:` block in manifest | ☐ |

**Gate:** All `area_sqm` / `volume_cum` non-null for acceptance runs.

---

### PHASE P1 — Grid Frame Builder + Axis Clustering + Manifest bays

**Goal:** Extract structural grid, cluster axes, emit N bay cells when manifest specifies N.

| # | Task | File | Status |
|---|------|------|--------|
| P1.1 | Extract grid lines from configured + candidate GRID layers | `grid_frame.py` | ☑ |
| P1.2 | Cluster by angle → two axis families | `grid_frame.py` | ☑ |
| P1.3 | Cluster positions along each family | `grid_frame.py` | ☑ |
| P1.4 | Subsample axes to match `zone_count_expected` | `grid_frame.py` | ☑ |
| P1.5 | Build rectangular `BayCell` grid | `grid_frame.py` | ☑ |
| P1.6 | CLI + unit tests | `scripts/run_grid_frame_builder.py`, `tests/test_grid_frame.py` | ☑ |

**Verification:**
```
python scripts/run_grid_frame_builder.py --dwg "input/6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg" --p1-only
# Expect: 24 bays, frame_mode target_24
```

---

### PHASE P2 — Slab clipping, INT mapping, validation reporting

**Goal:** Clip bays to slab outline; assign INT labels; emit validation report and preview.

| # | Task | File | Status |
|---|------|------|--------|
| P2.1 | Extract slab outline (`S-FNDN-1`) | `slab_outline.py` | ☑ |
| P2.2 | Clip each bay to slab; compute coverage % | `bay_geometry.py` | ☑ |
| P2.3 | Assign INT-1 … INT-N row-major | `int_labels.py` | ☑ |
| P2.4 | Validate geometry, overlaps, low coverage | `geometry_validation.py` | ☑ |
| P2.5 | Write `grid_frame_report.md` | `grid_frame_report.py` | ☑ |
| P2.6 | Render SVG/PNG preview | `grid_frame_visualize.py` | ☑ |
| P2.7 | `zone_engine` section in `config.yaml` | `config.yaml` | ☑ |

**Verification:**
```
python scripts/run_grid_frame_builder.py
# Expect: grid_frame_report.md, preview SVG, non-zero clipped area, validation table
pytest tests/test_grid_frame.py -q
```

---

### PHASE P3 — Face assigner + zone union (T3)

**Goal:** Map Stage 1 micro-polygons to INT zones; area = union of faces per zone.

| # | Task | File | Status |
|---|------|------|--------|
| P3.1 | Filter slivers (`sliver_max_m2`, default 1.0) | `face_assigner.py` | ☑ |
| P3.2 | Assign face → bay by max intersection or centroid-in-cell | `face_assigner.py` | ☑ |
| P3.3 | `unary_union` per INT zone → `IntZoneData` | `zone_aggregator.py` | ☑ |
| P3.4 | Orphan face reporting | `face_assigner.py`, `zone_coverage_report.py` | ☑ |
| P3.5 | Compare zone areas to manifest (when P0 complete) | `manifest_reconciliation.py` | ☑ (SKIP until P0 transcribed) |
| P3.6 | Production readiness gates | `production_readiness.py` | ☑ |
| P3.7 | Pipeline orchestration + CLI | `int_zone_pipeline.py`, `run_int_zone_pipeline.py` | ☑ |

**Gate:** Warehouse DWG: 618 faces → 24 zones; \|zones\| = manifest; total clipped area within project tolerance.

---

### PHASE P4 — Profiles, J33B joint frame, pipeline integration

| # | Task | Status |
|---|------|--------|
| P4.1 | Profile classifier (`GRID_WAREHOUSE` vs `JOINT_WAREHOUSE`) | ☑ | `profile_classifier.py` |
| P4.2 | Joint frame builder (major-joint layers only, ~17 zones) | ☐ | Bay trim interim for 17; full joint frame TBD |
| P4.3 | Wire zone engine after `detect_regions` in `main.py` | ☑ | `zone_mode.py`, `--zones` |
| P4.4 | `--zone-profile` / `--manifest` CLI flags on `main.py` | ☑ |

---

### PHASE P5 — INT schedule export (Stage 3)

| # | Task | Status |
|---|------|--------|
| P5.1 | Excel sheet: Pour No., SQM, CUM, grid_ref, face_count | ☑ | `int_schedule_export.py` |
| P5.2 | DXF layers `INT_ZONES` / `INT_LABELS` | ☑ |
| P5.3 | Dual export: debug faces + official INT schedule | ☑ | `*_results.xlsx` + `*_int_schedule.xlsx` |

---

### PHASE P6 — Acceptance & sign-off

| # | Task | Status |
|---|------|--------|
| P6.1 | INT zone count vs PDF (24 / 17) | ☑ count; ☐ area vs schedule |
| P6.2 | Per-INT area error ≤ 0.05% vs manifest SQM | ☐ blocked on P0 |
| P6.3 | Update `acceptance_readiness_report.md` INT section | ☐ |
| P6.4 | Seed-assisted recovery for missing INT cell (T5) | ☐ optional |

---

## 10. Zone Engine Timeline (v2.0)

```
Completed (Jun 2026):
  P1 ████████  Grid frame + axis clustering + manifest bays
  P2 ████████  Slab clip + INT labels + validation report

In progress:
  P0 ██░░░░░░  Manifest transcription

Remaining:
  P3 ████████  Face assigner + zone union (code complete; warehouse gate when DWG present)
  P4 ░░░░░░░░  Profiles + main.py integration + J33B
  P5 ░░░░░░░░  INT schedule export
  P6 ░░░░░░░░  Manifest acceptance gates
```

Stage 1 (v1.0 Phases 1–10): **complete** — maintain for geometric QA only.

---

## 11. Testing Strategy — Zone Engine (v2.0)

| Phase | What to test | Tool |
|-------|----------------|------|
| P1 | Axis count, bay count = manifest N, orthogonal grid | `pytest tests/test_grid_frame.py` |
| P2 | Clip coverage, INT label stability, validation flags | pytest + `grid_frame_report.md` |
| P3 | Face assignment coverage, union area vs sum of faces | pytest + manifest |
| P4 | J33B 17 zones, profile selection | manual + pytest |
| P5 | Excel/DXF columns | manual AutoCAD open |
| P6 | Manifest deviation ≤ 0.05% | `area_benchmark` + manifest |

---

## 12. Risk Register — Zone Engine (v2.0)

| Risk | Mitigation |
|------|------------|
| Bay grid 1:1 ≠ QS pour grouping on some projects | Manifest grouping in YAML; hybrid merge (design only) |
| Slab outline concave hull over/under-shoots | Prefer polygonize when large region exists; tune `slab_min_polygon_area_m2` |
| INT label order ≠ PDF pour sequence | Manifest override labels; do not use area-sort for INT |
| Clipped bay area ≠ union of micro-faces | Ship P3 assigner; until then report both metrics |
| J33B irregular layout | P4 joint frame; do not force 24-cell grid |
| Stage 1 unchanged but confuses acceptance | Document dual metrics in readiness report (faces vs INT) |

---

## 13. Definition of Done — Zone Engine (v2.0)

**P1+P2 done (current):**
```
✓  build_grid_frame returns N bays when manifest specifies N
✓  INT labels stable row-major
✓  grid_frame_report.md generated with validation section
✓  pytest tests/test_grid_frame.py passing
```

**Full Zone Engine done (target):**
```
✓  P0 manifest transcribed for J33A and J33B
✓  P3 face assigner: micro-faces roll up to INT zones
✓  main.py runs Stage 1 + 2 in one command
✓  INT schedule Excel matches QS column layout
✓  Per-INT area within 0.05% of manifest SQM
✓  Stage 1 face export still available for debug
```

---

*END OF IMPLEMENTATION PLAN*
*v1.0 historical: DXF CAD Room Detection | May 2026*
*v2.0 current: Grid-Based Zone Detection Engine | June 2026*
