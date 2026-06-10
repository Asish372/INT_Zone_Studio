"""Validation-phase diagnostics (detection recall & accuracy). No product UI."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace
from shapely.geometry import LineString, MultiLineString, Polygon

from src.detector import filter_polygons, polygonize_regions, remove_duplicates
from src.extractor import SUPPORTED_TYPES, entity_to_segments, extract_entities
from src.endpoint_matching import DEFAULT_TIER2_STRUCTURAL_LAYERS
from src.gap_handler import _round_point, close_gaps, iterative_close_gaps, snap_endpoints
from src.geometry_precision import normalize_polygon
from src.layer_resolver import suggest_candidate_wall_layers
from src.parser import get_modelspace
from src.units import scale_factor


@dataclass
class TaggedSegment:
    line: LineString
    layer: str


@dataclass
class DrawingDiagnostics:
    source_path: str
    dxf_path: str
    conversion_note: str
    total_entities: int = 0
    entity_type_counts: dict[str, int] = field(default_factory=dict)
    layer_entity_counts: dict[str, int] = field(default_factory=dict)
    layer_geometry_counts: dict[str, int] = field(default_factory=dict)
    candidate_wall_layers: list[str] = field(default_factory=list)
    configured_wall_layers: list[str] = field(default_factory=list)
    configured_entities: int = 0
    configured_segments: int = 0
    candidate_entities: int = 0
    candidate_segments: int = 0
    open_endpoints_before_close: int = 0
    open_endpoints_after_close: int = 0
    gaps_closed: int = 0
    raw_polygon_count: int = 0
    invalid_polygon_count: int = 0
    regions_detected: int = 0
    regions_with_candidate_layers: int = 0
    candidate_largest_area_m2: float | None = None
    candidate_smallest_area_m2: float | None = None
    candidate_total_area_m2: float = 0.0
    largest_area_m2: float | None = None
    smallest_area_m2: float | None = None
    total_detected_area_m2: float = 0.0
    error: str | None = None


@dataclass
class GapRecord:
    drawing: str
    endpoint_a_x: float
    endpoint_a_y: float
    endpoint_b_x: float
    endpoint_b_y: float
    gap_distance: float
    layer_a: str
    layer_b: str
    within_current_threshold: bool
    suggested_closure_threshold: float
    status: str


def scan_modelspace(msp: Modelspace) -> tuple[int, dict[str, int], dict[str, int], dict[str, int]]:
    """Count all entities, types, layers, and boundary-geometry per layer."""
    entity_type_counts: Counter[str] = Counter()
    layer_entity_counts: Counter[str] = Counter()
    layer_geometry_counts: Counter[str] = Counter()

    total = 0
    for entity in msp:
        total += 1
        dxftype = entity.dxftype()
        layer = entity.dxf.layer or "0"
        entity_type_counts[dxftype] += 1
        layer_entity_counts[layer] += 1
        if dxftype in SUPPORTED_TYPES:
            layer_geometry_counts[layer] += 1

    return (
        total,
        dict(entity_type_counts),
        dict(layer_entity_counts),
        dict(layer_geometry_counts),
    )


def extract_tagged_segments(
    msp: Modelspace,
    layers: list[str] | None,
    ignore_layers: list[str],
    arc_segments: int,
) -> list[TaggedSegment]:
    """Extract segments with layer tags. None/empty layers = all non-ignored layers."""
    layer_set = {name.upper() for name in layers} if layers else None
    ignore_set = {name.upper() for name in ignore_layers}
    tagged: list[TaggedSegment] = []

    for entity in msp:
        if entity.dxftype() not in SUPPORTED_TYPES:
            continue
        layer_name = entity.dxf.layer or "0"
        if layer_name.upper() in ignore_set:
            continue
        if layer_set and layer_name.upper() not in layer_set:
            continue
        for seg in entity_to_segments(entity, arc_segments):
            tagged.append(TaggedSegment(line=seg, layer=layer_name))
    return tagged


def snap_tagged_endpoints(tagged: list[TaggedSegment], tol: float) -> list[TaggedSegment]:
    """Snap endpoints while preserving layer tags on each segment."""
    if not tagged or tol <= 0:
        return tagged

    lines = [t.line for t in tagged]
    snapped = snap_endpoints(lines, tol)
    return [
        TaggedSegment(line=snapped[i], layer=tagged[i].layer)
        for i in range(len(tagged))
    ]


def close_gaps_tagged(
    tagged: list[TaggedSegment],
    threshold: float,
    max_angle: float,
) -> tuple[list[TaggedSegment], int]:
    """Close gaps on line geometry; bridge segments tagged as GAP_BRIDGE."""
    lines = [t.line for t in tagged]
    closed_lines, count = close_gaps(lines, threshold, max_angle)
    result = list(tagged)
    for bridge in closed_lines[len(lines) :]:
        result.append(TaggedSegment(line=bridge, layer="GAP_BRIDGE"))
    return result, count


def count_open_endpoints(tagged: list[TaggedSegment]) -> int:
    """Count degree-1 endpoints in the segment network."""
    counts: dict[tuple[float, float], int] = defaultdict(int)
    for item in tagged:
        coords = list(item.line.coords)
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        counts[a] += 1
        counts[b] += 1
    return sum(1 for c in counts.values() if c == 1)


def _endpoint_segment_map(tagged: list[TaggedSegment]) -> dict[tuple[float, float], frozenset[int]]:
    """Map endpoints to source segment indices (for cross-segment gap pairing)."""
    seg_ids: dict[tuple[float, float], set[int]] = defaultdict(set)
    for idx, item in enumerate(tagged):
        if item.layer == "GAP_BRIDGE":
            continue
        coords = list(item.line.coords)
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        seg_ids[a].add(idx)
        seg_ids[b].add(idx)
    return {pt: frozenset(ids) for pt, ids in seg_ids.items()}


def endpoint_layer_map(tagged: list[TaggedSegment]) -> dict[tuple[float, float], str]:
    layers_at: dict[tuple[float, float], set[str]] = defaultdict(set)
    for item in tagged:
        if item.layer == "GAP_BRIDGE":
            continue
        coords = list(item.line.coords)
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        layers_at[a].add(item.layer)
        layers_at[b].add(item.layer)
    return {pt: sorted(names)[0] for pt, names in layers_at.items()}


def analyze_gaps(
    tagged: list[TaggedSegment],
    drawing_name: str,
    gap_threshold: float,
    max_pair_distance: float = 10000.0,
) -> list[GapRecord]:
    """Pair free endpoints after snap; report gaps for recall tuning."""
    counts: dict[tuple[float, float], int] = defaultdict(int)
    for item in tagged:
        if item.layer == "GAP_BRIDGE":
            continue
        coords = list(item.line.coords)
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        counts[a] += 1
        counts[b] += 1

    free_points = [pt for pt, c in counts.items() if c == 1]
    layers_map = endpoint_layer_map(tagged)
    segment_map = _endpoint_segment_map(tagged)
    records: list[GapRecord] = []
    used: set[int] = set()

    for i, p1 in enumerate(free_points):
        if i in used:
            continue
        best_j = -1
        best_dist = max_pair_distance + 1
        seg1 = segment_map.get(p1, frozenset())

        for j, p2 in enumerate(free_points):
            if j <= i or j in used:
                continue
            if seg1 and seg1 & segment_map.get(p2, frozenset()):
                continue
            dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
            if dist < 1e-9 or dist > max_pair_distance:
                continue
            if dist < best_dist:
                best_dist = dist
                best_j = j

        if best_j < 0:
            records.append(
                GapRecord(
                    drawing=drawing_name,
                    endpoint_a_x=p1[0],
                    endpoint_a_y=p1[1],
                    endpoint_b_x=float("nan"),
                    endpoint_b_y=float("nan"),
                    gap_distance=float("nan"),
                    layer_a=layers_map.get(p1, "unknown"),
                    layer_b="",
                    within_current_threshold=False,
                    suggested_closure_threshold=gap_threshold,
                    status="orphan_endpoint",
                )
            )
            used.add(i)
            continue

        p2 = free_points[best_j]
        used.add(i)
        used.add(best_j)
        within = best_dist <= gap_threshold
        suggested = gap_threshold if within else math.ceil(best_dist / 100.0) * 100.0
        if suggested < best_dist:
            suggested = math.ceil(best_dist)

        if within:
            status = "within_threshold_unclosed"
        elif best_dist <= gap_threshold * 2:
            status = "above_threshold_close"
        else:
            status = "large_gap_manual_review"

        records.append(
            GapRecord(
                drawing=drawing_name,
                endpoint_a_x=p1[0],
                endpoint_a_y=p1[1],
                endpoint_b_x=p2[0],
                endpoint_b_y=p2[1],
                gap_distance=round(best_dist, 3),
                layer_a=layers_map.get(p1, "unknown"),
                layer_b=layers_map.get(p2, "unknown"),
                within_current_threshold=within,
                suggested_closure_threshold=suggested,
                status=status,
            )
        )

    return records


@dataclass
class GapFailureDetail:
    """Why a within-threshold endpoint pair was not bridged by close_gaps."""

    drawing: str
    endpoint_a_x: float
    endpoint_a_y: float
    endpoint_b_x: float
    endpoint_b_y: float
    gap_distance: float
    layer_a: str
    layer_b: str
    gap_threshold: float
    max_gap_angle: float
    endpoint_a_bearing_deg: float
    endpoint_b_bearing_deg: float
    bridge_bearing_deg: float
    bearing_delta_deg: float
    failure_reason: str
    note: str


def _endpoint_bearings(tagged: list[TaggedSegment]) -> dict[tuple[float, float], list[float]]:
    """Map rounded free endpoints to segment departure bearings (degrees)."""
    bearings: dict[tuple[float, float], list[float]] = defaultdict(list)
    for item in tagged:
        if item.layer == "GAP_BRIDGE":
            continue
        coords = list(item.line.coords)
        if len(coords) < 2:
            continue
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        bearings[a].append(
            math.degrees(math.atan2(coords[1][1] - coords[0][1], coords[1][0] - coords[0][0]))
        )
        bearings[b].append(
            math.degrees(
                math.atan2(coords[-2][1] - coords[-1][1], coords[-2][0] - coords[-1][0])
            )
        )
    return bearings


def _nearest_free_neighbor(
    point: tuple[float, float],
    free_points: list[tuple[float, float]],
    exclude: tuple[float, float],
) -> tuple[float, float] | None:
    best: tuple[float, float] | None = None
    best_dist = float("inf")
    for other in free_points:
        if other == point or other == exclude:
            continue
        dist = math.hypot(point[0] - other[0], point[1] - other[1])
        if dist < best_dist:
            best_dist = dist
            best = other
    return best


def explain_within_threshold_unclosed(
    tagged: list[TaggedSegment],
    drawing_name: str,
    gap_threshold: float,
    max_gap_angle: float,
) -> list[GapFailureDetail]:
    """
    For pairs flagged within_threshold_unclosed, explain likely closure failure.

    Primary cause in practice: greedy endpoint pairing in close_gaps — an endpoint
    is matched to a different neighbor first, leaving a within-threshold pair open.
    """
    geometry_cfg_bearings = _endpoint_bearings(tagged)
    gaps = [g for g in analyze_gaps(tagged, drawing_name, gap_threshold) if g.status == "within_threshold_unclosed"]
    details: list[GapFailureDetail] = []

    counts: dict[tuple[float, float], int] = defaultdict(int)
    for item in tagged:
        if item.layer == "GAP_BRIDGE":
            continue
        coords = list(item.line.coords)
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        counts[a] += 1
        counts[b] += 1
    free_points = [pt for pt, c in counts.items() if c == 1]

    for gap in gaps:
        p1 = (gap.endpoint_a_x, gap.endpoint_a_y)
        p2 = (gap.endpoint_b_x, gap.endpoint_b_y)
        bridge_bearing = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
        a_bearings = geometry_cfg_bearings.get(p1, [0.0])
        b_bearings = geometry_cfg_bearings.get(p2, [0.0])
        a_bearing = a_bearings[0] if a_bearings else 0.0
        b_bearing = b_bearings[0] if b_bearings else 0.0
        delta = abs(a_bearing - b_bearing) % 360
        if delta > 180:
            delta = 360 - delta

        alt_a = _nearest_free_neighbor(p1, free_points, p2)
        alt_b = _nearest_free_neighbor(p2, free_points, p1)
        alt_a_dist = (
            round(math.hypot(p1[0] - alt_a[0], p1[1] - alt_a[1]), 3) if alt_a else None
        )
        alt_b_dist = (
            round(math.hypot(p2[0] - alt_b[0], p2[1] - alt_b[1]), 3) if alt_b else None
        )

        reason = "greedy_pairing_conflict"
        note = (
            "Both endpoints are within gap_threshold but close_gaps matched at least one "
            "endpoint to a different neighbor first (greedy nearest-neighbor order)."
        )
        if alt_a_dist is not None and alt_a_dist < gap.gap_distance:
            note += f" Endpoint A has a closer free neighbor at {alt_a_dist} units."
        if alt_b_dist is not None and alt_b_dist < gap.gap_distance:
            note += f" Endpoint B has a closer free neighbor at {alt_b_dist} units."
        if delta > max_gap_angle + 45:
            reason = "bearing_mismatch_suspected"
            note += f" Segment bearing delta {delta:.1f}° may discourage bridging (max_gap_angle={max_gap_angle})."

        details.append(
            GapFailureDetail(
                drawing=drawing_name,
                endpoint_a_x=p1[0],
                endpoint_a_y=p1[1],
                endpoint_b_x=p2[0],
                endpoint_b_y=p2[1],
                gap_distance=gap.gap_distance,
                layer_a=gap.layer_a,
                layer_b=gap.layer_b,
                gap_threshold=gap_threshold,
                max_gap_angle=max_gap_angle,
                endpoint_a_bearing_deg=round(a_bearing, 2),
                endpoint_b_bearing_deg=round(b_bearing, 2),
                bridge_bearing_deg=round(bridge_bearing, 2),
                bearing_delta_deg=round(delta, 2),
                failure_reason=reason,
                note=note,
            )
        )

    return details


def _polygon_area_stats(polygons: list[Polygon], unit: str) -> tuple[int, float | None, float | None, float]:
    scale = scale_factor(unit)
    areas_m2: list[float] = []
    invalid = 0

    for poly in polygons:
        if not poly.is_valid:
            invalid += 1
        normalized = normalize_polygon(poly)
        if normalized is None:
            invalid += 1
            continue
        areas_m2.append(normalized.area * (scale**2))

    if not areas_m2:
        return invalid, None, None, 0.0
    return invalid, max(areas_m2), min(areas_m2), sum(areas_m2)


def detect_from_tagged(
    tagged: list[TaggedSegment],
    config: dict[str, Any],
) -> tuple[list[Polygon], int, int, int, int]:
    """Run snap, gap close, polygonize. Returns polygons and diagnostic counts."""
    geometry_cfg = config.get("geometry", {})
    accuracy_cfg = config.get("accuracy", {})
    snap_tol = float(geometry_cfg.get("snap_tolerance", 1))
    gap_threshold = float(geometry_cfg.get("gap_threshold", 500))
    max_angle = float(geometry_cfg.get("max_gap_angle", 30))
    unit = geometry_cfg.get("drawing_unit", "mm")

    snapped = snap_tagged_endpoints(tagged, snap_tol)
    open_before = count_open_endpoints(snapped)

    iterative = bool(geometry_cfg.get("iterative_gap_close", True))
    max_passes = int(geometry_cfg.get("iterative_max_passes", 3))
    colinear_profile = bool(geometry_cfg.get("colinear_profile_match", True))
    tier2_enabled = bool(geometry_cfg.get("tier2_threshold_enabled", False))
    tier2_threshold = float(geometry_cfg.get("tier2_gap_threshold", 1000))
    tier2_layers = frozenset(
        geometry_cfg.get("tier2_structural_layers", list(DEFAULT_TIER2_STRUCTURAL_LAYERS))
    )
    layers_map = endpoint_layer_map(snapped)

    if iterative:
        source_lines = [t.line for t in snapped]
        closed_lines, gaps_closed = iterative_close_gaps(
            source_lines,
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
        closed_tagged = [TaggedSegment(line=line, layer="SRC") for line in closed_lines]
    else:
        closed_tagged, gaps_closed = close_gaps_tagged(snapped, gap_threshold, max_angle)

    open_after = count_open_endpoints(closed_tagged)

    lines = [t.line for t in closed_tagged]
    raw = polygonize_regions(MultiLineString(lines) if lines else MultiLineString())
    invalid_raw, _, _, _ = _polygon_area_stats(raw, unit)

    mode = str(accuracy_cfg.get("detection_mode", "exhaustive")).lower()
    exhaustive = mode == "exhaustive"
    min_area = float(geometry_cfg.get("min_area", 1.0))
    if exhaustive:
        min_area = float(accuracy_cfg.get("exhaustive_min_area_m2", 0.01))

    filtered = filter_polygons(raw, min_area, unit, exhaustive=exhaustive)
    dedupe_iou = float(accuracy_cfg.get("dedupe_iou_threshold", 0.98))
    final = remove_duplicates(filtered, iou_threshold=dedupe_iou)

    return final, len(raw), invalid_raw, open_before, gaps_closed, open_after


def diagnose_drawing(
    cad_path: Path,
    dxf_path: Path,
    doc: Drawing,
    config: dict[str, Any],
    conversion_note: str,
) -> tuple[DrawingDiagnostics, list[GapRecord]]:
    """Full diagnostic pass for one drawing."""
    diag = DrawingDiagnostics(
        source_path=str(cad_path),
        dxf_path=str(dxf_path),
        conversion_note=conversion_note,
    )

    msp = get_modelspace(doc)
    accuracy_cfg = config.get("accuracy", {})
    layers_cfg = config.get("layers", {})
    geometry_cfg = config.get("geometry", {})
    arc_segments = int(accuracy_cfg.get("arc_segments", 64))
    ignore_layers = layers_cfg.get("ignore_layers", [])
    wall_layers = layers_cfg.get("wall_layers", [])
    gap_threshold = float(geometry_cfg.get("gap_threshold", 500))

    diag.configured_wall_layers = list(wall_layers)

    (
        diag.total_entities,
        diag.entity_type_counts,
        diag.layer_entity_counts,
        diag.layer_geometry_counts,
    ) = scan_modelspace(msp)

    diag.candidate_wall_layers = suggest_candidate_wall_layers(diag.layer_geometry_counts)

    configured_tagged = extract_tagged_segments(msp, wall_layers, ignore_layers, arc_segments)
    candidate_tagged = extract_tagged_segments(
        msp, diag.candidate_wall_layers, ignore_layers, arc_segments
    )

    diag.configured_entities = len(extract_entities(msp, wall_layers, ignore_layers))
    diag.configured_segments = len(configured_tagged)
    diag.candidate_entities = sum(
        diag.layer_geometry_counts.get(layer, 0) for layer in diag.candidate_wall_layers
    )
    diag.candidate_segments = len(candidate_tagged)

    gaps: list[GapRecord] = []
    snap_tol = float(geometry_cfg.get("snap_tolerance", 1))

    if configured_tagged:
        snapped_cfg = snap_tagged_endpoints(configured_tagged, snap_tol)
        gaps = analyze_gaps(snapped_cfg, cad_path.name, gap_threshold)

        polys, raw_n, invalid, open_before, closed_n, open_after = detect_from_tagged(
            configured_tagged, config
        )
        diag.open_endpoints_before_close = open_before
        diag.open_endpoints_after_close = open_after
        diag.gaps_closed = closed_n
        diag.raw_polygon_count = raw_n
        diag.invalid_polygon_count = invalid
        diag.regions_detected = len(polys)
        _, largest, smallest, total = _polygon_area_stats(polys, geometry_cfg.get("drawing_unit", "mm"))
        diag.largest_area_m2 = largest
        diag.smallest_area_m2 = smallest
        diag.total_detected_area_m2 = total

    if candidate_tagged:
        snapped_cand = snap_tagged_endpoints(candidate_tagged, snap_tol)
        if not configured_tagged:
            gaps = analyze_gaps(snapped_cand, cad_path.name, gap_threshold)
            polys_c, raw_n, invalid, open_before, closed_n, open_after = detect_from_tagged(
                candidate_tagged, config
            )
            diag.open_endpoints_before_close = open_before
            diag.open_endpoints_after_close = open_after
            diag.gaps_closed = closed_n
            diag.raw_polygon_count = raw_n
            diag.invalid_polygon_count = invalid
            diag.regions_detected = len(polys_c)
            _, largest, smallest, total = _polygon_area_stats(
                polys_c, geometry_cfg.get("drawing_unit", "mm")
            )
            diag.largest_area_m2 = largest
            diag.smallest_area_m2 = smallest
            diag.total_detected_area_m2 = total

        cand_polys, _, _, _, _, _ = detect_from_tagged(candidate_tagged, config)
        diag.regions_with_candidate_layers = len(cand_polys)
        _, cl, cs, ct = _polygon_area_stats(cand_polys, geometry_cfg.get("drawing_unit", "mm"))
        diag.candidate_largest_area_m2 = cl
        diag.candidate_smallest_area_m2 = cs
        diag.candidate_total_area_m2 = ct

        if configured_tagged:
            gaps.extend(analyze_gaps(snapped_cand, f"{cad_path.name} (candidate)", gap_threshold))

    return diag, gaps
