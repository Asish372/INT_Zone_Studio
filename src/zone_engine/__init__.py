"""INT Zone Engine — Stage 2 (grid frame, geometry, assignment, scheduling)."""

from __future__ import annotations

from typing import Any

__all__ = [
    "GridFrameResult",
    "GridFrameGeometryResult",
    "SlabOutlineResult",
    "FaceData",
    "IntZoneData",
    "IntZonePipelineResult",
    "build_grid_frame",
    "build_grid_frame_geometry",
    "build_int_zone_pipeline",
    "detect_faces_from_modelspace",
    "extract_slab_outline",
    "assign_faces_to_bays",
    "polygons_to_faces",
    "aggregate_int_zones",
    "write_grid_frame_report",
    "write_int_zone_report",
    "render_grid_frame_preview",
    "process_file_zones",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "GridFrameResult": ("src.zone_engine.grid_frame", "GridFrameResult"),
    "build_grid_frame": ("src.zone_engine.grid_frame", "build_grid_frame"),
    "GridFrameGeometryResult": ("src.zone_engine.bay_geometry", "GridFrameGeometryResult"),
    "build_grid_frame_geometry": ("src.zone_engine.bay_geometry", "build_grid_frame_geometry"),
    "SlabOutlineResult": ("src.zone_engine.slab_outline", "SlabOutlineResult"),
    "extract_slab_outline": ("src.zone_engine.slab_outline", "extract_slab_outline"),
    "FaceData": ("src.zone_engine.models", "FaceData"),
    "IntZoneData": ("src.zone_engine.models", "IntZoneData"),
    "IntZonePipelineResult": ("src.zone_engine.models", "IntZonePipelineResult"),
    "assign_faces_to_bays": ("src.zone_engine.face_assigner", "assign_faces_to_bays"),
    "polygons_to_faces": ("src.zone_engine.face_assigner", "polygons_to_faces"),
    "build_int_zone_pipeline": ("src.zone_engine.int_zone_pipeline", "build_int_zone_pipeline"),
    "detect_faces_from_modelspace": (
        "src.zone_engine.int_zone_pipeline",
        "detect_faces_from_modelspace",
    ),
    "aggregate_int_zones": ("src.zone_engine.zone_aggregator", "aggregate_int_zones"),
    "write_grid_frame_report": ("src.zone_engine.grid_frame_report", "write_grid_frame_report"),
    "write_int_zone_report": ("src.zone_engine.zone_coverage_report", "write_int_zone_report"),
    "render_grid_frame_preview": (
        "src.zone_engine.grid_frame_visualize",
        "render_grid_frame_preview",
    ),
    "process_file_zones": ("src.zone_engine.zone_mode", "process_file_zones"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = __import__(module_name, fromlist=[attr_name])
    return getattr(module, attr_name)
