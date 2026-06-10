# UI/UX Brief
## DXF CAD Room Detection & Grid-Based Zone Detection Engine

| Document section | Version | Scope |
|------------------|---------|--------|
| §1–§8 below | **1.0** (historical) | Room detection CLI and Excel/DXF UX |
| §9–§11 below | **2.0** (current) | Zone Engine CLI, reports, and roadmap UX |

**Version:** 2.0 | **Date:** June 2026

---

## 1. Product Overview

This tool has **two interfaces** — both must be designed:

| Interface | Who Uses It | When |
|---|---|---|
| **CLI (Command Line)** | Developer, tech-savvy engineer | V1.0 — primary interface |
| **GUI (Desktop App)** | Non-technical engineer, field staff | V2.0 — future scope |

> **V1.0 Priority:** CLI must be clean, informative, and foolproof. The engineer should know exactly what happened at every step without reading a log file.

---

## 2. User Personas

### Persona A — Senior Structural Engineer (Primary User)
- **Name:** Rajesh, 42 years old
- **Tech level:** Comfortable with AutoCAD, basic Excel. Not a programmer.
- **Goal:** Get area + volume numbers out of DXF files without opening AutoCAD every time
- **Pain point:** Spends 2–3 hours per project doing manual area calculations
- **Expectation:** Run one command → get Excel file → done
- **Device:** Windows laptop, dual monitor, AutoCAD installed

### Persona B — Junior Draughtsman / CAD Operator (Secondary User)
- **Name:** Priya, 27 years old
- **Tech level:** Proficient with AutoCAD and DWG/DXF files
- **Goal:** Process multiple DXF files quickly and hand over a clean report
- **Pain point:** Repetitive boundary tracing for each slab section
- **Expectation:** Batch mode — drop folder, get results
- **Device:** Windows desktop

---

## 3. CLI Interface Design (V1.0)

### 3.1 Startup Banner

```
╔══════════════════════════════════════════════════════════╗
║          DXF Room Detector  v1.0                        ║
║          Automated Area & Volume Calculator             ║
╚══════════════════════════════════════════════════════════╝
```

### 3.2 Basic Usage

```bash
# Single file
python main.py --input input/S111_A.dxf

# With custom settings
python main.py --input input/S111_A.dxf --thickness 0.20 --gap 800 --prefix Slab

# Batch mode
python main.py --input input/ --batch

# Help
python main.py --help
```

### 3.3 Help Screen Design

```
DXF Room Detector — Help
─────────────────────────────────────────────────
Usage:
  python main.py --input <path> [options]

Required:
  --input  PATH     Path to DXF file OR folder (batch mode)

Options:
  --thickness  N    Slab thickness in metres   (default: 0.15)
  --gap        N    Max gap to auto-close in drawing units
                    (default: 500)
  --prefix    TEXT  Label prefix: Room, Slab, Region
                    (default: Room)
  --unit      TEXT  Drawing unit: mm, cm, m    (default: mm)
  --batch           Process all DXF files in input folder
  --preview         Show matplotlib visual before export
  --help            Show this help message

Output:
  output/<filename>_annotated.dxf
  output/<filename>_results.xlsx
  logs/run_<timestamp>.log

Examples:
  python main.py --input input/warehouse.dxf
  python main.py --input input/ --batch --thickness 0.20
─────────────────────────────────────────────────
```

### 3.4 Live Progress Output (Single File)

```
DXF Room Detector v1.0
══════════════════════════════════════════════════

  Settings loaded:
  ├─ Drawing unit  : mm
  ├─ Slab thick    : 0.15 m
  ├─ Gap threshold : 500 units
  └─ Label prefix  : Room

──────────────────────────────────────────────────
  Processing: S111_A.dxf
──────────────────────────────────────────────────

  ✓  File loaded         (2,847 entities found)
  ✓  Layers found        WALL, S-WALL, BEAM, SLAB (14 total)
  ✓  Entities extracted  1,203 LINE  |  412 LWPOLYLINE  |  38 ARC
  ✓  Geometry built      1,653 segments after merge
  ✓  Gaps closed         23 gaps (largest: 487 units)
  ⚠  Unresolved gaps     2 gaps too large to auto-close
                         → See: logs/run_20260531.log for coordinates

  ✓  Regions detected    47 rooms
  ✓  Areas calculated
  ✓  Labels assigned     Room 1 → Room 47

──────────────────────────────────────────────────
  EXPORT
──────────────────────────────────────────────────
  ✓  output/S111_A_annotated.dxf
  ✓  output/S111_A_results.xlsx

══════════════════════════════════════════════════
  SUMMARY
══════════════════════════════════════════════════

  Rooms Detected  :  47
  Total Area      :  4,821.3 m²
  Total Volume    :    723.2 m³
  Warnings        :  2  (see log for details)
  Time taken      :  4.2 seconds

══════════════════════════════════════════════════
  ✓  Done. Open output/S111_A_results.xlsx
══════════════════════════════════════════════════
```

### 3.5 Error State Output

```
══════════════════════════════════════════════════
  Processing: bad_file.dxf
══════════════════════════════════════════════════

  ✗  File not found: input/bad_file.dxf
     Check the file path and try again.

  ──────────────────────────────────────
  Tip: Run  python main.py --help  to see usage.
```

```
  ⚠  No entities found on layers: WALL, S-WALL
     Layers in this file: A-WALL, A-BEAM, S-SLAB

  Tip: Update layer names in config.yaml to match
       the actual layer names shown above.
```

### 3.6 Batch Mode Output

```
DXF Room Detector — Batch Mode
══════════════════════════════════════════════════
  Files found: 3 DXF files in input/

  [1/3] S111_A.dxf        ✓  47 rooms   4,821.3 m²
  [2/3] S111_J.dxf        ✓  31 rooms   3,104.8 m²
  [3/3] WAREHOUSE.dxf     ⚠  18 rooms   1,920.0 m²  (2 warnings)

──────────────────────────────────────────────────
  COMBINED SUMMARY
──────────────────────────────────────────────────
  Total Files     :  3
  Total Rooms     :  96
  Total Area      :  9,846.1 m²
  Total Volume    :  1,476.9 m³

  ✓  output/COMBINED_report.xlsx
  ✓  Individual files exported to output/
══════════════════════════════════════════════════
```

---

## 4. Excel Report Design

### Sheet 1 — Room Details

| Room ID | Label | Area (m²) | Perimeter (m) | Volume (m³) | Centroid X | Centroid Y | Source File |
|---|---|---|---|---|---|---|---|
| 1 | Room 1 | 120.45 | 44.20 | 18.07 | 5.22 | 6.10 | S111_A.dxf |
| 2 | Room 2 | 87.30 | 37.60 | 13.10 | 12.40 | 6.10 | S111_A.dxf |
| ... | | | | | | | |
| **TOTAL** | | **4,821.3** | | **723.2** | | | |

**Formatting Rules:**
- Header row: Bold, blue background (#1F3864), white text
- Total row: Bold, light gray background
- Area/Volume columns: 2 decimal places
- Alternate row shading for readability
- Column widths auto-fitted to content

### Sheet 2 — Summary

```
Project Summary
────────────────────────────────
Source Files    : S111_A.dxf
Run Date        : 31 May 2026
Settings Used   : thickness=0.15m, unit=mm

Results
────────────────────────────────
Total Rooms     : 47
Total Area      : 4,821.3 m²
Total Volume    : 723.2 m³
Largest Room    : Room 1 — 580.2 m²
Smallest Room   : Room 47 — 12.3 m²

Warnings
────────────────────────────────
2 unresolved gaps — see log file
```

---

## 5. Annotated DXF Output Design

```
Original drawing layers (unchanged)
    +
New layers added:
    │
    ├── DETECTED_REGIONS  (color: RED, line weight: 0.35mm)
    │     → LWPOLYLINE boundary of each detected room
    │
    └── ROOM_LABELS       (color: GREEN, font: Standard)
          → TEXT entity at centroid of each room
          → Content: "Room 1
                       Area: 120.5 m²
                       Vol: 18.1 m³"
```

**Visual Preview (matplotlib) — optional `--preview` flag:**

```
┌────────────────────────────────────────────────┐
│  DXF Room Detector — Preview                   │
│  S111_A.dxf                                    │
│                                                │
│  ┌──────────┐  ┌──────┐  ┌───────────┐        │
│  │          │  │      │  │           │        │
│  │  Room 1  │  │  R2  │  │  Room 3   │        │
│  │ 580.2 m² │  │87 m² │  │ 210.5 m²  │        │
│  │          │  │      │  │           │        │
│  └──────────┘  └──────┘  └───────────┘        │
│                                                │
│  [Different colors per room]                   │
│  [Centroid labels visible]                     │
│  Total: 47 rooms | 4,821 m² | 723 m³           │
│                                                │
│  [Save Preview]        [Continue Export]       │
└────────────────────────────────────────────────┘
```

---

## 6. GUI Design — V2.0 (Future Scope)

> **Note:** This is for future reference. V1.0 is CLI only.

### Main Window Layout

```
┌─────────────────────────────────────────────────────────┐
│  DXF Room Detector                         [—][□][✕]   │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │  INPUT FILE                                     │   │
│  │  [  input/S111_A.dxf                    ] [📂] │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  SETTINGS                                               │
│  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Drawing Unit: [mm▼]│  │ Slab Thickness: [0.15] m │  │
│  └──────────────────┘  └──────────────────────────┘   │
│  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Gap Threshold:[500]│  │ Label Prefix:  [Room   ] │  │
│  └──────────────────┘  └──────────────────────────┘   │
│                                                         │
│  LAYERS (from DXF file)                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ☑ WALL   ☑ S-WALL   ☑ BEAM   ☐ TEXT   ☐ DIM │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│                [  RUN DETECTION  ]                      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  PROGRESS                                               │
│  ████████████████████░░░░  75%  Detecting regions...    │
├─────────────────────────────────────────────────────────┤
│  RESULTS                                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Room │  Area (m²) │ Volume (m³) │  Status       │   │
│  │ 1    │   120.45   │    18.07    │  ✓ Detected   │   │
│  │ 2    │    87.30   │    13.10    │  ✓ Detected   │   │
│  │ 3    │   210.50   │    31.58    │  ⚠ Gap found  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Total: 47 rooms | 4,821 m² | 723 m³                   │
│                                                         │
│  [Export DXF]   [Export Excel]   [View Preview]        │
└─────────────────────────────────────────────────────────┘
```

---

## 7. UX Principles

| Principle | Implementation |
|---|---|
| **Zero guesswork** | Every step logs what it found. User always knows what happened. |
| **Fail loudly** | Errors print clearly with reason AND fix tip. No silent failures. |
| **Non-destructive** | Original DXF is never overwritten. New file always created. |
| **Configurable defaults** | All settings have sensible defaults — tool works out of the box |
| **Human assist, not human replace** | Unresolved gaps flagged clearly so engineer can fix them |
| **Audit trail** | Every run creates a log file with full details |

---

## 8. Warning & Error Message Guidelines

| Situation | Message Style | Example |
|---|---|---|
| Gap too large | `⚠ Warning + coordinates + tip` | `⚠ Gap of 1,240 units at (4520, 3100) — too large to auto-close. Fix in AutoCAD and re-run.` |
| 0 regions found | `⚠ Warning + layer suggestion` | `⚠ 0 rooms detected. Check layer names in config.yaml. Layers in file: A-WALL, S-BEAM` |
| File missing | `✗ Error + exact path + tip` | `✗ File not found: input/myfile.dxf. Check spelling and try again.` |
| Area looks wrong | Never hide — always show | All areas printed; user can visually verify against AutoCAD |

---

# Version 2.0 — Zone Engine UX

> **NEW (v2.0):** Engineers may run **two commands**: Stage 1 for geometric faces (`Room N`) and Stage 2 for INT grid zones (`INT-N`). Until `main.py` integration (P4), Stage 2 uses `scripts/run_grid_frame_builder.py`.

---

## 9. Zone Engine CLI (v2.0)

### 9.1 Grid frame + validation run

```bash
# Full P2: grid frame, slab clip, INT labels, report, preview
python scripts/run_grid_frame_builder.py \
  --dwg "input/6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg" \
  --manifest reference/j33a_zones_manifest.yaml \
  --report grid_frame_report.md \
  --preview output/grid_frame_preview

# P1 only (no slab clip / validation)
python scripts/run_grid_frame_builder.py --p1-only
```

### 9.2 Example console output (P2)

```
=== Grid frame geometry (P2) ===
Bays (frame): 24 (raw grid cells: 136)
Bays before clip: 24
Bays non-empty after clip: 24
Slab outline: concave_hull (11,065.6 m²)
Total raw area: 11,238.16 m²
Total clipped area: 10,878.86 m²
Mean coverage: 85.9%
Low coverage: 2 | Empty: 0 | Overlaps: 0
Report: grid_frame_report.md
Preview: output/grid_frame_preview.svg
  WARN: No S-FNDN-1 polygonize region >= 100 m² ...
```

### 9.3 UX principles (Zone Engine)

| Principle | Implementation |
|-----------|----------------|
| **Separate metrics** | Do not conflate “618 rooms” (Stage 1) with “24 INT zones” (Stage 2) in one summary line |
| **Deterministic INT IDs** | Same DWG + manifest → same INT-1…INT-N mapping |
| **Validation visible** | `grid_frame_report.md` is the primary human review artifact for Stage 2 |
| **Manifest-driven count** | Expected INT count comes from YAML, not guessed from face count |

---

## 10. Validation report UX (v2.0)

Primary deliverable: **`grid_frame_report.md`**

| Section | User action |
|---------|-------------|
| Summary | Confirm bay count = `zone_count_expected` from manifest |
| Slab clipping statistics | Check mean coverage; investigate low-coverage INT rows |
| Geometry validation | Review invalid / overlap / empty counts |
| Bay diagnostics table | Compare clipped m² per INT; flag `low_coverage` rows |

Optional: open **`output/grid_frame_preview.svg`** to visually verify bay grid vs slab outline.

---

## 11. Roadmap UX — integrated product (v2.0)

**Planned single-run experience (after P4–P5):**

```
DXF Zone Engine v2.0
══════════════════════════════════════════════════
  Stage 1 — Geometric faces
  ✓  618 micro-regions detected (debug)
  Stage 2 — INT zones (GRID_WAREHOUSE)
  ✓  24 INT zones (manifest: J33A)
  ✓  Face assignment: 618 → 24 (0 orphans)
  EXPORT
  ✓  output/..._int_schedule.xlsx   (Pour No., SQM, CUM)
  ✓  output/..._faces_debug.xlsx     (optional)
  ✓  grid_frame_report.md
══════════════════════════════════════════════════
```

**Excel (roadmap)** — INT schedule sheet columns: Pour No., Concrete Area (SQM), Concrete Volume (CUM), Manifest SQM, Deviation %, Face count, Grid ref.

**Annotated DXF (roadmap)** — layers `INT_ZONES` (clipped or union boundaries) and `INT_LABELS` (yellow-style callout text matching QS PDFs).

---

*END OF UI/UX BRIEF*
*v1.0 historical: DXF CAD Room Detection | May 2026*
*v2.0 current: Grid-Based Zone Detection Engine | June 2026*
