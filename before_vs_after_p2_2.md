# P2.2 Before vs After

**Generated:** 2026-06-05  
**Baseline:** P2.1 global matching (`logs/coverage_run_20260605_103423.json`)  
**After P2.2:** iterative close → renode → re-extract (`logs/coverage_run_20260605_120043.json`)

## Summary

P2.2 is now wired into production detection (`iterative_gap_close: true`, max 3 passes) while preserving P2.1 global min-cost endpoint matching in every closure pass.

| Metric | P2.1 | P2.2 | Delta |
| --- | ---: | ---: | ---: |
| **Detected blocks (total)** | 1,384 | 1,391 | **+7 (+0.5%)** |
| Missed diagnostic events | 103 | 103 | 0 |
| At-risk diagnostic events | 558 | 558 | 0 |
| Gaps closed | 129 | 136 | +7 |
| Open endpoints after close | 287 | 23 | −264 |

## Per-drawing results

| Drawing | P2.1 detected | P2.2 detected | Δ detected | P2.1 gaps closed | P2.2 gaps closed | P2.1 open | P2.2 open |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Warehouse Rev_F | 618 | 618 | 0 | 34 | 34 | 37 | 9 |
| S111_A | 384 | 384 | 0 | 9 | 9 | 152 | 1 |
| S111_J | 382 | 389 | **+7** | 86 | 93 | 98 | 13 |
| **Total** | **1,384** | **1,391** | **+7** | **129** | **136** | **287** | **23** |

## Validation outcome vs simulation target

| Target | Expected | Actual | Status |
| --- | ---: | ---: | --- |
| Total detected gain | +40 to +51 | **+7** | Not achieved |
| Warehouse gain | +20 (simulated) | 0 | Not achieved |
| S111_A behavior | 0 to −4 | 0 | OK |
| S111_J gain | +35 (simulated) | +7 | Partial |

### Interpretation

1. The P2.2 loop is active and functioning (pass-2 closures occur on S111_J: +7 bridges).
2. The major simulation effect did not reproduce in production counting:
   - topology health improved strongly (`open_endpoints_after_close` collapsed 287 → 23),
   - but block recall improved only modestly (+7).
3. P2.2 is therefore a **stability/topology cleanup win**, but **not** the expected recall jump by itself on this production path.

## What changed in code

- Iterative closure implementation: `src/gap_handler.py`
  - `iterative_close_gaps(...)`
  - close → renode (`node_geometry`) → re-extract loop
  - max 3 passes, early stop when `closed == 0`
- Production pipeline integration:
  - `src/validation_diagnostics.py` (`detect_from_tagged`)
  - `main.py` CLI path
  - `config.yaml` flags:
    - `geometry.iterative_gap_close: true`
    - `geometry.iterative_max_passes: 3`
- Reporting phase updated to P2.2:
  - `src/detection_coverage.py`
  - `detection_coverage_report.md`
  - `coverage_metrics.xlsx`

## Tests

- `tests/test_gap_handler.py` updated with iterative-loop coverage:
  - max-pass / stop behavior,
  - renode dependency behavior,
  - pass-2 closure scenario guard.
- `tests/test_p2_2_production_drawings.py` added:
  - Warehouse / S111_A / S111_J regression guards,
  - suite-level gain check against measured production baseline.

## Conclusion

P2.2 implementation is complete and validated in production runs.  
The measured gain is **+7 blocks**, so the simulated **+40 to +51** uplift was **not** achieved on the production pipeline.
