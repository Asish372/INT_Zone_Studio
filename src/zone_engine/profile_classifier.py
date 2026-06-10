"""Resolve GRID_WAREHOUSE vs JOINT_WAREHOUSE profile for zone engine runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.zone_engine.manifest_reconciliation import load_manifest

PROFILES = ("auto", "GRID_WAREHOUSE", "JOINT_WAREHOUSE", "MANIFEST_OVERRIDE")


def resolve_zone_profile(
    config: dict[str, Any],
    *,
    manifest_path: Path | str | None = None,
    cli_profile: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Return (profile_name, manifest_dict).

    Priority: CLI (non-auto) > manifest profile > config zone_engine.profile > GRID_WAREHOUSE.
    """
    manifest = load_manifest(manifest_path)
    zone_cfg = config.get("zone_engine", {})

    profile = (cli_profile or zone_cfg.get("profile", "auto")).strip().upper()
    if profile == "AUTO":
        if manifest.get("profile"):
            profile = str(manifest["profile"]).upper()
        else:
            profile = "GRID_WAREHOUSE"

    if profile not in ("GRID_WAREHOUSE", "JOINT_WAREHOUSE", "MANIFEST_OVERRIDE"):
        profile = "GRID_WAREHOUSE"

    return profile, manifest
