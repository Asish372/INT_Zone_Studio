# Validation Report — DXF Room Detection

Generated: 2026-06-01 07:05 UTC

## Run configuration

| Setting | Value |
| --- | --- |
| gap_threshold | 500 |
| snap_tolerance | 1 |
| drawing_unit | mm |
| detection_mode | exhaustive |
| configured wall_layers | WALL, S-WALL, BEAM |
| ODA File Converter | C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe |


## Executive summary

- **6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg:** configured=618 regions (10091.19 m2), candidate=618 regions (10091.19 m2), open endpoints after gap close=31
- **S111_A.dwg:** configured=397 regions (16348.58 m2), candidate=397 regions (16348.58 m2), open endpoints after gap close=20
- **S111_J.dwg:** configured=331 regions (5320.03 m2), candidate=331 regions (5320.03 m2), open endpoints after gap close=50

## Per-drawing diagnostics

### 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg

- **Source:** `C:\Users\Administrator\OneDrive\Desktop\Strtup\input\6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg`
- **DXF used:** `C:\Users\Administrator\OneDrive\Desktop\Strtup\output\.dxf_cache\6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf`
- **Conversion:** DWG converted via ODA (C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe)

| Metric | Value |
| --- | --- |
| Total entities (modelspace) | 2147 |
| Configured wall layers | WALL, S-WALL, BEAM |
| Entities on configured layers | 0 |
| Segments (configured layers) | 0 |
| Candidate wall layers (count) | 8 |
| Entities on candidate layers | 1524 |
| Segments (candidate layers) | 1524 |
| Open endpoints (before gap close) | 105 |
| Gaps auto-closed | 37 |
| Open endpoints (after gap close) | 31 |
| Raw polygons (polygonize) | 618 |
| Invalid polygons | 0 |
| **Regions detected** (configured layers) | **618** |
| Regions (candidate layers) | 618 |
| Largest area (m2) | 747.4439701706257 |
| Smallest area (m2) | 3.975947038270533e-11 |
| **Total detected area (m2)** | **10091.1943** |
| Candidate largest area (m2) | 747.4439701706257 |
| Candidate smallest area (m2) | 3.975947038270533e-11 |
| Candidate total area (m2) | 10091.1943 |

> **Likely failure:** No entities on configured `wall_layers`. Compare **Candidate wall layers** below and update `config.yaml`.

#### Entity types (modelspace)

| Type | Count |
| --- | --- |
| LINE | 1603 |
| INSERT | 271 |
| MTEXT | 249 |
| HATCH | 16 |
| CIRCLE | 8 |

#### Layer breakdown (all entities / boundary geometry)

| Layer | All entities | LINE/LWPOLY/ARC/POLY |
| --- | --- | --- |
| S-FNDN-1 | 775 | 741 |
| S-BEAM-2 | 531 | 531 |
| A-WALL-1 | 151 | 151 |
| S-COLS | 133 | 0 |
| G-ANNO-TEXT-2 | 108 | 0 |
| S-COLS-IDEN-1 | 85 | 0 |
| S-COLS-1 | 67 | 0 |
| G-ANNO-TEXT-1 | 51 | 43 |
| A-ANNO-NOTE | 43 | 0 |
| A-DETL-2 | 38 | 38 |
| A-DETL-3 | 34 | 34 |
| S-GRID-IDEN | 24 | 0 |
| S-GRID-IDEN-1 | 24 | 0 |
| S-GRID-1 | 24 | 24 |
| A-FLOR | 18 | 18 |
| A-DETL-GENF | 12 | 0 |
| A-DETL-1 | 7 | 7 |
| S-GRID-2 | 6 | 6 |
| A-WALL | 4 | 4 |
| S-FNDN-HDLN-1 | 3 | 3 |
| A-DETL-4 | 3 | 3 |
| G-ANNO-TEXT-3 | 3 | 0 |
| A-DETL-GENF-1 | 1 | 0 |
| PR31272-001D-client cad _Racking__dwg-1 | 1 | 0 |
| A-DETL-GENF-2 | 1 | 0 |

#### Candidate wall layers

| Layer | Boundary entities |
| --- | --- |
| S-FNDN-1 | 741 |
| S-BEAM-2 | 531 |
| A-WALL-1 | 151 |
| A-DETL-2 | 38 |
| A-DETL-3 | 34 |
| A-FLOR | 18 |
| A-DETL-1 | 7 |
| A-WALL | 4 |

### S111_A.dwg

- **Source:** `C:\Users\Administrator\OneDrive\Desktop\Strtup\input\S111_A.dwg`
- **DXF used:** `C:\Users\Administrator\OneDrive\Desktop\Strtup\output\.dxf_cache\S111_A.dxf`
- **Conversion:** DWG converted via ODA (C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe)

| Metric | Value |
| --- | --- |
| Total entities (modelspace) | 1638 |
| Configured wall layers | WALL, S-WALL, BEAM |
| Entities on configured layers | 0 |
| Segments (configured layers) | 0 |
| Candidate wall layers (count) | 6 |
| Entities on candidate layers | 1012 |
| Segments (candidate layers) | 1012 |
| Open endpoints (before gap close) | 170 |
| Gaps auto-closed | 75 |
| Open endpoints (after gap close) | 20 |
| Raw polygons (polygonize) | 397 |
| Invalid polygons | 0 |
| **Regions detected** (configured layers) | **397** |
| Regions (candidate layers) | 397 |
| Largest area (m2) | 810.000000000008 |
| Smallest area (m2) | 4.339381121098995e-11 |
| **Total detected area (m2)** | **16348.5757** |
| Candidate largest area (m2) | 810.000000000008 |
| Candidate smallest area (m2) | 4.339381121098995e-11 |
| Candidate total area (m2) | 16348.5757 |

> **Likely failure:** No entities on configured `wall_layers`. Compare **Candidate wall layers** below and update `config.yaml`.

#### Entity types (modelspace)

| Type | Count |
| --- | --- |
| LINE | 1074 |
| INSERT | 286 |
| MTEXT | 269 |
| HATCH | 7 |
| LWPOLYLINE | 1 |
| CIRCLE | 1 |

#### Layer breakdown (all entities / boundary geometry)

| Layer | All entities | LINE/LWPOLY/ARC/POLY |
| --- | --- | --- |
| S-FNDN-1 | 426 | 382 |
| S-BEAM-1 | 349 | 346 |
| A-WALL-2 | 139 | 139 |
| S-FNDN-HDLN-1 | 126 | 67 |
| S-COLS-IDEN-1 | 110 | 0 |
| S-COLS | 94 | 0 |
| G-ANNO-TEXT-1 | 93 | 0 |
| S-BEAM-HDLN-1 | 69 | 69 |
| S-COLS-1 | 46 | 0 |
| G-ANNO-TEXT-2 | 39 | 31 |
| A-ANNO-NOTE | 37 | 0 |
| S-GRID-IDEN | 29 | 0 |
| S-GRID-IDEN-1 | 29 | 0 |
| S-GRID-1 | 29 | 29 |
| A-WALL-HDLN | 10 | 2 |
| A-DETL-1 | 9 | 9 |
| A-DETL-GENF | 2 | 0 |
| 0-1 | 1 | 0 |
| A-DETL | 1 | 1 |

#### Candidate wall layers

| Layer | Boundary entities |
| --- | --- |
| S-FNDN-1 | 382 |
| S-BEAM-1 | 346 |
| A-WALL-2 | 139 |
| S-BEAM-HDLN-1 | 69 |
| S-FNDN-HDLN-1 | 67 |
| A-DETL-1 | 9 |

### S111_J.dwg

- **Source:** `C:\Users\Administrator\OneDrive\Desktop\Strtup\input\S111_J.dwg`
- **DXF used:** `C:\Users\Administrator\OneDrive\Desktop\Strtup\output\.dxf_cache\S111_J.dxf`
- **Conversion:** DWG converted via ODA (C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe)

| Metric | Value |
| --- | --- |
| Total entities (modelspace) | 1966 |
| Configured wall layers | WALL, S-WALL, BEAM |
| Entities on configured layers | 0 |
| Segments (configured layers) | 0 |
| Candidate wall layers (count) | 11 |
| Entities on candidate layers | 1486 |
| Segments (candidate layers) | 1486 |
| Open endpoints (before gap close) | 270 |
| Gaps auto-closed | 110 |
| Open endpoints (after gap close) | 50 |
| Raw polygons (polygonize) | 331 |
| Invalid polygons | 0 |
| **Regions detected** (configured layers) | **331** |
| Regions (candidate layers) | 331 |
| Largest area (m2) | 881.4392821565687 |
| Smallest area (m2) | 7.48708437465335e-13 |
| **Total detected area (m2)** | **5320.0263** |
| Candidate largest area (m2) | 881.4392821565687 |
| Candidate smallest area (m2) | 7.48708437465335e-13 |
| Candidate total area (m2) | 5320.0263 |

> **Likely failure:** No entities on configured `wall_layers`. Compare **Candidate wall layers** below and update `config.yaml`.

#### Entity types (modelspace)

| Type | Count |
| --- | --- |
| LINE | 1542 |
| MTEXT | 221 |
| INSERT | 153 |
| HATCH | 32 |
| CIRCLE | 10 |
| ARC | 4 |
| DIMENSION | 3 |
| LWPOLYLINE | 1 |

#### Layer breakdown (all entities / boundary geometry)

| Layer | All entities | LINE/LWPOLY/ARC/POLY |
| --- | --- | --- |
| A-DETL-THIN | 678 | 678 |
| S-FNDN-1 | 332 | 310 |
| A-DETL | 184 | 180 |
| G-ANNO-TEXT-1 | 158 | 0 |
| S-BEAM-1 | 155 | 155 |
| A-WALL-3 | 98 | 98 |
| S-COLS | 68 | 0 |
| S-COLS-IDEN-1 | 50 | 0 |
| G-ANNO-TEXT-2 | 45 | 30 |
| A-DETL-GENF | 35 | 0 |
| A-DETL-3 | 19 | 19 |
| A-DETL-2 | 18 | 18 |
| A-DETL-GENF-1 | 18 | 0 |
| S-GRID-IDEN | 13 | 0 |
| S-GRID-IDEN-1 | 13 | 0 |
| S-GRID-1 | 13 | 13 |
| A-ANNO-NOTE | 12 | 12 |
| A-DETL-1 | 11 | 11 |
| A-FLOR | 9 | 9 |
| DraftingView-SUMPDETAILS_dwg-1 | 7 | 0 |
| S-FSTN-1 | 4 | 0 |
| S-BEAM-HDLN-1 | 4 | 4 |
| A-DETL-5 | 4 | 4 |
| S-COLS-HDLN | 3 | 0 |
| A-DETL-GENF-3 | 3 | 0 |
| A-DETL-4 | 3 | 3 |
| A-ANNO-DIMS-1 | 3 | 0 |
| A-DETL-GENF-4 | 2 | 0 |
| A-DETL-6 | 2 | 2 |
| 0-1 | 1 | 0 |
| S-FNDN-HDLN-1 | 1 | 1 |

#### Candidate wall layers

| Layer | Boundary entities |
| --- | --- |
| A-DETL-THIN | 678 |
| S-FNDN-1 | 310 |
| A-DETL | 180 |
| S-BEAM-1 | 155 |
| A-WALL-3 | 98 |
| A-DETL-3 | 19 |
| A-DETL-2 | 18 |
| A-DETL-1 | 11 |
| A-FLOR | 9 |
| A-DETL-5 | 4 |
| S-BEAM-HDLN-1 | 4 |

## Gap analysis summary

Total gap/orphan records: **291** (see `gap_report.xlsx`)

| Status | Count |
| --- | --- |
| within_threshold_unclosed | 194 |
| large_gap_manual_review | 47 |
| orphan_endpoint | 37 |
| above_threshold_close | 13 |

## Recommended next tuning steps

1. If **configured entities = 0**, set `wall_layers` from candidate layers table.
2. If **open endpoints after close > 0**, raise `gap_threshold` using suggested values in `gap_report.xlsx`.
3. If **candidate regions >> configured regions**, current layer filter is too narrow.
4. Compare total area and region count to AutoCAD manual takeoff (ground truth).
