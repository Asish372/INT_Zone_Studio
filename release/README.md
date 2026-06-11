# Release artifacts

**Pilot Evaluation Build v1** · `0.1.0-pilot.1`

## Download (recommended)

Use **[GitHub Releases](https://github.com/Asish372/INT_Zone_Studio/releases/latest)** — versioned installer, checksums, and release notes.

## Local staging

After `npm run tauri:build` in `desktop/studio`:

```powershell
powershell -File scripts/stage_release_installer.ps1
```

Produces:

```
release/INT Zone Studio Standalone Setup 0.1.0-pilot.1.exe
```

## Publish to GitHub

```powershell
gh auth login
powershell -File scripts/publish_github_release.ps1
```

## Client quick sheet

See [CLIENT_STANDALONE_README.txt](CLIENT_STANDALONE_README.txt).
