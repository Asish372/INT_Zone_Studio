# Block Detection Improvement Plan

## Scope and Priority

This plan is strictly for **block detection coverage** (finding all valid slab/zone blocks).  
It explicitly excludes:

- area accuracy tuning,
- volume accuracy tuning,
- export/report format work.

In this document, "block" means a valid enclosed structural region that should be detected by the engine.

---

## Current Coverage Baseline

Evidence from existing diagnostics (`validation_report.md`, `gap_failure_analysis.md`, `verification_summary.md`):

- Drawings processed: `6276...Rev_F`, `S111_A`, `S111_J`
- Detected blocks (current): 618 / 397 / 331
- Open endpoints after gap close: 31 / 20 / 50
- Gap-risk records: 291 total
  - `within_threshold_unclosed`: 194
  - `large_gap_manual_review`: 47
  - `orphan_endpoint`: 37
  - `above_threshold_close`: 13
- Failure mode split for within-threshold misses:
  - `bearing_mismatch_suspected`: 169
  - `greedy_pairing_conflict`: 25

Critical baseline caveat:

- Recall is currently proxy-filled (100%) and **not** true detection coverage.

---

## 1) Remaining Missed Blocks

Remaining misses are most likely in these buckets:

1. **Gap-blocked closures**
   - Open loops that should form blocks but remain unclosed after `close_gaps`.
   - Quantified by unresolved endpoints and within-threshold unclosed pairs.

2. **Layer-selection misses**
   - Block boundaries present on layers not included in configured/auto-selected set.
   - Current config wall layers (`WALL`, `S-WALL`, `BEAM`) had 0 entities on all three reference drawings.

3. **Entity-type misses**
   - Engine only extracts `LINE`, `LWPOLYLINE`, `POLYLINE`, `ARC`.
   - `INSERT` entities are excluded from geometry extraction and can hide block-defining geometry.

4. **Post-bridge pairing misses**
   - Greedy nearest-neighbor endpoint matching leaves valid closures unresolved.

5. **Seed-recoverable misses**
   - Blocks not auto-detected but recoverable from an interior seed point (fallback not yet implemented).

---

## 2) Why Blocks Are Being Missed

### A. Gap-closure logic limitations

- `close_gaps` is greedy and endpoint-order dependent.
- Angle gating logic effectively does not reject bad bridges (`angle_ok` remains true in practice), but pairing still misses valid pairs because the first local choice consumes endpoints.
- Evidence: 25 `greedy_pairing_conflict` misses already identified.

### B. Bearing/micro-topology mismatch

- Many unresolved pairs occur at common door/opening geometries with 90/180 bearing deltas.
- Evidence: 169 `bearing_mismatch_suspected` misses.

### C. Layer resolution is availability-driven, not block-boundary aware

- `resolve_wall_layers` ranks by geometry density and includes many candidate layers.
- This helps availability but does not classify "block boundary" vs "detail/subdivision".
- Misses occur when true boundaries are sparse/noisy or when key layers are excluded/under-ranked.

### D. Unsupported entity pipeline

- `INSERT` is present in drawings but excluded by `SUPPORTED_TYPES`.
- If key boundary elements are block references, they are invisible to detection.

### E. No operational fallback for known misses

- Seed-assisted recovery is documented in design but not implemented in `src`.
- Result: unresolved misses remain unresolved.

---

## 3) Gap-Closure Limitations (Current Engine)

1. **Greedy pairing**
   - Local nearest match can consume a point needed for a better global closure.

2. **No global optimization**
   - No bipartite/min-cost matching over free endpoints.

3. **Single-pass closure**
   - No iterative repair/repolygonize cycle with convergence checks.

4. **No local adaptive thresholding**
   - Only one global `gap_threshold`; no local context expansion around suspected missed blocks.

5. **No confidence scoring**
   - Bridges are not scored/ranked for quality (distance + bearing + layer semantics).

6. **No block-level miss telemetry**
   - Diagnostics track endpoint/gap states, not explicit "candidate missed block count."

---

## 4) Layer-Related Misses

### Observed Issues

- Configured `wall_layers` are not aligned with actual project layers.
- Auto-fallback includes broad candidates but without boundary-role classification.
- Detail layers can introduce noise; boundary layers can be diluted.

### Coverage-Focused Layer Plan

1. **Introduce boundary layer tiers**
   - `primary_boundary_layers`
   - `secondary_boundary_layers`
   - `detail_layers_excluded_from_block_detection`

2. **Add layer contribution diagnostics**
   - For each detected block: contributing layers and boundary-length share.
   - For each missed candidate (from gap diagnostics): nearby layer mix.

3. **Per-project layer profile**
   - Freeze a validated layer map per client drawing family.
   - Disable pure density-based fallback once profile exists.

4. **Layer miss gate**
   - Fail coverage gate if configured primary layers return 0 entities.

---

## 5) Seed-Assisted Fallback Path

### Current State

- Design exists (`seed_assisted_fallback_design.md`), implementation does not.

### Required Implementation (Coverage First)

1. Add `src/seed_resolver.py` with:
   - seed ingest (`JSON/CSV/YAML`),
   - smallest containing face selection,
   - status classification (`ok`, `no_boundary`, `ambiguous`, `duplicate_of_auto`).

2. Integrate into pipeline after auto detection:
   - `auto_blocks -> seed_resolution -> dedupe -> merged_blocks`

3. Add local repair tier for missed seeds:
   - local segment window + local gap multiplier + repolygonize.

4. Add seed telemetry:
   - recovered block count,
   - unresolved seed count,
   - reason distribution.

### Coverage Role

Seed fallback is the **safety net** for high-priority missed blocks and must be treated as part of official coverage, not an external manual workaround.

---

## 6) Detection Coverage Metrics (Primary KPI Set)

Replace proxy metrics with operational coverage metrics:

1. **Block Recall (primary)**
   - `Recall = TP / (TP + FN)` against independent ground truth.

2. **Missed Block Count**
   - Absolute `FN` per drawing.

3. **Gap-Closure Effectiveness**
   - `ClosedPairs / CandidatePairs`
   - plus unresolved by status (`within_threshold_unclosed`, `orphan_endpoint`, etc.).

4. **Layer Coverage Ratio**
   - `% of ground-truth blocks with boundary edges represented in selected layers`.

5. **Seed Recovery Yield**
   - `Recovered_by_seed / Total_FN_before_seed`.

6. **Coverage Stability**
   - Run-to-run variance in detected block count and FN set for same input/config.

7. **Unsupported-entity Exposure**
   - `% drawings where boundary-correlated `INSERT` entities are present and unresolved`.

### Target Gates (coverage-first)

- Recall: per drawing >= 90%, aggregate >= 92% (or stricter client gate if provided).
- Within-threshold unresolved pairs: reduce by >= 70% from current baseline.
- Orphan endpoints after close: reduce by >= 60%.
- Seed recovery success on known missed set: >= 80%.

---

## Execution Plan (Coverage Work Only)

### Phase 1 — Instrumentation and Truth Baseline

1. Add block-coverage metrics report script (no area/volume outputs).
2. Replace proxy recall table with true GT-linked recall table.
3. Add per-drawing miss taxonomy report (gap/layer/entity/seed-recoverable).

### Phase 2 — Gap Closure Upgrade

1. Replace greedy endpoint pairing with global min-cost matching.
2. Add iterative close->polygonize loop with stop criteria.
3. Add bridge confidence scoring and rejection logging.

### Phase 3 — Layer Miss Reduction

1. Implement tiered boundary layer configuration.
2. Add layer contribution tracing per detected/missed block.
3. Freeze project-specific layer profiles for S111 family.

### Phase 4 — Seed Fallback Implementation

1. Implement `seed_resolver` core.
2. Wire optional seed file input to main/zone mode path.
3. Add recovery metrics and unresolved seed diagnostics.

### Phase 5 — Coverage Gate and Release Criteria

1. Enforce coverage KPI gates in validation scripts.
2. Block release if recall/miss-gate thresholds are not met.
3. Publish block coverage report as primary readiness artifact.

---

## Immediate Next Actions

1. Implement **Phase 1 instrumentation** first so improvements are measurable.
2. Prioritize **greedy-pairing replacement** (largest known miss driver with existing evidence).
3. Implement **seed fallback** immediately after gap upgrade to close residual misses.
4. Keep area/volume/export pipelines frozen during this coverage improvement cycle.

---

## Phase 1 Prioritized Implementation Sequence (Before Code)

This sequence is intentionally limited to:

- missing block categories,
- layer-related misses,
- entity support gaps,
- gap-closure limitations.

No area/volume/export/UI/delivery work is included.

### Priority table

| Priority | Improvement | Root cause | Expected recall gain | Implementation complexity | Risk |
| --- | --- | --- | --- | --- | --- |
| P1 | **Miss taxonomy + baseline truth instrumentation** | Misses are visible only as partial signals (`open endpoints`, `gap statuses`), not normalized into block-miss categories with stable IDs | **High enabling gain** (indirect, but required to measure all later gains) | **Medium** | **Low** |
| P2 | **Gap-closure failure observability (pair-level)** | `close_gaps` misses are known, but pairing decisions and rejection reasons are not fully auditable | **Low-Medium direct**, **High diagnostic** | **Low-Medium** | **Low** |
| P3 | **Layer miss instrumentation + boundary-role scoring** | Auto-fallback is density-based and not boundary-role aware; configured layers are frequently empty | **Medium-High** | **Medium** | **Medium** (misclassification noise) |
| P4 | **Entity support gap audit for `INSERT` and unsupported types** | Boundary-defining geometry can be hidden in unsupported entities; engine ignores these completely | **Medium** (higher on drawings with block-heavy boundaries) | **Medium** | **Medium** (false positives if block decomposition is naive) |
| P5 | **Candidate block miss estimator from unresolved topology** | No explicit estimate of likely missed blocks from unresolved loops/gaps | **Medium** | **Medium-High** | **Medium** (over/under-estimation) |
| P6 | **Coverage KPI gate in validation scripts** | Proxy recall can hide misses; no hard fail for coverage regressions | **High process gain** (prevents silent regressions) | **Low** | **Low** |

### Detailed sequence

#### 1) Build miss-category backbone (P1)

Implement first because all subsequent work depends on this structure.

- **What to add**
  - Canonical miss categories:
    - `gap_blocked_closure`
    - `layer_selection_miss`
    - `unsupported_entity_miss`
    - `pairing_conflict_miss`
    - `unknown_unresolved`
  - Stable miss record schema (`drawing`, `category`, `evidence refs`, `severity`, `coordinates`).
  - Baseline snapshot generator for each drawing.

- **Root cause addressed**
  - Missing blocks are not currently tracked as first-class, comparable records.

- **Expected recall gain**
  - Indirect but critical: enables reliable measurement of actual recall improvement.

- **Complexity**
  - Medium (data model + wiring in diagnostics scripts).

- **Risk**
  - Low (read-only instrumentation path).

#### 2) Deepen gap-closure diagnostics before algorithm changes (P2)

- **What to add**
  - Pair-attempt log from `close_gaps`:
    - candidate endpoints,
    - chosen partner,
    - skipped alternatives,
    - distance/bearing metrics,
    - reason code.
  - Distinguish:
    - `within_threshold_unclosed_due_to_pairing`
    - `within_threshold_unclosed_due_to_geometry`
    - `above_threshold_unclosed`.

- **Root cause addressed**
  - Greedy pairing failures are known but not traceable enough for safe fix design.

- **Expected recall gain**
  - Low-medium direct now; major enablement for Phase 2 closure algorithm update.

- **Complexity**
  - Low-medium.

- **Risk**
  - Low.

#### 3) Layer-related miss attribution and role scoring (P3)

- **What to add**
  - Layer-role score per layer (`primary-boundary likelihood`, `secondary`, `detail/noise`).
  - For each unresolved miss cluster, nearest-layer composition summary.
  - Config warning gate:
    - if configured primary layers produce 0 entities, emit coverage-critical warning.

- **Root cause addressed**
  - Current fallback chooses availability, not block-boundary intent.

- **Expected recall gain**
  - Medium-high once used to tune layer selection in next phase.

- **Complexity**
  - Medium.

- **Risk**
  - Medium due to potential role misclassification on unusual drawings.

#### 4) Entity support gap audit (P4)

- **What to add**
  - Unsupported-entity inventory:
    - count by entity type (`INSERT`, `CIRCLE`, etc.),
    - spatial correlation with unresolved misses.
  - `INSERT` exposure metric:
    - unresolved misses near block references / total unresolved misses.

- **Root cause addressed**
  - Engine may miss blocks if relevant boundaries are encapsulated in unsupported entities.

- **Expected recall gain**
  - Medium (drawing-dependent; can be high in block-heavy CAD standards).

- **Complexity**
  - Medium.

- **Risk**
  - Medium (wrong assumptions about block semantics if over-generalized).

#### 5) Missed-block estimator from unresolved topology (P5)

- **What to add**
  - Heuristic estimator for likely missed closed blocks based on:
    - unresolved endpoint clusters,
    - local cycle potential,
    - layer-role confidence,
    - unsupported-entity proximity.
  - Output as `estimated_fn_lower_bound` and `estimated_fn_upper_bound`.

- **Root cause addressed**
  - Team lacks a practical, per-run indicator of remaining missed blocks before manual review.

- **Expected recall gain**
  - Medium (improves targeting and triage; not a detector change by itself).

- **Complexity**
  - Medium-high.

- **Risk**
  - Medium (confidence interval calibration required).

#### 6) Enforce coverage KPI gate in verification (P6)

- **What to add**
  - Validation fail conditions for:
    - proxy-only recall usage,
    - unresolved within-threshold miss budget exceedance,
    - rising unsupported-entity exposure.
  - Trend report:
    - baseline vs current miss-category deltas.

- **Root cause addressed**
  - Coverage regressions can pass unnoticed when operational pipeline still "succeeds".

- **Expected recall gain**
  - High process gain by preventing regressions and forcing miss reduction work.

- **Complexity**
  - Low.

- **Risk**
  - Low.

---

## Phase 1 Exit Criteria

Phase 1 is complete when all are true:

1. Every unresolved detection issue maps to a canonical miss category.
2. Layer-related misses are quantifiable per drawing with role-scored evidence.
3. Unsupported entity exposure (especially `INSERT`) is measured and reported.
4. Gap-closure misses are attributable with pair-level reason codes.
5. Coverage KPI gate rejects proxy-only or regressive runs.
6. A stable baseline report exists for future Phase 2 algorithm upgrades.
