"""P1 — Grid frame builder: extract grid lines, cluster axes, generate bay cells."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from ezdxf.layouts import Modelspace
from shapely.geometry import LineString, Polygon

from src.extractor import SUPPORTED_TYPES, entity_to_segments
logger = logging.getLogger(__name__)

DEFAULT_GRID_LAYERS = ("S-GRID-1", "S-GRID-IDEN")
DEFAULT_ANGLE_TOLERANCE_DEG = 2.0
DEFAULT_POSITION_CLUSTER_MM = 500.0
DEFAULT_MIN_LINE_LENGTH_MM = 1000.0


@dataclass(frozen=True)
class GridLine:
    """One grid axis segment used for framing."""

    layer: str
    angle_deg: float
    length_mm: float
    position_mm: float
    midpoint: tuple[float, float]
    segment: LineString


@dataclass
class AxisFamily:
    """Parallel grid lines of one orientation (sorted by position)."""

    name: str
    angle_deg: float
    positions_mm: list[float]
    line_count: int
    source_layers: list[str] = field(default_factory=list)


@dataclass
class BayCell:
    """Rectangle between adjacent axes on two families."""

    bay_id: int
    row: int
    col: int
    polygon: Polygon
    area_m2: float
    centroid: tuple[float, float]
    bounds: tuple[float, float, float, float]
    axis_x_min_mm: float
    axis_x_max_mm: float
    axis_y_min_mm: float
    axis_y_max_mm: float
    int_label: str = ""
    raw_area_m2: float = 0.0
    clipped_polygon: Polygon | None = None
    clipped_area_m2: float = 0.0
    coverage_pct: float = 0.0

    def __post_init__(self) -> None:
        if self.raw_area_m2 <= 0:
            self.raw_area_m2 = self.area_m2
        if self.clipped_polygon is None:
            self.clipped_polygon = self.polygon
        if self.clipped_area_m2 <= 0 and self.clipped_polygon is not None:
            self.clipped_area_m2 = self.area_m2


@dataclass
class GridFrameResult:
    """Output of grid frame construction."""

    source_file: str
    grid_layers_used: list[str]
    candidate_grid_layers: list[str]
    raw_line_count: int
    grid_lines: list[GridLine]
    axis_families: list[AxisFamily]
    axis_a: AxisFamily | None
    axis_b: AxisFamily | None
    raw_bay_count: int
    bay_count: int
    bays: list[BayCell]
    expected_int_count: int | None
    expected_bay_count: int | None
    frame_mode: str
    frame_xs_mm: list[float] = field(default_factory=list)
    frame_ys_mm: list[float] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def discover_candidate_grid_layers(
    msp: Modelspace,
    *,
    configured_layers: list[str],
    min_line_entities: int = 1,
) -> list[str]:
    """Layers whose name contains GRID and that carry line geometry."""
    configured_upper = {name.upper() for name in configured_layers}
    counts: dict[str, int] = {}
    for entity in msp:
        if entity.dxftype() not in SUPPORTED_TYPES:
            continue
        layer = entity.dxf.layer or "0"
        if "GRID" not in layer.upper():
            continue
        counts[layer] = counts.get(layer, 0) + 1

    candidates = [
        layer
        for layer, count in counts.items()
        if count >= min_line_entities and layer.upper() not in configured_upper
    ]
    return sorted(candidates, key=lambda name: (-counts[name], name))


def _line_angle_deg(segment: LineString) -> float:
    (x0, y0), (x1, y1) = segment.coords[0], segment.coords[-1]
    return math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180.0


def _line_position_mm(segment: LineString, angle_deg: float) -> float:
    """Scalar position along the normal to the line (for sorting parallel axes)."""
    (x0, y0), (x1, y1) = segment.coords[0], segment.coords[-1]
    mid_x = (x0 + x1) / 2.0
    mid_y = (y0 + y1) / 2.0
    rad = math.radians(angle_deg)
    normal_x = -math.sin(rad)
    normal_y = math.cos(rad)
    return mid_x * normal_x + mid_y * normal_y


def _cluster_positions(
    positions: list[float],
    tolerance_mm: float,
) -> list[float]:
    if not positions:
        return []
    sorted_pos = sorted(positions)
    clusters: list[list[float]] = [[sorted_pos[0]]]
    for value in sorted_pos[1:]:
        if value - clusters[-1][-1] <= tolerance_mm:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return [sum(group) / len(group) for group in clusters]


def _angles_compatible(a: float, b: float, tolerance_deg: float) -> bool:
    delta = abs(a - b)
    delta = min(delta, 180.0 - delta)
    return delta <= tolerance_deg


def _cluster_lines_into_families(
    lines: list[GridLine],
    angle_tolerance_deg: float,
) -> list[list[GridLine]]:
    if not lines:
        return []
    families: list[list[GridLine]] = []
    for line in sorted(lines, key=lambda item: item.angle_deg):
        placed = False
        for family in families:
            if _angles_compatible(line.angle_deg, family[0].angle_deg, angle_tolerance_deg):
                family.append(line)
                placed = True
                break
        if not placed:
            families.append([line])
    return families


def _family_to_axis(
    family: list[GridLine],
    name: str,
    position_cluster_mm: float,
) -> AxisFamily:
    positions = [line.position_mm for line in family]
    merged = _cluster_positions(positions, position_cluster_mm)
    layers = sorted({line.layer for line in family})
    return AxisFamily(
        name=name,
        angle_deg=family[0].angle_deg,
        positions_mm=merged,
        line_count=len(family),
        source_layers=layers,
    )


def _select_axis_positions(
    positions: list[float],
    target_cells: int,
) -> list[float]:
    """Pick axis lines to obtain target_cells bays along this direction."""
    if target_cells < 1 or len(positions) < 2:
        return positions
    needed_axes = target_cells + 1
    if len(positions) <= needed_axes:
        return positions
    indices = [round(i * (len(positions) - 1) / (needed_axes - 1)) for i in range(needed_axes)]
    selected: list[float] = []
    last_index = -1
    for index in indices:
        index = max(0, min(index, len(positions) - 1))
        if index != last_index:
            selected.append(positions[index])
            last_index = index
    return selected


def _factor_bay_count(n: int) -> tuple[int, int] | None:
    """Return (cells_along_a, cells_along_b) with product n, closest to square."""
    if n < 1:
        return None
    best: tuple[int, int] | None = None
    best_delta = 10**9
    for a in range(1, int(math.sqrt(n)) + 1):
        if n % a != 0:
            continue
        b = n // a
        delta = abs(a - b)
        if delta < best_delta:
            best_delta = delta
            best = (a, b)
    return best


def _enumerate_bay_factors(n: int) -> list[tuple[int, int]]:
    """All (cells_a, cells_b) pairs with product exactly n."""
    if n < 1:
        return []
    pairs: list[tuple[int, int]] = []
    for cells_a in range(1, n + 1):
        if n % cells_a != 0:
            continue
        cells_b = n // cells_a
        pairs.append((cells_a, cells_b))
        if cells_a != cells_b:
            pairs.append((cells_b, cells_a))
    return pairs


def _resolve_target_axes(
    axis_a: AxisFamily,
    axis_b: AxisFamily,
    expected_bay_count: int,
) -> tuple[list[float], list[float], str]:
    """Choose major axes so bay count matches expected INT count when possible."""
    best: tuple[list[float], list[float], str] | None = None
    best_score = -1.0

    for cells_a, cells_b in _enumerate_bay_factors(expected_bay_count):
        selected_a = _select_axis_positions(axis_a.positions_mm, cells_a)
        selected_b = _select_axis_positions(axis_b.positions_mm, cells_b)
        bays = (len(selected_a) - 1) * (len(selected_b) - 1)
        if bays != expected_bay_count:
            continue
        score = min(
            len(selected_a) / max(len(axis_a.positions_mm), 1),
            len(selected_b) / max(len(axis_b.positions_mm), 1),
        )
        if score > best_score:
            best_score = score
            best = (selected_a, selected_b, f"target_{expected_bay_count}")

    if best is not None:
        return best

    return axis_a.positions_mm, axis_b.positions_mm, "raw_unmatched_target"


def _build_bay_polygons(
    xs: list[float],
    ys: list[float],
    *,
    unit_scale_m: float,
) -> list[BayCell]:
    if len(xs) < 2 or len(ys) < 2:
        return []

    bays: list[BayCell] = []
    bay_id = 0
    for row in range(len(ys) - 1):
        for col in range(len(xs) - 1):
            x0, x1 = xs[col], xs[col + 1]
            y0, y1 = ys[row], ys[row + 1]
            polygon = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            area_m2 = polygon.area * (unit_scale_m**2)
            centroid = (polygon.centroid.x, polygon.centroid.y)
            bay_id += 1
            bays.append(
                BayCell(
                    bay_id=bay_id,
                    row=row,
                    col=col,
                    polygon=polygon,
                    area_m2=area_m2,
                    centroid=centroid,
                    bounds=polygon.bounds,
                    axis_x_min_mm=x0,
                    axis_x_max_mm=x1,
                    axis_y_min_mm=y0,
                    axis_y_max_mm=y1,
                )
            )
    return bays


def _normal_to_world_coord(position_mm: float, angle_deg: float) -> tuple[float | None, float | None]:
    """Convert axis normal position to x or y coordinate (whichever is dominant)."""
    rad = math.radians(angle_deg)
    nx = -math.sin(rad)
    ny = math.cos(rad)
    if abs(nx) >= abs(ny):
        if abs(nx) < 1e-9:
            return None, None
        return position_mm / nx, None
    if abs(ny) < 1e-9:
        return None, None
    return None, position_mm / ny


def _assign_xy_axes(
    axis_a: AxisFamily,
    axis_b: AxisFamily,
    positions_a: list[float],
    positions_b: list[float],
) -> tuple[list[float], list[float]]:
    """Map two axis families to sorted x and y edge lists."""
    verticalish = axis_a
    vertical_positions = positions_a
    horizontalish = axis_b
    horizontal_positions = positions_b

    if abs(axis_a.angle_deg - 90.0) < abs(axis_b.angle_deg - 90.0):
        verticalish, horizontalish = axis_a, axis_b
        vertical_positions, horizontal_positions = positions_a, positions_b
    else:
        verticalish, horizontalish = axis_b, axis_a
        vertical_positions, horizontal_positions = positions_b, positions_a

    xs: list[float] = []
    ys: list[float] = []
    for position in vertical_positions:
        x, _ = _normal_to_world_coord(position, verticalish.angle_deg)
        if x is not None:
            xs.append(x)
    for position in horizontal_positions:
        _, y = _normal_to_world_coord(position, horizontalish.angle_deg)
        if y is not None:
            ys.append(y)

    return sorted(xs), sorted(ys)


def _is_orthogonal(angle_deg: float, tolerance_deg: float = DEFAULT_ANGLE_TOLERANCE_DEG) -> bool:
    """True when line is aligned to global X or Y (grid warehouse convention)."""
    near_horizontal = angle_deg <= tolerance_deg or angle_deg >= 180.0 - tolerance_deg
    near_vertical = abs(angle_deg - 90.0) <= tolerance_deg
    return near_horizontal or near_vertical


def extract_grid_lines(
    msp: Modelspace,
    layers: list[str],
    *,
    min_line_length_mm: float = DEFAULT_MIN_LINE_LENGTH_MM,
    orthogonal_only: bool = True,
    angle_tolerance_deg: float = DEFAULT_ANGLE_TOLERANCE_DEG,
) -> list[GridLine]:
    """Extract grid line segments from configured and candidate layers."""
    layer_set = {name.upper() for name in layers}
    lines: list[GridLine] = []

    for entity in msp:
        if entity.dxftype() not in SUPPORTED_TYPES:
            continue
        layer = entity.dxf.layer or "0"
        if layer.upper() not in layer_set:
            continue
        for segment in entity_to_segments(entity):
            length = segment.length
            if length < min_line_length_mm:
                continue
            angle = _line_angle_deg(segment)
            if orthogonal_only and not _is_orthogonal(angle, angle_tolerance_deg):
                continue
            position = _line_position_mm(segment, angle)
            mid = segment.interpolate(0.5, normalized=True)
            lines.append(
                GridLine(
                    layer=layer,
                    angle_deg=angle,
                    length_mm=length,
                    position_mm=position,
                    midpoint=(mid.x, mid.y),
                    segment=segment,
                )
            )

    logger.info("Extracted %d grid line segments from %s", len(lines), layers)
    return lines


def build_grid_frame(
    msp: Modelspace,
    *,
    source_file: str = "",
    grid_layers: list[str] | None = None,
    include_candidate_layers: bool = True,
    angle_tolerance_deg: float = DEFAULT_ANGLE_TOLERANCE_DEG,
    position_cluster_mm: float = DEFAULT_POSITION_CLUSTER_MM,
    min_line_length_mm: float = DEFAULT_MIN_LINE_LENGTH_MM,
    expected_bay_count: int | None = None,
    expected_int_count: int | None = None,
    unit_scale_m: float = 0.001,
) -> GridFrameResult:
    """Build bay grid from structural grid linework."""
    configured = list(grid_layers or DEFAULT_GRID_LAYERS)
    candidates = (
        discover_candidate_grid_layers(msp, configured_layers=configured)
        if include_candidate_layers
        else []
    )
    layers_used = list(dict.fromkeys(configured + candidates))
    warnings: list[str] = []

    grid_lines = extract_grid_lines(
        msp,
        layers_used,
        min_line_length_mm=min_line_length_mm,
        orthogonal_only=True,
        angle_tolerance_deg=angle_tolerance_deg,
    )
    if not grid_lines:
        warnings.append("No grid line segments found on configured or candidate layers.")
        return GridFrameResult(
            source_file=source_file,
            grid_layers_used=layers_used,
            candidate_grid_layers=candidates,
            raw_line_count=0,
            grid_lines=[],
            axis_families=[],
            axis_a=None,
            axis_b=None,
            raw_bay_count=0,
            bay_count=0,
            bays=[],
            expected_int_count=expected_int_count,
            expected_bay_count=expected_bay_count,
            frame_mode="empty",
            frame_xs_mm=[],
            frame_ys_mm=[],
            warnings=warnings,
        )

    families_raw = _cluster_lines_into_families(grid_lines, angle_tolerance_deg)
    if len(families_raw) < 2:
        warnings.append(
            f"Expected two axis families; found {len(families_raw)}. "
            "Cannot form orthogonal bay cells."
        )

    axis_families = [
        _family_to_axis(family, f"axis_{index + 1}", position_cluster_mm)
        for index, family in enumerate(
            sorted(families_raw, key=lambda fam: -len(fam))
        )
    ]

    axis_a: AxisFamily | None = axis_families[0] if axis_families else None
    axis_b: AxisFamily | None = axis_families[1] if len(axis_families) > 1 else None

    raw_bay_count = 0
    if axis_a and axis_b:
        raw_bay_count = max(0, (len(axis_a.positions_mm) - 1) * (len(axis_b.positions_mm) - 1))

    target = expected_bay_count or expected_int_count
    frame_mode = "raw"
    positions_a = axis_a.positions_mm if axis_a else []
    positions_b = axis_b.positions_mm if axis_b else []

    if axis_a and axis_b and target is not None and target > 0:
        positions_a, positions_b, frame_mode = _resolve_target_axes(axis_a, axis_b, target)
        if frame_mode == "raw_unmatched_target":
            warnings.append(
                f"Could not derive exactly {target} bays from grid axes; reporting raw partition."
            )

    frame_xs: list[float] = []
    frame_ys: list[float] = []
    bays: list[BayCell] = []
    if axis_a and axis_b:
        xs, ys = _assign_xy_axes(axis_a, axis_b, positions_a, positions_b)
        frame_xs = list(xs)
        frame_ys = list(ys)
        if len(xs) < 2 or len(ys) < 2:
            warnings.append(
                f"Insufficient orthogonal axes for bay polygons (x={len(xs)}, y={len(ys)})."
            )
        else:
            bays = _build_bay_polygons(xs, ys, unit_scale_m=unit_scale_m)

    if target is not None and bays and len(bays) != target:
        warnings.append(
            f"Bay count {len(bays)} does not match expected INT count {target}."
        )

    return GridFrameResult(
        source_file=source_file,
        grid_layers_used=layers_used,
        candidate_grid_layers=candidates,
        raw_line_count=len(grid_lines),
        grid_lines=grid_lines,
        axis_families=axis_families,
        axis_a=axis_a,
        axis_b=axis_b,
        raw_bay_count=raw_bay_count,
        bay_count=len(bays),
        bays=bays,
        expected_int_count=expected_int_count or expected_bay_count,
        expected_bay_count=expected_bay_count or expected_int_count,
        frame_mode=frame_mode,
        frame_xs_mm=frame_xs,
        frame_ys_mm=frame_ys,
        warnings=warnings,
    )
