# INT Zone Studio — Pilot Evaluation Build v1

**Freeze tag:** `pilot-v1`  
**Mode:** Pilot Validation (not production release)

---

## What this build is

INT Zone Studio in a controlled evaluation build for real slab-drawing workflows.  
This is **not** a Production Release, Commercial Release, or Enterprise Edition.

---

## Supported workflow

```
Import Drawing
      ↓
Automatic Detection
      ↓
Review
      ↓
Recovery
      ↓
Save Project
      ↓
Reopen Project
      ↓
Export Package
```

Anything outside this path is out of scope for pilot-v1.

---

## Pilot size

### Round 1

| Item | Target |
|------|--------|
| Drawings | 3–5 real slab drawings |
| Users | 1–2 engineers |

**Observe:**

- Was Recovery used?
- Was the Gap panel useful?
- Did Save/Open make sense?
- Which export package format was used?

### Round 2 (only if Round 1 passes)

| Item | Target |
|------|--------|
| Drawings | 10–20 |
| Users | Multiple engineers |

---

## Most valuable data (priority over raw detection %)

```
Suspected Gaps
      ↓
Engineer clicks gap
      ↓
Recover
      ↓
Useful?
```

**Primary success signal:** engineer says the gap list took them directly to the missing cell.

That validates the core audit complaint: finding and fixing gaps without manual hunting.

---

## Metrics to collect per session

| Metric | Notes |
|--------|-------|
| Detection count | Baseline only |
| Suspected gap count | |
| Gap recoveries performed | **Key metric** |
| Save success | |
| Open/reopen success | |
| Export package usage | Which format(s) |
| User confusion points | Verbatim quotes |

Template: copy `pilot_metrics_template.csv` per drawing/session.

---

## Development freeze rules

From `pilot-v1` forward:

| Allowed | Not allowed |
|---------|-------------|
| Crash fixes | New features |
| Data-loss fixes | Architecture changes |
| Pilot feedback fixes | AI additions |
| Small UX polish | Cloud sync work |
| Client language | Menu expansion |

Do not redesign workflows unless pilot users repeatedly fail the same step.

---

## Cursor / agent instruction

> P0 workflow hardening is accepted. Create pilot freeze at `pilot-v1` and stop feature development. Support a controlled pilot on 3–5 real slab drawings. Collect pilot metrics. We are in Pilot Validation Mode — feedback is product-market fit signal, not development feedback.
