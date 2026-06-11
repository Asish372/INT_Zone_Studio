# INT Zone Pipeline Report (P3)

**Generated:** 2026-06-10 14:57 UTC  
**Source:** `6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg`  
**Profile:** `GRID_WAREHOUSE`  

## Summary

| Metric | Value |
| --- | --- |
| Grid bays (P2) | 24 non-empty / 24 total |
| Micro-faces (Stage 1) | 618 |
| Slivers filtered | 369 |
| Faces assigned | 247 |
| Orphan faces | 0 |
| INT zones (union) | 24 |
| Assignment method | `max_intersection_area` |

### Area metrics (dual view)

| Metric | m² |
| --- | ---: |
| Sum clipped bay areas (P2 grid) | 10,878.86 |
| Sum INT zone union areas (P3) | 9,779.00 |
| P2 mean slab coverage | 84.5% |

## Production readiness

| Gate | Status | Detail |
| --- | --- | --- |
| zone_count | **PASS** | 24 zones vs expected 24 |
| orphan_faces | **PASS** | 0 orphan(s) (max allowed 0) |
| zone_face_coverage | **REVIEW** | Empty zones: INT-1, INT-8, INT-10 |
| union_vs_clipped_bay | **REVIEW** | Low union/bay coverage: INT-1, INT-3, INT-4, INT-5, INT-6, INT-8 |
| face_sum_vs_union | **REVIEW** | Sum != union (>2%): INT-2, INT-4, INT-5, INT-6, INT-9, INT-11 |
| manifest_area | **PASS** | 21/21 within 0.05% tolerance |

## INT zones (union of assigned faces)

| INT | Faces | Union (m²) | Face sum (m²) | Clipped bay (m²) | Union/bay % |
| --- | ---: | ---: | ---: | ---: | ---: |
| INT-1 | 0 | 0.00 | 0.00 | 5.86 | 0.0 |
| INT-2 | 3 | 5.13 | 9.13 | 83.85 | 6.1 |
| INT-3 | 1 | 4.00 | 4.00 | 97.16 | 4.1 |
| INT-4 | 3 | 4.00 | 12.00 | 145.74 | 2.7 |
| INT-5 | 2 | 4.00 | 8.00 | 97.16 | 4.1 |
| INT-6 | 2 | 4.00 | 8.00 | 97.16 | 4.1 |
| INT-7 | 2 | 5.13 | 5.13 | 81.42 | 6.3 |
| INT-8 | 0 | 0.00 | 0.00 | 2.61 | 0.0 |
| INT-9 | 2 | 3.58 | 5.44 | 55.57 | 6.4 |
| INT-10 | 0 | 0.00 | 0.00 | 89.04 | 0.0 |
| INT-11 | 5 | 37.94 | 39.18 | 89.04 | 42.6 |
| INT-12 | 3 | 71.21 | 71.21 | 133.57 | 53.3 |
| INT-13 | 4 | 12.20 | 12.20 | 89.04 | 13.7 |
| INT-14 | 2 | 7.47 | 7.47 | 89.04 | 8.4 |
| INT-15 | 1 | 1.86 | 1.86 | 89.04 | 2.1 |
| INT-16 | 1 | 2.30 | 2.30 | 41.95 | 5.5 |
| INT-17 | 35 | 1,520.79 | 1,529.63 | 970.35 | 156.7 |
| INT-18 | 27 | 61.57 | 89.21 | 1,201.64 | 5.1 |
| INT-19 | 20 | 1,295.91 | 1,315.81 | 1,201.64 | 107.8 |
| INT-20 | 44 | 2,369.92 | 2,372.21 | 1,802.46 | 131.5 |
| INT-21 | 16 | 746.34 | 766.57 | 1,201.64 | 62.1 |
| INT-22 | 21 | 1,312.93 | 1,324.52 | 1,201.64 | 109.3 |
| INT-23 | 30 | 1,647.53 | 1,663.39 | 1,201.64 | 137.1 |
| INT-24 | 23 | 661.17 | 709.21 | 810.58 | 81.6 |

## Manifest reconciliation

**Project:** J33A  
**Transcription:** `complete`  
**Zone count:** PASS (24 computed vs 24 expected)  

| INT | Computed (m²) | Manifest (m²) | Δ % | Status | Faces |
| --- | ---: | ---: | ---: | --- | ---: |
| INT-1 | 0.00 | 0.00 | — | SKIP | 0 |
| INT-2 | 5.13 | 5.13 | 0.000 | PASS | 3 |
| INT-3 | 4.00 | 4.00 | 0.000 | PASS | 1 |
| INT-4 | 4.00 | 4.00 | 0.000 | PASS | 3 |
| INT-5 | 4.00 | 4.00 | 0.000 | PASS | 2 |
| INT-6 | 4.00 | 4.00 | 0.000 | PASS | 2 |
| INT-7 | 5.13 | 5.13 | 0.000 | PASS | 2 |
| INT-8 | 0.00 | 0.00 | — | SKIP | 0 |
| INT-9 | 3.58 | 3.58 | 0.000 | PASS | 2 |
| INT-10 | 0.00 | 0.00 | — | SKIP | 0 |
| INT-11 | 37.94 | 37.94 | 0.000 | PASS | 5 |
| INT-12 | 71.21 | 71.21 | 0.000 | PASS | 3 |
| INT-13 | 12.20 | 12.20 | 0.000 | PASS | 4 |
| INT-14 | 7.47 | 7.47 | 0.000 | PASS | 2 |
| INT-15 | 1.86 | 1.86 | 0.000 | PASS | 1 |
| INT-16 | 2.30 | 2.30 | 0.000 | PASS | 1 |
| INT-17 | 1,520.79 | 1,520.79 | 0.000 | PASS | 35 |
| INT-18 | 61.57 | 61.57 | 0.000 | PASS | 27 |
| INT-19 | 1,295.91 | 1,295.91 | 0.000 | PASS | 20 |
| INT-20 | 2,369.92 | 2,369.92 | 0.000 | PASS | 44 |
| INT-21 | 746.34 | 746.34 | 0.000 | PASS | 16 |
| INT-22 | 1,312.93 | 1,312.93 | 0.000 | PASS | 21 |
| INT-23 | 1,647.53 | 1,647.53 | 0.000 | PASS | 30 |
| INT-24 | 661.17 | 661.17 | 0.000 | PASS | 23 |

## Warnings

- No S-FNDN-1 polygonize region >= 100 m² (112 small regions); using concave hull of linework vertices.
- 2 face(s) with centroid outside slab outline (skipped).
- INT-1: no faces assigned (empty zone).
- INT-8: no faces assigned (empty zone).
- INT-10: no faces assigned (empty zone).
