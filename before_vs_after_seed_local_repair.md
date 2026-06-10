# Seed-Assisted Fallback — P2 Local Gap Repair Before vs After

**Generated:** 2026-06-06  
**Baseline:** P1 seed infra (1,411 auto; 0 seed recovery)  
**After:** P1 + P2 local gap repair + validated seed manifest

---

## Summary

P2 adds localized gap closure inside `resolve_seed_region()` when smallest-face finds no containing polygon. Global auto detection is unchanged; recovery happens only when seeds are supplied and local repair closes enough topology to form a new face.

| Metric | P1 only | P2 local repair (no seeds) | P2 + `poc_seed_manifest.yaml` |
| --- | ---: | ---: | ---: |
| **Detected blocks (total)** | 1,411 | 1,411 | **1,412** |
| Raw polygonize faces | 1,411 | 1,411 | 1,411 |
| Seed-assisted recovered | 0 | 0 | **+1** |
| Local repair bridges (validated seed) | — | — | 3 (S111_J) |
| Auto regression | — | None | None |

---

## Per-drawing results

| Drawing | P1 auto | P2 auto (no seeds) | P2 + seeds | Seed recovered | Local repair used |
| --- | ---: | ---: | ---: | ---: | --- |
| Warehouse Rev_F | 618 | 618 | 618 | 0 | 0 (745 mm = duplicate_of_auto) |
| S111_A | 387 | 387 | 387 | 0 | 0 |
| S111_J | 406 | 406 | **407** | **+1** | 1 (`j-wall-fndn-900`) |
| **Total** | **1,411** | **1,411** | **1,412** | **+1** | |

---

## Validated recovery

| Seed ID | Drawing | Status | Bridges | Area (m²) | Notes |
| --- | --- | --- | ---: | ---: | --- |
| `j-wall-fndn-900` | S111_J | **ok** | 3 | 3.29 | A-WALL-3\|S-FNDN-1 @ 900 mm |
| `wh-pour-break-745` | Warehouse | duplicate_of_auto | 0 | 1.06 | Cell already in auto #242 |
| `wh-grid-150mm-east` | Warehouse | no_boundary | 6 | — | Partial repair; needs interior pick |
| `j-orphan-fndn-a/b` | S111_J | no_boundary | 3–4 | — | Partial repair; needs interior pick |

---

## Key findings

1. **Global closed faces unchanged** — raw polygonize still equals auto (1,411). P2 does not alter global topology.
2. **Local repair unlocks open cells** — S111_J +1 block confirms the mechanism: 3 synthetic bridges in crop → new 3.29 m² face.
3. **Warehouse 745 mm is not an FN** — pour-break midpoint seed matches existing auto region; crossing-blocked gap does not suppress that cell.
4. **Gap-midpoint seeds under-recover** — 25 partial-repair cases bridge gaps but miss the pour interior; engineer picks needed.
5. **Estimated remaining recoverable:** **+4 to +12** blocks with interior engineer seeds on partial-repair clusters.

---

## What changed in code

| Module | Change |
| --- | --- |
| `src/seed_resolver.py` | `_local_gap_repair_segments()`, P2 fallback path |
| `src/models.py` | `SeedResolution.repair_bridges` |
| `config.yaml` | `local_repair_enabled`, multiplier, max_gap, structural/crossing flags |
| `main.py` | `endpoint_layers` passed to seed resolver |
| `tests/test_seed_resolver.py` | +3 P2 tests (13 total) |
| `reference/poc_seed_manifest.yaml` | Validated production coordinates |

---

## Validation outcome

| Gate | Target | Actual | Status |
| --- | --- | --- | --- |
| P2 implementation | Complete | Complete | Pass |
| No regression without seeds | 1,411 | 1,411 | Pass |
| Unit + P2.5 regression | Green | Green | Pass |
| Production seed recovery | ≥ +1 | **+1** | Pass |
| Global topology unchanged | Yes | Yes | Pass |

---

## Usage

```bash
python main.py input/S111_J.dwg --seeds reference/poc_seed_manifest.yaml
python main.py input/ --batch --seeds reference/poc_seed_manifest.yaml
```

---

## Recommended next step

Engineer interior picks for S111_J orphan clusters (`j-orphan-fndn-a/b`, grid 912 mm) and Warehouse partial-repair zones (`wh-grid-150mm-east`). Replace gap-midpoint coordinates with confirmed pour-cell interiors in `reference/poc_seed_manifest.yaml`.
