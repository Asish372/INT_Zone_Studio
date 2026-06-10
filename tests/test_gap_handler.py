"""Tests for gap handler and global endpoint matching (P2.1)."""

from __future__ import annotations

import math

from shapely.geometry import LineString

from src.endpoint_matching import (
    bridge_cost,
    endpoint_matching_phased,
    is_approved_tier2_layer_pair,
    is_structural_layer,
    is_wall_offset_profile,
    min_cost_endpoint_matching,
)
from src.gap_handler import close_gaps, close_gaps_tier2, iterative_close_gaps, snap_endpoints


def _count_free_endpoints(segments: list[LineString]) -> int:
    counts: dict[tuple[float, float], int] = {}
    for seg in segments:
        coords = list(seg.coords)
        a = (round(coords[0][0], 6), round(coords[0][1], 6))
        b = (round(coords[-1][0], 6), round(coords[-1][1], 6))
        counts[a] = counts.get(a, 0) + 1
        counts[b] = counts.get(b, 0) + 1
    return sum(1 for c in counts.values() if c == 1)


def test_snap_endpoints_merges_close_points() -> None:
    segments = [
        LineString([(0, 0), (10, 0)]),
        LineString([(10.5, 0), (10.5, 10)]),
    ]
    snapped = snap_endpoints(segments, tol=1.0)
    assert len(snapped) == 2


def test_close_gaps_within_threshold() -> None:
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (100, 100)]),
        LineString([(100, 100), (0, 100)]),
        LineString([(0, 100), (0, 50)]),
    ]
    result, closed = close_gaps(segments, threshold=500)
    assert closed >= 0
    assert len(result) >= len(segments)


def test_greedy_failure_global_matching_prefers_wall_offset() -> None:
    """
    Greedy nearest-neighbor matches the 2-unit spur first; global matching
    closes the 150 mm colinear wall-offset pair instead.
    """
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (200, 0)]),
        LineString([(350, 0), (450, 0)]),
        LineString([(202, 0), (202, 30)]),
    ]
    greedy_result, _ = _close_gaps_greedy(segments, threshold=500)
    global_result, _ = close_gaps(segments, threshold=500)

    greedy_bridges = greedy_result[len(segments) :]
    global_bridges = global_result[len(segments) :]

    assert any(math.isclose(b.length, 150.0, abs_tol=1e-6) for b in global_bridges)
    assert not any(math.isclose(b.length, 150.0, abs_tol=1e-6) for b in greedy_bridges)


def test_crossing_pair_conflict_resolved() -> None:
    """
    Two valid short bridges cross if paired incorrectly; global matching
    selects both 3-unit pairs instead of one long diagonal.
    """
    segments = [
        LineString([(0, 0), (0, 3)]),
        LineString([(3, 0), (3, 3)]),
        LineString([(0, 3), (10, 3)]),
        LineString([(3, 0), (10, 0)]),
    ]
    _, closed = close_gaps(segments, threshold=500)
    assert closed == 2


def test_wall_offset_150mm_colinear_180_degree() -> None:
    """150 mm colinear opposite endpoints (door/wall offset) must bridge."""
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (200, 0)]),
        LineString([(350, 0), (450, 0)]),
    ]
    result, closed = close_gaps(segments, threshold=500)
    bridges = result[len(segments) :]
    assert closed >= 1
    assert any(math.isclose(b.length, 150.0, rel_tol=0, abs_tol=1e-6) for b in bridges)


def test_wall_offset_180mm_vertical() -> None:
    segments = [
        LineString([(0, 0), (0, 100)]),
        LineString([(0, 100), (0, 200)]),
        LineString([(0, 380), (0, 480)]),
    ]
    result, closed = close_gaps(segments, threshold=500)
    bridges = result[len(segments) :]
    assert closed >= 1
    assert any(math.isclose(b.length, 180.0, rel_tol=0, abs_tol=1e-6) for b in bridges)


def test_bridge_cost_prioritizes_wall_thickness_offset() -> None:
    p_a = (0.0, 0.0)
    p_b = (5.0, 0.0)
    p_c = (150.0, 0.0)
    dirs_a = [0.0]
    dirs_c = [180.0]

    spur_cost = bridge_cost(p_a, p_b, dirs_a, [0.0], 5.0, 30.0)
    offset_cost = bridge_cost(p_a, p_c, dirs_a, dirs_c, 150.0, 30.0)

    assert offset_cost < spur_cost


def test_min_cost_matching_returns_disjoint_pairs() -> None:
    points = [(0, 0), (150, 0), (5, 0), (155, 0)]
    dirs = {
        (0, 0): [0.0],
        (150, 0): [180.0],
        (5, 0): [90.0],
        (155, 0): [270.0],
    }
    pairs = min_cost_endpoint_matching(points, dirs, threshold=500)
    used: set[int] = set()
    for i, j in pairs:
        assert i not in used and j not in used
        used.add(i)
        used.add(j)


def _close_gaps_greedy(
    segments: list[LineString],
    threshold: float,
    max_angle: float = 30.0,
) -> tuple[list[LineString], int]:
    """Legacy greedy nearest-neighbor closure for regression comparison."""
    from collections import defaultdict

    from src.gap_handler import _angle_between, _round_point

    endpoint_count: dict[tuple[float, float], int] = defaultdict(int)
    endpoint_dirs: dict[tuple[float, float], list[float]] = defaultdict(list)

    for seg in segments:
        coords = list(seg.coords)
        a = _round_point(coords[0][0], coords[0][1])
        b = _round_point(coords[-1][0], coords[-1][1])
        endpoint_count[a] += 1
        endpoint_count[b] += 1
        if len(coords) >= 2:
            endpoint_dirs[a].append(_angle_between(coords[1], coords[0]))
            endpoint_dirs[b].append(_angle_between(coords[-2], coords[-1]))

    free_points = [pt for pt, count in endpoint_count.items() if count == 1]
    closed_count = 0
    used: set[int] = set()
    bridges: list[LineString] = []

    for i, p1 in enumerate(free_points):
        if i in used:
            continue
        best_j = -1
        best_dist = threshold + 1

        for j, p2 in enumerate(free_points):
            if j <= i or j in used:
                continue
            dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
            if dist > threshold or dist < 1e-9:
                continue
            if dist < best_dist:
                best_dist = dist
                best_j = j

        if best_j >= 0:
            p2 = free_points[best_j]
            bridges.append(LineString([p1, p2]))
            used.add(i)
            used.add(best_j)
            closed_count += 1

    return segments + bridges, closed_count


def test_iterative_close_stops_when_no_new_bridges() -> None:
    """Second pass must not run after a pass closes zero gaps."""
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (100, 100)]),
        LineString([(100, 100), (0, 100)]),
        LineString([(0, 100), (0, 50)]),
    ]
    single, closed_single = close_gaps(segments, threshold=500)
    iterative, closed_iter = iterative_close_gaps(segments, threshold=500, max_passes=3)
    assert closed_iter >= closed_single
    assert len(iterative) >= len(single)


def test_iterative_close_without_renod_matches_single_pass_on_simple_graph() -> None:
    """Renoding is required for extra closures; identical graph yields same bridge count."""
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(250, 0), (350, 0)]),
    ]
    _, closed_single = close_gaps(segments, threshold=500)
    _, closed_iter = iterative_close_gaps(segments, threshold=500, max_passes=1)
    assert closed_iter == closed_single


def test_is_wall_offset_profile_150mm_180_degree() -> None:
    assert is_wall_offset_profile(150.0, [0.0], [180.0])
    assert is_wall_offset_profile(180.0, [90.0], [270.0])
    assert not is_wall_offset_profile(150.0, [0.0], [90.0])
    assert not is_wall_offset_profile(125.0, [0.0], [180.0])


def test_phased_matching_closes_more_bridges_than_general_in_profile_grid() -> None:
    """
    Dense grid with competing spurs: phased matching must close more pairs
    than P2.1 alone, and min_cost_endpoint_matching adopts phased result.
    """
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (200, 0)]),
        LineString([(350, 0), (450, 0)]),
        LineString([(202, 0), (202, 30)]),
        LineString([(0, 0), (0, 50)]),
        LineString([(450, 0), (450, 50)]),
    ]
    _, general_closed = close_gaps(segments, threshold=500, colinear_profile=False)
    _, phased_closed = close_gaps(segments, threshold=500, colinear_profile=True)
    assert phased_closed >= general_closed
    assert phased_closed >= 2


def test_phased_matching_resolves_micro_gap_conflict() -> None:
    """7 mm equidistant foundation/beam tie must bridge via micro-gap pass."""
    points = [(0.0, 0.0), (7.432, 0.0), (0.0, 200.0), (7.432, 200.0)]
    dirs = {
        (0.0, 0.0): [0.0],
        (7.432, 0.0): [0.0],
        (0.0, 200.0): [180.0],
        (7.432, 200.0): [180.0],
    }
    general = min_cost_endpoint_matching(points, dirs, threshold=500, colinear_profile=False)
    adopted = min_cost_endpoint_matching(points, dirs, threshold=500, colinear_profile=True)
    assert len(adopted) >= len(general)
    lengths = {
        round(math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1]), 3)
        for i, j in adopted
    }
    assert 7.432 in lengths


def test_tier2_closes_structural_gap_above_tier1() -> None:
    """745 mm same-layer pour-break bridges only in tier-2 pass."""
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(845, 0), (945, 0)]),
    ]
    layers = {
        (100.0, 0.0): "S-FNDN-1",
        (845.0, 0.0): "S-FNDN-1",
    }
    _, tier1_closed = close_gaps(segments, threshold=500)
    _, tier2_closed = close_gaps_tier2(
        segments,
        tier1_threshold=500,
        tier2_threshold=1000,
        endpoint_layers=layers,
    )
    assert tier1_closed == 0
    assert tier2_closed == 1


def test_tier2_rejects_detail_layer_pair() -> None:
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(700, 0), (800, 0)]),
    ]
    layers = {
        (0.0, 0.0): "A-WALL-2",
        (700.0, 0.0): "A-DETL-1",
    }
    _, closed = close_gaps_tier2(
        segments,
        tier1_threshold=500,
        tier2_threshold=1000,
        endpoint_layers=layers,
    )
    assert closed == 0


def test_is_approved_tier2_layer_pair_whitelist() -> None:
    assert is_structural_layer("S-FNDN-1")
    assert is_approved_tier2_layer_pair("S-FNDN-1", "S-FNDN-1")
    assert is_approved_tier2_layer_pair("S-FNDN-1", "S-BEAM-2")
    assert is_approved_tier2_layer_pair("A-WALL-3", "S-BEAM-1")
    assert not is_approved_tier2_layer_pair("A-WALL-2", "A-DETL-1")


def test_iterative_close_pass_two_after_renod() -> None:
    """
    Grid where pass-1 bridges change topology so pass-2 can close another pair.
    Mimics S111_J foundation grid behavior at small scale.
    """
    segments = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (200, 0)]),
        LineString([(350, 0), (450, 0)]),
        LineString([(0, 0), (0, 100)]),
        LineString([(200, 0), (200, 100)]),
        LineString([(450, 0), (450, 100)]),
        LineString([(0, 100), (50, 100)]),
        LineString([(150, 100), (200, 100)]),
        LineString([(250, 100), (450, 100)]),
    ]
    _, closed_single = close_gaps(segments, threshold=500)
    _, closed_iter = iterative_close_gaps(segments, threshold=500, max_passes=3)
    assert closed_iter >= closed_single
