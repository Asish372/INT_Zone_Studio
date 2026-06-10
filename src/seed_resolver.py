"""Seed-assisted region detection — smallest containing face strategy (P1)."""

from __future__ import annotations

import csv
import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.strtree import STRtree

from src.detector import filter_polygons, node_geometry, polygonize_regions, remove_duplicates
from src.endpoint_matching import DEFAULT_TIER2_STRUCTURAL_LAYERS
from src.gap_handler import close_gaps, extract_linestrings
from src.geometry_precision import normalize_polygon
from src.models import SeedRequest, SeedResolution
from src.units import scale_factor

logger = logging.getLogger(__name__)

SeedStatus = Literal[
    "ok",
    "ambiguous",
    "no_boundary",
    "outside_walls",
    "duplicate_of_auto",
    "invalid",
]

NESTED_AREA_RATIO = 0.85  # resolved face smaller than containing auto → keep as nested


def polygon_iou(a: Polygon, b: Polygon) -> float:
    """Intersection-over-union for two polygons."""
    if a.is_empty or b.is_empty or not a.intersects(b):
        return 0.0
    inter = a.intersection(b).area
    union = a.union(b).area
    return inter / union if union > 0 else 0.0


def _seed_assist_cfg(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("seed_assist", {})


def _interior_contains(polygon: Polygon, point: Point, epsilon: float) -> bool:
    """Treat boundary points as inside using a tiny buffer."""
    if polygon.contains(point):
        return True
    if epsilon <= 0:
        return False
    return polygon.buffer(epsilon).contains(point)


def _drawing_matches(seed_drawing: str, cad_name: str) -> bool:
    """Match seed drawing field to CAD filename or stem."""
    seed_lower = seed_drawing.lower().strip()
    name_lower = cad_name.lower().strip()
    stem_lower = Path(cad_name).stem.lower()
    return (
        seed_lower == name_lower
        or seed_lower == stem_lower
        or name_lower.startswith(seed_lower)
        or stem_lower.startswith(seed_lower)
        or seed_lower in name_lower
    )


def load_seeds(path: Path | str, *, drawing: str | None = None) -> list[SeedRequest]:
    """Parse JSON, YAML, or CSV seed file."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Seed file not found: {file_path}")

    suffix = file_path.suffix.lower()
    raw: Any
    if suffix in (".yaml", ".yml"):
        with file_path.open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    elif suffix == ".json":
        with file_path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
    elif suffix == ".csv":
        return _load_seeds_csv(file_path, drawing=drawing)
    else:
        raise ValueError(f"Unsupported seed file format: {suffix}")

    return _parse_seed_document(raw, drawing=drawing)


def _load_seeds_csv(path: Path, *, drawing: str | None = None) -> list[SeedRequest]:
    seeds: list[SeedRequest] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            row_drawing = (row.get("drawing") or drawing or "").strip()
            if not row_drawing:
                continue
            if drawing and not _drawing_matches(row_drawing, drawing):
                continue
            seeds.append(
                SeedRequest(
                    drawing=row_drawing,
                    x=float(row["x"]),
                    y=float(row["y"]),
                    label_hint=row.get("label_hint") or None,
                    id=row.get("id") or None,
                )
            )
    return seeds


def _parse_seed_document(raw: Any, *, drawing: str | None = None) -> list[SeedRequest]:
    seeds: list[SeedRequest] = []

    if isinstance(raw, list):
        entries = raw
    elif isinstance(raw, dict):
        if "seeds" in raw:
            entries = [{"drawing": raw.get("drawing", drawing or ""), **s} for s in raw["seeds"]]
        elif "drawings" in raw:
            entries = []
            for block in raw["drawings"]:
                block_name = block.get("drawing", "")
                for s in block.get("seeds", []):
                    entries.append({"drawing": block_name, **s})
        else:
            entries = [raw]
    else:
        raise ValueError("Seed file must be a dict or list")

    for item in entries:
        if not isinstance(item, dict):
            continue
        row_drawing = str(item.get("drawing", drawing or "")).strip()
        if not row_drawing:
            if drawing:
                row_drawing = drawing
            else:
                continue
        if drawing and not _drawing_matches(row_drawing, drawing):
            continue
        seeds.append(
            SeedRequest(
                drawing=row_drawing,
                x=float(item["x"]),
                y=float(item["y"]),
                label_hint=item.get("label_hint"),
                id=item.get("id"),
            )
        )
    return seeds


def filter_seeds_for_drawing(seeds: list[SeedRequest], cad_name: str) -> list[SeedRequest]:
    """Return seeds whose drawing field matches the CAD file."""
    return [s for s in seeds if _drawing_matches(s.drawing, cad_name)]


def _crop_segments(
    segments: list[LineString],
    point: Point,
    radius: float,
) -> list[LineString]:
    if radius <= 0 or not segments:
        return segments

    tree = STRtree(segments)
    query_geom = point.buffer(radius)
    indices = tree.query(query_geom)
    cropped: list[LineString] = []
    for idx in indices:
        seg = segments[int(idx)]
        if seg.intersects(query_geom):
            cropped.append(seg)
    return cropped if cropped else segments


def _find_containing_faces(
    point: Point,
    segments: list[LineString],
    *,
    interior_epsilon: float,
) -> list[Polygon]:
    if not segments:
        return []

    multi = MultiLineString(segments)
    noded = node_geometry(multi)
    raw_faces = polygonize_regions(noded)

    matches: list[Polygon] = []
    for face in raw_faces:
        normalized = normalize_polygon(face)
        if normalized is None:
            continue
        if _interior_contains(normalized, point, interior_epsilon):
            matches.append(normalized)
    return matches


def _is_duplicate_of_auto(
    resolved: Polygon,
    point: Point,
    auto_polygons: list[Polygon],
    iou_threshold: float,
) -> tuple[bool, str]:
    """Return whether seed polygon duplicates an auto-detected region."""
    for idx, auto in enumerate(auto_polygons, start=1):
        iou = polygon_iou(resolved, auto)
        if iou >= iou_threshold:
            return True, f"IoU {iou:.3f} with auto region #{idx} (threshold {iou_threshold})"

        if _interior_contains(auto, point, 0.0):
            if resolved.area >= auto.area * NESTED_AREA_RATIO:
                return True, f"Seed lies in auto region #{idx} with similar area"
            # Nested: smaller interior face — keep seed
    return False, ""


@dataclass
class MergedPolygon:
    """Polygon with detection provenance for downstream compute/export."""

    polygon: Polygon
    detection_method: str = "auto"
    seed_id: str | None = None
    seed_x: float | None = None
    seed_y: float | None = None
    label_hint: str | None = None


def _local_gap_repair_segments(
    segments: list[LineString],
    point: Point,
    search_radius: float,
    config: dict[str, Any],
    endpoint_layers: dict[tuple[float, float], str] | None = None,
) -> tuple[list[LineString], int]:
    """
    P2: localized gap closure on cropped segments only.

    Re-runs tier-1 + expanded tier-2 matching within search_radius without
    modifying the global segment network passed to auto detection.
    """
    cfg = _seed_assist_cfg(config)
    if not bool(cfg.get("local_repair_enabled", True)):
        return _crop_segments(segments, point, search_radius), 0

    geometry_cfg = config.get("geometry", {})
    cropped = _crop_segments(segments, point, search_radius)
    if not cropped:
        return [], 0

    gap_threshold = float(geometry_cfg.get("gap_threshold", 500))
    max_angle = float(geometry_cfg.get("max_gap_angle", 30))
    multiplier = float(cfg.get("local_gap_multiplier", 2.0))
    max_cap = float(cfg.get("local_repair_max_gap", 1200.0))
    structural_only = bool(cfg.get("local_repair_structural_only", True))
    reject_crossing = bool(cfg.get("local_repair_reject_crossing", False))
    colinear = bool(geometry_cfg.get("colinear_profile_match", True))

    local_tier2 = min(gap_threshold * multiplier, max_cap)
    tier2_layers = frozenset(
        geometry_cfg.get("tier2_structural_layers", list(DEFAULT_TIER2_STRUCTURAL_LAYERS))
    )
    layers = endpoint_layers if structural_only else None

    if structural_only and not endpoint_layers:
        # No layer metadata — single elevated threshold pass (tests / legacy paths)
        repaired, closed = close_gaps(
            cropped,
            local_tier2,
            max_angle,
            colinear_profile=colinear,
            tier2_enabled=False,
            reject_tier2_crossing=reject_crossing,
        )
    else:
        repaired, closed = close_gaps(
            cropped,
            gap_threshold,
            max_angle,
            colinear_profile=colinear,
            tier2_enabled=True,
            tier2_threshold=local_tier2,
            endpoint_layers=layers,
            structural_layers=tier2_layers,
            reject_tier2_crossing=reject_crossing,
        )

    if closed > 0:
        repaired = extract_linestrings(MultiLineString(repaired))

    if closed > 0:
        logger.info(
            "Local gap repair near (%.1f, %.1f): %d bridge(s), tier2=%.0f mm",
            point.x,
            point.y,
            closed,
            local_tier2,
        )
    return repaired, closed


def resolve_seed_region(
    seed: SeedRequest,
    segments: list[LineString],
    config: dict[str, Any],
    auto_polygons: list[Polygon] | None = None,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
) -> SeedResolution:
    """Resolve one seed to the smallest containing polygon face."""
    cfg = _seed_assist_cfg(config)
    geometry_cfg = config.get("geometry", {})
    accuracy_cfg = config.get("accuracy", {})
    unit = geometry_cfg.get("drawing_unit", "mm")
    scale = scale_factor(unit)

    search_radius = float(cfg.get("search_radius", 5000))
    interior_epsilon = float(cfg.get("interior_epsilon", 1.0))
    dedupe_iou = float(cfg.get("dedupe_iou_threshold", 0.90))
    min_area_m2 = float(cfg.get("min_area_m2", accuracy_cfg.get("exhaustive_min_area_m2", 0.01)))
    exhaustive = str(accuracy_cfg.get("detection_mode", "exhaustive")).lower() == "exhaustive"

    if not math.isfinite(seed.x) or not math.isfinite(seed.y):
        return SeedResolution(
            seed=seed,
            polygon=None,
            status="invalid",
            message="Seed coordinates must be finite numbers",
            area_m2_drawing=None,
        )

    point = Point(seed.x, seed.y)
    auto_polygons = auto_polygons or []

    cropped = _crop_segments(segments, point, search_radius)
    faces = _find_containing_faces(point, cropped, interior_epsilon=interior_epsilon)
    repair_bridges = 0

    if not faces and bool(cfg.get("local_repair_enabled", True)):
        repaired, repair_bridges = _local_gap_repair_segments(
            segments,
            point,
            search_radius,
            config,
            endpoint_layers=endpoint_layers,
        )
        faces = _find_containing_faces(
            point, repaired, interior_epsilon=interior_epsilon
        )

    if not faces:
        return SeedResolution(
            seed=seed,
            polygon=None,
            status="no_boundary",
            message=(
                f"No closed face contains seed ({seed.x:.3f}, {seed.y:.3f}) "
                f"within search_radius={search_radius}"
                + (
                    f" (local repair bridged {repair_bridges} gap(s))"
                    if repair_bridges
                    else ""
                )
            ),
            area_m2_drawing=None,
            repair_bridges=repair_bridges,
        )

    if len(faces) > 1:
        smallest = min(faces, key=lambda p: p.area)
        logger.debug(
            "Seed %s: %d containing faces; selected smallest (area=%.3f)",
            seed.id or "anonymous",
            len(faces),
            smallest.area,
        )
    else:
        smallest = faces[0]

    filtered = filter_polygons([smallest], min_area_m2, unit, exhaustive=exhaustive)
    if not filtered:
        area_m2 = smallest.area * (scale**2)
        return SeedResolution(
            seed=seed,
            polygon=None,
            status="no_boundary",
            message=f"Resolved face below min_area_m2={min_area_m2} (area={area_m2:.6f} m²)",
            area_m2_drawing=area_m2,
        )

    resolved = filtered[0]
    area_m2 = resolved.area * (scale**2)

    is_dup, dup_msg = _is_duplicate_of_auto(resolved, point, auto_polygons, dedupe_iou)
    if is_dup:
        return SeedResolution(
            seed=seed,
            polygon=resolved,
            status="duplicate_of_auto",
            message=dup_msg,
            area_m2_drawing=area_m2,
        )

    return SeedResolution(
        seed=seed,
        polygon=resolved,
        status="ok",
        message=(
            f"{'Local repair + ' if repair_bridges else ''}"
            f"smallest containing face area={area_m2:.4f} m²"
            + (f" ({repair_bridges} local bridge(s))" if repair_bridges else "")
        ),
        area_m2_drawing=area_m2,
        repair_bridges=repair_bridges,
    )


def resolve_all_seeds(
    seeds: list[SeedRequest],
    segments: list[LineString],
    config: dict[str, Any],
    auto_polygons: list[Polygon] | None = None,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
) -> list[SeedResolution]:
    """Resolve each seed and dedupe against auto + prior accepted seeds."""
    cfg = _seed_assist_cfg(config)
    allow_duplicate_seed = bool(cfg.get("allow_duplicate_seed", False))
    dedupe_iou = float(cfg.get("dedupe_iou_threshold", 0.90))

    auto_polygons = list(auto_polygons or [])
    accepted: list[Polygon] = []
    resolutions: list[SeedResolution] = []
    seen_points: set[tuple[float, float]] = set()

    for seed in seeds:
        key = (round(seed.x, 3), round(seed.y, 3))
        if key in seen_points and not allow_duplicate_seed:
            resolutions.append(
                SeedResolution(
                    seed=seed,
                    polygon=None,
                    status="duplicate_of_auto",
                    message="Duplicate seed coordinates in input file",
                    area_m2_drawing=None,
                )
            )
            continue
        seen_points.add(key)

        resolution = resolve_seed_region(
            seed, segments, config, auto_polygons, endpoint_layers
        )
        if resolution.status == "ok" and resolution.polygon is not None:
            for prior in accepted:
                if polygon_iou(resolution.polygon, prior) >= dedupe_iou:
                    resolution = SeedResolution(
                        seed=seed,
                        polygon=resolution.polygon,
                        status="duplicate_of_auto",
                        message="Seed polygon overlaps prior seed resolution",
                        area_m2_drawing=resolution.area_m2_drawing,
                    )
                    break
            else:
                accepted.append(resolution.polygon)
                auto_polygons.append(resolution.polygon)

        resolutions.append(resolution)
        logger.info(
            "Seed %s (%s): status=%s — %s",
            seed.id or "anonymous",
            seed.label_hint or "",
            resolution.status,
            resolution.message,
        )

    return resolutions


def merge_regions(
    auto_polygons: list[Polygon],
    seed_resolutions: list[SeedResolution],
    config: dict[str, Any],
) -> list[MergedPolygon]:
    """Merge auto-detected polygons with accepted seed-assisted regions."""
    cfg = _seed_assist_cfg(config)
    dedupe_iou = float(cfg.get("dedupe_iou_threshold", 0.90))

    merged: list[MergedPolygon] = [
        MergedPolygon(polygon=p, detection_method="auto") for p in auto_polygons
    ]

    seed_polys: list[Polygon] = []
    for res in seed_resolutions:
        if res.status != "ok" or res.polygon is None:
            continue
        seed_polys.append(res.polygon)
        merged.append(
            MergedPolygon(
                polygon=res.polygon,
                detection_method=(
                    "seed_assisted_local_repair"
                    if res.repair_bridges > 0
                    else "seed_assisted"
                ),
                seed_id=res.seed.id,
                seed_x=res.seed.x,
                seed_y=res.seed.y,
                label_hint=res.seed.label_hint,
            )
        )

    if not seed_polys:
        return merged

    all_polys = [m.polygon for m in merged]
    deduped = remove_duplicates(all_polys, iou_threshold=dedupe_iou)
    if len(deduped) == len(all_polys):
        return merged

    # Rebuild provenance after dedupe — prefer auto over seed on collision
    kept: list[MergedPolygon] = []
    for poly in deduped:
        provenance = next((m for m in merged if polygon_iou(m.polygon, poly) >= dedupe_iou), None)
        if provenance is None:
            provenance = MergedPolygon(polygon=poly, detection_method="auto")
        else:
            provenance = MergedPolygon(
                polygon=poly,
                detection_method=provenance.detection_method,
                seed_id=provenance.seed_id,
                seed_x=provenance.seed_x,
                seed_y=provenance.seed_y,
                label_hint=provenance.label_hint,
            )
        kept.append(provenance)
    return kept
