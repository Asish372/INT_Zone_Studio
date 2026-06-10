# Software Flow Document
## DXF CAD Room Detection & Grid-Based Zone Detection Engine

| Document section | Version | Scope |
|------------------|---------|--------|
| §1–§7 below | **1.0** (historical) | Generic DXF room detection — polygonize pipeline |
| §8–§14 below | **2.0** (current) | Grid-Based Zone Detection Engine — INT zones |

**Version:** 2.0 | **Date:** June 2026

---

## 1. Top-Level System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│          (Engineer runs CLI or opens GUI)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    Provides DXF file
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: INPUT LAYER                           │
│                                                                  │
│   ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│   │  DXF File   │    │ config.yaml  │    │  CLI Arguments   │  │
│   │ (S111_A.dxf)│    │(gap, layers, │    │(--thickness 0.15)│  │
│   └──────┬──────┘    │  thickness)  │    └────────┬─────────┘  │
│          │           └──────┬───────┘             │            │
│          └──────────────────┴─────────────────────┘            │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────── ┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 2: PROCESSING PIPELINE                   │
│                                                                  │
│   [Parser] → [Extractor] → [Geometry Builder] → [Gap Handler]   │
│                                    ↓                            │
│                            [Polygonizer]                        │
│                                    ↓                            │
│                    [Calculator] → [Labeler]                     │
│                                                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 3: OUTPUT LAYER                          │
│                                                                  │
│   ┌─────────────────┐    ┌─────────────────┐    ┌───────────┐  │
│   │  Annotated DXF  │    │  Excel Report   │    │  Run Log  │  │
│   │(room boundaries │    │(Room ID, Area,  │    │(.log file)│  │
│   │  + labels)      │    │  Volume, etc.)  │    │           │  │
│   └─────────────────┘    └─────────────────┘    └───────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Processing Pipeline

### Stage 1 — DXF Parser

```
DXF File on Disk
        │
        ▼
ezdxf.readfile(path)
        │
        ├── SUCCESS ──► doc object + modelspace ready
        │                        │
        │               list_layers(doc)
        │               prints all layer names
        │
        └── FAILURE ──► Log ERROR
                         Skip file
                         Continue batch (if batch mode)
```

### Stage 2 — Entity Extractor

```
modelspace (all entities)
        │
        ▼
Filter by config layers
(e.g. WALL, S-WALL, BEAM)
        │
        ├── LINE entities ──────────────► LineString(x1,y1 → x2,y2)
        │
        ├── LWPOLYLINE entities ────────► [LineString, LineString, ...]
        │                                  (one per segment pair)
        │
        ├── ARC entities ──────────────► LineString(64 interpolated points)
        │
        └── OTHER (TEXT, HATCH, etc.) ─► SKIP + log "skipped N entities"
                │
                ▼
        List[LineString]   ← all usable segments
```

### Stage 3 — Geometry Builder

```
List[LineString]  (raw segments, may have micro-gaps)
        │
        ▼
snap_endpoints(tolerance=1 unit)
  → Endpoints within 1 unit snapped together
  → Eliminates micro-gaps from drafting imprecision
        │
        ▼
merge_collinear()
  → Adjacent segments on same line merged
  → Reduces segment count, speeds up polygonization
        │
        ▼
unary_union()
  → All segments merged into single MultiLineString
  → Intersections properly "noded"
        │
        ▼
MultiLineString  ← ready for gap detection
```

### Stage 4 — Gap Handler (Most Critical)

```
MultiLineString
        │
        ▼
Find all "dangling endpoints"
(endpoints connected to only 1 segment)
        │
        ▼
For each pair of dangling endpoints:
        │
        ├── Distance ≤ gap_threshold (500 units)?
        │          │
        │          ▼
        │   Insert synthetic LineString
        │   connecting the two endpoints
        │   Log: "Gap closed at (x1,y1)→(x2,y2) dist=450"
        │
        └── Distance > gap_threshold?
                   │
                   ▼
           Log: "Unresolved gap at (x1,y1)→(x2,y2) dist=1200"
           Flag for human review
           Continue processing (room may still partially detect)
        │
        ▼
Updated MultiLineString
(original segments + synthetic gap-closers)
```

### Stage 5 — Polygonizer

```
Updated MultiLineString
        │
        ▼
shapely.ops.polygonize()
        │
        ├── Returns: List[Polygon]  (all detected closed regions)
        │
        ▼
filter_polygons(min_area = 1.0 m²)
  → Removes tiny artifacts (column cross-sections, text boxes, etc.)
        │
        ▼
remove_duplicates()
  → Removes overlapping polygons (IoU check)
        │
        ▼
sort_polygons()
  → Sorted by area (largest first)
        │
        ▼
List[Polygon]  ← clean set of detected rooms/regions
```

### Stage 6 — Calculator

```
For each Polygon in List[Polygon]:
        │
        ├── area_m2     = polygon.area × (scale_factor²)
        │                 scale_factor = 0.001 if drawing_unit = mm
        │
        ├── perimeter_m = polygon.length × scale_factor
        │
        ├── centroid    = polygon.centroid  (Shapely Point)
        │
        └── volume_m3   = area_m2 × slab_thickness (e.g. 0.15m)
        │
        ▼
List[RegionData]
```

### Stage 7 — Labeler

```
List[RegionData]  (no labels yet)
        │
        ▼
For each region (sorted by area desc):
        │
        ├── label = f"{prefix} {id}"   e.g. "Room 1", "Room 2"
        │
        ├── label_position = centroid
        │      └── if centroid is OUTSIDE polygon (concave rooms):
        │              use polylabel() for visual center
        │
        └── label_text = "Room 1\n120.5 m²\nVol: 18.1 m³"
        │
        ▼
List[RegionData]  ← with labels and positions
```

### Stage 8 — Exporter

```
List[RegionData]
        │
        ├─────────────────────────────────────────────────────┐
        ▼                                                     ▼
DXF Export                                             Excel Export
        │                                                     │
Open original DXF                               Create pandas DataFrame
        │                                                     │
Create layer "DETECTED_REGIONS"                 Columns: ID, Label,
Create layer "ROOM_LABELS"                       Area, Perimeter,
        │                                        Volume, X, Y, File
For each region:                                              │
  Draw LWPOLYLINE boundary               Add TOTALS row at bottom
  Add TEXT at label_position                                  │
        │                               Format headers (bold, blue)
Save as new file                                              │
(never overwrite original)              Save as .xlsx
        │                                                     │
        ▼                                                     ▼
output/annotated.dxf               output/results.xlsx
```

---

## 3. Complete Data Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌─────────────┐
│  DXF     │────►│  Parser  │────►│  Extractor   │────►│  Geometry   │
│  File    │     │          │     │              │     │  Builder    │
└──────────┘     └──────────┘     └──────────────┘     └──────┬──────┘
                                                              │
                                                    List[LineString]
                                                              │
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────▼──────┐
│  Excel   │◄────│  Labeler │◄────│  Calculator  │◄────│  Gap        │
│  + DXF   │     │          │     │              │     │  Handler    │
│  Output  │     └──────────┘     └──────────────┘     └──────┬──────┘
└──────────┘                                                   │
                                                     MultiLineString
                                                     (gaps closed)
                                                               │
                                                    ┌──────────▼──────┐
                                                    │  Polygonizer    │
                                                    │                 │
                                                    └─────────────────┘
```

---

## 4. Error Flow

```
Any module encounters error
           │
           ▼
    Is it FATAL?
    (file not found, write permission denied)
           │
    YES ───┴─── NO
     │                │
     ▼                ▼
  Log ERROR      Log WARNING
  Print message  Continue processing
  Exit code 1    Skip problematic entity
                 Flag for human review
                        │
                        ▼
                 End of run:
                 Summary shows:
                 "X warnings — review log"
```

---

## 5. Batch Processing Flow

```
input/ folder
     │
     ▼
Scan for *.dxf files
     │
     ├── file_1.dxf ──► [Pipeline] ──► output/file_1_result.xlsx
     │                                 output/file_1_annotated.dxf
     │
     ├── file_2.dxf ──► [Pipeline] ──► output/file_2_result.xlsx
     │                                 output/file_2_annotated.dxf
     │
     └── file_3.dxf ──► [Pipeline] ──► output/file_3_result.xlsx
                                        output/file_3_annotated.dxf
                                                │
                                                ▼
                                  output/COMBINED_report.xlsx
                                  (all rooms from all files merged)
```

---

## 6. Human Review / Assist Flow

```
After auto-processing:
          │
          ▼
Unresolved gaps flagged?
          │
    YES ──┴── NO
     │              │
     ▼              ▼
Print list of    Done ✓
unresolved gaps
(coordinates + distance)
     │
     ▼
Engineer manually fixes
gap in AutoCAD
     │
     ▼
Re-run tool on fixed DXF
     │
     ▼
100% rooms detected ✓
```

---

## 7. Module Dependency Map

```
main.py
  ├── config_loader.py    (loads config.yaml)
  ├── parser.py
  │     └── ezdxf
  ├── extractor.py
  │     ├── parser.py
  │     └── shapely.geometry
  ├── geometry.py
  │     └── shapely.ops
  ├── gap_handler.py
  │     └── shapely.geometry, scipy.spatial
  ├── detector.py
  │     └── shapely.ops.polygonize
  ├── calculator.py
  │     └── shapely.geometry
  ├── labeler.py
  │     └── shapely (centroid, polylabel)
  └── exporter.py
        ├── ezdxf
        ├── pandas
        └── openpyxl
```

---

# Version 2.0 — Grid-Based Zone Detection Engine

> **NEW (v2.0):** The product has evolved from “detect every closed room polygon” to a **two-stage** system: Stage 1 geometric faces (unchanged baseline) plus Stage 2 **INT zone partition** for QS deliverables (`INT-1` … `INT-n`). Implementation lives under `src/zone_engine/`. Related design: `int_zone_engine_design.md`, `zone_detection_design.md`.

---

## 8. Top-Level System Flow (v2.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│   Stage 1: python main.py --input drawing.dxf                   │
│   Stage 2: python scripts/run_grid_frame_builder.py --dwg …     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              DXF/DWG + config.yaml + optional manifest YAML
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────────────┐
│ STAGE 1 (frozen)    │           │ STAGE 2 — Zone Engine       │
│ Geometric faces     │           │ (grid-based INT partition)  │
│ Parser → … → Export │           │                             │
└──────────┬──────────┘           └──────────────┬──────────────┘
           │                                     │
           │  List[Polygon] faces F              │  List[BayCell] / IntZone
           │  (618 / 331 / 397 on samples)       │  (24 / 17 target)
           └─────────────────┬───────────────────┘
                             ▼
                   ┌─────────────────────┐
                   │ STAGE 3 (roadmap)   │
                   │ INT schedule export │
                   │ area = union(zone)  │
                   └─────────────────────┘
```

**Outputs today:**

| Stage | CLI entry | Primary outputs |
|-------|-----------|-----------------|
| 1 | `main.py` | Annotated DXF, Excel (`Room N`), gap logs |
| 2 | `scripts/run_grid_frame_builder.py` | `grid_frame_report.md`, `output/grid_frame_preview.svg` |
| 3 | *planned* | INT-labelled Excel/DXF, manifest comparison |

---

## 9. Zone Engine Pipeline (v2.0)

### 9.1 Orchestration — `build_grid_frame_geometry`

```
Modelspace (DXF)
        │
        ▼
┌───────────────────┐
│ Grid Frame Builder│  P1 — grid_frame.build_grid_frame
│ + Axis Clustering │
└─────────┬─────────┘
          │  GridFrameResult (bays, axes, frame_mode)
          ▼
┌───────────────────┐
│ Slab Boundary     │  slab_outline.extract_slab_outline
│ Extraction        │  (S-FNDN-1 polygonize → concave hull fallback)
└─────────┬─────────┘
          │  SlabOutlineResult.polygon
          ▼
┌───────────────────┐
│ Slab Boundary     │  bay_geometry.clip_bays_to_slab
│ Clipping          │  raw bay ∩ slab → clipped_polygon, coverage_pct
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ INT Zone Mapping  │  int_labels.assign_int_labels
│ (row-major)       │  INT-1 … INT-N deterministic by (row, col)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Validation        │  geometry_validation.validate_bay_geometries
│ Reporting         │  + grid_frame_report.write_grid_frame_report
└─────────┬─────────┘
          │
          ▼
   GridFrameGeometryResult
   (frame, slab, bays, validation, warnings)
```

### 9.2 Grid Frame Builder + Axis Clustering

```
Configured grid_layers (S-GRID-1, S-GRID-IDEN)
        + discover_candidate_grid_layers (names containing GRID)
        │
        ▼
extract_grid_lines (orthogonal LINE/LWPOLYLINE/ARC, min length)
        │
        ▼
_cluster_lines_into_families (angle tolerance, default 2°)
        │
        ▼
_family_to_axis → _cluster_positions (position_cluster_mm, default 500)
        │
        ├── axis_a: merged positions along family 1
        └── axis_b: merged positions along family 2
        │
        ▼
Manifest-aware frame (if expected_int_count from manifest)
        │
        ├── _factor_bay_count(N) → (cells_a, cells_b)
        ├── _select_axis_positions → subsample axes to N+1 lines per axis
        └── _resolve_target_axes → frame_mode e.g. target_24
        │
        ▼
_assign_xy_axes → sorted frame_xs_mm, frame_ys_mm
        │
        ▼
_build_bay_polygons → List[BayCell] (raw rectangles between adjacent axes)
```

**Manifest input:** `reference/j33a_zones_manifest.yaml` → `zone_count_expected: 24` passed as `expected_int_count` by `run_grid_frame_builder.py`.

### 9.3 Slab Boundary Clipping

```
BayCell.polygon (full grid rectangle)
        │
        ▼
intersection(bay, slab_outline.polygon)
        │
        ├── Polygon → clipped_polygon, clipped_area_m2
        ├── MultiPolygon → largest part kept
        └── empty → coverage_pct = 0, flag in validation
        │
        ▼
coverage_pct = clipped_area_m2 / raw_area_m2 × 100
```

Slab outline methods: `polygonize` on `S-FNDN-1` when a region ≥ `slab_min_polygon_area_m2`; else `concave_hull` of layer vertices.

### 9.4 INT Zone Mapping

```
List[BayCell] (after clip)
        │
        ▼
sort by (row, col, bay_id) ascending
        │
        ▼
for i, bay in enumerate(ordered, 1):
    bay.int_label = f"INT-{i}"
```

Same geometry → same labels across runs (audit requirement for QS).

### 9.5 Validation Reporting

```
Per bay: validity, low_coverage (< low_coverage_pct), empty_clip
Pairwise: overlap_area_m2 between clipped bays
Aggregate: totals, mean coverage, warning strings
        │
        ▼
grid_frame_report.md + optional SVG/PNG preview
```

---

## 10. Stage 1 ↔ Stage 2 Relationship (v2.0)

```
Stage 1 faces (detector.py)          Stage 2 bays (zone_engine)
────────────────────────────         ────────────────────────────
618 micro-polygons (warehouse)   →   24 INT-labelled bay cells (grid)
331 (S111_J)                     →   17 INT (joint profile — roadmap)
Purpose: geometric recall QA       Purpose: QS pour partition
Labels: Room 1 … Room N            Labels: INT-1 … INT-n
```

**Roadmap bridge (not yet in `main.py`):** Face assigner maps each Stage 1 polygon to a bay by max intersection or centroid-in-cell, then `unary_union` per INT zone for schedule area (design §6.1 in `int_zone_engine_design.md`).

---

## 11. Complete Data Flow Diagram (v2.0)

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│  DXF     │────►│ Grid Frame   │────►│ Axis clustering │
│  + GRID  │     │ Builder      │     │ + manifest N    │
└──────────┘     └──────┬───────┘     └────────┬────────┘
                          │                      │
                          │    ┌─────────────────┘
                          ▼    ▼
                   ┌──────────────┐     ┌─────────────┐
                   │ Bay cells    │────►│ Slab clip   │
                   │ (raw rects)  │     │ S-FNDN-1    │
                   └──────┬───────┘     └──────┬──────┘
                          │                    │
                          ▼                    ▼
                   ┌──────────────┐     ┌─────────────┐
                   │ INT labels   │────►│ Validation  │
                   │ INT-1…INT-n  │     │ + report    │
                   └──────────────┘     └─────────────┘

Parallel path (Stage 1, unchanged):
DXF → Parser → Extractor → Geometry → Gap → Polygonize → Calculator → Export
```

---

## 12. Error Flow (Zone Engine, v2.0)

```
Zone engine step fails or degrades
           │
           ▼
    Recoverable? (empty grid, slab hull fallback, bay count mismatch)
           │
    YES ───┴─── NO (no DXF, no grid layers at all)
     │                │
     ▼                ▼
  Log WARNING      Log ERROR
  Append to        Exit code 1
  result.warnings  (run_grid_frame_builder)
  Continue with
  partial result
           │
           ▼
  grid_frame_report.md lists warnings + validation FAIL/PASS
```

---

## 13. Batch / Manifest Flow (v2.0)

```
reference/j33a_zones_manifest.yaml  (zone_count_expected: 24)
reference/j33b_zones_manifest.yaml  (zone_count_expected: 17, roadmap)
        │
        ▼
run_grid_frame_builder.py --dwg <path> --manifest <yaml>
        │
        ▼
grid_frame_report.md  (per-drawing diagnostics)
output/grid_frame_preview.svg
```

---

## 14. Module Dependency Map (v2.0)

```
scripts/run_grid_frame_builder.py
  ├── src/parser.py, src/converter.py, src/units.py
  └── src/zone_engine/
        ├── grid_frame.py          ← P1 Grid Frame Builder, Axis Clustering,
        │                            Manifest-aware bay generation
        ├── slab_outline.py        ← Slab boundary extraction
        ├── bay_geometry.py        ← Slab clipping orchestration
        ├── int_labels.py          ← INT zone mapping
        ├── geometry_validation.py ← Validation rules
        ├── grid_frame_report.py   ← Validation reporting (Markdown)
        └── grid_frame_visualize.py← Preview SVG/PNG

main.py (Stage 1 — not yet calling zone_engine)
  ├── detector.py, calculator.py, exporter.py, …
  └── (roadmap) zone assigner after detect_regions
```

---

*END OF SOFTWARE FLOW DOCUMENT*
*v1.0 historical: DXF CAD Room Detection | May 2026*
*v2.0 current: Grid-Based Zone Detection Engine | June 2026*
