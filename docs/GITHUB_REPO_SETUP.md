# GitHub repository setup

One-time steps after pushing branding and docs.

## Repository profile

**Settings → General → Social preview**

Upload: `docs/branding/social-preview.png` (1280×640)

**About** (right sidebar on repo home):

| Field | Suggested text |
|-------|----------------|
| Description | Slab pour-cell detection & export for structural engineers — Pilot Evaluation Build v1 |
| Website | https://github.com/Asish372/INT_Zone_Studio/releases/latest |
| Topics | `cad` `dxf` `structural-engineering` `slab` `desktop-app` `tauri` `python` |

CLI (after `gh auth login`):

```powershell
gh repo edit Asish372/INT_Zone_Studio `
  --description "Slab pour-cell detection & export for structural engineers — Pilot Evaluation Build v1" `
  --add-topic cad --add-topic dxf --add-topic structural-engineering `
  --add-topic slab --add-topic desktop-app --add-topic tauri
```

## Publish release with installer

1. Build (if needed): `cd desktop/studio && npm run tauri:build`
2. Ensure installer exists: `release/INT Zone Studio Standalone Setup 0.1.0-pilot.1.exe`
3. Ensure PDF exists: `docs/INT_Zone_Studio_User_Guide.pdf`
4. Publish:

```powershell
gh auth login
powershell -File scripts/publish_github_release.ps1
```

This uploads **three files** to [Releases](https://github.com/Asish372/INT_Zone_Studio/releases):

| Asset | Source |
|-------|--------|
| `INT Zone Studio Standalone Setup 0.1.0-pilot.1.exe` | `release/` (62 MB) |
| `INT_Zone_Studio_User_Guide.pdf` | `docs/` (also in repo) |
| `SHA256SUMS.txt` | auto-generated checksums |

### Manual upload (no `gh` CLI)

1. GitHub → **Releases** → **Draft a new release**
2. Tag: `v0.1.0-pilot.1` · Title: `INT Zone Studio · Pilot Evaluation Build v1`
3. Attach the exe, PDF, and `release/SHA256SUMS.txt`
4. Paste notes from `.github/release_template.md` · Publish

## Regenerate logo / icons after logo change

```bash
python scripts/generate_brand_assets.py
```
