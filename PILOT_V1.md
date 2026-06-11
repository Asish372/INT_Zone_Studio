# INT Zone Studio — Pilot Evaluation Build v1

**Version:** `v0.1.0-pilot.1`  
**Freeze tag:** `pilot-v1`  
**Mode:** Pilot Validation (not production release)

---

## Milestone (accepted)

| Item | Status |
|------|--------|
| Repo in git | Done |
| `pilot-v1` tag | Done |
| Freeze rules formalized | Done |

P0 workflow hardening is accepted. Feature development stops here.  
Next meaningful data comes from **real engineers**, not code.

---

## What this build is

INT Zone Studio in a controlled evaluation build for real slab-drawing workflows.  
This is **not** a Production Release, Commercial Release, or Enterprise Edition.

**Say:** INT Zone Studio · Pilot Evaluation Build v1

---

## Supported workflow (only)

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

## Primary validation signal (most important)

**Not** raw detection count.

```
Suspected Gap
      ↓
Engineer clicked
      ↓
Recovered successfully
      ↓
Useful?
```

If this chain works consistently, the biggest audit blocker is solved.

**Success quote:** *"Gap list ne mujhe directly missing cell tak pahucha diya"*

Do not optimize detection accuracy in isolation — optimize **gap-to-recovery usefulness** for real engineers.

---

## Known limitation — INT Zone count in Studio

**Generate Zones** in Pilot Evaluation Build v1 uses a **placeholder** aggregator (`workspace_zones.py`), not the authoritative `build_int_zone_pipeline`.

| Source | INT zone count (warehouse example) | Authoritative? |
|--------|-----------------------------------|----------------|
| Studio UI (Generate Zones) | 18 | **No** |
| CLI / `*_int_zone_report.md` | 24 | **Yes** |
| Slab schedule / manifest | 24 | **Yes** |

Stage 1 detection is aligned (618 micro-faces CLI = Studio). Divergence is **Stage 2 only**.

**For pilot metrics and Round 1 exit evaluation:** do not fail or pass on Studio INT zone count. Use CLI INT zone report for schedule comparison. Note engineer confusion if they compare Studio zones to schedule.

See: `docs/research/v2_north_star_int_zones.md`, `docs/research/studio_zone_engine_alignment.md`.

---

## Round 1 — scientific capture

**Size:** 3–5 drawings · 1–2 engineers

Record **one row per drawing** in `pilot_metrics_template.csv` (copy per session).

| Metric | Record |
|--------|--------|
| Drawing Name | |
| Total Polygons Detected | |
| INT Zones (Studio UI) | Informational only — **non-authoritative** |
| INT Zones (CLI / schedule) | Use `run_int_zone_pipeline` report or manifest for validation |
| Suspected Gaps Found | |
| Recoveries Attempted | |
| Recoveries Successful | |
| Save Success | Y/N |
| Reopen Success | Y/N |
| Export Success | Y/N |
| Confusion Points | Verbatim notes |
| Time to Complete Workflow | Minutes |

Also note: engineer ID/session, round (`R1`/`R2`), gap panel useful (Y/N), success quote if any.

---

## Round 1 exit criteria

All must pass to advance to Round 2:

| Criterion | Target |
|-----------|--------|
| Crashes | **0** |
| Data loss | **0** |
| Save/Reopen success | **≥ 90%** |
| Export success | **≥ 90%** |
| Useful recovery via gap guidance | **≥ 1** engineer finds at least one |

If pass → **Round 2**

---

## Round 2 (only if Round 1 passes)

| Item | Target |
|------|--------|
| Drawings | 10–20 |
| Users | Multiple engineers |
| Variety | Different slab types, different consultants |

**Goal:** Robustness — **not** features.

---

## During pilot: note, do not build

Pilot objective: **Learn. Not Build.**

| User asks for | Action |
|---------------|--------|
| Recent Projects | Note in feedback log. Do **not** build. |
| Search bar | Note. Do **not** build. |
| AI recovery suggestions | Note. Do **not** build. |
| Any new feature / menu expansion | Note. Do **not** build. |

Feedback is **product-market fit signal**, not a development backlog.

---

## Development freeze rules

From `pilot-v1` forward:

| Allowed | Not allowed |
|---------|-------------|
| Crash fixes | New features |
| Data-loss fixes | Architecture changes |
| Pilot feedback fixes (from real sessions) | AI additions |
| Small UX polish (labels, clarity) | Cloud sync work |
| Client language corrections | Menu expansion |

Do not redesign workflows unless pilot users **repeatedly** fail the same step.

---

## Risk & readiness (current verdict)

| Area | Level | Notes |
|------|-------|-------|
| Technical risk | **Low** | Engineering hardening accepted |
| Product risk | **Medium** | Gap→recovery workflow unproven with real users |
| Business risk | **Unknown** | PMF not yet validated |

| Readiness | Score |
|-----------|-------|
| Engineering readiness | ~9/10 |
| Controlled pilot readiness | ~9/10 |
| Commercial rollout readiness | ~7/10 |
| Product-market validation | **Not yet proven** |

v1.0 direction will be decided by **first pilot feedback**, not by further internal iteration.

---

## Cursor / agent instruction

> P0 workflow hardening is accepted. Repo is frozen at `pilot-v1`. Support a controlled pilot on 3–5 real slab drawings. Capture metrics per drawing. Primary signal: Suspected Gap → click → Recover → useful. Do not add features during pilot — note requests only. We are in Pilot Validation Mode.
