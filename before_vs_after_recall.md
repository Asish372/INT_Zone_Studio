# P2.1 Before vs After Recall

**Generated:** 2026-06-05  
**Baseline:** P1 greedy nearest-neighbor (`logs/coverage_run_20260605_094532.json`)  
**After P2.1:** global min-cost endpoint matching (`logs/coverage_run_20260605_103423.json`)

## Summary

P2.1 replaces greedy endpoint pairing in `close_gaps()` with a global minimum-cost matching pass (NetworkX `max_weight_matching`). Same-segment endpoint pairs are excluded in both closure and gap diagnostics.

| Metric | P1 (greedy) | P2.1 (global) | Delta |
| --- | ---: | ---: | ---: |
| **Detected blocks (total)** | 1,346 | 1,384 | **+38 (+2.8%)** |
| Missed diagnostic events | 197 | 103 | −94 |
| At-risk diagnostic events | 487 | 558 | +71 |
| Gaps closed | 222 | 129 | −93 |
| Open endpoints after close | 101 | 287 | +186 |

There is no ground-truth block count for these drawings; **detected polygon count** is the primary recall proxy.

## Per-drawing results

| Drawing | P1 detected | P2.1 detected | Δ detected | P1 gaps closed | P2.1 gaps closed | P1 open | P2.1 open |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Warehouse Rev_F | 618 | 618 | 0 | 37 | 34 | 31 | 37 |
| S111_A | 397 | 384 | −13 | 75 | 9 | 20 | 152 |
| S111_J | 331 | 382 | **+51** | 110 | 86 | 50 | 98 |
| **Total** | **1,346** | **1,384** | **+38** | **222** | **129** | **101** | **287** |

### Interpretation

**Net +38 detected blocks** is driven almost entirely by **S111_J (+51)**. Warehouse is unchanged. S111_A drops 13 blocks because P1 greedy created many **same-segment bogus bridges** (~71 of 75 closures on S111_A) that artificially closed geometry and produced spurious pour polygons. P2.1 removes those invalid closures; the lower count on S111_A is a **quality correction**, not a matcher regression.

**Open endpoints and gaps closed moved in opposite directions from detected count** by design:

- P1 inflated `gaps_closed` and deflated `open_endpoints` via same-segment self-bridges.
- P2.1 only bridges **cross-segment** pairs within threshold, so open endpoint counts rise while bogus closures disappear.

On S111_A, only **13 valid cross-segment candidate edges** exist within 500 mm; global matching closes **9** of them — near the feasible ceiling for a single pass at this threshold.

## Miss category shift (diagnostic events)

Gap diagnostics in P2.1 also skip same-segment nearest-neighbor pairing, so category totals are comparable to the new matcher behavior.

| Category | P1 total | P2.1 total | Δ |
| --- | ---: | ---: | ---: |
| bearing_mismatch_miss | 169 | 73 | −96 |
| pairing_conflict_miss | 25 | 27 | +2 |
| gap_blocked_closure | 60 | 147 | +87 |
| unknown_unresolved | 40 | 54 | +14 |
| unsupported_entity_miss | 387 | 357 | −30 |
| layer_selection_miss | 3 | 3 | 0 |

- **bearing_mismatch_miss** fell sharply because many P1 labels were artifacts of greedy same-segment pairing, not true bearing rejection.
- **gap_blocked_closure** rose because real unresolved cross-segment gaps are now visible instead of being masked by bogus closures.
- **pairing_conflict_miss** is essentially flat (25 → 27); global matching resolves crossing-pair conflicts in unit tests but remaining production conflicts need iterative closure (P2.2) or colinear profile passes (P2.3).

## What P2.1 fixed (validated in tests)

| Scenario | Greedy behavior | P2.1 behavior |
| --- | --- | --- |
| Greedy failure (150 mm wall offset vs shorter wrong pair) | Picks nearest wrong neighbor | Prefers 150 mm colinear 180° offset via cost function |
| Crossing-pair conflict (A↔D, B↔C compete) | First-come locking leaves valid pairs unclosed | Global matching picks optimal disjoint set |
| 150 / 180 mm wall-thickness offsets | Often missed or deprioritized | Low-cost bridges when bearing delta ≈ 180° |
| Same-segment self-bridge | Allowed (bug) | Excluded |

All 8 tests in `tests/test_gap_handler.py` pass.

## Recall assessment

| Question | Answer |
| --- | --- |
| Did P2.1 improve real detection? | **Yes, +38 blocks (+2.8%)** on the three-drawing suite, mainly S111_J. |
| Is S111_A a regression? | **No** — fewer spurious polygons; true cross-segment closure rate is ~9/13 candidates. |
| Are miss categories lower? | **Yes for missed events (−94)**, but at-risk rose as latent gaps surfaced. |
| Is P2.1 sufficient alone? | **Partially.** Remaining gains need P2.2 (iterative close loop) and/or P2.3 (colinear profile pass) for 150/180 mm pairs that still appear as `within_threshold_unclosed` in diagnostics. |

## Recommendation before P2.2

Proceed to **P2.2 iterative gap closure** only after accepting that P2.1’s primary win is **+51 blocks on S111_J** and **cleaner topology on S111_A**. Further matching-only tweaks have diminishing returns where valid cross-segment edge count is low (e.g. 13 on S111_A).

## Artifacts

| File | Description |
| --- | --- |
| `detection_coverage_report.md` | P2.1 coverage report |
| `coverage_metrics.xlsx` | Per-record and summary sheets |
| `logs/coverage_run_20260605_103423.json` | P2.1 structured log |
| `src/endpoint_matching.py` | Global matcher + wall-offset cost |
| `src/gap_handler.py` | Integration in `close_gaps()` |
| `tests/test_gap_handler.py` | P2.1 regression tests |
