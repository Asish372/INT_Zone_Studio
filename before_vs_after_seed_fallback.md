# Seed-Assisted Fallback — Before vs After

**Generated:** 2026-06-06  
**Baseline:** P2.5 tier-2 structural threshold (1,411 auto-detected blocks)  
**After P1 seed infra:** smallest-face strategy + merge/dedupe pipeline

## Summary

P1 delivers the seed-assisted detection infrastructure: YAML/JSON seed input, smallest containing face resolution, IoU dedupe against auto regions, and merge into the existing `compute_all` pipeline. Production auto detection is unchanged when no seeds are supplied.

| Metric | P2.5 auto | P1 seed (no seeds file) | P1 + example manifest |
| --- | ---: | ---: | ---: |
| **Detected blocks (total)** | 1,411 | 1,411 | 1,411 |
| Raw polygonize faces | 1,411 | 1,411 | 1,411 |
| Seed-assisted recovered | — | 0 | 0* |
| Regression on any drawing | — | None | None |

\*Example manifest uses placeholder coordinates — all resolve to `no_boundary` or `duplicate_of_auto` until replaced with CAD picks.

## Per-drawing results

| Drawing | P2.5 auto | Raw faces | Auto-discovered seeds | Simulated recovery |
| --- | ---: | ---: | ---: | ---: |
| Warehouse Rev_F | 618 | 618 | 0 | 0 |
| S111_A | 387 | 387 | 0 | 0 |
| S111_J | 406 | 406 | 0 | 0 |
| **Total** | **1,411** | **1,411** | **0** | **0** |

## Key finding

**Raw polygonize count equals auto-detected count on all three production drawings.** Every closed face in the prepared segment network is already in the automatic output. The estimated 0–15 remaining FN blocks are **topologically open** pour cells — not recoverable by P1 smallest-face alone until gaps are closed (P2 local repair) or walls are completed in CAD.

## Simulated recovery (controlled test)

| Scenario | Auto | After seed | Delta |
| --- | ---: | ---: | ---: |
| Two-room synthetic DXF, one room omitted from auto set | 1 | 2 | **+1** |

Test: `tests/test_seed_resolver.py::test_seed_recovers_region_absent_from_auto`

This confirms the merge pipeline works when a closed face exists in the segment network but is absent from auto output.

## What changed in code

| Module | Change |
| --- | --- |
| `src/seed_resolver.py` | New — load/resolve/merge |
| `src/models.py` | `SeedRequest`, `SeedResolution`, provenance fields |
| `src/calculator.py` | `region_meta` for `detection_method` |
| `main.py` | `--seeds` CLI, seed logging |
| `config.yaml` | `seed_assist` block |
| `tests/test_seed_resolver.py` | 10 tests |

## Expected FN recovery (forward-looking)

| Phase | Est. additional blocks | Notes |
| --- | ---: | --- |
| P1 on current production (no P2) | 0 | All closed faces already auto-detected |
| P1 + engineer interior seeds | 0–5 | Only if seed lies in partially closed loop |
| P2 local gap repair + seeds | **+5 to +15** | Targets open topology FN reservoir |

## Validation outcome

| Gate | Target | Actual | Status |
| --- | --- | --- | --- |
| P1 implementation complete | Yes | Yes | Pass |
| No regression without seeds | 1,411 | 1,411 | Pass |
| Unit tests | All green | 10/10 | Pass |
| P2.5 production regression | Hold | Hold | Pass |
| Production auto recovery (P1 alone) | 0–15 | 0 | Expected — open gaps |

## Recommended next step

Implement **P2 local gap repair** in `resolve_seed_region()`, then populate `reference/poc_seed_manifest.yaml` with engineer-picked interior coordinates for Warehouse pour-break (745 mm) and S111_J grid orphan clusters.

**Usage:**

```bash
python main.py input/S111_J.dwg --seeds reference/poc_seed_manifest.yaml
```
