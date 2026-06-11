# FAQ & Troubleshooting

**INT Zone Studio · Pilot Evaluation Build v1**

---

## General

### Is this a production release?

No. This is **Pilot Evaluation Build v1** (`0.1.0-pilot.1`) for field validation with engineers. Client language: *INT Zone Studio · Pilot Evaluation Build v1*.

### Does it send data to the cloud?

No. All processing and storage are **local**. No telemetry in this build.

### Do I need Python installed?

**No** for the standalone Windows installer from [Releases](https://github.com/Asish372/INT_Zone_Studio/releases/latest). Python is only needed if you run from source.

---

## Import & drawings

### DWG import failed — what now?

1. Wait 5 seconds after app open, then retry import.
2. Close all INT Zone Studio windows, reopen from Start Menu, retry.
3. Export the drawing as **DXF** from your CAD tool and import the DXF.

### Import is very slow

Large slab plans can take **30–60 seconds** on first load. Wait until the loading indicator clears before running detection.

### Open Project vs Import Drawing?

| Action | Use when |
|--------|----------|
| **Import Drawing** | Starting work from a CAD file (DXF/DWG) |
| **Open Project** | Continuing a saved `.pjson` workspace |

---

## Detection & gaps

### Detection count seems wrong

Pilot success is measured by **gap-to-recovery usefulness**, not raw polygon count alone. Run validation, check **Suspected Gaps**, and try seed recovery on one missing cell before concluding detection failed.

### Re-run Detection did not fix my drawing

Re-run refreshes the session view. It does not re-read the file from disk. To start fresh from CAD, **Import Drawing** again (note: unsaved session changes may be lost).

### Seed recovery did nothing

- Ensure **Seed Recovery** tool is active (tool **A** or Detection menu).
- Click inside a closed region bounded by detected walls.
- Zoom in if the click target is ambiguous.

---

## Save & export

### Save asks for a path — no file browser?

Expected in pilot v1. Type or paste the full path, e.g. `C:\Projects\MySlab.pjson`. Create the folder in Explorer first if needed.

### Export succeeded — where are my files?

Use **Open folder** on the export success panel. Default export location depends on your last export settings shown in the dialog.

### Which export option for deliverables?

Use **Export Project Package** for pilot sessions (PDF + DXF + CSV + Excel in one folder).

---

## Errors & crashes

### Red error bar on screen

1. Read the message text.
2. Close INT Zone Studio completely.
3. Reopen from Start Menu, wait 5 seconds, retry the step.

### App will not start / engine error

1. Reinstall from the latest [Release](https://github.com/Asish372/INT_Zone_Studio/releases/latest).
2. Ensure Windows is 64-bit and up to date.
3. Open a [GitHub Issue](https://github.com/Asish372/INT_Zone_Studio/issues) with steps and a sanitized drawing if possible.

---

## Reporting bugs

Include:

- Version (`0.1.0-pilot.1`)
- Windows version
- Drawing format (DXF/DWG) — attach only if you have permission to share
- Steps from import to failure
- Screenshot of error bar if shown

Use [GitHub Issues](https://github.com/Asish372/INT_Zone_Studio/issues) or your pilot facilitator.
