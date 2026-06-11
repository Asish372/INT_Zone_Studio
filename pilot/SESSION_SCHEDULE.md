# Round 1 Session Schedule

**Status:** Prepared — awaiting engineer availability  
**Package:** `release/INT-Zone-Studio-Pilot-v1/`

| Session | Engineer | Date | Drawings | Metrics file | Status |
|---------|----------|------|----------|--------------|--------|
| S1 | Engineer A (TBD) | TBD | Drawing 1–2 | copy `pilot_metrics_template.csv` | pending |
| S2 | Engineer B (TBD) | TBD | Drawing 3–5 | copy `pilot_metrics_template.csv` | pending |

## Founder dry-run (complete)

| Drawing | Result |
|---------|--------|
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf | save/reopen/export Y; 618 polygons; 18 INT zones; 0 gaps on this drawing |

**Note:** Gap usefulness signal needs a drawing with suspected gaps — prioritize drawings 2–5 that show recoverable gaps in validation.

## After each session

1. Append rows to `pilot_metrics_template.csv`
2. Append confusion to `pilot_feedback_log.csv`
3. Run: `python scripts/pilot_evaluate_round1.py`
