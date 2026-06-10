# Gap Failure Analysis

Generated: 2026-06-01 07:20 UTC

## Scope

Only **`within_threshold_unclosed`** gaps (distance ≤ `gap_threshold` but not bridged).
No new product features — diagnostics for recall tuning.

## Configuration

| Setting | Value |
| --- | --- |
| gap_threshold | 500.0 |
| snap_tolerance | 1.0 |
| max_gap_angle | 30.0 |

## Summary

| Drawing | within_threshold_unclosed count |
| --- | --- |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 31 |
| S111_A.dwg | 60 |
| S111_J.dwg | 103 |

**Total:** 194 gaps

## Failure reasons (aggregate)

| failure_reason | count |
| --- | --- |
| bearing_mismatch_suspected | 169 |
| greedy_pairing_conflict | 25 |

## Recommended next tuning (no code yet)

1. If **greedy_pairing_conflict** dominates: consider sorting gap pairs by distance ascending before bridging.
2. If **bearing_mismatch_suspected** appears: review `max_gap_angle` or allow orthogonal door gaps.
3. Re-measure recall after threshold-only changes.

## Detail table (first 100 rows)

| drawing | gap_dist | layer_a | layer_b | point_a | point_b | reason | bearing_Δ° | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | A-WALL | A-WALL | (210740.3, 215480.1) | (210590.3, 215480.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | A-WALL-1 | A-WALL-1 | (209250.3, 201780.1) | (209250.3, 201630.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 125.0 | A-WALL-1 | S-BEAM-2 | (210590.3, 201630.1) | (210590.3, 201505.1) | greedy_pairing_conflict | 0.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | A-WALL-1 | A-WALL-1 | (205900.3, 201630.1) | (205900.3, 201780.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 291.548 | A-WALL-1 | S-BEAM-2 | (210590.3, 201780.1) | (210340.3, 201630.1) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 164295.2) | (210590.3, 164295.2) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 168730.1) | (210590.3, 168730.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 169730.1) | (210590.3, 169730.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 177360.1) | (210590.3, 177360.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 178360.1) | (210590.3, 178360.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 185990.1) | (210590.3, 185990.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 186990.1) | (210590.3, 186990.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 193120.9) | (210590.3, 193120.9) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-BEAM-2 | (210740.3, 194120.9) | (210590.3, 194120.9) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-FNDN-1 | (210590.3, 200251.6) | (210740.3, 200251.6) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-FNDN-1 | (210590.3, 201251.6) | (210740.3, 201251.6) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-FNDN-1 | S-FNDN-1 | (210740.3, 216263.1) | (210590.3, 216263.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 180.0 | S-FNDN-1 | S-FNDN-1 | (70545.3, 168597.1) | (70725.3, 168597.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 180.0 | S-FNDN-1 | S-FNDN-1 | (72095.3, 169155.1) | (72095.3, 169335.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 180.0 | S-FNDN-1 | S-FNDN-1 | (171995.3, 169335.1) | (171995.3, 169155.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 180.0 | S-FNDN-1 | S-FNDN-1 | (173365.3, 168597.1) | (173545.3, 168597.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-BEAM-2 | S-BEAM-2 | (204620.3, 215450.1) | (204470.3, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 419.076 | S-BEAM-2 | S-BEAM-2 | (204345.3, 215450.1) | (204470.3, 215050.1) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 180.0 | S-BEAM-2 | S-BEAM-2 | (72355.3, 167255.1) | (72355.3, 167435.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 180.0 | S-BEAM-2 | S-BEAM-2 | (113745.3, 169090.1) | (113565.3, 169090.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 180.0 | S-BEAM-2 | S-BEAM-2 | (113790.3, 167255.1) | (113790.3, 167435.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 180.0 | S-BEAM-2 | S-BEAM-2 | (171750.3, 167255.1) | (171750.3, 167435.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | A-WALL-1 | A-WALL-1 | (210740.3, 200751.6) | (210590.3, 200751.6) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 459.23 | S-FNDN-1 | A-DETL-3 | (186280.3, 162250.1) | (185840.3, 162381.6) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-BEAM-2 | S-BEAM-2 | (210740.3, 208382.4) | (210590.3, 208382.4) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 150.0 | S-BEAM-2 | S-BEAM-2 | (210590.3, 213763.1) | (210740.3, 213763.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (64463.5, 215300.1) | (64463.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (60723.5, 125600.1) | (60573.5, 125600.1) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (60723.5, 135726.1) | (60573.5, 135726.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (237683.5, 215300.1) | (237683.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (68083.9, 215300.1) | (68083.9, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (127343.5, 215450.1) | (127343.5, 215300.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (71704.2, 215300.1) | (71704.2, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (75324.6, 215300.1) | (75324.6, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (78945.0, 215300.1) | (78945.0, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (82565.4, 215300.1) | (82565.4, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (86185.7, 215300.1) | (86185.7, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (89806.1, 215300.1) | (89806.1, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (93426.5, 215300.1) | (93426.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (95797.5, 215300.1) | (95797.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (97046.9, 215300.1) | (97046.9, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (96817.5, 215450.1) | (96817.5, 215300.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (100667.2, 215300.1) | (100667.2, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (104287.6, 215300.1) | (104287.6, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (106427.5, 215300.1) | (106427.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (114331.5, 215300.1) | (114331.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (118193.5, 215300.1) | (118193.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (120919.5, 215300.1) | (120919.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (124213.5, 215300.1) | (124213.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (125727.3, 215300.1) | (125727.3, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (126727.3, 215450.1) | (126727.3, 215300.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (60723.5, 215300.1) | (60573.5, 215300.1) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (60573.5, 205175.4) | (60723.5, 205175.4) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (60573.5, 195314.8) | (60723.5, 195314.8) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (60573.5, 204175.4) | (60723.5, 204175.4) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (60573.5, 185454.1) | (60723.5, 185454.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (60573.5, 165451.4) | (60723.5, 165451.4) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (66683.5, 125450.1) | (66683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (75683.5, 125450.1) | (75683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (270793.5, 131955.1) | (270643.5, 131955.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (270643.5, 125600.1) | (270793.5, 125600.1) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (270793.5, 215300.1) | (270643.5, 215300.1) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (270643.5, 205175.4) | (270793.5, 205175.4) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (270793.5, 196294.8) | (270643.5, 196294.8) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (270643.5, 195314.8) | (270793.5, 195314.8) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (270643.5, 197294.8) | (270793.5, 197294.8) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 4.0 | A-WALL-2 | A-DETL-1 | (270643.5, 185454.1) | (270643.5, 185450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (93683.5, 125450.1) | (93683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (102683.5, 125450.1) | (102683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (156683.5, 125450.1) | (156683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (174683.5, 125450.1) | (174683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (183683.5, 125450.1) | (183683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (201683.5, 125450.1) | (201683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (210683.5, 125450.1) | (210683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (255683.5, 125450.1) | (255683.5, 125600.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (208783.5, 215300.1) | (208783.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (209783.5, 215450.1) | (209783.5, 215300.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (174683.5, 215450.1) | (174683.5, 215300.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (145763.5, 215300.1) | (145763.5, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (65613.5, 217418.8) | (65463.5, 217418.8) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (68608.6, 229500.0) | (68608.6, 229650.0) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (65613.5, 219387.5) | (65463.5, 219387.5) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (65613.5, 227668.8) | (65463.5, 227668.8) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (65463.5, 225687.5) | (65613.5, 225687.5) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (65463.5, 229500.0) | (65613.5, 229500.0) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_A.dwg | 150.0 | A-WALL-2 | A-WALL-2 | (71728.6, 229650.0) | (71728.6, 229500.0) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 150.0 | A-WALL-3 | A-WALL-3 | (136976.0, 215450.1) | (136826.0, 215450.1) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 150.0 | A-WALL-3 | A-WALL-3 | (126911.0, 215450.1) | (126911.0, 215300.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 150.0 | A-WALL-3 | A-WALL-3 | (136826.0, 163150.1) | (136976.0, 163150.1) | bearing_mismatch_suspected | 90.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 150.0 | A-WALL-3 | A-WALL-3 | (136826.0, 171799.1) | (136976.0, 171799.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 150.0 | A-WALL-3 | A-WALL-3 | (136976.0, 180512.1) | (136826.0, 180512.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 150.0 | S-FNDN-1 | S-FNDN-1 | (72546.0, 163000.1) | (72546.0, 163150.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 20.0 | S-FNDN-1 | A-WALL-3 | (49946.0, 215300.1) | (49926.0, 215300.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 20.0 | S-FNDN-1 | A-WALL-3 | (49946.0, 215450.1) | (49926.0, 215450.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |
| S111_J.dwg | 150.0 | S-FNDN-1 | S-FNDN-1 | (49946.0, 163000.1) | (49946.0, 163150.1) | bearing_mismatch_suspected | 180.0 | Both endpoints are within gap_threshold but close_gaps matched at least one endp… |


_… 94 more rows omitted._
