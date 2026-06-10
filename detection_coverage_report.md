# Detection Coverage Report (P2.5 + Seed Assist + P2 Local Repair)

**Generated:** 2026-06-06 00:44 UTC  
**Phase:** P2.5 + Seed-Assisted Fallback (P1 + P2 local gap repair)  


**Seeds file:** `poc_seed_manifest.yaml`

## Seed-assisted totals

| Drawing | Auto | With seeds | Seed recovered | Local repair |
| --- | ---: | ---: | ---: | --- |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 618 | 618 | 0 | 745 mm pour-break = already auto-detected |
| S111_A.dwg | 387 | 387 | 0 | — |
| S111_J.dwg | 406 | **407** | **+1** | `j-wall-fndn-900` (3 bridges, 3.29 m²) |
| **Total** | **1,411** | **1,412** | **+1** | Est. +4–12 with engineer interior seeds |

## Executive summary

| Drawing | Detected | Missed | At risk | Open endpoints | Layer source |
| --- | ---: | ---: | ---: | ---: | --- |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 618 | 26 | 111 | 9 | auto_fallback |
| S111_A.dwg | 387 | 7 | 183 | 1 | auto_fallback |
| S111_J.dwg | 406 | 70 | 264 | 13 | auto_fallback |

## Run configuration

| Setting | Value |
| --- | --- |
| gap_threshold | 500 |
| snap_tolerance | 1 |
| configured wall_layers | WALL, S-WALL, BEAM |
| detection_mode | exhaustive |
| colinear_profile_match | True |
| tier2_threshold_enabled | True |
| tier2_gap_threshold | 1000 |

## Miss category totals

| Category | Count |
| --- | ---: |
| unsupported_entity_miss | 357 |
| gap_blocked_closure | 147 |
| bearing_mismatch_miss | 73 |
| unknown_unresolved | 54 |
| pairing_conflict_miss | 27 |
| layer_selection_miss | 3 |

## 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg

### Summary

- Layer source: `auto_fallback`
- Detected blocks: **618**
- Missed events: **26**
- At-risk events: **111**
- Gaps closed: 35
- Open endpoints after close: 9

### Unsupported entity exposure

- `INSERT`: 271
- `MTEXT`: 249
- `HATCH`: 16
- `CIRCLE`: 8

### Misses by category

| Category | Count |
| --- | ---: |
| unsupported_entity_miss | 72 |
| bearing_mismatch_miss | 25 |
| unknown_unresolved | 22 |
| gap_blocked_closure | 17 |
| layer_selection_miss | 1 |

### Sample miss / at-risk records (first 30)

| block_id | status | category | layer | entity | confidence | reason |
| --- | --- | --- | --- | --- | ---: | --- |
| layer-miss-configured-empty | missed | layer_selection_miss | WALL,S-WALL,BEAM | layer_config | 0.95 | Configured wall_layers contain zero boundary entities; detec… |
| gap-miss-0001 | at_risk | gap_blocked_closure | A-WALL|S-FNDN-1 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=783.0 |
| gap-miss-0002 | at_risk | gap_blocked_closure | A-WALL|S-FNDN-1 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=783.0 |
| gap-miss-0003 | at_risk | gap_blocked_closure | A-WALL-1|S-BEAM-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=1100.273 |
| gap-miss-0004 | at_risk | gap_blocked_closure | A-WALL-1|A-WALL-1 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=1340.0 |
| gap-miss-0005 | at_risk | gap_blocked_closure | A-WALL-1|A-DETL-3 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=1230.0 |
| gap-miss-0006 | at_risk | gap_blocked_closure | A-WALL-1|A-WALL-1 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=4690.0 |
| gap-miss-0007 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0008 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0009 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0010 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0011 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0012 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0013 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0014 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0015 | missed | bearing_mismatch_miss | S-FNDN-1|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0016 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0017 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0018 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=180.0; failu… |
| gap-miss-0019 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=180.0; failu… |
| gap-miss-0020 | at_risk | gap_blocked_closure | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=745.432 |
| gap-miss-0021 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=180.0; failu… |
| gap-miss-0022 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=180.0; failu… |
| gap-miss-0023 | missed | bearing_mismatch_miss | S-BEAM-2|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0024 | missed | bearing_mismatch_miss | S-BEAM-2|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=419.076; fai… |
| gap-miss-0025 | missed | bearing_mismatch_miss | S-BEAM-2|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0026 | at_risk | gap_blocked_closure | S-BEAM-2|S-BEAM-2 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=538.539 |
| gap-miss-0027 | at_risk | gap_blocked_closure | S-BEAM-2|S-BEAM-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=1855.815 |
| gap-miss-0028 | missed | bearing_mismatch_miss | S-BEAM-2|S-BEAM-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=180.0; failu… |
| gap-miss-0029 | at_risk | unknown_unresolved | S-BEAM-2 | gap_endpoint | 0.65 | Gap status: orphan_endpoint |


## S111_A.dwg

### Summary

- Layer source: `auto_fallback`
- Detected blocks: **387**
- Missed events: **7**
- At-risk events: **183**
- Gaps closed: 18
- Open endpoints after close: 1

### Unsupported entity exposure

- `INSERT`: 286
- `MTEXT`: 269
- `HATCH`: 7
- `CIRCLE`: 1

### Misses by category

| Category | Count |
| --- | ---: |
| unsupported_entity_miss | 94 |
| gap_blocked_closure | 70 |
| unknown_unresolved | 19 |
| bearing_mismatch_miss | 4 |
| pairing_conflict_miss | 2 |
| layer_selection_miss | 1 |

### Sample miss / at-risk records (first 30)

| block_id | status | category | layer | entity | confidence | reason |
| --- | --- | --- | --- | --- | ---: | --- |
| layer-miss-configured-empty | missed | layer_selection_miss | WALL,S-WALL,BEAM | layer_config | 0.95 | Configured wall_layers contain zero boundary entities; detec… |
| gap-miss-0001 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=2342.854 |
| gap-miss-0002 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=2279.989 |
| gap-miss-0003 | missed | bearing_mismatch_miss | A-WALL-2|A-WALL-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0004 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=9862.0 |
| gap-miss-0005 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=9862.0 |
| gap-miss-0006 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=9001.25 |
| gap-miss-0007 | at_risk | unknown_unresolved | A-WALL-2 | gap_endpoint | 0.65 | Gap status: orphan_endpoint |
| gap-miss-0008 | at_risk | gap_blocked_closure | S-BEAM-1|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=4001.953 |
| gap-miss-0009 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3620.374 |
| gap-miss-0010 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3620.374 |
| gap-miss-0011 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=616.19 |
| gap-miss-0012 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=616.19 |
| gap-miss-0013 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3620.374 |
| gap-miss-0014 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3620.374 |
| gap-miss-0015 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=1540.0 |
| gap-miss-0016 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=711.872 |
| gap-miss-0017 | at_risk | gap_blocked_closure | A-WALL-2|A-DETL-1 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=2123.433 |
| gap-miss-0018 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3620.374 |
| gap-miss-0019 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3620.374 |
| gap-miss-0020 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=2371.005 |
| gap-miss-0021 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=2371.005 |
| gap-miss-0022 | missed | pairing_conflict_miss | A-WALL-2|A-WALL-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=229.369; fai… |
| gap-miss-0023 | missed | pairing_conflict_miss | A-WALL-2|A-WALL-2 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=229.369; fai… |
| gap-miss-0024 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3620.374 |
| gap-miss-0025 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3620.374 |
| gap-miss-0026 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=1030.97 |
| gap-miss-0027 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=4610.0 |
| gap-miss-0028 | at_risk | gap_blocked_closure | A-WALL-2|A-DETL-1 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=646.0 |
| gap-miss-0029 | at_risk | gap_blocked_closure | A-WALL-2|A-WALL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3862.0 |


## S111_J.dwg

### Summary

- Layer source: `auto_fallback`
- Detected blocks: **406**
- Missed events: **70**
- At-risk events: **264**
- Gaps closed: 104
- Open endpoints after close: 13

### Unsupported entity exposure

- `MTEXT`: 221
- `INSERT`: 153
- `HATCH`: 32
- `CIRCLE`: 10
- `DIMENSION`: 3

### Misses by category

| Category | Count |
| --- | ---: |
| unsupported_entity_miss | 191 |
| gap_blocked_closure | 60 |
| bearing_mismatch_miss | 44 |
| pairing_conflict_miss | 25 |
| unknown_unresolved | 13 |
| layer_selection_miss | 1 |

### Sample miss / at-risk records (first 30)

| block_id | status | category | layer | entity | confidence | reason |
| --- | --- | --- | --- | --- | ---: | --- |
| layer-miss-configured-empty | missed | layer_selection_miss | WALL,S-WALL,BEAM | layer_config | 0.95 | Configured wall_layers contain zero boundary entities; detec… |
| gap-miss-0001 | missed | bearing_mismatch_miss | A-WALL-3|A-WALL-3 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0002 | at_risk | gap_blocked_closure | A-WALL-3|S-FNDN-1 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3965.0 |
| gap-miss-0003 | at_risk | gap_blocked_closure | A-WALL-3|S-FNDN-1 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=3965.0 |
| gap-miss-0004 | at_risk | gap_blocked_closure | A-WALL-3|S-FNDN-1 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=1085.5 |
| gap-miss-0005 | missed | bearing_mismatch_miss | A-WALL-3|A-WALL-3 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0006 | at_risk | gap_blocked_closure | A-WALL-3|A-DETL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=6149.0 |
| gap-miss-0007 | at_risk | gap_blocked_closure | A-WALL-3|A-DETL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=6337.295 |
| gap-miss-0008 | at_risk | gap_blocked_closure | A-WALL-3|S-FNDN-1 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=600.0 |
| gap-miss-0009 | at_risk | gap_blocked_closure | A-WALL-3|S-FNDN-1 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=600.0 |
| gap-miss-0010 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0011 | missed | bearing_mismatch_miss | S-FNDN-1|A-WALL-3 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=20.0; failur… |
| gap-miss-0012 | missed | bearing_mismatch_miss | S-FNDN-1|A-WALL-3 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=20.0; failur… |
| gap-miss-0013 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0014 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0015 | at_risk | gap_blocked_closure | S-FNDN-1|A-DETL-2 | gap_endpoint | 0.70 | Gap status: large_gap_manual_review; distance=1422.431 |
| gap-miss-0016 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0017 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0018 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0019 | missed | pairing_conflict_miss | S-FNDN-1|S-BEAM-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=7.432; failu… |
| gap-miss-0020 | missed | pairing_conflict_miss | S-FNDN-1|S-BEAM-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=7.432; failu… |
| gap-miss-0021 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0022 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0023 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0024 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0025 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0026 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0027 | missed | bearing_mismatch_miss | S-FNDN-1|S-FNDN-1 | gap_endpoint | 0.85 | Gap status: within_threshold_unclosed; distance=150.0; failu… |
| gap-miss-0028 | at_risk | gap_blocked_closure | A-WALL-3|S-BEAM-1 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=903.12 |
| gap-miss-0029 | at_risk | gap_blocked_closure | A-WALL-3|S-BEAM-1 | gap_endpoint | 0.70 | Gap status: above_threshold_close; distance=707.549 |

## Notes

- `detected` rows represent polygonized blocks from the current pipeline.
- `missed` / `at_risk` rows are diagnostic events, not ground-truth FN labels.
- P2.5 adds unified dual-threshold matching: tier-1 ≤ 500 mm, tier-2 501–1000 mm on structural whitelist only.
- P2.3 colinear 150/180 mm profile pre-pass + micro-gap resolver + P2.1 global matching.
- P2.2 iterative close → renode → re-extract (max 3 passes) remains enabled.
- **P2 local gap repair:** when a seed has no containing face, cropped segments get elevated tier-2 closure (≤ 1000 mm, structural whitelist, relaxed crossing guard) without mutating global topology.
- Gap diagnostics skip same-segment pairs.
- See `before_vs_after_seed_local_repair.md` for P1 vs P2 comparison.
- See `seed_local_gap_repair_plan.md` for Warehouse 745 mm and S111_J orphan cluster details.
