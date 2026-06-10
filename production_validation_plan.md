# Production Validation Plan — INT Zones

Date: 2026-06-02  
Phase: Production Validation (feature freeze)  
Scope: Validate generated INT zones against client-expected outputs on real project drawings.  
Constraint: No geometry-engine changes and no new feature work in this phase.

---

## 1) Current evidence review (what exists now)

The delivery bundle contains strong **operational** evidence, but incomplete **client-ground-truth** evidence:

- Delivery package and hash manifest exist for all core outputs and QA docs.
- Detection and export pipeline runs complete on all target drawings.
- INT zone production milestone passes structural checks (zone counts, label stability, no overlaps, no invalid geometry).
- Acceptance report explicitly states recall and real AutoCAD area benchmarks were pending, then later closed using proxy baselines due missing client-authoritative sources in the environment.
- Area benchmark and recall summary files were filled with detector-equals-reference proxy values, not independent measurements.

Conclusion: the program is operationally stable, but not yet fully validated against client expectations.

---

## 2) Real validation vs proxy validation

### 2.1 Real validation (acceptable for client acceptance)

Evidence is **real** only when all of the following are true:

1. The reference comes from client-authoritative artifacts (client PDF schedule, client CAD, or explicit signed client mapping).
2. The reference is independently measured outside the detector output.
3. The measurement method is reproducible and documented.
4. Raw evidence (screenshots, takeoff logs, exported tables) is attached and traceable.

Examples:
- AutoCAD region counts performed manually from client CAD with documented boundary-layer settings.
- AutoCAD `AREA` measurements for selected regions.
- Direct transcription of client schedule values (not backfilled from generated outputs).
- Client-reviewed INT label ↔ pour mapping for each zone.

### 2.2 Proxy validation (informational only)

Evidence is **proxy** when the reference value is derived from generated outputs or assumptions instead of client ground truth.

Examples in current bundle:
- Recall table where AutoCAD region counts equal detected counts by construction.
- Area benchmark where AutoCAD area equals detector area by construction.
- Manifest values marked “derived from deterministic pipeline output due missing source PDF.”

Policy for Production Validation:
- Proxy evidence can be retained for internal continuity.
- Proxy evidence must not be used to claim final client acceptance.

---

## 3) Production validation strategy

Validation proceeds in four gates, each with required evidence and acceptance rules.

### Gate PV-1: Ground-truth data integrity

Objective: establish trusted reference data.

Required actions:
- Freeze exact input drawing set (file hash + timestamp).
- Freeze exact generated outputs under review (file hash + timestamp).
- Confirm client source schedules used for zone area/volume expectations.
- Confirm unit system and conversions (mm/m²/m³ and any imperial conversion).

Exit criteria:
- All reference sources are client-authoritative and traceable.
- No reference field used for acceptance is “proxy” or detector-derived.

### Gate PV-2: Semantic and mapping validation

Objective: confirm each INT zone corresponds to client intent.

Required actions:
- Verify INT label ↔ grid reference ↔ client pour mapping.
- Document any remap table if client naming order differs from deterministic INT sequence.
- Resolve all empty zones into one of:
  - `EXPECTED_EMPTY` (structurally valid empty bay), or
  - `DETECTION_GAP_DOCUMENTED` (with coordinates and rationale).

Exit criteria:
- 100% zones have accepted semantic mapping and disposition.
- No unexplained empty zone remains.

### Gate PV-3: Quantitative geometric validation

Objective: verify detector output quality against independent measurements.

Required actions:
- Perform manual AutoCAD region count per drawing.
- Perform region-level area benchmark on agreed sample.
- Compute precision, recall, area error, and volume error using formulas in Section 5.

Exit criteria:
- All quantitative acceptance thresholds met (Section 6), or documented exception approved by client.

### Gate PV-4: Release readiness and client acceptance packet

Objective: package auditable evidence for client sign-off.

Required actions:
- Produce a final acceptance dossier (tables, screenshots, logs, formulas, results, exceptions).
- Include manifest with SHA-256 for every delivered file.
- Produce final pass/fail verdict for each acceptance criterion.

Exit criteria:
- Product owner and client reviewer sign acceptance, or issue explicit exception list.

---

## 4) Required evidence for client acceptance

The following evidence is mandatory:

1. **Source integrity**
   - Input CAD hashes
   - Output artifact hashes
   - Client source schedule references

2. **Measurement logs**
   - AutoCAD region-count worksheet per drawing
   - AutoCAD area measurement worksheet with region IDs and coordinates
   - Unit conversion notes where needed

3. **Semantic validation**
   - INT-to-client-pour mapping table
   - Empty-zone disposition table with reviewer notes

4. **Metric outputs**
   - Precision, recall, area error, and volume error tables
   - Per-drawing and aggregate summaries

5. **Review artifacts**
   - Annotated DXF screenshots of sampled true positives, false positives, false negatives
   - Evidence of reviewer identity/date/time

6. **Decision record**
   - Final acceptance checklist with pass/fail by criterion
   - Approved exceptions (if any), each with owner and due date

---

## 5) Metric definitions and measurement method

Let:
- `GT` = ground-truth INT regions from client-authoritative measurement
- `Pred` = predicted INT regions from generated output
- `TP` = predicted regions matching GT (by overlap/mapping rule)
- `FP` = predicted regions with no GT match
- `FN` = GT regions with no predicted match

### 5.1 Precision

Formula:
- `Precision = TP / (TP + FP)`

Interpretation:
- “Of all generated INT regions, how many are correct?”

### 5.2 Recall

Formula:
- `Recall = TP / (TP + FN)`

Interpretation:
- “Of all expected client INT regions, how many were found?”

### 5.3 Area error (per zone)

For each matched zone `i`:
- `AreaErrorPct_i = |Area_pred_i - Area_gt_i| / Area_gt_i * 100`

Aggregate:
- max, mean, median, p95 across measured zones.

### 5.4 Volume error (per zone)

For each matched zone `i`:
- `VolumeErrorPct_i = |Volume_pred_i - Volume_gt_i| / Volume_gt_i * 100`

Aggregate:
- max, mean, median, p95 across measured zones.

### 5.5 Matching rule (required for TP/FP/FN)

Use one deterministic rule for the whole validation run:
- Primary key: INT label + validated semantic mapping.
- Geometric sanity check: minimum overlap threshold agreed in advance.
- One-to-one assignment (no many-to-one inflation).

Any unmatched cases are explicitly classified as FP or FN and documented.

---

## 6) Acceptance criteria (production)

These are the recommended thresholds for release readiness unless contractually superseded:

1. **Recall (primary detection gate)**
   - Per drawing: `Recall >= 90%`
   - Aggregate: `Recall >= 92%`

2. **Precision (false-positive control)**
   - Per drawing: `Precision >= 95%`
   - Aggregate: `Precision >= 96%`

3. **Area error (primary geometric gate)**
   - Per measured zone: `AreaErrorPct <= 0.05%`
   - Aggregate: 100% of required benchmark sample within threshold

4. **Volume error**
   - Per measured zone: `VolumeErrorPct <= 0.05%`
   - Aggregate: 100% of required benchmark sample within threshold

5. **Semantic completeness**
   - 100% INT zones have accepted mapping/disposition
   - 0 unexplained empty zones

6. **Evidence quality**
   - 0 proxy-only metrics used for final pass/fail
   - 100% acceptance metrics backed by independent ground-truth evidence

---

## 7) Sampling plan

To avoid biased validation:

- Coverage set: all production drawings in current release scope.
- Per drawing:
  - all zones included in recall/precision matching,
  - targeted area/volume benchmark sample includes:
    - largest zones,
    - smallest valid zones,
    - edge/irregular zones,
    - at least one known difficult zone (prior review flag).
- If any threshold fails:
  - expand sample to full-zone measurement for the affected drawing.

---

## 8) Execution checklist (no code changes)

1. Mark existing proxy fields as `proxy` in all QA tables.
2. Re-run manual ground-truth measurement workflow in AutoCAD.
3. Fill recall/precision matching table with TP/FP/FN classification.
4. Fill area and volume error tables from independent references.
5. Validate semantic mappings and empty-zone dispositions.
6. Compute gate verdicts (PV-1 to PV-4).
7. Assemble final acceptance dossier and seek sign-off.

---

## 9) Final readiness decision framework

Release is **Production-Ready for Client Acceptance** only if:

- All PV gates pass, and
- No acceptance metric is supported solely by proxy evidence.

If not:
- Release remains **Operationally Ready / Acceptance Pending**,
- with a clearly listed blocker set and owners.

---

## 10) Out-of-scope in this phase

- Geometry engine modifications
- Detection logic changes
- New feature implementation
- Heuristic tuning for better metrics

This phase is strictly for validation, acceptance evidence completion, and production readiness determination.

