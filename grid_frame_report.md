# Grid Frame Report (P2)

**Generated:** 2026-06-02 05:20 UTC  
**Source:** `6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg`  
**Frame mode:** `target_24`  

## Summary

| Metric | Value |
| --- | --- |
| Grid layers used | S-GRID-1, S-GRID-IDEN, S-GRID-2 |
| Candidate grid layers | S-GRID-2 |
| Raw grid segments | 27 |
| Axis family count | 2 |
| Axis A lines / merged positions | 18 / 18 |
| Axis B lines / merged positions | 9 / 9 |
| Raw bay count (all adjacent axes) | 136 |
| Bay count (frame used) | 24 |
| Expected INT count | 24 |
| Validation | PASS (bay count matches expected INT count) |
| Slab layer | S-FNDN-1 |
| Slab outline method | concave_hull |
| Slab outline area (m²) | 11,065.64 |
| Bays before clip | 24 |
| Bays non-empty after clip | 24 |

## Warnings

- No S-FNDN-1 polygonize region >= 100 m² (33 small regions); using concave hull of linework vertices.
- No S-FNDN-1 polygonize region >= 100 m² (33 small regions); using concave hull of linework vertices.

## Slab clipping statistics

- **Slab outline:** `concave_hull` on `S-FNDN-1`
- **Slab area:** 11,065.64 m²
- **Total raw bay area:** 11,238.16 m²
- **Total clipped bay area:** 10,878.86 m²
- **Area retained after clip:** 96.8%
- **Mean per-bay coverage:** 85.9%

## Geometry validation summary

| Check | Count |
| --- | ---: |
| Invalid clipped geometry | 0 |
| Low coverage bays | 2 |
| Empty after clip | 0 |
| Overlapping bay pairs | 0 |

## INT labels

Labels assigned deterministically in **row-major** order (row ascending, then column ascending). Repeated runs with the same grid produce identical `INT-n` mapping.

## Grid line extraction

| Layer | Segments |
| --- | ---: |
| S-GRID-1 | 24 |
| S-GRID-2 | 3 |

## Axis families

- **axis_1**: angle 90.0°, 18 segments → 18 axis positions (layers: S-GRID-1)
- **axis_2**: angle 0.0°, 9 segments → 9 axis positions (layers: S-GRID-1, S-GRID-2)

## Sorted axis positions

### Axis A (primary family)

| Index | Position (mm) |
| ---: | ---: |
| 1 | -210,740.28 |
| 2 | -203,217.78 |
| 3 | -195,495.28 |
| 4 | -184,195.28 |
| 5 | -172,895.28 |
| 6 | -161,595.28 |
| 7 | -150,295.28 |
| 8 | -138,995.28 |
| 9 | -127,695.28 |
| 10 | -116,395.28 |
| 11 | -105,095.28 |
| 12 | -93,795.28 |
| 13 | -82,495.28 |
| 14 | -71,195.28 |
| 15 | -59,895.28 |
| 16 | -48,595.28 |
| 17 | -39,470.28 |
| 18 | -30,345.28 |

### Axis B (secondary family)

| Index | Position (mm) |
| ---: | ---: |
| 1 | 153,152.60 |
| 2 | 154,740.10 |
| 3 | 156,752.60 |
| 4 | 158,340.10 |
| 5 | 160,740.10 |
| 6 | 162,280.10 |
| 7 | 164,805.89 |
| 8 | 186,490.10 |
| 9 | 215,450.10 |

## Bay diagnostics

### Bay cells (raw vs clipped)

| INT | Row | Col | Raw (m²) | Clipped (m²) | Coverage % | Flags |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| INT-1 | 0 | 0 | 106.38 | 17.37 | 16.3 | low_coverage |
| INT-2 | 0 | 1 | 122.04 | 91.92 | 75.3 | — |
| INT-3 | 0 | 2 | 122.04 | 91.92 | 75.3 | — |
| INT-4 | 0 | 3 | 81.36 | 61.28 | 75.3 | — |
| INT-5 | 0 | 4 | 122.04 | 91.92 | 75.3 | — |
| INT-6 | 0 | 5 | 95.56 | 15.11 | 15.8 | low_coverage |
| INT-7 | 1 | 0 | 117.83 | 78.78 | 66.9 | — |
| INT-8 | 1 | 1 | 135.18 | 135.18 | 100.0 | — |
| INT-9 | 1 | 2 | 135.18 | 135.18 | 100.0 | — |
| INT-10 | 1 | 3 | 90.12 | 90.12 | 100.0 | — |
| INT-11 | 1 | 4 | 135.18 | 135.18 | 100.0 | — |
| INT-12 | 1 | 5 | 105.85 | 67.24 | 63.5 | — |
| INT-13 | 2 | 0 | 120.14 | 119.72 | 99.6 | — |
| INT-14 | 2 | 1 | 137.83 | 137.83 | 100.0 | — |
| INT-15 | 2 | 2 | 137.83 | 137.83 | 100.0 | — |
| INT-16 | 2 | 3 | 91.89 | 91.89 | 100.0 | — |
| INT-17 | 2 | 4 | 137.83 | 137.83 | 100.0 | — |
| INT-18 | 2 | 5 | 107.93 | 106.63 | 98.8 | — |
| INT-19 | 3 | 0 | 1,496.54 | 1,496.54 | 100.0 | — |
| INT-20 | 3 | 1 | 1,716.84 | 1,716.84 | 100.0 | — |
| INT-21 | 3 | 2 | 1,716.84 | 1,716.84 | 100.0 | — |
| INT-22 | 3 | 3 | 1,144.56 | 1,144.56 | 100.0 | — |
| INT-23 | 3 | 4 | 1,716.84 | 1,716.84 | 100.0 | — |
| INT-24 | 3 | 5 | 1,344.35 | 1,344.35 | 100.0 | — |

## Expected INT count

INT zones are intended to align **one pour per structural bay** on grid warehouse drawings. Face assignment to micro-polygons is **not** included in this phase.

Manifest / profile expects **24** INT zones. Current frame yields **24** bay polygons.

---

*End of grid frame report (P2)*
