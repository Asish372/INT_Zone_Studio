# Test Strategy
## INT Zone Studio — Windows Desktop Application

| Field | Value |
| --- | --- |
| **Document title** | INT Zone Studio — Test Strategy |
| **Version** | 1.0 |
| **Status** | Approved for implementation |
| **Date** | 6 June 2026 |
| **Classification** | Internal / Confidential |
| **Platform** | Windows 10/11 x64 |
| **Parent documents** | [PRD_Desktop_Application.md](PRD_Desktop_Application.md), [06_IMPLEMENTATION_PLAN.md](06_IMPLEMENTATION_PLAN.md), [04_DOMAIN_MODEL.md](04_DOMAIN_MODEL.md), [client_validation_package.md](client_validation_package.md), [ARCHITECTURE_DESKTOP_APPLICATION.md](ARCHITECTURE_DESKTOP_APPLICATION.md), [03_Backend_Schema.md](03_Backend_Schema.md), [UIUX_Specification_Desktop.md](UIUX_Specification_Desktop.md) |

---

## Document purpose

This document defines the **quality assurance strategy** for INT Zone Studio v1.0: test layers, golden fixtures, CI release gates, E2E journeys, performance benchmarks, and defect severity. It complements existing engine tests in `tests/` with a new `tests/desktop/` suite.

**Quality objectives:**

1. **Export parity** — CLI and desktop outputs match for identical inputs (NFR-12).
2. **Zero smoke crashes** — J33A, J33B, S111_A complete without crash (NFR-04).
3. **Acceptance workflow completeness** — Phases A–E achievable in-app (PRD §1.5).
4. **Engine immutability** — No undetected changes to frozen `src/` baseline.

---

## 1. Test pyramid

```
                    ┌─────────────┐
                    │  E2E / UI   │  Playwright + manual QA
                    │  (few)      │
                ┌───┴─────────────┴───┐
                │ Integration + Parity │  Sidecar, export, IPC
                │ (moderate)           │
            ┌───┴─────────────────────┴───┐
            │ Contract + Domain unit       │  Schemas, policies, serializers
            │ (many)                       │
        ┌───┴─────────────────────────────┴───┐
        │ Engine unit (existing pytest)        │  src/ frozen regression
        └─────────────────────────────────────┘
```

| Layer | Scope | Tools | Location |
| --- | --- | --- | --- |
| **L1 — Engine unit** | Parser, gap handler, zone engine, exporters | pytest | `tests/test_*.py` |
| **L2 — Domain unit** | Acceptance/export policies, path validation, DTO mappers | Vitest, pytest | `desktop/app/src/domain/__tests__/`, `tests/desktop/test_domain_*.py` |
| **L3 — Contract** | IPC JSON Schema, result DTO ↔ `IntZonePipelineResult` | pytest + jsonschema | `tests/desktop/test_ipc_contract.py` |
| **L4 — Integration** | Sidecar run + export on golden drawings | pytest subprocess | `tests/desktop/test_sidecar_integration.py` |
| **L5 — Parity** | Headers, row counts, gate table vs CLI baseline | pytest hash fixtures | `tests/desktop/test_export_parity.py` |
| **L6 — E2E** | J1–J5 user journeys | Playwright (Tauri) | `tests/desktop/e2e/` |
| **L7 — Performance** | Engine time, viewer FPS, scene load | Custom scripts | `tests/desktop/bench_*.py` |
| **L8 — Installer** | Clean VM MSI smoke | CI weekly + manual | `tests/desktop/installer/` |
| **L9 — Accessibility** | WCAG 2.1 AA core flows | axe-core in Playwright | `tests/desktop/e2e/a11y/` |

---

## 2. Golden fixtures

### 2.1 Drawing set

| Fixture ID | Drawing | Manifest | Zones | Purpose |
| --- | --- | --- | ---: | --- |
| **GF-S111-A** | S111_A.dxf / .dwg | `reference/s111_a_zones_manifest.yaml` | 24 | Happy path J1; primary parity baseline |
| **GF-J33A** | Warehouse Rev_F | `reference/j33a_zones_manifest.yaml` | 24 | Smoke NFR-04 |
| **GF-J33B** | S111_J | `reference/j33b_zones_manifest.yaml` | 17 | Joint profile |
| **GF-S111-J** | S111_J | J33B manifest | 17 | INT-8 variance (0.207% adjudication) |

### 2.2 Baseline capture procedure

Run once per engine version bump; store under `tests/desktop/fixtures/{fixture_id}/`:

```
tests/desktop/fixtures/s111_a/
├── cli/
│   ├── result_gates.json          # gate name + status + detail
│   ├── int_schedule_headers.json  # Excel row 1
│   ├── int_schedule_row_count.txt
│   ├── zone_report_gates.md       # extracted gate table
│   └── file_hashes.sha256         # all export artifacts
├── sidecar/
│   └── (same structure — populated in P0)
└── README.md                      # capture date, engine version, command used
```

**Capture command:**

```powershell
python scripts/run_int_zone_pipeline.py `
  --input reference/S111_A.dxf `
  --manifest reference/s111_a_zones_manifest.yaml `
  --output output/baseline_s111_a
python tests/desktop/scripts/capture_golden.py --fixture s111_a --source output/baseline_s111_a
```

### 2.3 Parity comparison rules

| Artifact | Match criterion |
| --- | --- |
| `*_int_schedule.xlsx` | Header row exact string match; data row count = zones + 1 totals row |
| `*_int_zone_report.md` | Gate table: name, status, detail (normalized whitespace) |
| `result.json` gates | Same names and statuses as CLI serialized gates |
| `*_int_zones.dxf` | Layers INT_ZONES, INT_LABELS present; entity count within tolerance |
| `*_annotated.dxf` | Layer DETECTED_REGIONS present |
| Sign-off PDF | **Not parity-scoped** — UI additive only |

Numeric cell values: compare at 4 decimal places; fail if any Δ > 1e-6 m² unless documented engine float variance.

---

## 3. Test suites by phase

Aligned with [06_IMPLEMENTATION_PLAN.md](06_IMPLEMENTATION_PLAN.md):

| Phase | Required tests before exit |
| --- | --- |
| P0 | `test_ipc_contract`, `test_result_schema`, golden gate match S111_A |
| P1 | `test_project_schema`, wizard integration (mock IPC) |
| P2 | `test_run_staging`, `test_audit_log`, cancel integration |
| P3 | `bench_viewer_fps`, selection sync e2e stub |
| P4 | `test_dto_to_table_mapping`, report section presence |
| P5 | `test_acceptance_policy`, `test_export_policy`, checklist persistence |
| P6 | `test_export_parity` all golden fixtures |
| P7 | `test_batch_queue`, `test_portfolio_rollup` |
| P8 | installer smoke, a11y, full e2e J1–J5 |

---

## 4. CI release gates (blockers)

All must pass on `main` before v1.0 tag:

| Gate ID | Command / check | Blocks release |
| --- | --- | --- |
| **RG-01** | `pytest tests/ -v --tb=short` | Yes |
| **RG-02** | `pytest tests/desktop/ -v` | Yes |
| **RG-03** | Export parity: S111_A, J33A, J33B headers + row counts | Yes |
| **RG-04** | No `src/` diff without `[freeze-exception]` in commit message | Yes |
| **RG-05** | `npm test` + `npm run build` in `desktop/app/` | Yes |
| **RG-06** | `cargo test` in `desktop/app/src-tauri/` | Yes |
| **RG-07** | E2E J1 happy path (Playwright) | Yes |
| **RG-08** | Install size report < 500 MB or documented waiver | Yes |
| **RG-09** | axe-core: zero critical violations on S03, S06, S12 | Yes |
| **RG-10** | Manual smoke sign-off J33A/J33B/S111_A | Yes (QA) |

### 4.1 CI workflow (GitHub Actions outline)

```yaml
# .github/workflows/desktop-ci.yml (conceptual)
jobs:
  engine-tests:
    runs-on: windows-latest
    steps:
      - run: pytest tests/ -v
  desktop-tests:
    needs: engine-tests
    steps:
      - run: pytest tests/desktop/ -v
      - run: npm ci && npm test --prefix desktop/app
  parity:
    needs: desktop-tests
    steps:
      - run: pytest tests/desktop/test_export_parity.py -v
  e2e:
    needs: parity
    if: github.ref == 'refs/heads/main'
    steps:
      - run: npm run e2e --prefix desktop/app
```

---

## 5. Domain policy tests

Pure unit tests for [04_DOMAIN_MODEL.md](04_DOMAIN_MODEL.md) §7 policies.

### 5.1 AcceptanceEligibilityPolicy

| Case | Input | Expected |
| --- | --- | --- |
| AC-01 | `orphan_faces` FAIL, target `accepted` | `allowed: false` |
| AC-02 | All gates PASS, checklist complete | `allowed: true` |
| AC-03 | `manifest_area` FAIL + adjudication Accept computed | `allowed: true` |
| AC-04 | Checklist row FAIL, no adjudication | `allowed: false` |
| AC-05 | Only REVIEW gates, checklist confirmed | `allowed: true` |
| AC-06 | `rejected` without notes | `allowed: false` |

### 5.2 ExportEligibilityPolicy

| Case | Expected |
| --- | --- |
| EX-01 | No active run → block all export |
| EX-02 | Successful run, not accepted → bundle with banner |
| EX-03 | Sign-off PDF without questionnaire → block |

### 5.3 Exception classification

Verify gate → classification mapping matches UIUX §7.5:

| Gate | Classification |
| --- | --- |
| `orphan_faces` FAIL | blocking |
| `manifest_area` FAIL | blocking |
| `zone_count` REVIEW | review |
| `face_sum_vs_union` REVIEW | informational |

---

## 6. IPC and contract tests

### 6.1 Schema validation

Every sidecar response validated against:

- `desktop/schemas/ipc.v1.schema.json`
- `desktop/schemas/result.v1.schema.json`
- `desktop/schemas/project.v1.schema.json`

### 6.2 Method coverage

| Method | Tests |
| --- | --- |
| `engine.getInfo` | Returns version, freeze date, capabilities |
| `engine.inspectDrawing` | Valid DXF; ODA_NOT_CONFIGURED for DWG without ODA |
| `engine.runDetection` | Success + progress notifications; ENGINE_RUN_FAILED on corrupt file |
| `engine.exportArtifacts` | Each format flag; EXPORT_VERIFICATION_FAILED on mock mismatch |
| `engine.cancelRun` | Cancel mid-run; prior result preserved |

### 6.3 DTO field completeness

Assert `result.json` zones include all fields required for UIUX T1–T3:

```
label, area_m2, volume_m3, face_count, grid_ref, bay_coverage_pct,
face_sum_area_m2, clipped_bay_area_m2, detection_tier, polygonGeoJson
```

Cross-reference [`IntZoneData`](src/zone_engine/models.py).

---

## 7. E2E test scenarios (J1–J5)

Tool: Playwright driving Tauri WebView (or `@tauri-apps/api` test harness).

| Journey | ID | Steps | Success assertion |
| --- | --- | --- | --- |
| **J1** | E2E-J1 | New project → S111_A → run → map spot-check → export bundle | Export folder exists; headers match golden; elapsed < 15 min engineer time (manual timing) |
| **J2** | E2E-J2 | Portfolio 3 drawings → checklist 65 zones → sign-off | Acceptance = Accepted; sign-off PDF exists |
| **J3** | E2E-J3 | Open S111_J → exception inbox → INT-8 adjudication | Disposition persisted in `adjudications.json` |
| **J4** | E2E-J4 | Batch 3 DWGs → Run All | 3 Complete rows; failed file does not block |
| **J5** | E2E-J5 | Re-import DWG → run → compare runs | Delta column shows gate changes |

### 7.1 E2E environment

| Requirement | Value |
| --- | --- |
| OS | Windows 11 x64 clean VM or CI runner |
| ODA | Pre-installed or use DXF-only path for CI |
| Data | Golden fixtures from `reference/` |
| Isolation | `%TEMP%/intzone-e2e-{runId}/` project dirs |

---

## 8. Performance benchmarks

### 8.1 Engine runtime

| Fixture | Max wall time (reference HW) | PRD ref |
| --- | --- | --- |
| S111_A | 120 s | NFR-02 order of magnitude |
| J33A | 120 s | |
| Batch 3 files | 360 s sequential | |

Reference HW: 8-core CPU, 16 GB RAM, NVMe SSD (document actual machine in benchmark README).

### 8.2 Viewer

| Metric | Target | Measurement |
| --- | --- | --- |
| Pan/zoom FPS | ≥ 30 | `bench_viewer_fps.py` — 10 s interaction trace |
| Scene load time | ≤ 3 s | Time to first frame S111_A |
| Zone filter | < 100 ms | 65 zones search (FR-18) |

### 8.3 UI responsiveness

| Action | Max block |
| --- | --- |
| UI thread during run | 200 ms (FR-10) |
| Tab switch | 100 ms |

---

## 9. Installer smoke test

**Frequency:** Weekly on `main`; mandatory before release.

| Step | Verification |
| --- | --- |
| 1 | Clean Win11 VM — no prior install |
| 2 | Run signed MSI silent or interactive |
| 3 | Launch INT Zone Studio |
| 4 | Import S111_A.dxf (no ODA required) |
| 5 | Run detection to completion |
| 6 | Export full delivery bundle |
| 7 | Verify 7 artifact types in output folder |
| 8 | Uninstall leaves user projects intact |

**Script location:** `tests/desktop/installer/smoke_checklist.ps1`

---

## 10. Accessibility testing

**Standard:** WCAG 2.1 Level AA on core flows (NFR-10).

| Flow | Screens | Checks |
| --- | --- | --- |
| New project + run | S02, S03, S05 | Keyboard nav, focus visible, labels |
| Zone review | S06, S07 | Table arrow keys, status text not color-only |
| Export | S12 | Form labels, error announcements |

**Tool:** `@axe-core/playwright` — fail CI on `critical` or `serious` violations.

**Manual:** NVDA spot-check on S07 zone list and S11 checklist.

---

## 11. Manual QA matrix

Maps to [client_validation_package.md](client_validation_package.md) and acceptance review kit.

| Kit phase | Manual test | Automated overlap |
| --- | --- | --- |
| A — Orientation | Freeze notice readable; 65/65 summary | — |
| B — Visual | All INT labels on map | E2E-J2 partial |
| C — Schedule | Excel vs structural PDF | Parity RG-03 |
| D — Adjudication | INT-8 worksheet | E2E-J3 |
| E — Sign-off | PDF matches form 08 | Manual compare |

### 11.1 Regression policy

| Change type | Required tests |
| --- | --- |
| Engine version bump | Full `tests/` + re-capture all golden fixtures |
| App-only UI change | Vitest + affected e2e |
| IPC schema change | Contract tests + app version bump |
| ExportGateway change | Full parity suite |

**Rule:** App may ship without engine change; engine change requires app compatibility verification.

---

## 12. Defect severity

| Severity | Definition | Example | Release blocker? |
| --- | --- | --- | --- |
| **S1 — Critical** | Crash, data loss, export mismatch | Wrong SQM in Excel vs CLI | Yes |
| **S2 — Major** | Feature broken, blocking FAIL ignored | Accepted allowed with orphan FAIL | Yes |
| **S3 — Minor** | Workaround exists | Wrong tab restored on reopen | No |
| **S4 — Trivial** | Cosmetic | 1 px alignment | No |

Export header mismatch is always **S1**.

---

## 13. Test data management

| Rule | Detail |
| --- | --- |
| Client drawings | Store in `reference/`; no secrets in repo |
| Generated output | CI uses `%TEMP%`; never commit `output/` from tests |
| PII | Reviewer names in tests use fixtures only |
| Large files | Git LFS if DWGs exceed 10 MB |

---

## 14. Responsibilities

| Role | Responsibility |
| --- | --- |
| **Engineering** | Unit, contract, integration tests; fix failures |
| **QA** | E2E scripts, manual kit walkthrough, release sign-off RG-10 |
| **DevOps** | CI pipeline, installer smoke schedule |
| **Architecture** | Golden fixture approval on engine bump |

---

## 15. Traceability

| PRD | Test coverage |
| --- | --- |
| FR-08–FR-13 | IPC integration, cancel tests |
| FR-14–FR-20 | Viewer bench, selection e2e |
| FR-21–FR-25 | Report section tests |
| FR-26–FR-32 | Policy tests AC-* |
| FR-33–FR-41 | Parity RG-03 |
| FR-42–FR-44 | E2E-J4, portfolio unit tests |
| NFR-04 | Smoke GF-J33A/B, GF-S111-A |
| NFR-08 | Audit log integration |
| NFR-10 | axe-core RG-09 |
| NFR-12 | Parity suite |

---

## 16. References

| Document | Use |
| --- | --- |
| [06_IMPLEMENTATION_PLAN.md](06_IMPLEMENTATION_PLAN.md) | Phase exit tests |
| [04_DOMAIN_MODEL.md](04_DOMAIN_MODEL.md) | Policy test cases |
| [ARCHITECTURE_DESKTOP_APPLICATION.md](ARCHITECTURE_DESKTOP_APPLICATION.md) | IPC methods |
| [03_Backend_Schema.md](03_Backend_Schema.md) | Engine models |
| [UIUX_Specification_Desktop.md](UIUX_Specification_Desktop.md) | Tables T1–T7 |
| [output/client_delivery/QA_evidence/export_verification.md](output/client_delivery/QA_evidence/export_verification.md) | Header contract |

---

*END OF TEST STRATEGY*  
*INT Zone Studio — Desktop Application | v1.0 | June 2026*
