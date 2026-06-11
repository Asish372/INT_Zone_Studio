# Round 1 Engineer Session Checklist

**Build:** INT Zone Studio · Pilot Evaluation Build v1  
**Package:** `release/INT-Zone-Studio-Pilot-v1/`

## Before session

- [ ] Python 3.10+ installed (`Add to PATH` ticked)
- [ ] `pip install -r requirements.txt` in release folder
- [ ] App opens without engine error
- [ ] Blank copy of `pilot_metrics_template.csv` for this engineer
- [ ] Copy of `pilot_feedback_log.csv` or shared team log
- [ ] Drawing file ready (see `pilot/drawings_manifest.csv`)

## Brief engineer (15 min)

Supported workflow only:

`Import Drawing → Detection → Review → Recovery → Save → Reopen → Export`

Clarify upfront:

| Topic | Say this |
|-------|----------|
| Open Project vs Import | Import = new CAD file. Open = saved `.pjson` workspace. |
| Save | Type full path (e.g. `C:\Projects\name.pjson`) — no file picker yet. |
| Export | Use **Export Project Package** only (not the other 7 options). |
| Re-run Detection | Refreshes view — not a full new detection pass. |

**Primary question:** Did the Suspected Gaps panel get you to a missing cell and was recovery useful?

## During session (observer)

1. Start timer at Import Drawing
2. Do not guide unless stuck > 2 minutes on same step
3. Note verbatim confusion → `pilot_feedback_log.csv`
4. Stop timer at successful Export Project Package

## After session (per drawing)

One row in `pilot_metrics_template.csv`:

- `session_id`, `round=R1`, `engineer`, `drawing_name`
- `total_polygons_detected`, `suspected_gaps_found`
- `recoveries_attempted`, `recoveries_successful`
- `save_success`, `reopen_success`, `export_success` (Y/N)
- `time_to_complete_minutes`
- `gap_panel_useful` (Y/N)
- `confusion_points`, `success_quote` if any

## Do not build during pilot

Note only: Recent Projects, search bar, AI recovery, save file picker, true re-detect.
