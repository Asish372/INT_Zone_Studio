"""P5 — INT zone schedule export (Excel + DXF layers)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from ezdxf import colors
from ezdxf.document import Drawing

from src.units import scale_factor
from src.zone_engine.int_labels import sort_bays_for_display
from src.zone_engine.models import IntZoneData, IntZonePipelineResult

logger = logging.getLogger(__name__)

INT_EXCEL_COLUMNS = [
    "Pour No.",
    "Concrete Area (SQM)",
    "Concrete Volume (CUM)",
    "Face Count",
    "Grid Ref",
    "Detection Tier",
    "Centroid X (m)",
    "Centroid Y (m)",
    "Union/Bay Coverage %",
]


def _int_zones_sorted(zones: list[IntZoneData]) -> list[IntZoneData]:
    return sorted(zones, key=lambda z: int(z.label.split("-")[1]))


def export_int_schedule_excel(
    zones: list[IntZoneData],
    output_path: str | Path,
    config: dict[str, Any],
) -> Path:
    """Export INT schedule matching QS PDF column semantics."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    unit = config.get("geometry", {}).get("drawing_unit", "mm")
    scale = scale_factor(unit)

    rows = []
    for zone in _int_zones_sorted(zones):
        cx = zone.polygon.centroid.x * scale if not zone.polygon.is_empty else 0.0
        cy = zone.polygon.centroid.y * scale if not zone.polygon.is_empty else 0.0
        rows.append(
            {
                "Pour No.": zone.label,
                "Concrete Area (SQM)": round(zone.area_m2, 4),
                "Concrete Volume (CUM)": round(zone.volume_m3, 4),
                "Face Count": zone.face_count,
                "Grid Ref": zone.grid_ref or "",
                "Detection Tier": zone.detection_tier,
                "Centroid X (m)": round(cx, 2),
                "Centroid Y (m)": round(cy, 2),
                "Union/Bay Coverage %": round(zone.bay_coverage_pct, 1),
            }
        )

    df = pd.DataFrame(rows, columns=INT_EXCEL_COLUMNS)
    if not df.empty:
        summary = {
            "Pour No.": "TOTAL",
            "Concrete Area (SQM)": df["Concrete Area (SQM)"].sum(),
            "Concrete Volume (CUM)": df["Concrete Volume (CUM)"].sum(),
            "Face Count": df["Face Count"].sum(),
            "Grid Ref": "",
            "Detection Tier": "",
            "Centroid X (m)": "",
            "Centroid Y (m)": "",
            "Union/Bay Coverage %": "",
        }
        df = pd.concat([df, pd.DataFrame([summary])], ignore_index=True)

    sheet_name = config.get("zone_engine", {}).get("int_excel_sheet", "INT Schedule")
    df.to_excel(path, index=False, sheet_name=sheet_name)
    logger.info("Exported INT schedule Excel: %s", path)
    return path


def _ensure_int_layers(doc: Drawing, config: dict[str, Any]) -> tuple[str, str]:
    zone_cfg = config.get("zone_engine", {})
    region_layer = zone_cfg.get("dxf_int_zone_layer", "INT_ZONES")
    label_layer = zone_cfg.get("dxf_int_label_layer", "INT_LABELS")

    for name, color in ((region_layer, 1), (label_layer, 2)):
        if name not in doc.layers:
            doc.layers.add(name, color=color)

    return region_layer, label_layer


def _text_height(config: dict[str, Any]) -> float:
    unit = config.get("geometry", {}).get("drawing_unit", "mm")
    if unit == "mm":
        return 300.0
    if unit == "cm":
        return 30.0
    return 0.3


def export_int_zones_dxf(
    doc: Drawing,
    zones: list[IntZoneData],
    output_path: str | Path,
    config: dict[str, Any],
) -> Path:
    """Write INT zone boundaries and labels to dedicated DXF layers."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    region_layer, label_layer = _ensure_int_layers(doc, config)
    msp = doc.modelspace()
    height = _text_height(config)

    for zone in _int_zones_sorted(zones):
        if zone.polygon.is_empty:
            continue
        coords = list(zone.polygon.exterior.coords)
        msp.add_lwpolyline(
            coords,
            close=True,
            dxfattribs={"layer": region_layer, "color": colors.CYAN},
        )
        cx, cy = zone.polygon.centroid.x, zone.polygon.centroid.y
        label_text = (
            f"{zone.label}\n"
            f"SQM: {zone.area_m2:.2f}\n"
            f"CUM: {zone.volume_m3:.2f}\n"
            f"Faces: {zone.face_count}"
        )
        msp.add_text(
            label_text,
            dxfattribs={
                "layer": label_layer,
                "height": height,
                "insert": (cx, cy),
            },
        )

    doc.saveas(str(path))
    logger.info("Exported INT zones DXF: %s", path)
    return path


def export_int_pipeline_outputs(
    doc: Drawing,
    pipeline: IntZonePipelineResult,
    paths: dict[str, Path],
    config: dict[str, Any],
) -> dict[str, Path]:
    """Export P5 INT schedule + optional coverage report path."""
    zone_cfg = config.get("zone_engine", {})
    written: dict[str, Path] = {}

    if zone_cfg.get("export_int_excel", True) and "int_excel" in paths:
        written["int_excel"] = export_int_schedule_excel(
            pipeline.zones,
            paths["int_excel"],
            config,
        )

    if zone_cfg.get("export_int_dxf", True) and "int_dxf" in paths:
        written["int_dxf"] = export_int_zones_dxf(
            doc,
            pipeline.zones,
            paths["int_dxf"],
            config,
        )

    return written
