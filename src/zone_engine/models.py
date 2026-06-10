"""Data models for INT zone assignment (Stage 2 / P3)."""

from __future__ import annotations

from dataclasses import dataclass, field

from shapely.geometry import Polygon


@dataclass
class FaceData:
    """Stage 1 micro-polygon before zone rollup."""

    face_id: int
    polygon: Polygon
    area_m2: float


@dataclass
class FaceAssignment:
    """Mapping of one micro-face to an INT bay cell."""

    face_id: int
    int_label: str
    bay_id: int
    intersection_area_m2: float
    method: str


@dataclass
class OrphanFace:
    """Face that could not be assigned to a bay cell."""

    face_id: int
    area_m2: float
    reason: str
    nearest_int_label: str | None = None


@dataclass
class FaceAssignmentSummary:
    """Aggregate statistics from face-to-bay assignment."""

    total_faces: int
    sliver_count: int
    assigned_count: int
    orphan_count: int
    assignments: list[FaceAssignment]
    orphans: list[OrphanFace]
    method: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class IntZoneData:
    """QS pour zone after unary_union of assigned micro-faces."""

    zone_id: int
    label: str
    polygon: Polygon
    area_m2: float
    volume_m3: float
    face_ids: list[int]
    face_count: int
    face_sum_area_m2: float
    clipped_bay_area_m2: float
    bay_coverage_pct: float
    profile: str
    detection_tier: str
    grid_ref: str | None
    source_file: str


@dataclass
class ManifestZoneRow:
    """One row from reference manifest YAML."""

    label: str
    area_sqm: float | None
    volume_cum: float | None
    grid_ref: str | None
    notes: str | None


@dataclass
class ManifestZoneComparison:
    """Per-zone comparison of computed vs manifest area."""

    label: str
    computed_area_sqm: float
    manifest_area_sqm: float | None
    delta_sqm: float | None
    delta_pct: float | None
    within_tolerance: bool | None
    face_count: int
    has_assigned_faces: bool


@dataclass
class ManifestReconciliation:
    """Manifest vs engine reconciliation summary."""

    project: str
    profile: str
    transcription_status: str
    expected_zone_count: int
    computed_zone_count: int
    zone_count_match: bool
    area_tolerance_pct: float
    comparisons: list[ManifestZoneComparison]
    total_computed_sqm: float
    total_manifest_sqm: float | None
    total_delta_pct: float | None
    zones_with_manifest_area: int
    zones_within_tolerance: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class ProductionReadinessGate:
    """Single acceptance gate for P3 production assessment."""

    name: str
    status: str  # PASS | FAIL | REVIEW | SKIP
    detail: str


@dataclass
class IntZonePipelineResult:
    """Full P2 geometry + P3 zone assignment output."""

    geometry: object  # GridFrameGeometryResult — avoid circular import in type hints
    zones: list[IntZoneData]
    assignment: FaceAssignmentSummary
    manifest: ManifestReconciliation | None
    readiness: list[ProductionReadinessGate]
    warnings: list[str] = field(default_factory=list)
