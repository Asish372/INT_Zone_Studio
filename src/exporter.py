"""Module 8: Export annotated DXF and Excel reports."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from ezdxf import colors
from ezdxf.document import Drawing

from src.units import scale_factor
from src.models import RegionData

logger = logging.getLogger(__name__)

EXCEL_COLUMNS = [
    "Region ID",
    "Label",
    "Area (m²)",
    "Perimeter (m)",
    "Volume (m³)",
    "Centroid X",
    "Centroid Y",
    "Source File",
]


def _ensure_layers(doc: Drawing, config: dict[str, Any]) -> tuple[str, str]:
    output_cfg = config.get("output", {})
    region_layer = output_cfg.get("dxf_region_layer", "DETECTED_REGIONS")
    label_layer = output_cfg.get("dxf_label_layer", "REGION_LABELS")

    for name, color in ((region_layer, 3), (label_layer, 2)):
        if name not in doc.layers:
            doc.layers.add(name, color=color)

    return region_layer, label_layer


def export_dxf(
    doc: Drawing,
    regions: list[RegionData],
    output_path: str | Path,
    config: dict[str, Any],
) -> Path:
    """Add region boundaries and labels to the DXF and save to a new file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    region_layer, label_layer = _ensure_layers(doc, config)
    msp = doc.modelspace()

    for region in regions:
        coords = list(region.polygon.exterior.coords)
        msp.add_lwpolyline(
            coords,
            close=True,
            dxfattribs={"layer": region_layer, "color": colors.GREEN},
        )
        cx, cy = region.centroid.x, region.centroid.y
        msp.add_text(
            region.label_text,
            dxfattribs={
                "layer": label_layer,
                "height": _text_height(config),
                "insert": (cx, cy),
            },
        )

    doc.saveas(str(path))
    logger.info("Exported annotated DXF: %s", path)
    return path


def _text_height(config: dict[str, Any]) -> float:
    unit = config.get("geometry", {}).get("drawing_unit", "mm")
    if unit == "mm":
        return 250.0
    if unit == "cm":
        return 25.0
    return 0.25


def export_excel(
    regions: list[RegionData],
    output_path: str | Path,
    config: dict[str, Any] | None = None,
) -> Path:
    """Export region metrics to an Excel file with a summary row."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    unit = "mm"
    if config:
        unit = config.get("geometry", {}).get("drawing_unit", "mm")
    scale = scale_factor(unit)

    rows = [
        {
            "Region ID": r.region_id,
            "Label": r.label,
            "Area (m²)": r.area_m2,
            "Perimeter (m)": r.perimeter_m,
            "Volume (m³)": r.volume_m3,
            "Centroid X": round(r.centroid.x * scale, 2),
            "Centroid Y": round(r.centroid.y * scale, 2),
            "Source File": Path(r.source_file).name,
        }
        for r in regions
    ]

    df = pd.DataFrame(rows, columns=EXCEL_COLUMNS)

    if not df.empty:
        summary = {
            "Region ID": "",
            "Label": "TOTAL",
            "Area (m²)": df["Area (m²)"].sum(),
            "Perimeter (m)": "",
            "Volume (m³)": df["Volume (m³)"].sum(),
            "Centroid X": "",
            "Centroid Y": "",
            "Source File": "",
        }
        df = pd.concat([df, pd.DataFrame([summary])], ignore_index=True)

    df.to_excel(path, index=False, sheet_name="Regions")
    logger.info("Exported Excel: %s", path)
    return path


def export_csv(
    regions: list[RegionData],
    output_path: str | Path,
    config: dict[str, Any] | None = None,
) -> Path:
    """Export region metrics to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    export_excel(regions, path.with_suffix(".xlsx"), config)
    df = pd.read_excel(path.with_suffix(".xlsx"))
    df.to_csv(path, index=False)
    return path


def export_results(
    doc: Drawing,
    regions: list[RegionData],
    paths: dict[str, Path],
    config: dict[str, Any],
) -> dict[str, Path]:
    """Export DXF and/or Excel based on config flags."""
    output_cfg = config.get("output", {})
    written: dict[str, Path] = {}

    if output_cfg.get("export_dxf", True) and "dxf" in paths:
        written["dxf"] = export_dxf(doc, regions, paths["dxf"], config)

    if output_cfg.get("export_excel", True) and "excel" in paths:
        written["excel"] = export_excel(regions, paths["excel"], config)

    if output_cfg.get("export_csv", False) and "csv" in paths:
        written["csv"] = export_csv(regions, paths["csv"], config)

    return written
