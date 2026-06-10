"""Run DXF → segments + auto polygons for the polygon workspace viewer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ezdxf.layouts import Modelspace
from shapely.geometry import LineString, Polygon

from src.detector import detect_regions
from src.endpoint_matching import DEFAULT_TIER2_STRUCTURAL_LAYERS
from src.extractor import extract_all_segments, extract_entities
from src.gap_handler import close_gaps, iterative_close_gaps
from src.layer_resolver import resolve_wall_layers
from src.converter import ensure_dxf
from src.parser import get_modelspace, load_dxf
from src.validation_diagnostics import (
    endpoint_layer_map,
    extract_tagged_segments,
    snap_tagged_endpoints,
)
from src.zone_engine.face_assigner import polygons_to_faces
from src.zone_engine.models import FaceData
from src.units import scale_factor


@dataclass
class DetectionResult:
    source_file: str
    segments: list[LineString]
    cad_segments: list[LineString]
    polygons: list[Polygon]
    faces: list[FaceData]
    unit_scale_m: float


def _prepare_segments(msp: Modelspace, config: dict[str, Any]) -> list[LineString]:
    """Mirror main.py segment preparation (snap + iterative gap close)."""
    layers_cfg = config.get("layers", {})
    ignore_layers = layers_cfg.get("ignore_layers", [])
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    if not resolution.wall_layers:
        return []

    accuracy_cfg = config.get("accuracy", {})
    arc_segments = int(accuracy_cfg.get("arc_segments", 64))
    tagged = extract_tagged_segments(
        msp, resolution.wall_layers, ignore_layers, arc_segments
    )
    if not tagged:
        return []

    geometry_cfg = config.get("geometry", {})
    snap_tol = float(geometry_cfg.get("snap_tolerance", 1))
    gap_threshold = float(geometry_cfg.get("gap_threshold", 500))
    max_angle = float(geometry_cfg.get("max_gap_angle", 30))
    colinear_profile = bool(geometry_cfg.get("colinear_profile_match", True))
    tier2_enabled = bool(geometry_cfg.get("tier2_threshold_enabled", False))
    tier2_threshold = float(geometry_cfg.get("tier2_gap_threshold", 1000))
    tier2_layers = frozenset(
        geometry_cfg.get("tier2_structural_layers", list(DEFAULT_TIER2_STRUCTURAL_LAYERS))
    )

    snapped = snap_tagged_endpoints(tagged, snap_tol)
    layers_map = endpoint_layer_map(snapped)
    segments = [t.line for t in snapped]

    iterative = bool(geometry_cfg.get("iterative_gap_close", True))
    max_passes = int(geometry_cfg.get("iterative_max_passes", 3))
    if iterative:
        segments, _ = iterative_close_gaps(
            segments,
            gap_threshold,
            max_angle,
            snap_tol=0.0,
            max_passes=max_passes,
            colinear_profile=colinear_profile,
            tier2_enabled=tier2_enabled,
            tier2_threshold=tier2_threshold,
            endpoint_layers=layers_map,
            structural_layers=tier2_layers,
        )
    else:
        segments, _ = close_gaps(
            segments, gap_threshold, max_angle, colinear_profile=colinear_profile
        )
        if tier2_enabled:
            from src.gap_handler import close_gaps_tier2

            segments, _ = close_gaps_tier2(
                segments,
                gap_threshold,
                tier2_threshold,
                max_angle,
                endpoint_layers=layers_map,
                structural_layers=tier2_layers,
                colinear_profile=colinear_profile,
            )
    return segments


def _cad_linework_segments(msp: Modelspace, config: dict[str, Any]) -> list[LineString]:
    """Raw wall-layer linework for gray background in viewer."""
    layers_cfg = config.get("layers", {})
    ignore_layers = layers_cfg.get("ignore_layers", [])
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    entities = extract_entities(msp, resolution.wall_layers, ignore_layers)
    if not entities:
        return []
    arc_segments = int(config.get("accuracy", {}).get("arc_segments", 64))
    return extract_all_segments(entities, arc_segments=arc_segments)


def detect_from_modelspace(
    msp: Modelspace,
    config: dict[str, Any],
    *,
    source_file: str = "",
) -> DetectionResult:
    """Detect all closed polygons from modelspace."""
    geometry_cfg = config.get("geometry", {})
    unit_scale_m = scale_factor(geometry_cfg.get("drawing_unit", "mm"))
    segments = _prepare_segments(msp, config)
    cad_segments = _cad_linework_segments(msp, config)
    polygons = detect_regions(segments, config) if segments else []
    faces = polygons_to_faces(polygons, unit_scale_m=unit_scale_m)
    return DetectionResult(
        source_file=source_file,
        segments=segments,
        cad_segments=cad_segments,
        polygons=polygons,
        faces=faces,
        unit_scale_m=unit_scale_m,
    )


def detect_from_dxf_path(dxf_path: Path | str, config: dict[str, Any]) -> DetectionResult:
    path = Path(dxf_path)
    msp = get_modelspace(load_dxf(path))
    return detect_from_modelspace(msp, config, source_file=path.name)


def detect_from_cad_path(
    cad_path: Path | str,
    config: dict[str, Any],
    *,
    cache_dir: Path | str | None = None,
    source_file: str | None = None,
) -> DetectionResult:
    """Detect polygons from a DXF or DWG file (DWG is converted via ODA cache)."""
    path = Path(cad_path)
    display_name = source_file or path.name
    if path.suffix.lower() == ".dxf":
        dxf_path = path
    else:
        cache = Path(cache_dir) if cache_dir else path.parent
        dxf_path = ensure_dxf(path, cache)
    msp = get_modelspace(load_dxf(dxf_path))
    return detect_from_modelspace(msp, config, source_file=display_name)
