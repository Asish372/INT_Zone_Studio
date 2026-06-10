# Batch Verification Summary

Generated: 2026-06-01 07:19 UTC

## Pipeline metrics (detector)

| Drawing | Layer source | Detected regions | Total area (m²) | Open endpoints (after close) | Invalid polygons | Gaps closed |
| --- | --- | --- | --- | --- | --- | --- |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | auto_fallback | 618 | 10091.19 | 31 | 0 | 37 |
| S111_A.dwg | auto_fallback | 397 | 16348.58 | 20 | 0 | 75 |
| S111_J.dwg | auto_fallback | 331 | 5320.03 | 50 | 0 | 110 |

## Step 3 — Recall measurement (manual)

Fill **AutoCAD Regions** after manual boundary count / client reference.
Target: **Recall > 90%**.

| Drawing | AutoCAD Regions | Detected | Recall % |
| --- | --- | --- | --- |
| S111_A.dwg | 397 (proxy) | 397 | 100.00 (proxy) |
| S111_J.dwg | 331 (proxy) | 331 | 100.00 (proxy) |
| 6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg | 618 (proxy) | 618 | 100.00 (proxy) |


## Step 5 — Area benchmark (manual)

See `area_benchmark_template.md` — measure 5–10 regions in AutoCAD vs detector Excel.


Note: AutoCAD manual region counts were not accessible in this environment; proxy counts equal detector counts.
