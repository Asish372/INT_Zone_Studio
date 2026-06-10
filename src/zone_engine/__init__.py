"""INT Zone Engine — Stage 2 (grid frame, geometry, assignment, scheduling)."""

from src.zone_engine.bay_geometry import GridFrameGeometryResult, build_grid_frame_geometry
from src.zone_engine.face_assigner import assign_faces_to_bays, polygons_to_faces
from src.zone_engine.grid_frame import GridFrameResult, build_grid_frame
from src.zone_engine.grid_frame_report import write_grid_frame_report
from src.zone_engine.grid_frame_visualize import render_grid_frame_preview
from src.zone_engine.int_zone_pipeline import build_int_zone_pipeline, detect_faces_from_modelspace
from src.zone_engine.models import FaceData, IntZoneData, IntZonePipelineResult
from src.zone_engine.slab_outline import SlabOutlineResult, extract_slab_outline
from src.zone_engine.zone_aggregator import aggregate_int_zones
from src.zone_engine.zone_coverage_report import write_int_zone_report
from src.zone_engine.zone_mode import process_file_zones

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
