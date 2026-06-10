"""FastAPI sidecar for the polygon workspace."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from shapely.geometry import Polygon

import ezdxf
import yaml
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from desktop.engine_sidecar.detect_pipeline import detect_from_cad_path  # noqa: E402
from desktop.engine_sidecar.polygon_records import (  # noqa: E402
    faces_to_polygon_records,
    polygon_overlaps_existing,
    polygon_to_record,
)
from desktop.engine_sidecar.scene_builder import build_scene  # noqa: E402
from desktop.engine_sidecar.session_store import WorkspaceSession, get_or_create_session  # noqa: E402
from desktop.engine_sidecar.project_store import (  # noqa: E402
    create_project,
    get_project,
    list_projects,
    load_version,
    save_version,
)
from desktop.engine_sidecar.workspace_save import (  # noqa: E402
    build_workspace_payload,
    load_workspace_state,
    save_detection_report_pdf,
    save_polygons_csv,
    save_polygons_dxf,
    save_polygons_json,
    save_polygons_xlsx,
    save_project_json,
    save_workspace_state,
    save_zones_dxf,
)
from desktop.engine_sidecar.workspace_validation import validate_workspace  # noqa: E402
from desktop.engine_sidecar.suspected_gaps import analyze_suspected_gaps  # noqa: E402
from desktop.engine_sidecar.workspace_zones import (  # noqa: E402
    generate_int_zones,
    merge_zones,
    rename_zone,
)
from src.converter import ensure_dxf  # noqa: E402
from src.models import SeedRequest  # noqa: E402
from src.seed_resolver import resolve_seed_region  # noqa: E402
from src.units import scale_factor  # noqa: E402

APP_DIR = Path(__file__).resolve().parent.parent / "app"
DEFAULT_CONFIG = PROJECT_ROOT / "config.yaml"
WORKSPACE_OUTPUT = PROJECT_ROOT / "output" / "polygon_workspace"
DXF_CACHE_DIR = PROJECT_ROOT / "output" / ".dxf_cache"
CAD_EXTENSIONS = {".dxf", ".dwg"}


def _load_config() -> dict[str, Any]:
    with DEFAULT_CONFIG.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _session_dep(x_session_id: str | None = Header(default=None)) -> WorkspaceSession:
    return get_or_create_session(x_session_id)


def _scene_payload(session: WorkspaceSession) -> dict[str, Any]:
    return build_scene(
        source_file=session.source_file,
        cad_segments=session.cad_segments,
        polygons=session.polygons,
        unit_label=session.unit_label,
    )


def _summary(session: WorkspaceSession) -> dict[str, Any]:
    counts = session.counts()
    return {
        "session_id": session.session_id,
        "source_file": session.source_file,
        "unit_label": session.unit_label,
        "counts": counts,
        "selected_id": session.selected_id,
        "selected_ids": session.selected_ids,
        "expected_polygon_count": session.expected_polygon_count,
        "current_user": session.current_user,
        "current_role": session.current_role,
        "zones": session.zones,
        "validation": session.validation_result,
        "project_id": session.project_id,
        "workspace_save_path": session.workspace_save_path,
        "cad_available": session.cad_available,
        "actions": [
            {"message": a.message, "kind": a.kind, "at": a.at, "user": a.user}
            for a in session.actions
        ],
    }


def _polygon_public(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rec.get("id"),
        "source": rec.get("source"),
        "status": rec.get("status", "active"),
        "review_status": rec.get("review_status", "pending"),
        "layer": rec.get("layer", "DETECTED_REGIONS"),
        "area_m2": rec.get("area_m2"),
        "perimeter_m": rec.get("perimeter_m"),
        "centroid": rec.get("centroid"),
        "created_by": rec.get("created_by", "System"),
        "int_zone": rec.get("int_zone"),
        "ring": rec.get("ring"),
    }


def _resolve_seed(session: WorkspaceSession, x: float, y: float):
    config = _load_config()
    seed = SeedRequest(
        drawing=session.source_file,
        x=x,
        y=y,
        label_hint=None,
        id=f"click-{x:.1f}-{y:.1f}",
    )
    return resolve_seed_region(
        seed,
        session.segments,
        config,
        auto_polygons=session.auto_polygons,
    )


app = FastAPI(title="INT Zone Studio Engine", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecoverRequest(BaseModel):
    x: float
    y: float


class ExportRequest(BaseModel):
    formats: list[str] = ["json", "dxf"]
    use_timestamp: bool = True


class SelectRequest(BaseModel):
    polygon_id: int | None = None
    polygon_ids: list[int] | None = None


class ReviewRequest(BaseModel):
    review_status: str


class ExpectedCountRequest(BaseModel):
    count: int


class UserRequest(BaseModel):
    user: str
    role: str = "engineer"


class ZoneMergeRequest(BaseModel):
    zone_a: str
    zone_b: str


class ZoneRenameRequest(BaseModel):
    old_label: str
    new_label: str


class CommentRequest(BaseModel):
    text: str


class MarkupRequest(BaseModel):
    x: float
    y: float
    text: str = ""


class ProjectCreateRequest(BaseModel):
    name: str


class VersionSaveRequest(BaseModel):
    label: str | None = None


class VersionLoadRequest(BaseModel):
    project_id: str
    version_id: str


class WorkspaceSaveRequest(BaseModel):
    path: str


class OpenFolderRequest(BaseModel):
    path: str


def _resolve_cad_path(
    source_file: str,
    source_file_path: str | None,
    workspace_path: str | None,
) -> Path | None:
    candidates: list[Path] = []
    if source_file_path:
        candidates.append(Path(source_file_path))
    if workspace_path:
        ws = Path(workspace_path).resolve().parent
        if source_file:
            candidates.append(ws / source_file)
    if source_file:
        candidates.append(PROJECT_ROOT / "input" / source_file)
        upload_glob = list((WORKSPACE_OUTPUT / "uploads").glob(f"*_{source_file}"))
        candidates.extend(upload_glob)
        candidates.append(WORKSPACE_OUTPUT / "uploads" / source_file)
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved.is_file() and resolved.suffix.lower() in CAD_EXTENSIONS:
            return resolved
    return None


def _polygons_to_auto(session: WorkspaceSession) -> list[Polygon]:
    auto: list[Polygon] = []
    for rec in session.polygons:
        if rec.get("status") == "deleted" or rec.get("source") != "auto":
            continue
        ring = rec.get("ring") or []
        if len(ring) < 3:
            continue
        try:
            poly = Polygon(ring)
            if poly.is_valid and not poly.is_empty:
                auto.append(poly)
        except Exception:
            continue
    return auto


def _attach_cad_to_session(session: WorkspaceSession, cad_path: Path) -> None:
    config = _load_config()
    try:
        if cad_path.suffix.lower() == ".dwg":
            dxf_path = ensure_dxf(cad_path, DXF_CACHE_DIR)
        else:
            dxf_path = cad_path
        result = detect_from_cad_path(
            cad_path,
            config,
            cache_dir=DXF_CACHE_DIR,
            source_file=session.source_file or cad_path.name,
        )
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.dxf_path = dxf_path
    session.segments = result.segments
    session.cad_segments = result.cad_segments
    session.auto_polygons = list(result.polygons)
    session.unit_label = config.get("geometry", {}).get("drawing_unit", "mm")
    session.unit_scale_m = result.unit_scale_m
    session.cad_available = True
    session.source_file_path = str(cad_path.resolve())


def _apply_workspace_to_session(session: WorkspaceSession, data: dict[str, Any]) -> None:
    session.source_file = data.get("source_file", "")
    session.source_file_path = data.get("source_file_path") or None
    session.polygons = data.get("polygons") or []
    session.zones = data.get("zones") or []
    session.validation_result = data.get("validation")
    raw_comments = data.get("comments") or {}
    session.comments = {
        int(k): v for k, v in raw_comments.items() if str(k).isdigit()
    }
    session.markups = data.get("markups") or []
    session.expected_polygon_count = data.get("expected_polygon_count")
    session.project_id = data.get("project_id")
    session.unit_label = data.get("unit_label", "mm")
    session.current_user = data.get("current_user", session.current_user)
    session.current_role = data.get("current_role", session.current_role)
    session.workspace_save_path = data.get("workspace_path")
    max_id = max((p.get("id", 0) for p in session.polygons), default=0)
    session.next_id = max_id
    session.selected_id = None
    session.selected_ids = []
    session.segments = []
    session.cad_segments = []
    session.auto_polygons = _polygons_to_auto(session)
    session.cad_available = False
    session.dxf_path = None
    session.upload_path = None
    session.history.seed(session.polygons)
    session.actions.clear()

    cad_path = _resolve_cad_path(
        session.source_file,
        session.source_file_path,
        session.workspace_save_path,
    )
    if cad_path is not None:
        try:
            _attach_cad_to_session(session, cad_path)
            session.log(f"CAD source loaded: {cad_path.name}", kind="info")
        except HTTPException:
            session.log(
                "Original CAD source not available. Polygon workspace loaded in review-only mode.",
                kind="warn",
            )
    else:
        session.log(
            "Original CAD source not available. Polygon workspace loaded in review-only mode.",
            kind="warn",
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "int-zone-studio-engine"}


@app.get("/")
async def index() -> FileResponse:
    index_path = APP_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="Viewer UI not found")
    return FileResponse(index_path)


@app.post("/session")
async def new_session() -> dict[str, str]:
    session = get_or_create_session(None)
    return {"session_id": session.session_id}


@app.post("/upload")
async def upload_cad(
    file: UploadFile = File(...),
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Upload a .dxf or .dwg file")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in CAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload a .dxf or .dwg file")

    config = _load_config()
    upload_dir = WORKSPACE_OUTPUT / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    DXF_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid4().hex[:8]}_{Path(file.filename).name}"
    dest = upload_dir / unique_name
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="File is empty")
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 200 MB)")
    dest.write_bytes(content)

    display_name = Path(file.filename).name
    try:
        if suffix == ".dwg":
            dxf_path = ensure_dxf(dest, DXF_CACHE_DIR)
            converted_from = "dwg"
        else:
            dxf_path = dest
            converted_from = None
        result = detect_from_cad_path(dxf_path, config, source_file=display_name)
    except (RuntimeError, ValueError, FileNotFoundError, OSError, ezdxf.DXFStructureError) as exc:
        dest.unlink(missing_ok=True)
        detail = str(exc)
        if "ODA" in detail or "DWG" in detail.upper():
            detail += (
                " Install ODA File Converter: "
                "https://www.opendesign.com/guestfiles/oda_file_converter"
            )
        raise HTTPException(status_code=422, detail=detail) from exc

    unit_label = config.get("geometry", {}).get("drawing_unit", "mm")
    records = faces_to_polygon_records(result.faces, unit_scale_m=result.unit_scale_m)
    max_id = max((r["id"] for r in records), default=0)

    session.source_file = display_name
    session.dxf_path = dxf_path
    session.upload_path = dest
    session.source_file_path = str(dest.resolve())
    session.segments = result.segments
    session.cad_segments = result.cad_segments
    session.polygons = records
    session.auto_polygons = list(result.polygons)
    session.next_id = max_id
    session.unit_label = unit_label
    session.unit_scale_m = result.unit_scale_m
    session.cad_available = True
    session.workspace_save_path = None
    session.selected_id = None
    session.selected_ids = []
    session.zones = []
    session.validation_result = None
    session.expected_polygon_count = len(records)
    session.history.seed(records)
    session.actions.clear()
    session.log(f"Loaded {display_name}", kind="success")
    if converted_from == "dwg":
        session.log("Converted DWG to DXF via ODA cache", kind="info")
    session.log(f"Auto detection completed — {len(records)} polygons", kind="success")

    scene = _scene_payload(session)
    return {
        "ok": True,
        "session_id": session.session_id,
        "source_file": session.source_file,
        "converted_from": converted_from,
        "unit_label": session.unit_label,
        "counts": session.counts(),
        "polygon_count": scene["polygon_count"],
        "scene": scene,
        "actions": _summary(session)["actions"],
    }


@app.get("/scene")
async def get_scene(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    if not session.polygons and not session.cad_segments:
        raise HTTPException(status_code=404, detail="No drawing loaded. Upload a DXF or DWG first.")
    return {
        "session_id": session.session_id,
        "summary": _summary(session),
        "scene": _scene_payload(session),
    }


@app.get("/summary")
async def get_summary(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    return _summary(session)


@app.post("/select")
async def select_polygon(
    body: SelectRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    if body.polygon_ids is not None:
        valid = [p["id"] for p in session.polygons if p["id"] in body.polygon_ids]
        session.selected_ids = valid
        session.selected_id = valid[0] if valid else None
        selected = [
            _polygon_public(p) for p in session.polygons if p["id"] in valid
        ]
        return {"ok": True, "selected_ids": valid, "selected": selected}
    if body.polygon_id is None:
        session.selected_id = None
        session.selected_ids = []
        return {"ok": True, "selected": None, "selected_ids": []}
    match = next((p for p in session.polygons if p["id"] == body.polygon_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Polygon not found")
    session.selected_id = body.polygon_id
    session.selected_ids = [body.polygon_id]
    return {"ok": True, "selected": _polygon_public(match), "selected_ids": [body.polygon_id]}


@app.post("/recover/preview")
async def recover_preview(
    body: RecoverRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    if not session.segments:
        raise HTTPException(status_code=404, detail="No drawing loaded. Upload a DXF or DWG first.")

    resolution = _resolve_seed(session, body.x, body.y)
    if resolution.polygon is None:
        raise HTTPException(
            status_code=422,
            detail=resolution.message or f"Could not recover polygon (status={resolution.status})",
        )

    active = [p for p in session.polygons if p.get("status", "active") != "deleted"]
    if polygon_overlaps_existing(resolution.polygon, active):
        raise HTTPException(status_code=409, detail="Polygon already exists at this location")

    ring = [[float(x), float(y)] for x, y in resolution.polygon.exterior.coords]
    metrics = polygon_to_record(
        resolution.polygon,
        polygon_id=session.next_id + 1,
        source="seed",
        unit_scale_m=session.unit_scale_m,
    )
    return {
        "ok": True,
        "status": resolution.status,
        "message": resolution.message or "Preview ready",
        "preview": {
            "ring": ring,
            "area_m2": metrics["area_m2"],
            "perimeter_m": metrics["perimeter_m"],
            "centroid": metrics["centroid"],
        },
    }


@app.post("/recover")
async def recover_polygon(
    body: RecoverRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    if not session.segments:
        raise HTTPException(status_code=404, detail="No drawing loaded. Upload a DXF or DWG first.")

    resolution = _resolve_seed(session, body.x, body.y)
    if resolution.polygon is None:
        raise HTTPException(
            status_code=422,
            detail=resolution.message or f"Could not recover polygon (status={resolution.status})",
        )

    active = [p for p in session.polygons if p.get("status", "active") != "deleted"]
    if polygon_overlaps_existing(resolution.polygon, active):
        raise HTTPException(status_code=409, detail="Polygon already exists at this location")

    session.snapshot_polygons()
    session.next_id += 1
    record = polygon_to_record(
        resolution.polygon,
        polygon_id=session.next_id,
        source="seed",
        unit_scale_m=session.unit_scale_m,
    )
    record["review_status"] = "pending"
    record["created_by"] = "User"
    session.polygons.append(record)
    session.auto_polygons.append(resolution.polygon)
    session.selected_id = record["id"]
    session.log(f"Seed added — polygon #{record['id']}", kind="success")

    scene = _scene_payload(session)
    return {
        "ok": True,
        "session_id": session.session_id,
        "status": resolution.status,
        "message": resolution.message or "Polygon recovered",
        "polygon": record,
        "counts": session.counts(),
        "selected": _polygon_public(record),
        "scene": scene,
        "actions": _summary(session)["actions"],
    }


@app.post("/polygon/{polygon_id}/delete")
async def delete_polygon(
    polygon_id: int,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    match = next((p for p in session.polygons if p["id"] == polygon_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Polygon not found")
    session.snapshot_polygons()
    match["status"] = "deleted"
    if session.selected_id == polygon_id:
        session.selected_id = None
    session.log(f"Polygon #{polygon_id} marked deleted", kind="warn")
    return {
        "ok": True,
        "counts": session.counts(),
        "scene": _scene_payload(session),
        "actions": _summary(session)["actions"],
    }


def _export_response(
    session: WorkspaceSession,
    paths: dict[str, str],
) -> dict[str, Any]:
    absolute_paths: dict[str, str] = {}
    folders: list[str] = []
    for key, rel in paths.items():
        full = (PROJECT_ROOT / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
        absolute_paths[key] = str(full)
        folders.append(str(full.parent))
    folder = folders[0] if folders else str(WORKSPACE_OUTPUT.resolve())
    if len(set(folders)) == 1:
        folder = folders[0]
    return {
        "ok": True,
        "polygon_count": session.counts()["total"],
        "paths": paths,
        "absolute_paths": absolute_paths,
        "folder": folder,
        "summary": {
            "file_count": len(paths),
            "formats": list(paths.keys()),
            "polygon_count": session.counts()["total"],
        },
        "actions": _summary(session)["actions"],
    }


@app.post("/export")
async def export_workspace(
    body: ExportRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    if session.counts()["total"] == 0:
        raise HTTPException(status_code=404, detail="No active polygons to export")

    WORKSPACE_OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = Path(session.source_file).stem if session.source_file else "workspace"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") if body.use_timestamp else ""
    suffix = f"_{ts}" if ts else ""
    paths: dict[str, str] = {}

    for fmt in body.formats:
        fmt_l = fmt.lower()
        if fmt_l == "json":
            p = WORKSPACE_OUTPUT / f"{stem}{suffix}_corrected_polygons.json"
            save_polygons_json(session.polygons, p, source_file=session.source_file)
            paths["json"] = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        elif fmt_l == "dxf":
            p = WORKSPACE_OUTPUT / f"{stem}{suffix}_corrected_polygons.dxf"
            save_polygons_dxf(session.polygons, p)
            paths["dxf"] = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        elif fmt_l == "csv":
            p = WORKSPACE_OUTPUT / f"{stem}{suffix}_corrected_polygons.csv"
            save_polygons_csv(session.polygons, p)
            paths["csv"] = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        elif fmt_l in ("project", "pjson"):
            p = WORKSPACE_OUTPUT / f"{stem}{suffix}.pjson"
            save_project_json(
                session.polygons,
                p,
                source_file=session.source_file,
                session_id=session.session_id,
            )
            paths["project"] = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        elif fmt_l in ("xlsx", "excel"):
            p = WORKSPACE_OUTPUT / f"{stem}{suffix}_schedule.xlsx"
            save_polygons_xlsx(session.polygons, p)
            paths["xlsx"] = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        elif fmt_l == "pdf":
            p = WORKSPACE_OUTPUT / f"{stem}{suffix}_detection_report.pdf"
            save_detection_report_pdf(
                p,
                source_file=session.source_file,
                polygons=session.polygons,
                validation=session.validation_result,
                zones=session.zones or None,
            )
            paths["pdf"] = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        elif fmt_l in ("zones_dxf", "zones-dxf"):
            if not session.zones:
                generate_int_zones(session.polygons)
            p = WORKSPACE_OUTPUT / f"{stem}{suffix}_int_zones.dxf"
            save_zones_dxf(session.zones, session.polygons, p)
            paths["zones_dxf"] = str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
        elif fmt_l == "package":
            for sub_fmt, ext, saver in [
                ("json", "_corrected_polygons.json", lambda fp: save_polygons_json(session.polygons, fp, source_file=session.source_file)),
                ("dxf", "_corrected_polygons.dxf", lambda fp: save_polygons_dxf(session.polygons, fp)),
                ("csv", "_corrected_polygons.csv", lambda fp: save_polygons_csv(session.polygons, fp)),
                ("xlsx", "_schedule.xlsx", lambda fp: save_polygons_xlsx(session.polygons, fp)),
            ]:
                fp = WORKSPACE_OUTPUT / f"{stem}{suffix}{ext}"
                saver(fp)
                paths[sub_fmt] = str(fp.relative_to(PROJECT_ROOT)).replace("\\", "/")
            pdf_p = WORKSPACE_OUTPUT / f"{stem}{suffix}_detection_report.pdf"
            save_detection_report_pdf(
                pdf_p,
                source_file=session.source_file,
                polygons=session.polygons,
                validation=session.validation_result,
                zones=session.zones or None,
            )
            paths["pdf"] = str(pdf_p.relative_to(PROJECT_ROOT)).replace("\\", "/")

    session.log(f"Exported {len(paths)} file(s)", kind="success")
    return _export_response(session, paths)


@app.post("/workspace/save")
async def save_workspace_state_endpoint(
    body: WorkspaceSaveRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    if not session.polygons:
        raise HTTPException(status_code=404, detail="No workspace to save")
    if not body.path.strip():
        raise HTTPException(status_code=400, detail="Save path is required")
    save_path = Path(body.path.strip())
    if save_path.suffix.lower() not in {".pjson", ".json"}:
        save_path = save_path.with_suffix(".pjson")
    payload = build_workspace_payload(
        polygons=session.polygons,
        source_file=session.source_file,
        source_file_path=session.source_file_path or "",
        session_id=session.session_id,
        workspace_path=str(save_path),
        expected_polygon_count=session.expected_polygon_count,
        project_id=session.project_id,
        zones=session.zones,
        validation=session.validation_result,
        comments=session.comments,
        markups=session.markups,
        unit_label=session.unit_label,
        current_user=session.current_user,
        current_role=session.current_role,
    )
    written = save_workspace_state(payload, save_path)
    session.workspace_save_path = str(written.resolve())
    session.log(f"Workspace saved: {written.name}", kind="success")
    return {
        "ok": True,
        "path": str(written.resolve()),
        "relative_path": str(written.relative_to(PROJECT_ROOT)).replace("\\", "/")
        if written.is_relative_to(PROJECT_ROOT)
        else str(written),
        "actions": _summary(session)["actions"],
    }


@app.post("/workspace/load-project")
async def load_workspace_project(
    file: UploadFile = File(...),
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Select a .pjson workspace file")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pjson", ".json"}:
        raise HTTPException(status_code=400, detail="Open a .pjson workspace file")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Workspace file is empty")
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid workspace JSON") from exc

    fmt = data.get("format")
    if fmt not in ("polygon_workspace_project",):
        raise HTTPException(status_code=422, detail="Not a polygon workspace project file")

    _apply_workspace_to_session(session, data)
    scene = _scene_payload(session)
    summary = _summary(session)
    return {
        "ok": True,
        "session_id": session.session_id,
        "source_file": session.source_file,
        "unit_label": session.unit_label,
        "workspace_save_path": session.workspace_save_path,
        "cad_available": session.cad_available,
        "counts": session.counts(),
        "scene": scene,
        "validation": session.validation_result,
        "zones": session.zones,
        "comments": {str(k): v for k, v in session.comments.items()},
        "markups": session.markups,
        "expected_polygon_count": session.expected_polygon_count,
        "project_id": session.project_id,
        "current_user": session.current_user,
        "current_role": session.current_role,
        "actions": summary["actions"],
    }


@app.post("/open-folder")
async def open_folder(body: OpenFolderRequest) -> dict[str, Any]:
    folder = Path(body.path.strip())
    if folder.is_file():
        folder = folder.parent
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder}")
    resolved = str(folder.resolve())
    try:
        if sys.platform == "win32":
            os.startfile(resolved)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", resolved], check=True)
        else:
            subprocess.run(["xdg-open", resolved], check=True)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not open folder: {exc}") from exc
    return {"ok": True, "path": resolved}


@app.post("/validate")
async def run_validation(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    if not session.polygons:
        raise HTTPException(status_code=404, detail="No polygons to validate")
    if not session.cad_available or not session.dxf_path:
        raise HTTPException(
            status_code=422,
            detail="CAD source required for gap validation. Import the original drawing or open a project with CAD available.",
        )
    config = _load_config()
    result = validate_workspace(session.polygons)
    suspected, gap_summary = analyze_suspected_gaps(
        dxf_path=session.dxf_path,
        config=config,
        segments=session.segments,
        auto_polygons=session.auto_polygons,
        source_file=session.source_file,
    )
    result["suspected_gaps"] = suspected
    result["gap_summary"] = gap_summary
    result["counts"]["gaps"] = gap_summary["recoverable"]
    if gap_summary["recoverable"] > 0:
        result["issues"].append(
            {
                "type": "suspected_gap",
                "severity": "warning",
                "message": (
                    f"{gap_summary['total']} suspected gaps found "
                    f"({gap_summary['recoverable']} recoverable, {gap_summary['informational']} informational)"
                ),
            }
        )
    if session.expected_polygon_count is not None:
        detected = session.counts()["total"]
        count_gap = max(0, session.expected_polygon_count - detected)
        if count_gap > 0:
            result["issues"].append(
                {
                    "type": "gap",
                    "severity": "warning",
                    "message": f"Expected {session.expected_polygon_count} polygons, detected {detected} (missing {count_gap})",
                }
            )
    session.validation_result = result
    session.log(
        f"Validation completed — {gap_summary['recoverable']} recoverable suspected gaps",
        kind="success",
    )
    return {"ok": True, "validation": result, "actions": _summary(session)["actions"]}


@app.post("/polygon/{polygon_id}/review")
async def review_polygon(
    polygon_id: int,
    body: ReviewRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    allowed = {"pending", "approved", "rejected", "needs_review"}
    status = body.review_status.lower().replace(" ", "_")
    if status not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {allowed}")
    if session.current_role == "engineer" and status == "approved":
        raise HTTPException(status_code=403, detail="Only reviewer/manager can approve")
    match = next((p for p in session.polygons if p["id"] == polygon_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Polygon not found")
    session.snapshot_polygons()
    match["review_status"] = status
    session.log(f"Polygon #{polygon_id} → {status}", kind="info")
    return {
        "ok": True,
        "polygon": _polygon_public(match),
        "scene": _scene_payload(session),
        "actions": _summary(session)["actions"],
    }


@app.post("/expected-count")
async def set_expected_count(
    body: ExpectedCountRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    session.expected_polygon_count = body.count
    session.log(f"Expected polygon count set to {body.count}", kind="info")
    return {"ok": True, "expected_polygon_count": body.count}


@app.post("/user")
async def set_user(
    body: UserRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    session.current_user = body.user
    session.current_role = body.role
    session.log(f"Switched to {body.user} ({body.role})", kind="info")
    return {"ok": True, "user": body.user, "role": body.role}


@app.post("/zones/generate")
async def zones_generate(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    if not session.polygons:
        raise HTTPException(status_code=404, detail="No polygons loaded")
    session.snapshot_polygons()
    session.zones = generate_int_zones(session.polygons)
    session.log(f"Generated {len(session.zones)} INT zones", kind="success")
    return {
        "ok": True,
        "zones": session.zones,
        "scene": _scene_payload(session),
        "actions": _summary(session)["actions"],
    }


@app.get("/zones")
async def zones_list(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    return {"zones": session.zones}


@app.post("/zones/merge")
async def zones_merge(
    body: ZoneMergeRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    session.snapshot_polygons()
    session.zones = merge_zones(session.zones, session.polygons, body.zone_a, body.zone_b)
    session.log(f"Merged zones {body.zone_b} → {body.zone_a}", kind="success")
    return {"ok": True, "zones": session.zones, "scene": _scene_payload(session)}


@app.post("/zones/rename")
async def zones_rename(
    body: ZoneRenameRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    session.snapshot_polygons()
    session.zones = rename_zone(session.zones, session.polygons, body.old_label, body.new_label)
    session.log(f"Renamed zone {body.old_label} → {body.new_label}", kind="success")
    return {"ok": True, "zones": session.zones, "scene": _scene_payload(session)}


@app.post("/undo")
async def undo_action(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    restored = session.history.undo(session.polygons)
    if restored is None:
        raise HTTPException(status_code=400, detail="Nothing to undo")
    session.restore_polygons(restored)
    session.log("Undo", kind="info")
    return {"ok": True, "scene": _scene_payload(session), "counts": session.counts()}


@app.post("/redo")
async def redo_action(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    restored = session.history.redo(session.polygons)
    if restored is None:
        raise HTTPException(status_code=400, detail="Nothing to redo")
    session.restore_polygons(restored)
    session.log("Redo", kind="info")
    return {"ok": True, "scene": _scene_payload(session), "counts": session.counts()}


@app.post("/polygon/{polygon_id}/comment")
async def add_comment(
    polygon_id: int,
    body: CommentRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    session.comments.setdefault(polygon_id, []).append(
        {"user": session.current_user, "text": body.text, "at": datetime.now(timezone.utc).isoformat()}
    )
    session.log(f"Comment on polygon #{polygon_id}", kind="info")
    return {"ok": True, "comments": session.comments.get(polygon_id, [])}


@app.get("/polygon/{polygon_id}/comments")
async def get_comments(
    polygon_id: int,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    return {"comments": session.comments.get(polygon_id, [])}


@app.post("/markups")
async def add_markup(
    body: MarkupRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    markup = {
        "id": len(session.markups) + 1,
        "x": body.x,
        "y": body.y,
        "text": body.text,
        "user": session.current_user,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    session.markups.append(markup)
    session.log(f"Markup added at ({body.x:.1f}, {body.y:.1f})", kind="info")
    return {"ok": True, "markup": markup, "markups": session.markups}


@app.get("/markups")
async def list_markups(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    return {"markups": session.markups}


@app.get("/projects")
async def projects_list() -> dict[str, Any]:
    return {"projects": list_projects()}


@app.post("/projects")
async def projects_create(body: ProjectCreateRequest) -> dict[str, Any]:
    project = create_project(body.name)
    return {"ok": True, "project": project}


@app.get("/projects/{project_id}")
async def projects_get(project_id: str) -> dict[str, Any]:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@app.post("/projects/{project_id}/versions")
async def projects_save_version(
    project_id: str,
    body: VersionSaveRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    if not session.polygons:
        raise HTTPException(status_code=404, detail="No polygons to save")
    result = save_version(
        project_id,
        source_file=session.source_file,
        polygons=session.polygons,
        session_id=session.session_id,
        label=body.label,
    )
    session.project_id = project_id
    session.log(f"Saved version {result['version']['id']}", kind="success")
    return {"ok": True, **result}


@app.post("/projects/load-version")
async def projects_load_version(
    body: VersionLoadRequest,
    session: WorkspaceSession = Depends(_session_dep),
) -> dict[str, Any]:
    data = load_version(body.project_id, body.version_id)
    session.source_file = data.get("source_file", "")
    session.polygons = data.get("polygons", [])
    session.history.seed(session.polygons)
    session.project_id = body.project_id
    session.zones = []
    session.validation_result = None
    session.log(f"Loaded version {body.version_id}", kind="success")
    scene = _scene_payload(session)
    return {
        "ok": True,
        "scene": scene,
        "counts": session.counts(),
        "actions": _summary(session)["actions"],
    }


@app.post("/cloud/sync")
async def cloud_sync(session: WorkspaceSession = Depends(_session_dep)) -> dict[str, Any]:
    """Local cloud-sync stub — writes workspace snapshot to cloud folder."""
    if not session.polygons:
        raise HTTPException(status_code=404, detail="No workspace to sync")
    cloud_dir = WORKSPACE_OUTPUT / "cloud_sync"
    cloud_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(session.source_file).stem if session.source_file else "workspace"
    p = cloud_dir / f"{stem}_{session.session_id[:8]}.pjson"
    save_project_json(session.polygons, p, source_file=session.source_file, session_id=session.session_id)
    session.log("Cloud sync completed (local)", kind="success")
    return {"ok": True, "path": str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")}


if APP_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=APP_DIR), name="static")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "desktop.engine_sidecar.api:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    main()
