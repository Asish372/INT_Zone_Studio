# Backend Schema
## DXF CAD Room Detection & Grid-Based Zone Detection Engine

| Document section | Version | Scope |
|------------------|---------|--------|
| §1–§6 below | **1.0** (historical) | Stage 1 room detection models and contracts |
| §7–§12 below | **2.0** (current) | Zone Engine models, config, outputs |

**Version:** 2.0 | **Date:** June 2026

---

## 1. Overview

This system has **no database**. All data lives in:
- Config files (YAML)
- In-memory Python objects during processing
- Output files (DXF, Excel, CSV, log)

The schema document defines:
- All Python data models (dataclasses)
- Module input/output contracts
- Config file schema
- Output file schemas
- Internal API between modules

---

## 2. Core Data Models

### 2.1 AppConfig

Loaded from `config.yaml` at startup. Passed to every module.

```python
@dataclass
class AppConfig:
    # Input
    input_path:      str          # path to DXF file or folder
    file_pattern:    str = "*.dxf"

    # Layer settings
    wall_layers:     List[str]    # e.g. ["WALL", "S-WALL", "BEAM"]
    ignore_layers:   List[str]    # e.g. ["TEXT", "HATCH", "DIM"]

    # Geometry settings
    drawing_unit:    str   = "mm"    # "mm" | "cm" | "m"
    slab_thickness:  float = 0.15    # in metres
    gap_threshold:   float = 500.0   # in drawing units
    snap_tolerance:  float = 1.0     # in drawing units
    min_area_m2:     float = 1.0     # minimum area to keep (m²)
    arc_points:      int   = 64      # arc interpolation resolution

    # Output settings
    output_dir:      str   = "./output"
    export_dxf:      bool  = True
    export_excel:    bool  = True
    export_csv:      bool  = False
    label_prefix:    str   = "Room"
    dxf_region_layer:str  = "DETECTED_REGIONS"
    dxf_label_layer: str  = "ROOM_LABELS"

    # Logging
    log_dir:         str   = "./logs"
    log_level:       str   = "INFO"    # DEBUG | INFO | WARNING | ERROR

    # Derived (computed at load time, not in yaml)
    scale_factor:    float = 0.001     # auto-set from drawing_unit
    batch_mode:      bool  = False     # True if input_path is a folder
```

**Scale factor computation:**
```python
SCALE_MAP = {"mm": 0.001, "cm": 0.01, "m": 1.0}
config.scale_factor = SCALE_MAP[config.drawing_unit]
```

---

### 2.2 RawEntity

Output of the extractor. Intermediate model before Shapely conversion.

```python
@dataclass
class RawEntity:
    entity_type:  str           # "LINE" | "LWPOLYLINE" | "ARC"
    layer:        str           # e.g. "WALL"
    coordinates:  List[tuple]   # list of (x, y) points
    is_closed:    bool = False  # True if LWPOLYLINE is closed
    source_file:  str  = ""
```

---

### 2.3 Segment

A single Shapely LineString with metadata.

```python
@dataclass
class Segment:
    geometry:     LineString    # Shapely LineString
    source_type:  str           # "original" | "synthetic_gap_closer"
    layer:        str           # source layer name
    gap_distance: float = 0.0  # 0 unless synthetic
```

---

### 2.4 GapReport

Produced by the Gap Handler for every gap found.

```python
@dataclass
class GapReport:
    gap_id:         int
    start_point:    tuple         # (x, y) in drawing units
    end_point:      tuple         # (x, y) in drawing units
    distance:       float         # in drawing units
    was_closed:     bool          # True = auto-closed, False = too large
    closure_method: str           # "synthetic_line" | "unresolved"
    note:           str           # Human-readable message for log
```

---

### 2.5 RegionData ← Main Output Object

The central model. One instance per detected room/region.
Passed between Calculator → Labeler → Exporter.

```python
@dataclass
class RegionData:
    # Identity
    region_id:    int           # Auto-incremented, starts at 1
    label:        str           # e.g. "Room 1"
    source_file:  str           # e.g. "S111_A.dxf"

    # Geometry
    polygon:      Polygon       # Shapely Polygon object
    centroid:     Point         # Shapely Point (label placement position)

    # Calculated metrics (all in SI units)
    area_m2:      float         # Area in square metres (≤0.05% accuracy)
    perimeter_m:  float         # Perimeter in metres
    volume_m3:    float         # area_m2 × slab_thickness

    # Label
    label_text:   str           # "Room 1\n120.5 m²\nVol: 18.1 m³"
    label_pos:    Point         # visual center for DXF text placement

    # Quality flags
    has_arc:      bool = False  # True if boundary contains ARC entities
    gap_closed:   int  = 0      # number of gaps closed to form this region
```

---

### 2.6 RunSummary

Produced at the end of every run. Printed to console + written to log.

```python
@dataclass
class RunSummary:
    # Input
    source_files:      List[str]
    total_entities:    int
    entities_used:     int
    entities_skipped:  int

    # Gap handling
    gaps_found:        int
    gaps_closed:       int
    gaps_unresolved:   int

    # Detection results
    regions_detected:  int
    regions_filtered:  int      # removed by min_area filter

    # Metrics
    total_area_m2:     float
    total_volume_m3:   float
    largest_region:    str      # "Room 1 — 580.2 m²"
    smallest_region:   str      # "Room 47 — 12.3 m²"

    # Output
    output_files:      List[str]
    log_file:          str
    duration_seconds:  float
    warnings:          List[str]
    errors:            List[str]
```

---

## 3. Module Input/Output Contracts

Each module has a clear contract — what it takes in and what it returns.

### 3.1 parser.py

```python
def load_dxf(filepath: str) -> ezdxf.document.Drawing:
    """
    IN:  filepath — absolute or relative path to .dxf file
    OUT: ezdxf Drawing object
    ERR: FileNotFoundError, ezdxf.DXFStructureError
    """

def get_modelspace(doc: Drawing) -> Modelspace:
    """
    IN:  ezdxf Drawing object
    OUT: Modelspace layout object
    ERR: AttributeError if doc is invalid
    """

def list_layers(doc: Drawing) -> List[str]:
    """
    IN:  ezdxf Drawing object
    OUT: List of all layer names (strings)
    ERR: None — returns empty list on failure
    """
```

---

### 3.2 extractor.py

```python
def extract_entities(
    msp: Modelspace,
    layers: List[str]
) -> List[RawEntity]:
    """
    IN:  msp — modelspace from parser
         layers — list of layer names to include
    OUT: List[RawEntity] — filtered entities only
    ERR: None — unsupported types skipped silently
    """

def entities_to_segments(
    entities: List[RawEntity],
    arc_points: int = 64
) -> List[Segment]:
    """
    IN:  entities — list of RawEntity
         arc_points — interpolation resolution for ARC
    OUT: List[Segment] — Shapely LineString objects
    ERR: None — bad entities skipped and logged
    """
```

---

### 3.3 geometry.py

```python
def snap_endpoints(
    segments: List[Segment],
    tolerance: float
) -> List[Segment]:
    """
    IN:  segments — raw segments from extractor
         tolerance — snap distance in drawing units
    OUT: List[Segment] — snapped segments
    """

def build_multilinestring(
    segments: List[Segment]
) -> MultiLineString:
    """
    IN:  segments — all usable segments
    OUT: Single Shapely MultiLineString (noded)
    """
```

---

### 3.4 gap_handler.py

```python
def find_dangling_endpoints(
    geometry: MultiLineString
) -> List[Point]:
    """
    IN:  noded MultiLineString
    OUT: List of Points where lines are open (dangling ends)
    """

def close_gaps(
    geometry: MultiLineString,
    threshold: float
) -> Tuple[MultiLineString, List[GapReport]]:
    """
    IN:  geometry — noded MultiLineString
         threshold — max gap size to auto-close (drawing units)
    OUT: (updated_geometry, list_of_gap_reports)
         updated_geometry has synthetic lines inserted for closed gaps
    """
```

---

### 3.5 detector.py

```python
def detect_regions(
    geometry: MultiLineString,
    min_area_m2: float,
    scale_factor: float
) -> List[Polygon]:
    """
    IN:  geometry — gap-handled MultiLineString
         min_area_m2 — minimum area in m² to keep
         scale_factor — drawing unit to metre conversion
    OUT: List[Polygon] — sorted by area descending
    """
```

---

### 3.6 calculator.py

```python
def compute_metrics(
    polygons: List[Polygon],
    config: AppConfig
) -> List[RegionData]:
    """
    IN:  polygons — list of detected Polygon objects
         config — AppConfig (for scale_factor, thickness, prefix)
    OUT: List[RegionData] — with area, perimeter, volume computed
         Labels NOT yet assigned (done by labeler.py)
    """
```

---

### 3.7 labeler.py

```python
def assign_labels(
    regions: List[RegionData],
    prefix: str = "Room"
) -> List[RegionData]:
    """
    IN:  regions — from calculator (no labels yet)
         prefix — "Room" | "Slab" | "Region"
    OUT: List[RegionData] — with label, label_text, label_pos set
    """
```

---

### 3.8 exporter.py

```python
def export_dxf(
    source_dxf_path: str,
    regions: List[RegionData],
    config: AppConfig
) -> str:
    """
    IN:  source_dxf_path — original DXF (read-only)
         regions — labelled RegionData list
         config — for layer names and output path
    OUT: str — path of output DXF file written
    ERR: PermissionError if output not writable
    """

def export_excel(
    regions: List[RegionData],
    output_path: str
) -> str:
    """
    IN:  regions — labelled RegionData list
         output_path — where to write .xlsx
    OUT: str — path of output Excel file written
    """

def export_summary(
    summary: RunSummary,
    log_path: str
) -> None:
    """
    IN:  summary — RunSummary object
         log_path — path to write/append log file
    OUT: None (side effect: file written + console printed)
    """
```

---

## 4. Config File Schema (config.yaml)

Full schema with types, defaults, and validation rules:

```yaml
# ─── INPUT ───────────────────────────────────────────────────
input:
  input_dir:    string    # required | path to DXF file or folder
  file_pattern: string    # optional | default: "*.dxf"

# ─── LAYERS ──────────────────────────────────────────────────
layers:
  wall_layers:            # required | min 1 item
    - string
  ignore_layers:          # optional | default: []
    - string

# ─── GEOMETRY ────────────────────────────────────────────────
geometry:
  drawing_unit:           string  # required | enum: ["mm","cm","m"]
  slab_thickness:         float   # required | min: 0.001, max: 2.0
  gap_threshold:          float   # optional | default: 500.0, min: 0
  snap_tolerance:         float   # optional | default: 1.0, min: 0
  min_area:               float   # optional | default: 1.0, min: 0
  arc_interpolation_points: int   # optional | default: 64, min: 32

# ─── OUTPUT ──────────────────────────────────────────────────
output:
  output_dir:             string  # optional | default: "./output"
  export_dxf:             bool    # optional | default: true
  export_excel:           bool    # optional | default: true
  export_csv:             bool    # optional | default: false
  label_prefix:           string  # optional | default: "Room"
  dxf_region_layer:       string  # optional | default: "DETECTED_REGIONS"
  dxf_label_layer:        string  # optional | default: "ROOM_LABELS"

# ─── LOGGING ─────────────────────────────────────────────────
logging:
  log_dir:    string    # optional | default: "./logs"
  log_level:  string    # optional | enum: ["DEBUG","INFO","WARNING","ERROR"]
```

**Validation rules:**
- `slab_thickness` must be > 0
- `drawing_unit` must be one of `mm`, `cm`, `m`
- `wall_layers` must have at least 1 item
- `arc_interpolation_points` must be ≥ 32 (below 32 breaks 0.05% accuracy)
- `gap_threshold` must be ≥ 0 (set to 0 to disable gap closing)

---

## 5. Output File Schemas

### 5.1 Excel File (.xlsx)

**Sheet: "Rooms"**

| Column | Python Type | Excel Format | Notes |
|---|---|---|---|
| Region ID | int | Number, 0 decimal | Auto-increment from 1 |
| Label | str | Text | e.g. "Room 1" |
| Area (m²) | float | Number, 2 decimal | Computed from polygon |
| Perimeter (m) | float | Number, 2 decimal | Polygon boundary length |
| Volume (m³) | float | Number, 2 decimal | area × thickness |
| Centroid X | float | Number, 3 decimal | Drawing coord in metres |
| Centroid Y | float | Number, 3 decimal | Drawing coord in metres |
| Source File | str | Text | e.g. "S111_A.dxf" |

**Sheet: "Summary"**

| Field | Value |
|---|---|
| Run Date | 2026-05-31 14:30:22 |
| Source Files | S111_A.dxf |
| Settings | mm, 0.15m, gap=500 |
| Total Rooms | 47 |
| Total Area (m²) | 4,821.30 |
| Total Volume (m³) | 723.20 |
| Warnings | 2 |

---

### 5.2 Log File (.log)

```
[2026-05-31 14:30:01] INFO     Run started — S111_A.dxf
[2026-05-31 14:30:01] INFO     Config loaded — unit=mm, thickness=0.15, gap=500
[2026-05-31 14:30:02] INFO     File loaded — 2,847 entities found
[2026-05-31 14:30:02] INFO     Layers found: WALL, S-WALL, BEAM, SLAB (14 total)
[2026-05-31 14:30:02] INFO     Entities extracted — LINE:1203 POLYLINE:412 ARC:38
[2026-05-31 14:30:03] INFO     Geometry built — 1,653 segments
[2026-05-31 14:30:03] INFO     Gap closed — id=1  (4520,3100)→(4980,3100)  dist=460
[2026-05-31 14:30:03] INFO     Gap closed — id=2  (7200,1800)→(7650,1800)  dist=450
[2026-05-31 14:30:03] WARNING  Gap unresolved — id=23 (9100,2200)→(9100,3800) dist=1600
[2026-05-31 14:30:03] WARNING  Gap unresolved — id=24 (2300,4500)→(4100,4500) dist=1800
[2026-05-31 14:30:04] INFO     Regions detected — 47 polygons
[2026-05-31 14:30:04] INFO     Regions after filter — 47 (0 removed by min_area)
[2026-05-31 14:30:04] INFO     Exported — output/S111_A_annotated.dxf
[2026-05-31 14:30:04] INFO     Exported — output/S111_A_results.xlsx
[2026-05-31 14:30:05] INFO     Run complete — 47 rooms | 4,821.3 m² | 4.2 sec
```

---

### 5.3 Annotated DXF Structure

```
Original DXF
├── [All original layers — UNCHANGED]
│
├── DETECTED_REGIONS  (new layer)
│   ├── LWPOLYLINE — Room 1 boundary
│   ├── LWPOLYLINE — Room 2 boundary
│   └── ... (one per room)
│
└── ROOM_LABELS  (new layer)
    ├── TEXT — "Room 1\n120.5 m²\nVol: 18.1 m³"  at (5.22, 6.10)
    ├── TEXT — "Room 2\n87.3 m²\nVol: 13.1 m³"   at (12.40, 6.10)
    └── ... (one per room)
```

---

## 6. Internal State — Processing Run

The full pipeline passes one shared state object:

```python
@dataclass
class ProcessingState:
    config:          AppConfig
    source_file:     str
    doc:             Drawing          = None   # after parser
    raw_entities:    List[RawEntity]  = None   # after extractor
    segments:        List[Segment]    = None   # after geometry builder
    geometry:        MultiLineString  = None   # after unary_union
    gap_reports:     List[GapReport]  = None   # after gap_handler
    polygons:        List[Polygon]    = None   # after detector
    regions:         List[RegionData] = None   # after calculator + labeler
    summary:         RunSummary       = None   # after export
    errors:          List[str]        = field(default_factory=list)
    warnings:        List[str]        = field(default_factory=list)
```

---

# Version 2.0 — Grid-Based Zone Detection Engine

> **NEW (v2.0):** Stage 2 data models live in `src/zone_engine/`. Stage 1 `RegionData` remains for micro-face debug export; INT zones use `BayCell` and related types until `IntZoneData` is introduced with face assignment (roadmap).

---

## 7. Zone Engine Data Models (v2.0)

### 7.1 GridLine

One extracted grid axis segment (post-extractor, pre-clustering).

```python
@dataclass(frozen=True)
class GridLine:
    layer: str
    angle_deg: float
    length_mm: float
    position_mm: float          # scalar along axis normal (for clustering)
    midpoint: tuple[float, float]
    segment: LineString
```

---

### 7.2 AxisFamily

Parallel grid lines merged into sorted axis positions.

```python
@dataclass
class AxisFamily:
    name: str                     # e.g. axis_1, axis_2
    angle_deg: float
    positions_mm: list[float]     # clustered axis positions
    line_count: int
    source_layers: list[str]
```

---

### 7.3 BayCell

Rectangle between adjacent axes on two families; carries raw and clipped geometry.

```python
@dataclass
class BayCell:
    bay_id: int
    row: int
    col: int
    polygon: Polygon              # raw bay rectangle
    area_m2: float
    centroid: tuple[float, float]
    bounds: tuple[float, float, float, float]
    axis_x_min_mm: float
    axis_x_max_mm: float
    axis_y_min_mm: float
    axis_y_max_mm: float
    int_label: str = ""           # INT-1 … INT-N (after mapping)
    raw_area_m2: float = 0.0
    clipped_polygon: Polygon | None = None
    clipped_area_m2: float = 0.0
    coverage_pct: float = 0.0     # clipped / raw × 100
```

**INT zone mapping:** `int_label` assigned in stable row-major order `(row, col)`.

---

### 7.4 GridFrameResult

Output of P1 Grid Frame Builder (includes manifest-aware bay generation).

```python
@dataclass
class GridFrameResult:
    source_file: str
    grid_layers_used: list[str]
    candidate_grid_layers: list[str]
    raw_line_count: int
    grid_lines: list[GridLine]
    axis_families: list[AxisFamily]
    axis_a: AxisFamily | None
    axis_b: AxisFamily | None
    raw_bay_count: int            # all adjacent-axis cells before subsampling
    bay_count: int                # frame used (target N when manifest set)
    bays: list[BayCell]
    expected_int_count: int | None
    expected_bay_count: int | None
    frame_mode: str               # raw | target_24 | empty | raw_unmatched_target
    frame_xs_mm: list[float]
    frame_ys_mm: list[float]
    warnings: list[str]
```

---

### 7.5 SlabOutlineResult

Authoritative slab boundary from `S-FNDN-1` (or configured layer).

```python
@dataclass
class SlabOutlineResult:
    layer: str
    method: str                   # polygonize | concave_hull
    polygon: Polygon
    area_m2: float
    segment_count: int
    polygonize_count: int
    warnings: list[str]
```

---

### 7.6 GridFrameGeometryResult

P2 aggregate: frame + slab clip + labels + validation.

```python
@dataclass
class GridFrameGeometryResult:
    frame: GridFrameResult
    slab: SlabOutlineResult
    bays: list[BayCell]
    validation: GeometryValidationSummary
    bay_count_before_clip: int
    bay_count_after_clip: int
    warnings: list[str]
```

---

### 7.7 GeometryValidationSummary / BayValidation / OverlapRecord

```python
@dataclass
class BayValidation:
    bay_id: int
    int_label: str
    raw_area_m2: float
    clipped_area_m2: float
    coverage_pct: float
    is_valid: bool
    validity_reason: str
    low_coverage: bool
    empty_clip: bool
    flags: list[str]

@dataclass
class OverlapRecord:
    int_label_a: str
    int_label_b: str
    overlap_area_m2: float

@dataclass
class GeometryValidationSummary:
    bay_validations: list[BayValidation]
    overlaps: list[OverlapRecord]
    invalid_bay_count: int
    low_coverage_count: int
    empty_clip_count: int
    overlap_pair_count: int
    total_raw_area_m2: float
    total_clipped_area_m2: float
    mean_coverage_pct: float
    warnings: list[str]
```

---

### 7.8 IntZoneData (roadmap — face assignment)

Planned when Stage 1 faces are merged into zones (not yet in `models.py`):

```python
@dataclass
class IntZoneData:
    zone_id: int
    label: str                    # INT-1
    polygon: Polygon              # unary_union of assigned micro-faces
    area_m2: float
    volume_m3: float
    face_ids: list[int]
    profile: str                  # GRID_WAREHOUSE | JOINT_WAREHOUSE | …
    detection_tier: str           # T0b, T3, …
    grid_ref: str | None
    source_file: str
```

---

### 7.9 ZonesManifest (reference YAML)

```yaml
schema_version: int
project: str
profile: str                     # GRID_WAREHOUSE | JOINT_WAREHOUSE
zone_count_expected: int         # drives manifest-aware bay generation
source_pdf: str
dwg_counterpart: str
zones:
  - label: str                   # INT-1
    area_sqm: float | null       # T0 acceptance ground truth
    volume_cum: float | null
    grid_ref: str | null
    notes: str | null
```

Files: `reference/j33a_zones_manifest.yaml`, `reference/j33b_zones_manifest.yaml`.

---

## 8. Zone Engine Module Contracts (v2.0)

### 8.1 `grid_frame.py`

```python
def build_grid_frame(
    msp: Modelspace,
    *,
    source_file: str = "",
    grid_layers: list[str] | None = None,
    include_candidate_layers: bool = True,
    angle_tolerance_deg: float = 2.0,
    position_cluster_mm: float = 500.0,
    min_line_length_mm: float = 1000.0,
    expected_bay_count: int | None = None,
    expected_int_count: int | None = None,
    unit_scale_m: float = 0.001,
) -> GridFrameResult:
    """P1: extract grid lines, cluster axes, build bays; subsample axes when expected_int_count set."""

def discover_candidate_grid_layers(msp, *, configured_layers, min_line_entities=1) -> list[str]:
    """Auto-discover layers whose name contains GRID."""
```

---

### 8.2 `slab_outline.py`

```python
def extract_slab_outline(
    msp: Modelspace,
    config: dict,
    *,
    slab_layer: str = "S-FNDN-1",
    unit_scale_m: float = 0.001,
    min_polygon_area_m2: float = 100.0,
    concave_hull_ratio: float = 0.2,
) -> SlabOutlineResult:
```

---

### 8.3 `bay_geometry.py`

```python
def build_grid_frame_geometry(
    msp: Modelspace,
    config: dict,
    *,
    source_file: str = "",
    unit_scale_m: float = 0.001,
    expected_int_count: int | None = None,
    zone_cfg: dict | None = None,
) -> GridFrameGeometryResult:
    """Orchestrates P1 + slab clip + INT labels + validation."""

def clip_bays_to_slab(bays, slab, *, unit_scale_m=0.001) -> int:
    """Returns count of non-empty clipped bays."""
```

---

### 8.4 `int_labels.py`

```python
def assign_int_labels(bays: list[BayCell]) -> list[BayCell]:
    """Row-major INT-1 … INT-N."""

def sort_bays_for_display(bays: list[BayCell]) -> list[BayCell]:
```

---

### 8.5 `geometry_validation.py`

```python
def validate_bay_geometries(
    bays: list[BayCell],
    *,
    unit_scale_m: float = 0.001,
    low_coverage_pct: float = 25.0,
    overlap_area_m2: float = 0.5,
) -> GeometryValidationSummary:
```

---

### 8.6 `grid_frame_report.py` / `grid_frame_visualize.py`

```python
def write_grid_frame_report(result: GridFrameResult | GridFrameGeometryResult, path: Path) -> None

def render_grid_frame_preview(geometry: GridFrameGeometryResult, stem: Path) -> list[Path]:
    """Writes .svg and optionally .png preview."""
```

---

## 9. Config Schema Extension — `zone_engine` (v2.0)

Appended to `config.yaml` (Stage 1 keys unchanged):

```yaml
zone_engine:
  grid_layers:
    - S-GRID-1
    - S-GRID-IDEN
  include_candidate_layers: true    # optional; default true in code
  grid_angle_tolerance_deg: 2.0
  position_cluster_mm: 500.0
  min_grid_line_length_mm: 1000.0
  slab_outline_layer: S-FNDN-1
  slab_min_polygon_area_m2: 100.0
  slab_concave_hull_ratio: 0.2
  low_coverage_pct: 25.0
  overlap_area_m2: 0.5
  # roadmap:
  # profile: GRID_WAREHOUSE
  # manifest_path: reference/j33a_zones_manifest.yaml
  # barrier_layers: [S-FNDN-HDLN, S-FNDN-HDLN-1]
  # sliver_max_m2: 1.0
```

---

## 10. Output File Schemas (v2.0)

### 10.1 `grid_frame_report.md`

Generated by `write_grid_frame_report`. Sections:

| Section | Content |
|---------|---------|
| Summary | Layers, axis counts, raw vs frame bay count, expected INT, slab method |
| Slab clipping statistics | Raw vs clipped totals, mean coverage |
| Geometry validation summary | Invalid, low coverage, empty, overlap pairs |
| INT labels | Row-major assignment note |
| Bay diagnostics table | INT, row, col, raw m², clipped m², coverage %, flags |

### 10.2 Preview artifacts

| File | Description |
|------|-------------|
| `output/grid_frame_preview.svg` | Bays + slab outline + axes |
| `output/grid_frame_preview.png` | Optional raster preview |

### 10.3 Roadmap — INT schedule Excel (Stage 3)

| Column | Type | Notes |
|--------|------|-------|
| Pour No. | str | INT-1 |
| Concrete Area (SQM) | float | From clipped or union polygon |
| Concrete Volume (CUM) | float | area × thickness |
| Grid ref | str | Optional from manifest |
| Face count | int | Micro-faces assigned (QA) |
| Manifest area (SQM) | float | T0 comparison |
| Deviation % | float | vs manifest when transcribed |

---

## 11. Internal State — Zone Engine Run (v2.0)

```python
@dataclass
class ZoneEngineState:
    config: dict
    manifest: dict | None
    source_file: str
    msp: Modelspace | None = None
    frame: GridFrameResult | None = None
    slab: SlabOutlineResult | None = None
    geometry: GridFrameGeometryResult | None = None
    stage1_faces: list[Polygon] | None = None   # roadmap: link to detector
    warnings: list[str] = field(default_factory=list)
```

---

## 12. Stage 1 vs Stage 2 Object Binding (v2.0)

| Concern | Stage 1 object | Stage 2 object | Notes |
|---------|----------------|----------------|-------|
| Micro geometry | `RegionData` / `Polygon` | — | 300–600+ faces |
| QS partition | — | `BayCell` + `int_label` | 17–24 INT zones |
| Area for billing | `RegionData.area_m2` | `BayCell.clipped_area_m2` (today); `IntZoneData` (union, roadmap) | Clipped bay ≠ full face union until assigner ships |
| Export label | `Room N` | `INT-N` | Separate CLI paths today |

---

*END OF BACKEND SCHEMA*
*v1.0 historical: DXF CAD Room Detection | May 2026*
*v2.0 current: Grid-Based Zone Detection Engine | June 2026*
