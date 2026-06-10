# Technical Requirements Document
## DXF CAD Room Detection & Area Calculation System

**Version:** 1.0
**Status:** Draft
**Date:** May 31, 2026
**Related Document:** PRD v1.0 – DXF CAD Room Detection & Area Calculation System

---

## 1. Document Information

| Field | Details |
|---|---|
| Document Title | DXF CAD Room Detection & Area Calculation System – TRD |
| Version | 1.0 |
| Status | Draft |
| Date | May 31, 2026 |
| Language | Python 3.10+ |
| Primary Libraries | ezdxf 1.x, Shapely 2.x, pandas, matplotlib, openpyxl |
| OS Support | Windows 10+, macOS 12+, Ubuntu 20.04+ |
| Related Doc | PRD v1.0 – DXF CAD Room Detection & Area Calculation System |

---

## 2. System Overview

The system is a Python-based desktop/CLI application that ingests DXF (Drawing Exchange Format) files, processes the geometric entities contained within them, and produces:

- **(a)** An annotated output DXF with detected regions labelled
- **(b)** A structured Excel/CSV report with area and volume data

### 2.1 High-Level Data Flow

```
INPUT (DXF File)
    ↓
[1] DXF Parser           ← ezdxf reads file, lists entities & layers
    ↓
[2] Entity Extractor     ← Filters LINE, LWPOLYLINE, ARC from config layers
    ↓
[3] Geometry Builder     ← Converts to Shapely LineStrings, snaps endpoints
    ↓
[4] Gap Handler          ← Detects & closes door/shutter gaps
    ↓
[5] Polygonizer          ← shapely.ops.polygonize → closed regions
    ↓
[6] Area & Volume Calc   ← area × scale², volume = area × thickness
    ↓
[7] Label Assigner       ← Room 1, Room 2... + centroid positions
    ↓
[8] Exporter             ← Annotated DXF + Excel/CSV
    ↓
OUTPUT (Annotated DXF + Excel Report)
```

---

## 3. Technology Stack

| Library / Tool | Version | Purpose | Installation |
|---|---|---|---|
| Python | 3.10+ | Core runtime language | python.org |
| ezdxf | 1.1+ | Read and write DXF files; access all CAD entities | `pip install ezdxf` |
| Shapely | 2.0+ | Geometry: polygon building, area, centroid, buffers | `pip install shapely` |
| pandas | 2.0+ | Tabular data manipulation and CSV/Excel export | `pip install pandas` |
| openpyxl | 3.1+ | Excel (.xlsx) file creation | `pip install openpyxl` |
| matplotlib | 3.7+ | Optional visual preview of detected regions | `pip install matplotlib` |
| PyYAML | 6.0+ | Read YAML configuration files | `pip install pyyaml` |
| pytest | 7.0+ | Unit and integration testing | `pip install pytest` |

---

## 4. Project Structure

```
cad-area-detector/
├── main.py                   ← CLI entry point
├── config.yaml               ← User configuration file
├── requirements.txt          ← Python dependencies
├── input/                    ← Drop DXF files here
├── output/                   ← Annotated DXF + Excel results
├── logs/                     ← Run logs
├── tests/
│   ├── test_parser.py
│   ├── test_detector.py
│   └── test_exporter.py
└── src/
    ├── __init__.py
    ├── parser.py             ← Module 1: DXF Parser
    ├── extractor.py          ← Module 2: Entity Extractor
    ├── geometry.py           ← Module 3: Geometry Builder
    ├── gap_handler.py        ← Module 4: Gap Handler
    ├── detector.py           ← Module 5: Region Detector / Polygonizer
    ├── calculator.py         ← Module 6: Area & Volume Calculator
    ├── labeler.py            ← Module 7: Label Assigner
    └── exporter.py           ← Module 8: Output Exporter
```

---

## 5. Module Specifications

### 5.1 Module 1 – DXF Parser (`parser.py`)

**Responsibility:** Load a DXF file from disk using ezdxf and return the document object and modelspace.

#### Key Functions

| Function | Input | Output | Description |
|---|---|---|---|
| `load_dxf(filepath)` | `str: file path` | `ezdxf.Document` | Opens DXF file; raises FileNotFoundError or DXFStructureError on failure |
| `get_modelspace(doc)` | `ezdxf.Document` | `ezdxf.layouts.Modelspace` | Returns model space layout for entity iteration |
| `list_layers(doc)` | `ezdxf.Document` | `List[str]` | Returns all layer names present in the DXF file |

#### Error Handling

- Invalid file path → `FileNotFoundError` with descriptive message
- Corrupted DXF structure → `ezdxf.DXFStructureError` caught and logged
- Unsupported DXF version → logged as warning; processing continues

---

### 5.2 Module 2 – Entity Extractor (`extractor.py`)

**Responsibility:** Filter and extract geometric entities from the modelspace based on configured layer names. Supported types: `LINE`, `LWPOLYLINE`, `ARC`.

#### Key Functions

| Function | Input | Output | Description |
|---|---|---|---|
| `extract_entities(msp, layers)` | `msp, List[str] layers` | `List[DXFEntity]` | Returns all LINE/LWPOLYLINE/ARC entities on specified layers |
| `entity_to_segments(entity)` | `DXFEntity` | `List[LineString]` | Converts a single entity to a list of Shapely LineString segments |
| `extract_all_segments(entities)` | `List[DXFEntity]` | `List[LineString]` | Converts all entities to Shapely segments; skips unsupported types |

#### Entity Conversion Rules

- `LINE` → single LineString from `(x1,y1)` to `(x2,y2)`
- `LWPOLYLINE` → sequence of LineString segments between consecutive vertices
- `ARC` → approximated as a LineString with N=`accuracy.arc_segments` interpolated points (default 64)
- `POLYLINE` → same segment rules as LWPOLYLINE (legacy 2D/3D polylines)
- `CIRCLE` → converted to closed polygon (may represent columns; filtered by `min_area`)

---

### 5.3 Module 3 – Geometry Builder (`geometry.py`)

**Responsibility:** Take raw LineString segments and prepare them for polygonization. This includes snapping nearby endpoints, merging collinear segments, and building a unified geometry collection.

#### Key Functions

| Function | Input | Output | Description |
|---|---|---|---|
| `snap_endpoints(segments, tol)` | `List[LineString], float` | `List[LineString]` | Snaps endpoints within tolerance to remove micro-gaps |
| `merge_collinear(segments)` | `List[LineString]` | `List[LineString]` | Merges collinear adjacent segments into single LineStrings |
| `build_geometry(segments)` | `List[LineString]` | `MultiLineString` | Assembles all segments into a Shapely MultiLineString for polygonization |
| `node_geometry(multi_line)` | `MultiLineString` | `MultiLineString` | Applies Shapely `unary_union` to properly node the geometry |

---

### 5.4 Module 4 – Gap Handler (`gap_handler.py`)

**Responsibility:** This is the most critical and complex module. It identifies gaps in boundary lines (caused by doors, shutters, or incomplete drafting) and closes them using configurable strategies.

#### Gap Detection Strategy

1. Find all free endpoints in the segment network (endpoints that connect to fewer than 2 segments)
2. Cluster free endpoints by proximity (within `gap_threshold` distance)
3. If a gap is smaller than `gap_threshold`, insert a synthetic LineString to close it
4. If a gap is larger than `gap_threshold`, log it as an unresolved gap and skip

#### Configuration Parameters

| Parameter | Default | Description |
|---|---|---|
| `gap_threshold` | 200 units | Maximum distance between two endpoints to be auto-closed (drawing units) |
| `snap_tolerance` | 1 unit | Distance within which endpoints are snapped together (micro-gap fix) |
| `max_gap_angle` | 30° | Maximum angular deviation allowed when bridging two endpoints |

> **Important Design Note:** The `gap_threshold` must be calibrated per project. Door openings in warehouse drawings are typically 900–3000 mm. The default threshold should be set based on the drawing scale used in the DXF file. All auto-closed gaps must be logged with their coordinates for audit.

---

### 5.5 Module 5 – Region Detector (`detector.py`)

**Responsibility:** Perform polygonization on the prepared geometry to extract all enclosed regions as Shapely Polygon objects.

#### Key Functions

| Function | Input | Output | Description |
|---|---|---|---|
| `polygonize(geometry)` | `MultiLineString` | `List[Polygon]` | Runs `shapely.ops.polygonize`; returns all fully enclosed polygons |
| `filter_polygons(polys, min_a)` | `List[Polygon], float` | `List[Polygon]` | Removes polygons smaller than `min_area` (e.g. < 1 m²) |
| `remove_duplicates(polys)` | `List[Polygon]` | `List[Polygon]` | Removes overlapping or near-identical polygons using IoU check |
| `sort_polygons(polys)` | `List[Polygon]` | `List[Polygon]` | Sorts detected polygons by area descending for consistent labelling |

#### Algorithm: Polygonization

1. Collect all line segments (after gap-fixing) into a `MultiLineString`
2. Apply `shapely.ops.unary_union` to properly node all intersections
3. Apply `shapely.ops.polygonize` to extract all enclosed faces
4. Filter by minimum area threshold
5. Return sorted list of valid `Polygon` objects

---

### 5.6 Module 6 – Calculator (`calculator.py`)

**Responsibility:** Compute area, perimeter, centroid, and volume for each detected polygon.

#### Key Functions

| Function | Input | Output | Description |
|---|---|---|---|
| `compute_area(polygon, scale)` | `Polygon, float` | `float` | Returns `polygon.area × scale_factor²` in m² |
| `compute_perimeter(polygon, scale)` | `Polygon, float` | `float` | Returns `polygon.length × scale_factor` in m |
| `compute_centroid(polygon)` | `Polygon` | `Point` | Returns `polygon.centroid` as Shapely Point |
| `compute_volume(area, thickness)` | `float, float` | `float` | Returns `area × thickness` in m³ |
| `compute_all(polygons, config)` | `List, Config` | `List[RegionData]` | Computes all metrics for all polygons; returns list of RegionData objects |

#### Scale Factor

> **Critical — DXF Drawing Units:** DXF files do not inherently define units. A "1 unit" in DXF could mean 1 mm, 1 cm, or 1 m. The user must specify the drawing unit in `config.yaml` (default: `mm`). The scale factor converts drawing units to metres.
>
> Example: if drawing is in `mm`, then `scale_factor = 0.001`
> Area in m² = `polygon.area × scale_factor²`

---

### 5.7 Module 7 – Label Assigner (`labeler.py`)

**Responsibility:** Assign human-readable labels to detected regions and determine text placement coordinates.

#### Key Functions

| Function | Input | Output | Description |
|---|---|---|---|
| `assign_labels(regions, prefix)` | `List[RegionData], str` | `List[RegionData]` | Assigns labels like "Room 1", "Slab 1" etc. (prefix from config) |
| `compute_label_position(polygon)` | `Polygon` | `Point` | Returns centroid if inside polygon, else uses polylabel algorithm |
| `format_label_text(region)` | `RegionData` | `str` | Formats label: `"Room 1\nArea: 120.5 m²\nVol: 18.1 m³"` |

---

### 5.8 Module 8 – Exporter (`exporter.py`)

**Responsibility:** Write results to output DXF and Excel/CSV files.

#### DXF Export

- Open the original DXF file using ezdxf
- Create a new layer called `DETECTED_REGIONS` with a distinct color
- Draw each detected polygon boundary as `LWPOLYLINE` on this layer
- Add `TEXT` entities at label positions on layer `REGION_LABELS`
- Save as a new file — **never overwrite the original**

#### Excel Export

- Create a pandas DataFrame with: Region ID, Label, Area (m²), Perimeter (m), Volume (m³), Centroid X, Centroid Y
- Add a summary row at the bottom with totals for Area and Volume
- Export using openpyxl with formatted headers

---

## 6. Configuration File Specification

All user-configurable parameters are stored in `config.yaml` in the project root.

```yaml
# DXF CAD Area Detector Configuration

input:
  input_dir: ./input          # Folder to scan for DXF files
  file_pattern: "*.dxf"       # File pattern to match

layers:
  wall_layers:                # Layers containing wall/boundary lines
    - WALL
    - S-WALL
    - BEAM
  ignore_layers:              # Layers to skip entirely
    - DIMENSIONS
    - TEXT
    - HATCH

geometry:
  drawing_unit: mm            # mm, cm, or m
  slab_thickness: 0.15        # metres (default 150mm)
  gap_threshold: 500          # drawing units — max gap to auto-close
  snap_tolerance: 1           # drawing units — micro-gap snap distance
  min_area: 1.0               # m² — ignore regions smaller than this (standard mode)

accuracy:
  area_tolerance_percent: 0.05   # PRD: max deviation vs AutoCAD AREA
  area_decimals: 4
  arc_segments: 64
  detection_mode: exhaustive       # exhaustive | standard
  exhaustive_min_area_m2: 0.01
  dedupe_iou_threshold: 0.98

output:
  output_dir: ./output
  export_dxf: true
  export_excel: true
  export_csv: false
  label_prefix: "Room"        # "Room", "Slab", "Region" etc.
  dxf_region_layer: DETECTED_REGIONS
  dxf_label_layer: REGION_LABELS

logging:
  log_dir: ./logs
  log_level: INFO             # DEBUG, INFO, WARNING, ERROR
```

---

## 7. Data Model

### 7.1 RegionData Dataclass

```python
@dataclass
class RegionData:
    region_id:   int       # Auto-incremented integer ID
    label:       str       # e.g. "Room 1"
    polygon:     Polygon   # Shapely Polygon object
    area_m2:     float     # Area in square metres
    perimeter_m: float     # Perimeter in metres
    volume_m3:   float     # Volume in cubic metres
    centroid:    Point     # Shapely Point (label position)
    label_text:  str       # Formatted multi-line label string
    source_file: str       # Path to source DXF file
```

### 7.2 Excel Output Schema

| Column | Type | Example | Notes |
|---|---|---|---|
| Region ID | Integer | 1 | Auto-incremented, starts at 1 |
| Label | String | Room 1 | Prefix + Region ID |
| Area (m²) | Float | 120.45 | 2 decimal places |
| Perimeter (m) | Float | 44.20 | 2 decimal places |
| Volume (m³) | Float | 18.07 | 2 decimal places |
| Centroid X | Float | 5.22 | In metres from drawing origin |
| Centroid Y | Float | 6.10 | In metres from drawing origin |
| Source File | String | S111_A.dxf | Name of input DXF file |

---

## 8. Error Handling Strategy

| Error Type | Handling | User Action Required |
|---|---|---|
| File not found | Log ERROR + skip file; continue batch | Check file path in config |
| Corrupted DXF | Log ERROR + skip file; continue batch | Validate DXF with AutoCAD |
| No entities on config layers | Log WARNING + skip file | Review layer names in `config.yaml` |
| Zero polygons detected | Log WARNING; export empty report | Check drawing for open boundaries |
| Gap too large to auto-close | Log WARNING with gap coordinates | Manually close gap in AutoCAD |
| Division by zero (scale=0) | Raise `ValueError` with clear message | Set valid `drawing_unit` in config |
| Output folder not writable | Log ERROR + abort | Check folder permissions |

---

## 9. Performance Requirements

| Scenario | Entity Count | Target Time | Optimization Strategy |
|---|---|---|---|
| Small drawing | < 1,000 | < 3 sec | No special optimization needed |
| Medium drawing | 1,000–5,000 | < 15 sec | Spatial indexing with STRtree for gap detection |
| Large drawing | 5,000–15,000 | < 60 sec | Layer-based filtering before processing; lazy loading |
| Batch (10 files) | Varies | < 10 min | Process files sequentially; log progress per file |

---

## 10. Testing Strategy

### 10.1 Unit Tests

- `test_parser.py`: Test `load_dxf` with valid file, missing file, corrupted file
- `test_extractor.py`: Test `entity_to_segments` with LINE, LWPOLYLINE, ARC, unknown type
- `test_gap_handler.py`: Test with gap within threshold, gap exceeding threshold, no gaps
- `test_calculator.py`: Test area/volume with known polygon; validate against manual calculation
- `test_exporter.py`: Test DXF output layer creation; test Excel column names and data types

### 10.2 Integration Tests

- End-to-end test with provided `S111_J.dxf`: verify N detected regions, compare areas with AutoCAD
- End-to-end test with provided `S111_A.dxf`: same verification
- Batch test: process both DXF files together; verify combined Excel output

### 10.3 Acceptance Criteria

| Test ID | Description | Pass Condition |
|---|---|---|
| T-01 | Load `S111_J.dxf` without errors | No exception raised; entities list non-empty |
| T-02 | Detect at least 1 closed region in `S111_J.dxf` | `polygons` list length >= 1 |
| T-03 | Area accuracy on known rectangular polygon | Computed area within **0.05%** of known value |
| T-08 | Detection recall on sample DWGs | Region count ≥ 90% of AutoCAD manual count (100% long-term) |
| T-04 | Auto-close a 500-unit door gap | Region detected correctly after gap closure |
| T-05 | Excel file produced with correct columns | All 8 columns present; no NaN in Area/Volume |
| T-06 | Output DXF contains `DETECTED_REGIONS` layer | Layer present; at least 1 LWPOLYLINE entity |
| T-07 | Batch: process 2 files; combined report produced | Excel has entries from both source files |

---

## 11. Full Dependency List (`requirements.txt`)

```
ezdxf>=1.1.0
shapely>=2.0.0
pandas>=2.0.0
openpyxl>=3.1.0
matplotlib>=3.7.0
PyYAML>=6.0
pytest>=7.0.0
pytest-cov>=4.0.0
```

---

## 12. CLI Reference

```bash
# Basic usage
python main.py --input input/S111_A.dxf

# With custom settings
python main.py --input input/S111_A.dxf --thickness 0.15 --gap 500 --prefix Room

# Batch mode
python main.py --input input/ --batch

# Show help
python main.py --help
```

### Expected Console Output (Success)

```
✓ Loaded: S111_A.dxf (2,847 entities)
✓ Gaps closed: 23
✓ Regions detected: 47
✓ Exported: output/results.xlsx
✓ Exported: output/annotated.dxf

SUMMARY
─────────────────────────────
Total Regions :  47
Total Area    :  4,821.3 m²
Total Volume  :    723.2 m³
─────────────────────────────
Log saved to  :  logs/run_20260531_143022.log
```

---

*END OF TECHNICAL REQUIREMENTS DOCUMENT*
*DXF CAD Room Detection System | TRD v1.0 | May 2026*