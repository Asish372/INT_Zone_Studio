# Installation — INT Zone Studio

**Version:** `0.1.0-pilot.1` (Pilot Evaluation Build v1)

---

## System requirements

| Requirement | Detail |
|-------------|--------|
| OS | Windows 10 or 11 (64-bit only) |
| RAM | 8 GB minimum; 16 GB recommended for large drawings |
| Disk | ~500 MB for application; extra space for projects and exports |
| Network | Internet on first install only if WebView2 is missing (installer handles this) |
| Python | **Not required** for the standalone installer |

---

## Download

1. Open [GitHub Releases](https://github.com/Asish372/INT_Zone_Studio/releases/latest).
2. Download **INT Zone Studio Standalone Setup 0.1.0-pilot.1.exe**.
3. Verify the file name matches your intended version (see [CHANGELOG.md](../../CHANGELOG.md)).

---

## Install

1. Double-click the setup executable.
2. Follow the installer prompts (default location is fine for most users).
3. When complete, launch from **Start Menu → INT Zone Studio** or the desktop shortcut.

The detection engine is bundled inside the app. It starts automatically when you open INT Zone Studio — no terminal or Python setup.

---

## First launch

1. Wait **5 seconds** after the window opens before importing a drawing.
2. On the Welcome screen, choose **Import Drawing** (new CAD file) or **Open Project** (saved `.pjson` workspace).
3. Large drawings may take **30–60 seconds** on first import — wait until loading finishes.

---

## Drawing files

| Format | Support |
|--------|---------|
| DXF | Native |
| DWG | Supported via bundled converter in standalone build |

If DWG import fails, export the drawing as DXF from AutoCAD or similar and import the DXF.

---

## Data location

Workspace and app data are stored locally:

```
%LOCALAPPDATA%\com.administrator.desktopstudio
```

Projects you save (`.pjson`) go to the path you specify when saving.

---

## Uninstall / reinstall

1. Windows Settings → Apps → INT Zone Studio → Uninstall.
2. Install the latest setup exe from Releases if you need a clean reinstall.

---

## Developer install

Contributors run from source. See [README — Quick start (developers)](../../README.md#quick-start-developers).

---

## Support

- [FAQ](FAQ.md)
- [User Guide](USER_GUIDE.md)
- [GitHub Issues](https://github.com/Asish372/INT_Zone_Studio/issues)
