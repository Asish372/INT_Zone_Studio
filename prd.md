# Product Requirements Document
## DXF CAD Room Detection & Area Calculation System

**Version:** 1.0
**Status:** Draft
**Date:** May 31, 2026
**Classification:** Internal / Confidential

---

## 1. Document Information

| Field | Details |
|---|---|
| Document Title | DXF CAD Room Detection & Area Calculation System – PRD |
| Version | 1.0 |
| Status | Draft |
| Date | May 31, 2026 |
| Project Type | Engineering Automation / CAD Processing Software |
| Tech Stack | Python, ezdxf, Shapely, pandas, matplotlib |
| Target Platform | Windows / macOS / Linux (Desktop Application or CLI Tool) |

---

## 2. Executive Summary

Civil and structural engineers working on warehouse, industrial, and commercial projects currently spend significant time manually identifying room or slab boundaries in AutoCAD (DXF/DWG) drawings and calculating their areas. This repetitive manual process is error-prone, time-consuming, and does not scale when a project has dozens or hundreds of enclosed spaces.

This product automates that workflow. Given a DXF CAD file containing structural elements such as walls, beams, slabs, doors, and shutters, the system will automatically detect all enclosed regions, calculate their areas and volumes, label them, and export the results into a structured format (DXF + Excel/CSV).

> **One-Line Summary:** "Give the software a DXF drawing — it detects every enclosed slab/room, calculates area and concrete volume, and exports a ready-to-use report."

---

## 3. Problem Statement

### 3.1 Current Manual Workflow

An engineer with a warehouse CAD drawing currently follows these steps:

1. Open drawing in AutoCAD
2. Manually select a region boundary
3. Use the AREA command to measure
4. Record area value in Excel
5. Compute volume (area × slab thickness) manually
6. Repeat for every room / slab section

> **The Scale Problem:** For a warehouse with 100 slab sections, the manual process requires 100+ repetitions of the same steps. This takes hours, is error-prone, and cannot be audited easily.

### 3.2 Root Cause

- No automated tool exists to extract closed regions from DXF files reliably
- Door and shutter openings break the geometric boundary of rooms, making auto-detection non-trivial
- Engineers must bridge the gap between CAD tools and quantity estimation manually

---

## 4. Goals & Objectives

### 4.1 Primary Goals

- Automate detection of enclosed regions (rooms/slabs) from DXF CAD files with **maximum recall** — every valid enclosed slab/room on clean drawings should be found; occasional human review of edge cases is acceptable
- Calculate the area and concrete volume for each detected region to **quantity-surveying precision** (target ≤ 0.05% deviation from AutoCAD AREA)
- Export results in both DXF (labelled drawing) and Excel/CSV (report) formats
- Handle door/shutter gaps intelligently without requiring manual boundary redraw

### 4.2 Secondary Goals

- Support multiple DXF files in batch mode (per project)
- Produce a clean, professional output ready to share with project stakeholders
- Allow user configuration of slab thickness, layer names, and tolerance values

---

## 5. Stakeholders

| Role | Responsibility | Interest |
|---|---|---|
| Client / Product Owner | Defines requirements, provides sample DXF files | Fast & accurate area reports |
| Civil / Structural Engineer (End User) | Uses the software daily on real projects | Reduces manual work, fewer errors |
| Developer | Builds and maintains the system | Clear specs, clean architecture |
| QA / Tester | Validates output accuracy against known areas | Reliable, reproducible results |

---

## 6. User Stories

### 6.1 Primary User Stories

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-01 | Engineer | Upload a DXF file and get all enclosed regions automatically detected | I don't have to manually trace boundaries in AutoCAD |
| US-02 | Engineer | See the calculated area of each detected slab/room | I can directly use it for material estimation |
| US-03 | Engineer | Get concrete volume = area × thickness for each region | I can immediately place concrete orders |
| US-04 | Engineer | Have the software handle door/shutter gaps automatically | I don't have to close every boundary manually |
| US-05 | Engineer | Export results to Excel with Room ID, Area, Volume | I can share the report with the project team |
| US-06 | Engineer | Get an annotated DXF file with region labels and areas | I can review the output inside AutoCAD |
| US-07 | Engineer | Set custom slab thickness per file or per run | I can handle different slab types in the same project |
| US-08 | Project Manager | See a total area summary across all detected regions | I can track overall quantities at project level |

---

## 7. Functional Requirements

| ID | Feature | Priority | Description |
|---|---|---|---|
| FR-01 | File Input | Must | System shall accept `.dxf` files as input. DWG files must be pre-converted to DXF before processing. |
| FR-02 | Layer Configuration | Must | System shall allow the user to specify which DXF layers contain walls, beams, slabs, and boundaries. |
| FR-03 | Entity Extraction | Must | System shall extract LINE, LWPOLYLINE, and ARC entities from the specified layers. |
| FR-04 | Polygon Construction | Must | System shall construct closed polygons (rooms/slabs) from extracted entities using a polygonization algorithm. |
| FR-05 | Gap Detection & Closure | Must | System shall detect and automatically close small gaps (e.g. door openings ≤ configurable threshold) in boundary lines. |
| FR-06 | Area Calculation | Must | System shall calculate the area of each detected closed polygon in square metres (m²). |
| FR-07 | Volume Calculation | Must | System shall calculate volume = area × slab thickness (user-configurable, default 0.15 m) for each region. |
| FR-08 | Region Labelling | Must | System shall assign an auto-incremented label (Room 1, Room 2… or Slab 1, Slab 2…) to each detected region. |
| FR-09 | Centroid Placement | Must | System shall place text labels at the centroid of each detected polygon in the output DXF. |
| FR-10 | DXF Export | Must | System shall export an annotated DXF file with polygon boundaries drawn and labels placed. |
| FR-11 | Excel/CSV Export | Must | System shall export an Excel/CSV report with: Region ID, Area (m²), Perimeter (m), Volume (m³), Centroid coordinates. |
| FR-12 | Summary Report | Should | System shall produce a summary row with total area and total volume across all detected regions. |
| FR-13 | Batch Processing | Should | System shall support processing multiple DXF files in a single run, producing individual and combined reports. |
| FR-14 | Minimum Area Filter | Should | System shall allow filtering out regions smaller than a configurable minimum area (e.g. ignore regions < 1 m²). |
| FR-15 | Visual Preview | Could | System could display a matplotlib/plotly preview of detected regions before export. |
| FR-16 | Configuration File | Could | System could accept a JSON/YAML config file for all user settings (layers, thickness, tolerance, output format). |

---

## 8. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Performance | Process a DXF file with up to 10,000 entities in under 30 seconds on a standard laptop (8GB RAM, modern CPU). |
| NFR-02 | Accuracy | Area calculation must match AutoCAD's AREA command result within **±0.05%** for clean drawings (quantity-surveying grade). |
| NFR-02a | Detection recall | On clean drawings, system shall detect **100% of enclosed slab/room regions** that AutoCAD would close with the same boundary layers and gap rules; near-term acceptance ≥ 90% with documented gaps, long-term target full coverage with optional human confirmation for ambiguous openings. |
| NFR-03 | Reliability | System must not crash on malformed DXF. Unknown entities must be skipped with a warning, not an exception. |
| NFR-04 | Usability | A CLI interface must be provided. An optional GUI (Tkinter/PyQt) is desirable for non-technical users. |
| NFR-05 | Portability | System must run on Windows 10+, macOS 12+, and Ubuntu 20.04+ without additional OS-level dependencies. |
| NFR-06 | Maintainability | Code must follow PEP-8, be fully commented, and have at least 70% unit test coverage. |
| NFR-07 | Configurability | All thresholds (gap tolerance, min area, slab thickness) must be user-configurable, not hardcoded. |
| NFR-08 | Logging | System must produce a detailed log file for each run showing: entities read, polygons found, errors skipped. |

---

## 9. Out of Scope (V1.0)

- 3D slab detection or volumetric analysis from 3D DXF models
- Direct DWG file reading without prior conversion to DXF
- AI-based room classification (e.g. "kitchen", "storeroom") — only numeric labels in V1.0
- Real-time AutoCAD plugin or integration
- Cloud deployment or web-based interface
- Multi-user / collaborative features
- Structural analysis, load calculations, or BIM integration

---

## 10. Success Metrics

| Metric | Near-term target | Long-term target | Measurement Method |
|---|---|---|---|
| Detection recall | ≥ 90% of rooms/slabs on clean drawings | **100%** — every enclosed region detected | Manual comparison with AutoCAD boundary trace; log missed regions and unresolved gaps |
| Detection precision | Minimize false regions (columns, hatching noise) | Fully accurate block boundaries; human assist OK for ambiguous doors | Review annotated DXF vs source |
| Area accuracy | ≤ 0.05% deviation from AutoCAD AREA | ≤ **0.05%** (maintain) | Benchmark polygons + sample project DWGs (`S111_A`, `S111_J`, warehouse slab) |
| Processing Speed | < 30 seconds per DXF file (up to 10k entities) | Same | Automated timing test |
| Gap handling | ≥ 80% of door/shutter gaps auto-closed | ≥ 95% within `gap_threshold` | Test set with annotated gap drawings |
| Export completeness | 100% of detected regions in Excel + DXF | Same | Output validation script |
| Crash rate | 0 crashes on provided sample files | Same | Smoke test suite |

**Detection philosophy:** Prefer **missing nothing** over aggressive filtering. Use `accuracy.detection_mode: exhaustive` in config (default) and tune `wall_layers` / `gap_threshold` per project. Engineers may confirm or exclude regions in a future review step; V1.0 exports all detected regions for transparency.

---

## 11. Timeline & Milestones

| Phase | Milestone | Duration | Deliverable |
|---|---|---|---|
| Phase 1 – POC | DXF reading + entity extraction working | 1–2 days | Script that prints all entities from sample DXF |
| Phase 2 – Detection | Basic polygon/region detection working | 2–4 days | Console output: list of detected regions with area |
| Phase 3 – Gap Fixing | Door/shutter gap handling implemented | 3–5 days | Improved detection on real sample files |
| Phase 4 – Export | DXF + Excel export functional | 2–3 days | Annotated DXF file + Excel report |
| Phase 5 – Testing | Accuracy validated on all sample DXF files | 2–3 days | Test report with accuracy metrics |
| Phase 6 – Polish | CLI / GUI, config file, logging, documentation | 3–5 days | Production-ready release |

**Total Estimated Duration:** 13–22 days

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DXF drawings are messy / inconsistent | High | High | Build robust tolerance settings; allow manual layer selection |
| Door gaps are larger than configurable threshold | Medium | High | Allow per-file gap threshold override; provide manual gap-close tool |
| Polygonization produces false positives | Medium | Medium | Add minimum area filter; allow user to review/confirm regions |
| Client DXF files use non-standard layer naming | High | Medium | Make layer names fully configurable in config file |
| Performance degradation on very large DXF files | Low | Medium | Implement spatial indexing with Shapely STRtree |

---

*END OF PRODUCT REQUIREMENTS DOCUMENT*
*DXF CAD Room Detection System | v1.0 | May 2026*