"""SVG/PNG preview for grid frame geometry."""

from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import Polygon

from src.zone_engine.bay_geometry import GridFrameGeometryResult

logger = logging.getLogger(__name__)


def _polygon_coords(polygon: Polygon) -> list[tuple[float, float]]:
    if polygon.is_empty:
        return []
    return list(polygon.exterior.coords)


def _plot_polygon(ax, polygon: Polygon, **kwargs) -> None:
    if polygon.is_empty:
        return
    coords = _polygon_coords(polygon)
    if len(coords) < 3:
        return
    patch = MplPolygon(coords, closed=True, **kwargs)
    ax.add_patch(patch)


def _plot_axes(ax, xs: list[float], ys: list[float], bounds) -> None:
    minx, miny, maxx, maxy = bounds
    for x in xs:
        ax.plot([x, x], [miny, maxy], color="#888888", linewidth=0.6, linestyle="--", zorder=2)
    for y in ys:
        ax.plot([minx, maxx], [y, y], color="#888888", linewidth=0.6, linestyle="--", zorder=2)


def render_grid_frame_preview(
    result: GridFrameGeometryResult,
    output_path: str | Path,
    *,
    dpi: int = 150,
    figsize: tuple[float, float] = (14, 10),
) -> list[Path]:
    """Write SVG and PNG previews. Returns paths written."""
    import matplotlib.pyplot as plt

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stem = path.stem if path.suffix else path.name
    parent = path.parent

    fig, ax = plt.subplots(figsize=figsize)

    slab = result.slab.polygon
    if not slab.is_empty:
        _plot_polygon(
            ax,
            slab,
            facecolor="none",
            edgecolor="#1a5276",
            linewidth=2.0,
            linestyle="-",
            zorder=1,
        )

    frame = result.frame
    if frame.frame_xs_mm and frame.frame_ys_mm:
        bounds = slab.bounds if not slab.is_empty else _combined_bounds(result)
        if bounds:
            _plot_axes(ax, frame.frame_xs_mm, frame.frame_ys_mm, bounds)

    clipped_patches = []
    raw_patches = []
    for bay in result.bays:
        if not bay.polygon.is_empty:
            raw_patches.append(MplPolygon(_polygon_coords(bay.polygon), closed=True))
        if bay.clipped_polygon and not bay.clipped_polygon.is_empty:
            clipped_patches.append(
                MplPolygon(_polygon_coords(bay.clipped_polygon), closed=True)
            )

    if raw_patches:
        ax.add_collection(
            PatchCollection(
                raw_patches,
                facecolor="#f5b7b1",
                edgecolor="#c0392b",
                alpha=0.25,
                linewidths=0.4,
                zorder=3,
            )
        )
    if clipped_patches:
        ax.add_collection(
            PatchCollection(
                clipped_patches,
                facecolor="#85c1e9",
                edgecolor="#2471a3",
                alpha=0.55,
                linewidths=0.8,
                zorder=4,
            )
        )

    for bay in result.bays:
        if bay.clipped_polygon and not bay.clipped_polygon.is_empty:
            cx, cy = bay.clipped_polygon.centroid.x, bay.clipped_polygon.centroid.y
        else:
            cx, cy = bay.centroid
        ax.text(
            cx,
            cy,
            bay.int_label,
            ha="center",
            va="center",
            fontsize=7,
            fontweight="bold",
            color="#1b2631",
            zorder=6,
        )

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(
        f"Grid frame — {result.frame.source_file} "
        f"({result.frame.bay_count} bays, slab: {result.slab.method})"
    )
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    _autoscale(ax, result)

    svg_path = parent / f"{stem}.svg"
    png_path = parent / f"{stem}.png"
    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    fig.savefig(png_path, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    logger.info("Wrote preview SVG %s and PNG %s", svg_path, png_path)
    return [svg_path, png_path]


def _combined_bounds(result: GridFrameGeometryResult) -> tuple[float, float, float, float] | None:
    bounds_list = []
    for bay in result.bays:
        if not bay.polygon.is_empty:
            bounds_list.append(bay.polygon.bounds)
    if not bounds_list:
        return None
    minx = min(b[0] for b in bounds_list)
    miny = min(b[1] for b in bounds_list)
    maxx = max(b[2] for b in bounds_list)
    maxy = max(b[3] for b in bounds_list)
    return minx, miny, maxx, maxy


def _autoscale(ax, result: GridFrameGeometryResult) -> None:
    bounds = None
    if not result.slab.polygon.is_empty:
        bounds = result.slab.polygon.bounds
    else:
        bounds = _combined_bounds(result)
    if bounds:
        minx, miny, maxx, maxy = bounds
        pad_x = (maxx - minx) * 0.02 or 1000
        pad_y = (maxy - miny) * 0.02 or 1000
        ax.set_xlim(minx - pad_x, maxx + pad_x)
        ax.set_ylim(miny - pad_y, maxy + pad_y)
    ax.grid(True, alpha=0.2)
