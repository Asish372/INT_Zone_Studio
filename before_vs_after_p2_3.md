# P2.3 Before vs After

**Generated:** 2026-06-05  
**Baseline:** P2.2 iterative closure (`logs/coverage_run_20260605_120043.json`)  
**After P2.3:** colinear profile matching (`logs/coverage_run_20260605_234732.json`)

## Summary

P2.3 adds colinear 150/180 mm profile weighting and a safe phased pre-pass (unique mutual partners only) before P2.1 global matching. Production pipeline flag: `geometry.colinear_profile_match: true`.

| Metric | P2.2 | P2.3 | Delta |
| --- | ---: | ---: | ---: |
| **Detected blocks (total)** | 1,391 | 1,401 | **+10 (+0.7%)** |
| Missed diagnostic events | 103 | 103 | 0 |
| At-risk diagnostic events | 558 | 558 | 0 |
| Gaps closed | 136 | 136 | 0 |
| Open endpoints after close | 23 | 23 | 0 |

## Per-drawing results

| Drawing | P2.2 detected | P2.3 detected | Δ detected | P2.2 open EP | P2.3 open EP |
| --- | ---: | ---: | ---: | ---: | ---: |
| Warehouse Rev_F | 618 | 618 | 0 | 9 | 9 |
| S111_A | 384 | 384 | 0 | 1 | 1 |
| S111_J | 389 | **399** | **+10** | 13 | 13 |
| **Total** | **1,391** | **1,401** | **+10** | **23** | **23** |

## Validation outcome vs plan target

| Target | Expected | Actual | Status |
| --- | ---: | ---: | --- |
| Total detected gain | +4 to +12 | **+10** | Within range |
| S111_J gain | +2 to +7 | **+10** | Exceeded |
| Warehouse gain | +2 to +5 | 0 | Not achieved |
| S111_A gain | +0 to +1 | 0 | OK (near ceiling) |
| Regression on any drawing | None | None | Pass |

### Interpretation

1. **Profile weight bonus** (`+WEIGHT_BASE` on 150/180 mm colinear pairs) shifts max-cardinality matching to prefer wall-offset bridges over competing short spurs in dense S111_J foundation grids.
2. **Warehouse Rev_F** unchanged — remaining 150 mm misses there are not simple cardinality losses; endpoints were likely consumed by different topology breaks (P2.5 / seed-assist candidates).
3. **Diagnostic counts flat** — bridged pairs healed existing faces or closed loops without changing miss-event taxonomy; block count is the operative recall metric.
4. **Estimated remaining FN** drops from **12–35** to roughly **2–25** (10 blocks recovered).

## What changed in code

- `src/endpoint_matching.py`
  - `is_wall_offset_profile()`, `is_micro_gap_pair()`
  - `endpoint_matching_phased()` — unique mutual partner pre-pass + general matching
  - Profile edge weight bonus in global matcher (`weight += WEIGHT_BASE`)
  - Adopts phased result when bridge count ≥ P2.1 alone
- `src/gap_handler.py` — `colinear_profile` flag threaded through `close_gaps` / `iterative_close_gaps`
- `config.yaml` — `colinear_profile_match: true`, `micro_gap_threshold: 15`
- `tests/test_gap_handler.py` — profile / phased matching unit tests
- `tests/test_p2_3_production_drawings.py` — production regression guards

## Representative examples recovered (S111_J)

| Pattern | Layer pair | Distance | Mechanism |
| --- | --- | ---: | --- |
| Foundation grid offset | `S-FNDN-1 \| S-FNDN-1` | 150 mm | Profile weight bonus wins over spur competition |
| Slab/wall micro tie | `S-FNDN-1 \| A-WALL-3` | 20 mm | Existing P2.1 cost; iterative pass |
| Beam junction cluster | `S-FNDN-1 \| S-BEAM-1` | 7.4 mm | Micro-gap unique partner pre-pass |

## Representative examples still missed

| Drawing | Pattern | Distance | Next step |
| --- | --- | ---: | --- |
| Warehouse | `S-FNDN-1 \| S-BEAM-2` | 150 mm | Endpoint consumed elsewhere — seed assist |
| Warehouse | `S-FNDN-1 \| S-FNDN-1` | 745 mm | P2.5 tier-2 threshold |
| S111_J | `A-WALL-3 \| S-BEAM-1` | 600–903 mm | P2.5 tier-2 threshold |
| All | Large wall gaps | >1000 mm | Seed-assisted fallback |

## Tests

- `pytest tests/test_gap_handler.py tests/test_p2_3_production_drawings.py` — 22 passed
- Full P2.x suite (incl. P2.2 guards) — 30 passed

## Conclusion

P2.3 implementation is complete and validated. Measured gain is **+10 blocks** (1,391 → 1,401), concentrated on **S111_J** as predicted. Warehouse offset-gap regions need **P2.5** and/or **seed-assisted fallback** for further auto recovery.

**Recommended next step:** P2.5 Tier-2 Threshold (600–1000 mm, structural whitelist).
