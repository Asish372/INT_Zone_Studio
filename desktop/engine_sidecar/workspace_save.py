"""Save corrected polygon sets from the workspace."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ezdxf import new as new_dxf
from shapely.geometry import Polygon


def active_polygons(polygons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for p in polygons if p.get("status", "active") != "deleted"]


def save_polygons_json(
    polygons: list[dict[str, Any]],
    output_path: Path | str,
    *,
    source_file: str = "",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    active = active_polygons(polygons)
    payload = {
        "source_file": source_file,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "polygon_count": len(active),
        "polygons": active,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def save_polygons_dxf(
    polygons: list[dict[str, Any]],
    output_path: Path | str,
    *,
    layer: str = "DETECTED_REGIONS",
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = new_dxf("R2010")
    if layer not in doc.layers:
        doc.layers.add(layer)
    msp = doc.modelspace()
    for poly in active_polygons(polygons):
        ring = poly.get("ring") or []
        if len(ring) < 3:
            continue
        msp.add_lwpolyline(ring, close=True, dxfattribs={"layer": layer})
    doc.saveas(str(path))
    return path


def save_polygons_csv(polygons: list[dict[str, Any]], output_path: Path | str) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for poly in active_polygons(polygons):
        centroid = poly.get("centroid") or [0, 0]
        rows.append(
            {
                "id": poly.get("id"),
                "source": poly.get("source"),
                "area_m2": poly.get("area_m2"),
                "perimeter_m": poly.get("perimeter_m"),
                "centroid_x": centroid[0] if len(centroid) > 0 else "",
                "centroid_y": centroid[1] if len(centroid) > 1 else "",
            }
        )
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["id", "source", "area_m2", "perimeter_m", "centroid_x", "centroid_y"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


WORKSPACE_FORMAT = "polygon_workspace_project"
WORKSPACE_VERSION = 2


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def build_workspace_payload(
    *,
    polygons: list[dict[str, Any]],
    source_file: str = "",
    source_file_path: str = "",
    session_id: str = "",
    workspace_path: str = "",
    expected_polygon_count: int | None = None,
    project_id: str | None = None,
    zones: list[dict[str, Any]] | None = None,
    validation: dict[str, Any] | None = None,
    comments: dict[int, list[dict[str, str]]] | None = None,
    markups: list[dict[str, Any]] | None = None,
    unit_label: str = "mm",
    current_user: str = "",
    current_role: str = "engineer",
) -> dict[str, Any]:
    return {
        "format": WORKSPACE_FORMAT,
        "version": WORKSPACE_VERSION,
        "session_id": session_id,
        "source_file": source_file,
        "source_file_path": source_file_path,
        "workspace_path": workspace_path,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "expected_polygon_count": expected_polygon_count,
        "project_id": project_id,
        "unit_label": unit_label,
        "current_user": current_user,
        "current_role": current_role,
        "polygons": polygons,
        "zones": zones or [],
        "validation": validation,
        "comments": {str(k): v for k, v in (comments or {}).items()},
        "markups": markups or [],
    }


def save_workspace_state(payload: dict[str, Any], output_path: Path | str) -> Path:
    path = Path(output_path).resolve()
    payload = {**payload, "workspace_path": str(path)}
    _atomic_write_text(path, json.dumps(payload, indent=2))
    return path


def load_workspace_state(path: Path | str) -> dict[str, Any]:
    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"Workspace file not found: {file_path}")
    data = json.loads(file_path.read_text(encoding="utf-8"))
    fmt = data.get("format")
    if fmt not in (WORKSPACE_FORMAT, "polygon_workspace_project"):
        raise ValueError(f"Unsupported workspace format: {fmt!r}")
    version = int(data.get("version", 1))
    if version > WORKSPACE_VERSION:
        raise ValueError(f"Unsupported workspace version: {version}")
    data["workspace_path"] = str(file_path)
    return data


def save_project_json(
    polygons: list[dict[str, Any]],
    output_path: Path | str,
    *,
    source_file: str = "",
    session_id: str = "",
) -> Path:
    payload = build_workspace_payload(
        polygons=polygons,
        source_file=source_file,
        session_id=session_id,
    )
    return save_workspace_state(payload, output_path)


def save_polygons_xlsx(polygons: list[dict[str, Any]], output_path: Path | str) -> Path:
    from openpyxl import Workbook

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Polygons"
    headers = [
        "id",
        "source",
        "review_status",
        "int_zone",
        "area_m2",
        "perimeter_m",
        "centroid_x",
        "centroid_y",
        "layer",
        "created_by",
    ]
    ws.append(headers)
    for poly in active_polygons(polygons):
        centroid = poly.get("centroid") or [0, 0]
        ws.append(
            [
                poly.get("id"),
                poly.get("source"),
                poly.get("review_status", "pending"),
                poly.get("int_zone") or "",
                poly.get("area_m2"),
                poly.get("perimeter_m"),
                centroid[0] if len(centroid) > 0 else "",
                centroid[1] if len(centroid) > 1 else "",
                poly.get("layer", ""),
                poly.get("created_by", ""),
            ]
        )
    wb.save(str(path))
    return path


def save_zones_dxf(
    zones: list[dict[str, Any]],
    polygons: list[dict[str, Any]],
    output_path: Path | str,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = new_dxf("R2010")
    layer = "INT_ZONES"
    if layer not in doc.layers:
        doc.layers.add(layer)
    msp = doc.modelspace()
    poly_by_id = {p["id"]: p for p in polygons}
    for zone in zones:
        for pid in zone.get("polygon_ids", []):
            rec = poly_by_id.get(pid)
            if not rec:
                continue
            ring = rec.get("ring") or []
            if len(ring) < 3:
                continue
            msp.add_lwpolyline(ring, close=True, dxfattribs={"layer": layer})
    doc.saveas(str(path))
    return path


def save_detection_report_pdf(
    output_path: Path | str,
    *,
    source_file: str,
    polygons: list[dict[str, Any]],
    validation: dict[str, Any] | None = None,
    zones: list[dict[str, Any]] | None = None,
) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    active = active_polygons(polygons)
    auto = sum(1 for p in active if p.get("source") == "auto")
    seed = sum(1 for p in active if p.get("source") == "seed")

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("INT Zone Studio — Detection Report", styles["Title"]),
        Spacer(1, 6 * mm),
        Paragraph(f"Source: {source_file or '—'}", styles["Normal"]),
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Total polygons: {len(active)} (Auto: {auto}, Recovered: {seed})",
            styles["Normal"],
        ),
    ]
    if validation:
        counts = validation.get("counts", {})
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Validation Summary", styles["Heading2"]))
        vdata = [["Check", "Count"]] + [
            [k.replace("_", " ").title(), str(v)] for k, v in counts.items()
        ]
        vt = Table(vdata, colWidths=[100 * mm, 40 * mm])
        vt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0078D4")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        story.append(vt)
    if zones:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"INT Zones: {len(zones)}", styles["Heading2"]))
        zdata = [["Zone", "Area (m²)", "Faces"]] + [
            [z["label"], f"{z.get('area_m2', 0):.2f}", str(z.get("face_count", 0))]
            for z in zones[:30]
        ]
        zt = Table(zdata, colWidths=[50 * mm, 50 * mm, 40 * mm])
        zt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        story.append(zt)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Polygon Schedule (first 50)", styles["Heading2"]))
    pdata = [["ID", "Source", "Area", "Perimeter", "Status"]]
    for p in active[:50]:
        pdata.append(
            [
                str(p.get("id")),
                str(p.get("source")),
                f"{p.get('area_m2', 0):.2f}",
                f"{p.get('perimeter_m', 0):.2f}",
                str(p.get("review_status", "pending")),
            ]
        )
    pt = Table(pdata, colWidths=[20 * mm, 30 * mm, 35 * mm, 35 * mm, 35 * mm])
    pt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(pt)
    doc.build(story)
    return path
