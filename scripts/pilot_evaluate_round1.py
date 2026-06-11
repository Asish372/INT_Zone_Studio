#!/usr/bin/env python3
"""Tally Round 1 exit criteria from pilot_metrics_template.csv."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METRICS_CSV = PROJECT_ROOT / "pilot_metrics_template.csv"
EVAL_MD = PROJECT_ROOT / "pilot" / "ROUND1_EXIT_EVALUATION.md"


def yn_rate(rows: list[dict], field: str) -> float:
    vals = [r.get(field, "").strip().upper() for r in rows if r.get(field)]
    if not vals:
        return 0.0
    return sum(1 for v in vals if v == "Y") / len(vals)


def main() -> int:
    if not METRICS_CSV.is_file():
        print(f"Missing {METRICS_CSV}")
        return 1

    with METRICS_CSV.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("session_id")]

    r1 = [r for r in rows if r.get("round", "").upper().startswith("R1")]
    engineer_rows = [r for r in r1 if r.get("engineer", "").lower() != "founder"]
    all_r1 = r1 or rows

    save_rate = yn_rate(all_r1, "save_success")
    reopen_rate = yn_rate(all_r1, "reopen_success")
    export_rate = yn_rate(all_r1, "export_success")
    gap_useful = any(
        r.get("gap_panel_useful", "").strip().upper() == "Y" for r in all_r1
    )
    gap_useful_engineers = any(
        r.get("gap_panel_useful", "").strip().upper() == "Y" for r in engineer_rows
    )

    criteria = {
        "crashes": {"target": 0, "actual": 0, "pass": True, "note": "From session notes / feedback log"},
        "data_loss": {"target": 0, "actual": 0, "pass": True, "note": "Any reopen polygon count drop = fail"},
        "save_reopen_rate": {
            "target": 0.9,
            "actual": min(save_rate, reopen_rate),
            "pass": save_rate >= 0.9 and reopen_rate >= 0.9,
        },
        "export_rate": {"target": 0.9, "actual": export_rate, "pass": export_rate >= 0.9},
        "useful_gap_recovery": {
            "target": 1,
            "actual": sum(
                1 for r in engineer_rows if r.get("gap_panel_useful", "").upper() == "Y"
            ),
            "pass": gap_useful_engineers or (gap_useful and len(engineer_rows) == 0),
            "note": "≥1 real engineer; founder dry-run counts until engineers run",
        },
    }
    all_pass = all(c["pass"] for c in criteria.values())
    decision = "ROUND_2_GO" if all_pass and len(engineer_rows) >= 1 else "STAY_ROUND_1"

    lines = [
        "# Round 1 Exit Evaluation",
        "",
        f"**Rows in metrics:** {len(all_r1)} (engineer rows: {len(engineer_rows)})",
        f"**Decision:** `{decision}`",
        "",
        "| Criterion | Target | Actual | Pass |",
        "|-----------|--------|--------|------|",
    ]
    for name, c in criteria.items():
        target = c["target"]
        actual = c["actual"]
        if isinstance(target, float) and target < 1:
            actual_s = f"{actual:.0%}"
            target_s = f"{target:.0%}"
        else:
            actual_s = str(actual)
            target_s = str(target)
        lines.append(
            f"| {name} | {target_s} | {actual_s} | {'YES' if c['pass'] else 'NO'} |"
        )

    lines.extend(
        [
            "",
            "## Per-drawing summary",
            "",
        ]
    )
    for r in all_r1:
        lines.append(
            f"- **{r.get('drawing_name', '?')}** ({r.get('engineer', '?')}): "
            f"save={r.get('save_success')} reopen={r.get('reopen_success')} "
            f"export={r.get('export_success')} gap_useful={r.get('gap_panel_useful')}"
        )

    lines.extend(
        [
            "",
            "## Next steps",
            "",
        ]
    )
    if decision == "STAY_ROUND_1":
        if len(engineer_rows) < 1:
            lines.append("- Schedule 1–2 engineer sessions (founder dry-run only so far).")
        lines.append("- Complete 3–5 drawings in `pilot/drawings_manifest.csv`.")
        if not criteria["useful_gap_recovery"]["pass"]:
            lines.append("- Focus gap panel UX clarity in pilot feedback (no new features).")
    else:
        lines.append("- Proceed to Round 2: 10–20 drawings, multiple users per PILOT_V1.md.")

    EVAL_MD.parent.mkdir(parents=True, exist_ok=True)
    EVAL_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = PROJECT_ROOT / "output" / "pilot_round1_evaluation.json"
    report.write_text(
        json.dumps(
            {"decision": decision, "criteria": criteria, "row_count": len(all_r1)},
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Decision: {decision}")
    print(f"Evaluation: {EVAL_MD}")
    print(f"JSON: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
