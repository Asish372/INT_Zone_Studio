"""Data models for detected regions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from shapely.geometry import Point, Polygon


@dataclass
class SeedRequest:
    """User-supplied interior point for seed-assisted detection."""

    drawing: str
    x: float
    y: float
    label_hint: str | None = None
    id: str | None = None


SeedStatus = Literal[
    "ok",
    "ambiguous",
    "no_boundary",
    "outside_walls",
    "duplicate_of_auto",
    "invalid",
]


@dataclass
class SeedResolution:
    """Result of resolving one seed against the segment network."""

    seed: SeedRequest
    polygon: Polygon | None
    status: SeedStatus
    message: str
    area_m2_drawing: float | None = None
    repair_bridges: int = 0


@dataclass
class RegionData:
    """Metrics and metadata for one detected enclosed region."""

    region_id: int
    label: str
    polygon: Polygon
    area_m2: float
    perimeter_m: float
    volume_m3: float
    centroid: Point
    label_text: str
    source_file: str
    detection_method: str = "auto"
    seed_x: float | None = None
    seed_y: float | None = None
    seed_id: str | None = None
