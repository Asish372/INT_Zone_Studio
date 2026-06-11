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

1. Build: `cd desktop/studio && npm run tauri:build`
2. Stage: `powershell -File scripts/stage_release_installer.ps1`
3. Publish: `powershell -File scripts/publish_github_release.ps1`

## Regenerate logo / icons after logo change

```bash
python scripts/generate_brand_assets.py
```
