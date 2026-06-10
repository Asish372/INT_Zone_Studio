# INT Zone Detection Visualization — Civil Engineer Deliverable

**Purpose:** Show what the software detected on the original slab plan — pour areas grouped into INT zones with final boundaries.

**Client receives one PDF only from this module.**

---

## Client deliverable

| Artifact | Path |
| --- | --- |
| **Detection Visualization PDF** | `output/client_delivery/DETECTION_VISUALIZATION_REPORT.pdf` |

Open in any PDF viewer or print at **A3 landscape**.

---

## PDF contents (per drawing, 9 sheets)

1. **Overview** — 4-step storyboard (input → detected → zones → boundaries)
2. **Detected pour areas** — individual pour cells on the slab plan
3. **Detection coverage** — green = pour area used, gray = not used
4. **Zone detail A** — full-page zoom with INT label and area (m²)
5. **Zone detail B** — full-page zoom
6. **Zone detail C** — full-page zoom
7. **Additional detail** — callouts D and E (2-up)
8. **INT zone map** — colour-coded zones with area (m²) labels
9. **Final pour boundaries** — bold outlines for site marking

No PASS/FAIL gates. No orphan counts. No validation metrics.

---

## Separate pipeline outputs (unchanged)

| Artifact | Purpose |
| --- | --- |
| `*_int_schedule.xlsx` / `.pdf` | QS pour schedule |
| `*_int_zones.dxf` | CAD zone boundaries |
| `*_annotated.dxf` | Detected regions in CAD |

---

## Internal only

| Artifact | Path |
| --- | --- |
| Geometry validation | `output/client_delivery/QA_evidence/geometry_validation/` |
| INT zone gate reports | `output/client_delivery/QA_evidence/*_int_zone_report.md` |
| Intermediate PNGs | `output/detection_visualization/{drawing}/` (build only) |

---

## Regenerate

```bash
python scripts/generate_detection_visualization.py
python scripts/generate_detection_visualization_pdf.py
python scripts/assemble_delivery_package.py
```
