"""Local project and version management."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECTS_ROOT = Path(__file__).resolve().parents[2] / "output" / "projects"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_projects() -> list[dict[str, Any]]:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    projects = []
    for pdir in sorted(PROJECTS_ROOT.iterdir()):
        if not pdir.is_dir():
            continue
        meta_path = pdir / "project.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            projects.append(meta)
    return projects


def get_project(project_id: str) -> dict[str, Any] | None:
    meta_path = PROJECTS_ROOT / project_id / "project.json"
    if not meta_path.is_file():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def create_project(name: str) -> dict[str, Any]:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    project_id = uuid4().hex[:12]
    pdir = PROJECTS_ROOT / project_id
    pdir.mkdir(parents=True)
    meta = {
        "id": project_id,
        "name": name,
        "created_at": _now(),
        "drawings": [],
        "versions": [],
    }
    (pdir / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def save_version(
    project_id: str,
    *,
    source_file: str,
    polygons: list[dict[str, Any]],
    session_id: str = "",
    label: str | None = None,
) -> dict[str, Any]:
    meta = get_project(project_id)
    if meta is None:
        raise ValueError(f"Project {project_id} not found")
    pdir = PROJECTS_ROOT / project_id
    versions_dir = pdir / "versions"
    versions_dir.mkdir(exist_ok=True)
    ver_num = len(meta.get("versions", [])) + 1
    ver_id = f"v{ver_num}"
    ver_label = label or ver_id
    payload = {
        "version_id": ver_id,
        "label": ver_label,
        "source_file": source_file,
        "session_id": session_id,
        "saved_at": _now(),
        "polygon_count": len([p for p in polygons if p.get("status") != "deleted"]),
        "polygons": polygons,
    }
    ver_path = versions_dir / f"{ver_id}.json"
    ver_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    drawing_name = source_file or f"Drawing {ver_num}"
    drawings = meta.get("drawings", [])
    if not any(d.get("name") == drawing_name for d in drawings):
        drawings.append({"id": uuid4().hex[:8], "name": drawing_name})
    versions = meta.get("versions", [])
    versions.append(
        {
            "id": ver_id,
            "label": ver_label,
            "source_file": source_file,
            "saved_at": payload["saved_at"],
            "polygon_count": payload["polygon_count"],
            "path": str(ver_path.relative_to(PROJECTS_ROOT)).replace("\\", "/"),
        }
    )
    meta["drawings"] = drawings
    meta["versions"] = versions
    meta["current_version"] = ver_id
    (pdir / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"version": versions[-1], "project": meta}


def load_version(project_id: str, version_id: str) -> dict[str, Any]:
    ver_path = PROJECTS_ROOT / project_id / "versions" / f"{version_id}.json"
    if not ver_path.is_file():
        raise ValueError(f"Version {version_id} not found")
    return json.loads(ver_path.read_text(encoding="utf-8"))
