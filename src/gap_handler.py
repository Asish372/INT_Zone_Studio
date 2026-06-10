"""Module 4: Snap endpoints and close door/shutter gaps."""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Any

from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union

from src.detector import node_geometry
from src.endpoint_matching import (
    DEFAULT_TIER2_STRUCTURAL_LAYERS,
    min_cost_endpoint_matching,
    tier2_endpoint_matching,
)

logger = logging.getLogger(__name__)


def _round_point(x: float, y: float, precision: int = 6) -> tuple[float, float]:
    return (round(x, precision), round(y, precision))


def _segment_endpoints(seg: LineString) -> tuple[tuple[float, float], tuple[float, float]]:
    coords = list(seg.coords)
    return coords[0], coords[-1]


def snap_endpoints(segments: list[LineString], tol: float) -> list[LineString]:
    """Snap endpoints within tolerance to remove micro-gaps."""
    if not segments or tol <= 0:
        return segments

    endpoints: list[tuple[float, float]] = []
    for seg in segments:
        a, b = _segment_endpoints(seg)
        endpoints.extend([a, b])

    clusters: list[list[tuple[float, float]]] = []
    used = [False] * len(endpoints)

    for i, pt in enumerate(endpoints):
        if used[i]:
            continue
        cluster = [pt]
        used[i] = True
        for j in range(i + 1, len(endpoints)):
            if used[j]:
                continue
            dx = pt[0] - endpoints[j][0]
            dy = pt[1] - endpoints[j][1]
            if math.hypot(dx, dy) <= tol:
                cluster.append(endpoints[j])
                used[j] = True
        clusters.append(cluster)

    def centroid(cluster: list[tuple[float, float]]) -> tuple[float, float]:
        n = len(cluster)
        return (sum(p[0] for p in cluster) / n, sum(p[1] for p in cluster) / n)

    snap_map: dict[tuple[float, float], tuple[float, float]] = {}
    for cluster in clusters:
        if len(cluster) == 1:
            snap_map[cluster[0]] = cluster[0]
        else:
            c = centroid(cluster)
            for p in cluster:
                snap_map[p] = c

    snapped: list[LineString] = []
    for seg in segments:
        coords = list(seg.coords)
        new_coords = [
            snap_map.get((coords[0][0], coords[0][1]), coords[0]),
            snap_map.get((coords[-1][0], coords[-1][1]), coords[-1]),
        ]
        if len(coords) > 2:
            new_coords = [new_coords[0]] + list(coords[1:-1]) + [new_coords[-1]]
        snapped.append(LineString(new_coords))

    return snapped


def _angle_between(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))


def _bridge_crosses_existing_segments(
    bridge: LineString,
    segments: list[LineString],
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> bool:
    """Reject tier-2 bridges that cross segment interiors (not just at endpoints)."""
    for seg in segments:
        if seg.equals(bridge):
            continue
        if not bridge.intersects(seg):
            continue
        intersection = bridge.intersection(seg)
        if intersection.is_empty:
            continue
        if intersection.geom_type == "Point":
            coords = (intersection.x, intersection.y)
            at_endpoint = (
                math.hypot(coords[0] - p1[0], coords[1] - p1[1]) < 1e-6
                or math.hypot(coords[0] - p2[0], coords[1] - p2[1]) < 1e-6
            )
            if at_endpoint:
                continue
        if bridge.crosses(seg):
            return True
    return False


def close_gaps_tier2(
    segments: list[LineString],
    tier1_threshold: float,
    tier2_threshold: float,
    max_angle: float = 30.0,
    *,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
    structural_layers: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
    colinear_profile: bool = True,
    reject_crossing: bool = True,
) -> tuple[list[LineString], int]:
    """
    P2.5: close structural-layer gaps in (tier1, tier2] after tier-1 closure.

    Only bridges endpoint pairs on the structural whitelist with approved
    same-layer or cross-layer combinations.
    """
    if not segments or not endpoint_layers or tier2_threshold <= tier1_threshold:
        return segments, 0

    endpoint_count: dict[tuple[float, float], int] = defaultdict(int)
    endpoint_dirs: dict[tuple[float, float], list[float]] = defaultdict(list)
    endpoint_segment_ids: dict[tuple[float, float], set[int]] = defaultdict(set)

    for seg_idx, seg in enumerate(segments):
        coords = list(seg.coords)
        a, b = _round_point(coords[0][0], coords[0][1]), _round_point(
            coords[-1][0], coords[-1][1]
        )
        endpoint_count[a] += 1
        endpoint_count[b] += 1
        endpoint_segment_ids[a].add(seg_idx)
        endpoint_segment_ids[b].add(seg_idx)
        if len(coords) >= 2:
            endpoint_dirs[a].append(_angle_between(coords[1], coords[0]))
            endpoint_dirs[b].append(_angle_between(coords[-2], coords[-1]))

    free_points = [pt for pt, count in endpoint_count.items() if count == 1]
    if len(free_points) < 2:
        return segments, 0

    seg_id_map = {pt: frozenset(ids) for pt, ids in endpoint_segment_ids.items()}
    matched_pairs = tier2_endpoint_matching(
        free_points,
        endpoint_dirs,
        tier1_threshold,
        tier2_threshold,
        max_angle,
        seg_id_map,
        endpoint_layers=endpoint_layers,
        structural_layers=structural_layers,
        colinear_profile=colinear_profile,
    )

    bridges: list[LineString] = []
    for i, j in matched_pairs:
        p1 = free_points[i]
        p2 = free_points[j]
        dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
        bridge = LineString([p1, p2])
        if reject_crossing and _bridge_crosses_existing_segments(bridge, segments, p1, p2):
            logger.debug(
                "Tier-2 bridge rejected (crossing): (%.2f, %.2f) -> (%.2f, %.2f) dist=%.2f",
                p1[0],
                p1[1],
                p2[0],
                p2[1],
                dist,
            )
            continue
        bridges.append(bridge)
        logger.debug(
            "Tier-2 closed gap: (%.2f, %.2f) -> (%.2f, %.2f) dist=%.2f",
            p1[0],
            p1[1],
            p2[0],
            p2[1],
            dist,
        )

    if bridges:
        logger.info("Tier-2 gaps closed: %d", len(bridges))
    return segments + bridges, len(bridges)


def close_gaps(
    segments: list[LineString],
    threshold: float,
    max_angle: float = 30.0,
    *,
    colinear_profile: bool = True,
    tier2_enabled: bool = False,
    tier2_threshold: float = 1000.0,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
    structural_layers: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
    reject_tier2_crossing: bool = True,
) -> tuple[list[LineString], int]:
    """
    Close gaps between free endpoints within threshold distance.

    Returns updated segments and count of gaps closed.
    """
    if not segments:
        return segments, 0

    endpoint_count: dict[tuple[float, float], int] = defaultdict(int)
    endpoint_dirs: dict[tuple[float, float], list[float]] = defaultdict(list)
    endpoint_segment_ids: dict[tuple[float, float], set[int]] = defaultdict(set)

    for seg_idx, seg in enumerate(segments):
        coords = list(seg.coords)
        a, b = _round_point(coords[0][0], coords[0][1]), _round_point(
            coords[-1][0], coords[-1][1]
        )
        endpoint_count[a] += 1
        endpoint_count[b] += 1
        endpoint_segment_ids[a].add(seg_idx)
        endpoint_segment_ids[b].add(seg_idx)
        if len(coords) >= 2:
            endpoint_dirs[a].append(_angle_between(coords[1], coords[0]))
            endpoint_dirs[b].append(_angle_between(coords[-2], coords[-1]))

    free_points = [pt for pt, count in endpoint_count.items() if count == 1]
    closed_count = 0
    bridges: list[LineString] = []

    seg_id_map = {pt: frozenset(ids) for pt, ids in endpoint_segment_ids.items()}
    matched_pairs = min_cost_endpoint_matching(
        free_points,
        endpoint_dirs,
        threshold,
        max_angle,
        seg_id_map,
        colinear_profile=colinear_profile,
        tier2_enabled=tier2_enabled,
        tier2_threshold=tier2_threshold,
        endpoint_layers=endpoint_layers,
        structural_layers=structural_layers,
    )
    for i, j in matched_pairs:
        p1 = free_points[i]
        p2 = free_points[j]
        dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
        bridge = LineString([p1, p2])
        if (
            tier2_enabled
            and dist > threshold
            and reject_tier2_crossing
            and _bridge_crosses_existing_segments(bridge, segments, p1, p2)
        ):
            logger.debug(
                "Tier-2 bridge rejected (crossing): dist=%.2f",
                dist,
            )
            continue
        bridges.append(bridge)
        closed_count += 1
        logger.debug(
            "Closed gap: (%.2f, %.2f) -> (%.2f, %.2f) dist=%.2f",
            p1[0],
            p1[1],
            p2[0],
            p2[1],
            dist,
        )

    unresolved = len(free_points) - 2 * closed_count
    if unresolved > 0:
        logger.warning("%d unresolved free endpoints (gap > threshold)", unresolved)

    result = segments + bridges
    logger.info("Gaps closed: %d", closed_count)
    return result, closed_count


def extract_linestrings(multi: MultiLineString) -> list[LineString]:
    """Extract individual LineStrings from a (possibly noded) multiline."""
    if multi.is_empty:
        return []
    noded = node_geometry(multi)
    if noded.is_empty:
        return []
    if noded.geom_type == "LineString":
        return [noded]
    return list(noded.geoms)


def iterative_close_gaps(
    segments: list[LineString],
    threshold: float,
    max_angle: float = 30.0,
    *,
    snap_tol: float = 0.0,
    max_passes: int = 3,
    colinear_profile: bool = True,
    tier2_enabled: bool = False,
    tier2_threshold: float = 1000.0,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
    structural_layers: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
) -> tuple[list[LineString], int]:
    """
    P2.2: close → renode → re-extract loop until no new bridges are added.

    Each pass runs P2.1 global min-cost matching, then refreshes topology via
    ``node_geometry`` so later passes can close pairs exposed by noding.
    """
    if not segments:
        return segments, 0

    max_passes = max(1, min(int(max_passes), 3))
    current = list(segments)
    total_closed = 0

    for pass_num in range(1, max_passes + 1):
        if snap_tol > 0:
            current = snap_endpoints(current, snap_tol)
        current, closed = close_gaps(
            current,
            threshold,
            max_angle,
            colinear_profile=colinear_profile,
            tier2_enabled=tier2_enabled,
            tier2_threshold=tier2_threshold,
            endpoint_layers=endpoint_layers,
            structural_layers=structural_layers,
        )
        total_closed += closed
        logger.info("Iterative gap close pass %d: closed=%d", pass_num, closed)
        if closed == 0:
            break
        if pass_num < max_passes:
            current = extract_linestrings(
                MultiLineString(current) if current else MultiLineString()
            )

    logger.info("Iterative gap close total: %d bridges", total_closed)
    return current, total_closed


def prepare_for_polygonize(
    segments: list[LineString],
    config: dict[str, Any],
) -> MultiLineString:
    """Snap endpoints, close gaps, and return a MultiLineString for polygonization."""
    geometry_cfg = config.get("geometry", {})
    snap_tol = float(geometry_cfg.get("snap_tolerance", 1))
    gap_threshold = float(geometry_cfg.get("gap_threshold", 500))
    max_angle = float(geometry_cfg.get("max_gap_angle", 30))

    iterative = bool(geometry_cfg.get("iterative_gap_close", True))
    max_passes = int(geometry_cfg.get("iterative_max_passes", 3))
    colinear_profile = bool(geometry_cfg.get("colinear_profile_match", True))

    if iterative:
        segments, _ = iterative_close_gaps(
            segments,
            gap_threshold,
            max_angle,
            snap_tol=snap_tol,
            max_passes=max_passes,
            colinear_profile=colinear_profile,
        )
    else:
        segments = snap_endpoints(segments, snap_tol)
        segments, _ = close_gaps(
            segments, gap_threshold, max_angle, colinear_profile=colinear_profile
        )

    if not segments:
        return MultiLineString()

    merged = unary_union(MultiLineString(segments))
    if merged.geom_type == "LineString":
        return MultiLineString([merged])
    if merged.geom_type == "MultiLineString":
        return merged
    return MultiLineString()
