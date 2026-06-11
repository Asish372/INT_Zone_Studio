# PILOT BUILD CHECKLIST

**Product:** INT Zone Studio · Pilot Evaluation Build v1  
**Tag:** `pilot-v1`  
**Use:** Run this checklist on every pilot build before handing to external engineers.

---

## Build identity

| Check | Pass |
|-------|------|
| Window title shows **Pilot Evaluation Build v1** | ☐ |
| Version is `0.1.0-pilot.1` (or current pilot semver) | ☐ |
| `PILOT_FEEDBACK.md` present in release folder | ☐ |
| `pilot_metrics_template.csv` present in release folder | ☐ |
| `PILOT_V1.md` / release notes included | ☐ |
| Python deps install (`pip install -r requirements.txt`) | ☐ |
| App launches without engine connection error | ☐ |

---

## Supported workflow (must all pass)

### 1. Import

| Step | Pass | Notes |
|------|------|-------|
| Import DXF from Welcome or Home → Import DXF | ☐ | |
| Drawing renders on canvas | ☐ | |
| Fit view shows full drawing | ☐ | |

### 2. Detect

| Step | Pass | Notes |
|------|------|-------|
| Run Detection (Detection tab or menu) | ☐ | |
| Polygons appear on canvas | ☐ | |
| Polygon count shown in UI | ☐ | |

### 3. Review

| Step | Pass | Notes |
|------|------|-------|
| Select polygon on canvas or in table | ☐ | |
| Properties / review status visible | ☐ | |
| Run Validation (if CAD source available) | ☐ | |

### 4. Recovery

| Step | Pass | Notes |
|------|------|-------|
| Suspected Gaps panel lists candidates | ☐ | |
| Click gap → navigates to location | ☐ | |
| Seed Recovery adds polygon | ☐ | |

### 5. Save

| Step | Pass | Notes |
|------|------|-------|
| Save Workspace (Ctrl+S) | ☐ | |
| Full path typed (e.g. `C:\Projects\name.pjson`) | ☐ | |
| Save confirmation in Messages | ☐ | |

### 6. Reopen

| Step | Pass | Notes |
|------|------|-------|
| Open Project loads saved `.pjson` | ☐ | |
| Polygons and edits restored | ☐ | |
| No data loss vs pre-save state | ☐ | |

### 7. Export

| Step | Pass | Notes |
|------|------|-------|
| Export Project Package completes | ☐ | |
| Output folder opens / path shown | ☐ | |
| Package contains expected formats | ☐ | |

---

## Pilot feedback tooling

| Step | Pass | Notes |
|------|------|-------|
| Help → Export Pilot Feedback Template opens/downloads template | ☐ | |
| Template fields match session capture needs | ☐ | |

---

## Exit gate (Round 1)

| Criterion | Target | This build |
|-----------|--------|------------|
| Crashes during checklist | 0 | ☐ |
| Data loss on save/reopen | 0 | ☐ |
| Checklist steps above | All pass | ☐ |

**Tester:** _________________  
**Date:** _________________  
**Build path / commit:** _________________  
**Sign-off:** ☐ Ready for external pilot

---

*Single-page checklist — do not expand scope beyond the seven workflow steps.*
