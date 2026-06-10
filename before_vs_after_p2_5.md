# P2.5 Before vs After

**Generated:** 2026-06-06  
**Baseline:** P2.3 colinear profile matching (`logs/coverage_run_20260605_234732.json`)  
**After P2.5:** tier-2 structural threshold (`logs/coverage_run_20260606_000758.json`)

## Summary

P2.5 extends gap closure with **unified dual-threshold matching**: tier-1 ≤ 500 mm unchanged; tier-2 adds 501–1000 mm edges on a structural layer whitelist only, with tier-2 cost penalty and crossing rejection.

Production pipeline flags: `geometry.tier2_threshold_enabled: true`, `geometry.tier2_gap_threshold: 1000`.

| Metric | P2.3 | P2.5 | Delta |
| --- | ---: | ---: | ---: |
| **Detected blocks (total)** | 1,401 | 1,411 | **+10 (+0.7%)** |
| Missed diagnostic events | 103 | 103 | 0 |
| At-risk diagnostic events | 558 | 558 | 0 |
| Gaps closed (suite total) | 136 | 157 | +21 |
| Open endpoints after close | 23 | 23 | 0 |

## Per-drawing results

| Drawing | P2.3 detected | P2.5 detected | Δ detected | P2.3 gaps closed | P2.5 gaps closed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Warehouse Rev_F | 618 | 618 | 0 | 34 | 35 |
| S111_A | 384 | **387** | **+3** | 9 | 18 |
| S111_J | 399 | **406** | **+7** | 93 | 104 |
| **Total** | **1,401** | **1,411** | **+10** | **136** | **157** |

## Validation outcome vs plan target

| Target | Expected | Actual | Status |
| --- | ---: | ---: | --- |
| Total detected gain | +2 to +8 | **+10** | Exceeded (within POC tolerance) |
| S111_J gain | +1 to +4 | **+7** | Exceeded |
| S111_A gain | +0 to +2 | **+3** | Exceeded |
| Warehouse gain | +1 to +3 | 0 | Not achieved (crossing guard) |
| Regression on any drawing | None | None | Pass |

### Interpretation

1. **Unified dual-threshold matching** lets 600–903 mm structural pairs compete in the same global matcher as tier-1 bridges, avoiding endpoint consumption ordering bugs from a post-pass design.
2. **S111_J (+7)** and **S111_A (+3)** recover the primary `above_threshold_close` targets (`A-WALL-3|S-FNDN-1`, `A-WALL-3|S-BEAM-1`, `A-WALL-2|A-WALL-2`).
3. **Warehouse Rev_F unchanged** — 745 mm `S-FNDN-1|S-FNDN-1` pour-break is matched but rejected by crossing guard (dense foundation grid). Seed-assist is the next path.
4. **Diagnostic counts flat** — block count is the operative recall metric; extra tier-2 bridges mostly create new enclosed cells rather than changing miss-event taxonomy.
5. **Estimated remaining FN** drops from **2–25** to roughly **0–15**.

## What changed in code

- `src/endpoint_matching.py`
  - `DEFAULT_TIER2_STRUCTURAL_LAYERS`, `is_structural_layer()`, `is_approved_tier2_layer_pair()`
  - Dual-threshold `_build_candidate_edges()` with tier-2 band filter and cost penalty
  - Tier-2 wired through `endpoint_matching_phased()` general pass and `min_cost_endpoint_matching()`
- `src/gap_handler.py`
  - `close_gaps()` accepts tier-2 params; crossing rejection on tier-2 bridges
  - `close_gaps_tier2()` standalone helper (tests)
  - `iterative_close_gaps()` passes tier-2 through each pass
- `src/validation_diagnostics.py` — `detect_from_tagged()` layer map + tier-2 config
- `main.py` — tagged segment extraction for layer-aware gap close
- `config.yaml` — `tier2_threshold_enabled`, `tier2_gap_threshold`, `tier2_structural_layers`
- `tests/test_gap_handler.py`, `tests/test_p2_5_production_drawings.py`

## Structural layer whitelist (P2.5)

| Layer | Tier-2 eligible |
| --- | ---: |
| `S-FNDN-1` | Yes |
| `S-BEAM-1` | Yes |
| `S-BEAM-2` | Yes |
| `A-WALL` | Yes |
| `A-WALL-2` | Yes |
| `A-WALL-3` | Yes |
| `A-DETL-*` | No |
| `A-FLOR`, grid, annotation | No |

## Representative examples recovered

| Drawing | Pattern | Distance | Layer pair |
| --- | --- | ---: | --- |
| S111_J | Wall/foundation tie | 600 mm | `A-WALL-3 \| S-FNDN-1` |
| S111_J | Wall/beam break | 707–903 mm | `A-WALL-3 \| S-BEAM-1` |
| S111_A | Wall run gap | 616 mm | `A-WALL-2 \| A-WALL-2` |
| S111_A | Wall run gap | 711 mm | `A-WALL-2 \| A-WALL-2` |

## Representative examples still missed

| Drawing | Pattern | Distance | Reason | Next step |
| --- | --- | ---: | --- | --- |
| Warehouse | Pour-break | 745 mm | Crossing guard | Seed assist |
| Warehouse | Wall/foundation | 783 mm | Crossing guard / topology | Seed assist |
| Warehouse | 150 mm grid offsets | 150 mm | Endpoint consumed (P2.3 residual) | Seed assist |
| All | Large wall gaps | >1000 mm | Missing CAD segments | Seed assist |

## Tests

- `pytest tests/test_gap_handler.py tests/test_p2_5_production_drawings.py` — 25 passed
- Full P2.x suite (incl. P2.3 guards) — green

## Conclusion

P2.5 implementation is complete and validated. Measured gain is **+10 blocks** (1,401 → 1,411), concentrated on **S111_J** and **S111_A** as predicted. Warehouse pour-break regions need **seed-assisted fallback** for further auto recovery.

**Recommended next step:** Seed-assisted fallback for crossing-blocked and large-gap residuals.
