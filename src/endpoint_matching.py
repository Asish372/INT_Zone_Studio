"""Global min-cost endpoint matching for gap closure (P2.1 + P2.3)."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable
from typing import Sequence

import networkx as nx

# Large weight base so max-cardinality matching prefers more pairs over lower cost.
_WEIGHT_BASE = 1_000_000.0

# P2.3 — wall-thickness / door-offset profile distances (mm).
_PROFILE_DISTANCES = (150.0, 180.0)
_PROFILE_DIST_TOL = 5.0
_PROFILE_BEARING_MIN = 135.0
_MICRO_GAP_MAX = 15.0

# P2.5 — structural layers eligible for tier-2 (501–1000 mm) gap closure.
DEFAULT_TIER2_STRUCTURAL_LAYERS: frozenset[str] = frozenset(
    {
        "S-FNDN-1",
        "S-BEAM-1",
        "S-BEAM-2",
        "A-WALL",
        "A-WALL-2",
        "A-WALL-3",
    }
)

_TIER2_CROSS_LAYER_PREFIXES: tuple[tuple[str, str], ...] = (
    ("S-FNDN-1", "S-BEAM"),
    ("S-FNDN-1", "A-WALL"),
    ("S-BEAM", "A-WALL"),
)


def _normalize_layer_name(layer: str) -> str:
    return (layer or "0").upper()


def is_structural_layer(
    layer: str,
    whitelist: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
) -> bool:
    """True when endpoint layer is on the tier-2 structural whitelist."""
    name = _normalize_layer_name(layer)
    if name in whitelist:
        return True
    return name in {_normalize_layer_name(item) for item in whitelist}


def is_approved_tier2_layer_pair(
    layer_a: str,
    layer_b: str,
    whitelist: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
) -> bool:
    """Same-layer or approved cross-layer structural pair; excludes detail layers."""
    la = _normalize_layer_name(layer_a)
    lb = _normalize_layer_name(layer_b)
    if la.startswith("A-DETL") or lb.startswith("A-DETL"):
        return False
    if not is_structural_layer(la, whitelist) or not is_structural_layer(lb, whitelist):
        return False
    if la == lb:
        return True
    for prefix_a, prefix_b in _TIER2_CROSS_LAYER_PREFIXES:
        if (la.startswith(prefix_a) and lb.startswith(prefix_b)) or (
            la.startswith(prefix_b) and lb.startswith(prefix_a)
        ):
            return True
    return False


def _normalize_angle_diff(a1: float, a2: float) -> float:
    delta = abs(a1 - a2) % 360.0
    return 360.0 - delta if delta > 180.0 else delta


def _bearing_delta(dirs1: Sequence[float], dirs2: Sequence[float]) -> float | None:
    if not dirs1 or not dirs2:
        return None
    return _normalize_angle_diff(dirs1[0], dirs2[0])


def _matches_profile_distance(
    dist: float,
    profile_distances: Sequence[float] = _PROFILE_DISTANCES,
    dist_tol: float = _PROFILE_DIST_TOL,
) -> bool:
    return any(abs(dist - target) <= dist_tol for target in profile_distances)


def is_wall_offset_profile(
    dist: float,
    dirs1: Sequence[float],
    dirs2: Sequence[float],
    *,
    profile_distances: Sequence[float] = _PROFILE_DISTANCES,
    dist_tol: float = _PROFILE_DIST_TOL,
    bearing_min: float = _PROFILE_BEARING_MIN,
) -> bool:
    """True for 150/180 mm colinear opposite-facing endpoint pairs (door/wall offset)."""
    if not _matches_profile_distance(dist, profile_distances, dist_tol):
        return False
    delta = _bearing_delta(dirs1, dirs2)
    return delta is not None and delta >= bearing_min


def is_micro_gap_pair(
    dist: float,
    dirs1: Sequence[float],
    dirs2: Sequence[float],
    max_angle: float,
    *,
    micro_gap_max: float = _MICRO_GAP_MAX,
) -> bool:
    """True for ultra-close equidistant-competition pairs (pairing conflict resolver)."""
    if dist > micro_gap_max:
        return False
    delta = _bearing_delta(dirs1, dirs2)
    if delta is None:
        return True
    return (
        delta <= max_angle + 5.0
        or abs(delta - 90.0) <= 5.0
        or abs(delta - 180.0) <= 5.0
    )


def bridge_cost(
    p1: tuple[float, float],
    p2: tuple[float, float],
    dirs1: Sequence[float],
    dirs2: Sequence[float],
    dist: float,
    max_angle: float,
) -> float:
    """Lower cost = preferred bridge. Wall-offset colinear pairs get top priority."""
    cost = dist
    if dirs1 and dirs2:
        delta = _normalize_angle_diff(dirs1[0], dirs2[0])
        if abs(delta - 180.0) <= 5.0 and _matches_profile_distance(dist):
            return 0.01
        if (
            delta <= max_angle + 5.0
            or abs(delta - 90.0) <= 5.0
            or abs(delta - 180.0) <= 5.0
        ):
            cost *= 0.85
        elif delta > max_angle + 45.0:
            cost *= 0.75
    if _matches_profile_distance(dist):
        cost = min(cost, dist * 0.35)
    return cost


def _build_candidate_edges(
    free_points: list[tuple[float, float]],
    endpoint_dirs: dict[tuple[float, float], list[float]],
    threshold: float,
    max_angle: float,
    seg_ids: dict[tuple[float, float], frozenset[int]],
    *,
    edge_filter: Callable[[int, int, float, Sequence[float], Sequence[float]], bool]
    | None = None,
    cost_fn: Callable[[int, int, float, Sequence[float], Sequence[float]], float]
    | None = None,
    excluded_nodes: set[int] | None = None,
    tier2_threshold: float | None = None,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
    structural_layers: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
    tier2_enabled: bool = False,
) -> list[tuple[int, int, float, float]]:
    excluded = excluded_nodes or set()
    edges: list[tuple[int, int, float, float]] = []
    n = len(free_points)
    tier1 = threshold
    max_dist = tier2_threshold if tier2_enabled and tier2_threshold else tier1

    for i in range(n):
        if i in excluded:
            continue
        p1 = free_points[i]
        dirs1 = endpoint_dirs.get(p1, [])
        seg1 = seg_ids.get(p1, frozenset())
        for j in range(i + 1, n):
            if j in excluded:
                continue
            p2 = free_points[j]
            if seg1 and seg1 & seg_ids.get(p2, frozenset()):
                continue
            dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
            if dist < 1e-9 or dist > max_dist:
                continue
            if tier2_enabled and dist > tier1:
                if not endpoint_layers:
                    continue
                la = endpoint_layers.get(p1, "")
                lb = endpoint_layers.get(p2, "")
                if not is_approved_tier2_layer_pair(la, lb, structural_layers):
                    continue
            dirs2 = endpoint_dirs.get(p2, [])
            if edge_filter is not None and not edge_filter(i, j, dist, dirs1, dirs2):
                continue
            if cost_fn is not None:
                cost = cost_fn(i, j, dist, dirs1, dirs2)
            else:
                cost = bridge_cost(p1, p2, dirs1, dirs2, dist, max_angle)
            if tier2_enabled and dist > tier1:
                cost += tier1 * 0.5
            weight = _WEIGHT_BASE - cost
            if is_wall_offset_profile(dist, dirs1, dirs2):
                weight += _WEIGHT_BASE
            edges.append((i, j, cost, weight))
    return edges


def _match_edges(edges: list[tuple[int, int, float, float] | tuple[int, int, float]]) -> list[tuple[int, int]]:
    if not edges:
        return []
    graph = nx.Graph()
    for edge in edges:
        if len(edge) == 4:
            i, j, _cost, weight = edge
        else:
            i, j, cost = edge
            weight = _WEIGHT_BASE - cost
        graph.add_edge(i, j, weight=weight)
    matched = nx.max_weight_matching(graph, maxcardinality=True, weight="weight")
    return [(min(u, v), max(u, v)) for u, v in matched]


def _unique_partner_pairs(
    edges: list[tuple[int, int, float, float] | tuple[int, int, float]],
) -> list[tuple[int, int]]:
    """Return mutual 1:1 candidate pairs (each node has exactly one partner)."""
    partners: dict[int, list[int]] = defaultdict(list)
    for edge in edges:
        i, j = edge[0], edge[1]
        partners[i].append(j)
        partners[j].append(i)

    pairs: list[tuple[int, int]] = []
    used: set[int] = set()
    for i, candidates in partners.items():
        if i in used or len(candidates) != 1:
            continue
        j = candidates[0]
        if partners.get(j) == [i]:
            pairs.append((min(i, j), max(i, j)))
            used.add(i)
            used.add(j)
    return pairs


def endpoint_matching_phased(
    free_points: list[tuple[float, float]],
    endpoint_dirs: dict[tuple[float, float], list[float]],
    threshold: float,
    max_angle: float = 30.0,
    endpoint_segment_ids: dict[tuple[float, float], frozenset[int]] | None = None,
    *,
    colinear_profile: bool = True,
    micro_gap_resolve: bool = True,
    profile_distances: Sequence[float] = _PROFILE_DISTANCES,
    dist_tol: float = _PROFILE_DIST_TOL,
    micro_gap_max: float = _MICRO_GAP_MAX,
    tier2_enabled: bool = False,
    tier2_threshold: float | None = None,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
    structural_layers: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
) -> list[tuple[int, int]]:
    """
    P2.3 phased matching: colinear profile → micro-gap → general P2.1.

    Returns index pairs (i, j) into ``free_points``.
    """
    n = len(free_points)
    if n < 2:
        return []

    seg_ids = endpoint_segment_ids or {}
    used: set[int] = set()
    all_pairs: list[tuple[int, int]] = []

    def _dirs_for(idx: int) -> list[float]:
        return endpoint_dirs.get(free_points[idx], [])

    if colinear_profile:

        def _profile_filter(
            _i: int, _j: int, dist: float, d1: Sequence[float], d2: Sequence[float]
        ) -> bool:
            return is_wall_offset_profile(
                dist,
                d1,
                d2,
                profile_distances=profile_distances,
                dist_tol=dist_tol,
            )

        profile_edges = _build_candidate_edges(
            free_points,
            endpoint_dirs,
            threshold,
            max_angle,
            seg_ids,
            edge_filter=_profile_filter,
            cost_fn=lambda _i, _j, _d, _d1, _d2: 0.001,
        )
        profile_pairs = _unique_partner_pairs(profile_edges)
        for i, j in profile_pairs:
            used.add(i)
            used.add(j)
        all_pairs.extend(profile_pairs)

    if micro_gap_resolve:

        def _micro_filter(
            _i: int, _j: int, dist: float, d1: Sequence[float], d2: Sequence[float]
        ) -> bool:
            return is_micro_gap_pair(dist, d1, d2, max_angle, micro_gap_max=micro_gap_max)

        micro_edges = _build_candidate_edges(
            free_points,
            endpoint_dirs,
            threshold,
            max_angle,
            seg_ids,
            edge_filter=_micro_filter,
            cost_fn=lambda _i, _j, dist, _d1, _d2: min(0.005, dist * 0.01),
            excluded_nodes=used,
        )
        micro_pairs = _unique_partner_pairs(micro_edges)
        for i, j in micro_pairs:
            used.add(i)
            used.add(j)
        all_pairs.extend(micro_pairs)

    general_edges = _build_candidate_edges(
        free_points,
        endpoint_dirs,
        threshold,
        max_angle,
        seg_ids,
        excluded_nodes=used,
        tier2_enabled=tier2_enabled,
        tier2_threshold=tier2_threshold,
        endpoint_layers=endpoint_layers,
        structural_layers=structural_layers,
    )
    general_pairs = _match_edges(general_edges)
    all_pairs.extend(general_pairs)
    return all_pairs


def _general_only_matching(
    free_points: list[tuple[float, float]],
    endpoint_dirs: dict[tuple[float, float], list[float]],
    threshold: float,
    max_angle: float,
    endpoint_segment_ids: dict[tuple[float, float], frozenset[int]] | None,
    *,
    tier2_enabled: bool = False,
    tier2_threshold: float | None = None,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
    structural_layers: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
) -> list[tuple[int, int]]:
    n = len(free_points)
    if n < 2:
        return []
    seg_ids = endpoint_segment_ids or {}
    edges = _build_candidate_edges(
        free_points,
        endpoint_dirs,
        threshold,
        max_angle,
        seg_ids,
        tier2_enabled=tier2_enabled,
        tier2_threshold=tier2_threshold,
        endpoint_layers=endpoint_layers,
        structural_layers=structural_layers,
    )
    return _match_edges(edges)


def tier2_endpoint_matching(
    free_points: list[tuple[float, float]],
    endpoint_dirs: dict[tuple[float, float], list[float]],
    tier1_threshold: float,
    tier2_threshold: float,
    max_angle: float = 30.0,
    endpoint_segment_ids: dict[tuple[float, float], frozenset[int]] | None = None,
    *,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
    structural_layers: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
    colinear_profile: bool = True,
) -> list[tuple[int, int]]:
    """
    P2.5 tier-2 pass: bridge structural pairs in (tier1, tier2] distance band only.

    Runs phased matching at ``tier2_threshold`` but filters to tier-2 band and
    structural layer whitelist pairs.
    """
    if not endpoint_layers or tier2_threshold <= tier1_threshold:
        return []

    def _tier2_filter(
        i: int, j: int, dist: float, _d1: Sequence[float], _d2: Sequence[float]
    ) -> bool:
        if dist <= tier1_threshold or dist > tier2_threshold:
            return False
        p1 = free_points[i]
        p2 = free_points[j]
        la = endpoint_layers.get(p1, "")
        lb = endpoint_layers.get(p2, "")
        return is_approved_tier2_layer_pair(la, lb, structural_layers)

    seg_ids = endpoint_segment_ids or {}
    edges = _build_candidate_edges(
        free_points,
        endpoint_dirs,
        tier2_threshold,
        max_angle,
        seg_ids,
        edge_filter=_tier2_filter,
    )
    if colinear_profile:
        profile_edges = [
            e
            for e in edges
            if is_wall_offset_profile(
                math.hypot(
                    free_points[e[0]][0] - free_points[e[1]][0],
                    free_points[e[0]][1] - free_points[e[1]][1],
                ),
                endpoint_dirs.get(free_points[e[0]], []),
                endpoint_dirs.get(free_points[e[1]], []),
            )
        ]
        profile_pairs = _unique_partner_pairs(profile_edges)
        used = {idx for pair in profile_pairs for idx in pair}
        general_edges = _build_candidate_edges(
            free_points,
            endpoint_dirs,
            tier2_threshold,
            max_angle,
            seg_ids,
            edge_filter=_tier2_filter,
            excluded_nodes=used,
        )
        return profile_pairs + _match_edges(general_edges)
    return _match_edges(edges)


def min_cost_endpoint_matching(
    free_points: list[tuple[float, float]],
    endpoint_dirs: dict[tuple[float, float], list[float]],
    threshold: float,
    max_angle: float = 30.0,
    endpoint_segment_ids: dict[tuple[float, float], frozenset[int]] | None = None,
    *,
    colinear_profile: bool = True,
    tier2_enabled: bool = False,
    tier2_threshold: float | None = None,
    endpoint_layers: dict[tuple[float, float], str] | None = None,
    structural_layers: frozenset[str] = DEFAULT_TIER2_STRUCTURAL_LAYERS,
) -> list[tuple[int, int]]:
    """
    Select endpoint pairs to bridge using maximum-cardinality min-cost matching.

    When ``colinear_profile`` is True (default), runs P2.3 phased matching and
    adopts it only when it closes strictly more bridges than P2.1 alone.
    Returns index pairs (i, j) into ``free_points``.
    """
    tier2_kwargs = {
        "tier2_enabled": tier2_enabled,
        "tier2_threshold": tier2_threshold,
        "endpoint_layers": endpoint_layers,
        "structural_layers": structural_layers,
    }
    general = _general_only_matching(
        free_points,
        endpoint_dirs,
        threshold,
        max_angle,
        endpoint_segment_ids,
        **tier2_kwargs,
    )
    if not colinear_profile:
        return general

    phased = endpoint_matching_phased(
        free_points,
        endpoint_dirs,
        threshold,
        max_angle,
        endpoint_segment_ids,
        **tier2_kwargs,
    )
    if len(phased) >= len(general):
        return phased
    return general
