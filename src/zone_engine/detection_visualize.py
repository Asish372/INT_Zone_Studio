"""Client-facing detection overlays — outline-first, no validation metrics."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import LineString, Polygon

from src.zone_engine.models import FaceAssignmentSummary, FaceData, IntZonePipelineResult

# Visually distinct colors for up to 32 INT zones
ZONE_PALETTE = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4",
    "#f032e6", "#bfef45", "#fabed4", "#469990", "#dcbeff", "#9A6324",
    "#800000", "#aaffc3", "#808000", "#ffd8b1", "#000075", "#a9a9a9",
    "#ffe119", "#4363d8", "#e6194b", "#3cb44b", "#f58231", "#911eb4",
    "#42d4f4", "#f032e6", "#bfef45", "#469990", "#dcbeff", "#9A6324",
    "#800000", "#aaffc3",
]

DETECTED_EDGE = "#0d7a2c"
DETECTED_FILL = "#66bb6a"
DETECTED_FILL_ALPHA = 0.42
STEP2_LW_FULL = 1.15
STEP2_LW_CIVIL = 1.6
STEP2_LW_ZOOM = 2.4
STEP2_ID_FONTSIZE_ZOOM = 11
CIVIL_DPI = 300
CIVIL_FILL_ALPHA = 0.32
BOUNDARY_LW_CIVIL = 2.5
DETECTED_BLOCK_EDGE = "#000000"
DETECTED_BLOCK_LW = 2.8
UNASSIGNED_EDGE = "#9e9e9e"
UNASSIGNED_FILL = "#eeeeee"
SLIVER_EDGE = "#9e9e9e"
SLIVER_FILL = "#e8e8e8"
SOURCE_LINE = "#424242"
SOURCE_LINE_FAINT = "#b0b0b0"
SLAB_EDGE = "#1565c0"
CALLOUT_EDGE = "#e65100"


def _coords(poly: Polygon) -> list[tuple[float, float]]:
    if poly.is_empty:
        return []
    return list(poly.exterior.coords)


def _zone_color_map(zones: list) -> dict[str, str]:
    return {z.label: ZONE_PALETTE[i % len(ZONE_PALETTE)] for i, z in enumerate(zones)}


def _face_label_map(assignment: FaceAssignmentSummary) -> dict[int, str]:
    return {a.face_id: a.int_label for a in assignment.assignments}


def _zone_label_text(zone) -> str:
    lines = [zone.label, f"{zone.area_m2:.1f} m²"]
    if zone.grid_ref:
        lines.append(str(zone.grid_ref))
    return "\n".join(lines)


def _zone_centroid(zone, result: IntZonePipelineResult) -> tuple[float, float]:
    if not zone.polygon.is_empty:
        c = zone.polygon.centroid
        return c.x, c.y
    bay = next((b for b in result.geometry.bays if b.int_label == zone.label), None)
    if bay and bay.clipped_polygon and not bay.clipped_polygon.is_empty:
        c = bay.clipped_polygon.centroid
        return c.x, c.y
    if bay:
        return bay.centroid
    return 0.0, 0.0


def _draw_zone_colored_face(
    ax,
    face: FaceData,
    int_label: str,
    colors: dict[str, str],
    *,
    linewidth: float = STEP2_LW_CIVIL,
    fill_alpha: float = CIVIL_FILL_ALPHA,
    zorder: int = 4,
) -> None:
    c = _coords(face.polygon)
    if len(c) < 3:
        return
    color = colors.get(int_label, "#888888")
    ax.add_patch(
        MplPolygon(
            c,
            closed=True,
            facecolor=color,
            edgecolor=color,
            alpha=fill_alpha,
            linewidth=linewidth,
            zorder=zorder,
        )
    )


def _draw_zone_legend_strip(ax, zones: list, colors: dict[str, str], *, y: float = 0.02) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    sorted_zones = sorted(zones, key=lambda z: int(z.label.split("-")[1]))
    handles = [
        Patch(facecolor=colors.get(z.label, "#ccc"), edgecolor="#333", label=z.label)
        for z in sorted_zones
        if not z.polygon.is_empty or z.area_m2 > 0
    ]
    if not handles:
        return
    ncol = min(len(handles), 12)
    ax.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, y),
        ncol=ncol,
        fontsize=6,
        framealpha=0.9,
        title="INT zones",
        title_fontsize=7,
    )


def _apply_title_block(
    fig,
    *,
    drawing_title: str,
    sheet_title: str,
    sheet_num: int,
    total_sheets: int,
    source_file: str,
    date_str: str = "",
) -> None:
    footer = (
        f"{drawing_title}  |  {sheet_title}  |  "
        f"Sheet {sheet_num} of {total_sheets}  |  Source: {source_file}"
    )
    if date_str:
        footer += f"  |  {date_str}"
    fig.text(0.5, 0.01, footer, ha="center", va="bottom", fontsize=8, color="#333333")


def _save_civil_fig(fig, out_path: Path, *, dpi: int = CIVIL_DPI) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return out_path


def assigned_face_ids(assignment: FaceAssignmentSummary) -> set[int]:
    return {a.face_id for a in assignment.assignments}


def faces_used_in_int_zones(result: IntZonePipelineResult) -> set[int]:
    """Face IDs that unary_union actually consumed — must match assignments."""
    ids: set[int] = set()
    for zone in result.zones:
        ids.update(zone.face_ids)
    return ids


def verify_step2_faces(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
) -> dict:
    """Confirm Step-2 face set equals INT-zone input faces."""
    assigned = assigned_face_ids(result.assignment)
    in_zones = faces_used_in_int_zones(result)
    all_ids = {f.face_id for f in all_faces}
    sliver_ids = all_ids - {a.face_id for a in result.assignment.assignments} - {
        o.face_id for o in result.assignment.orphans
    }
    return {
        "total_detected": len(all_faces),
        "sliver_count": result.assignment.sliver_count,
        "assigned_count": len(assigned),
        "orphan_count": result.assignment.orphan_count,
        "faces_in_zone_unions": len(in_zones),
        "assigned_equals_zones": assigned == in_zones,
        "assigned_ids": assigned,
        "zone_ids": in_zones,
    }


def _draw_linework(
    ax,
    segments: list[LineString],
    *,
    zorder: int = 1,
    faint: bool = False,
) -> None:
    if not segments:
        return
    seg_coords = [
        [(s.coords[0][0], s.coords[0][1]), (s.coords[-1][0], s.coords[-1][1])]
        for s in segments
    ]
    color = SOURCE_LINE_FAINT if faint else SOURCE_LINE
    lw = 0.2 if faint else 0.3
    alpha = 0.45 if faint else 0.85
    ax.add_collection(
        LineCollection(seg_coords, colors=color, linewidths=lw, alpha=alpha, zorder=zorder)
    )


def _sliver_face_ids(all_faces: list[FaceData], used_ids: set[int], assignment) -> set[int]:
    orphan_ids = {o.face_id for o in assignment.orphans}
    return {f.face_id for f in all_faces if f.face_id not in used_ids and f.face_id not in orphan_ids}


def _draw_int_input_polygon(
    ax,
    face: FaceData,
    *,
    linewidth: float,
    zorder: int = 4,
    show_fill: bool = True,
) -> None:
    c = _coords(face.polygon)
    if len(c) < 3:
        return
    ax.add_patch(
        MplPolygon(
            c,
            closed=True,
            facecolor=DETECTED_FILL if show_fill else "none",
            edgecolor=DETECTED_EDGE,
            alpha=DETECTED_FILL_ALPHA if show_fill else 1.0,
            linewidth=linewidth,
            zorder=zorder,
        )
    )


def _draw_face_id_label(ax, face: FaceData, *, fontsize: float, zorder: int = 8) -> None:
    cx, cy = face.polygon.centroid.x, face.polygon.centroid.y
    ax.text(
        cx, cy, str(face.face_id),
        ha="center", va="center",
        fontsize=fontsize, color="#004d1a", fontweight="bold", zorder=zorder,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.92,
                  edgecolor=DETECTED_EDGE, linewidth=0.6),
    )


def _autoscale(ax, result: IntZonePipelineResult, segments: list[LineString]) -> None:
    slab = result.geometry.slab.polygon
    if not slab.is_empty:
        minx, miny, maxx, maxy = slab.bounds
    elif segments:
        xs = [c[0] for s in segments for c in s.coords]
        ys = [c[1] for s in segments for c in s.coords]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
    else:
        return
    pad_x = (maxx - minx) * 0.02 or 1000
    pad_y = (maxy - miny) * 0.02 or 1000
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)


def _draw_detected_block_outlines(ax, faces: list[FaceData], *, zorder: int = 5) -> None:
    """One thick black outline per detected pour cell — no fill, no zone colour."""
    for face in faces:
        c = _coords(face.polygon)
        if len(c) < 3:
            continue
        ax.add_patch(
            MplPolygon(
                c,
                closed=True,
                facecolor="none",
                edgecolor=DETECTED_BLOCK_EDGE,
                linewidth=DETECTED_BLOCK_LW,
                zorder=zorder,
            )
        )


def _maximize_plan_axes(fig, ax, *, top: float = 0.90, bottom: float = 0.03) -> None:
    """Use nearly the full sheet for the plan (wide slabs fill page width)."""
    ax.set_aspect("equal", adjustable="box")
    fig.subplots_adjust(left=0.01, right=0.99, top=top, bottom=bottom)


def render_original_plan(
    result: IntZonePipelineResult,
    segments: list[LineString],
    *,
    title: str = "① Original plan",
) -> "matplotlib.axes.Axes":
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 10))
    _draw_linework(ax, segments)
    slab = result.geometry.slab.polygon
    if not slab.is_empty:
        ax.add_patch(
            MplPolygon(
                _coords(slab),
                closed=True,
                facecolor="none",
                edgecolor=SLAB_EDGE,
                linewidth=1.2,
                linestyle="--",
                zorder=2,
            )
        )
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.axis("off")
    _autoscale(ax, result, segments)
    return ax


def render_detected_faces_used_in_zones(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    *,
    id_min_area_m2: float = 2.0,
    title: str | None = None,
) -> "matplotlib.axes.Axes":
    """
    Step 2: ONLY faces assigned to INT zones (same polygons unary_union uses).

    Unassigned / sliver polygons are NOT drawn — they never become INT geometry.
    """
    import matplotlib.pyplot as plt

    used_ids = assigned_face_ids(result.assignment)
    face_by_id = {f.face_id: f for f in all_faces}

    if title is None:
        title = (
            f"② Faces used for INT zones ({len(used_ids)} polygons)\n"
            f"of {len(all_faces)} total detected — IDs on faces ≥ {id_min_area_m2:.0f} m²"
        )

    fig, ax = plt.subplots(figsize=(14, 10))
    _draw_linework(ax, segments)

    for face_id in sorted(used_ids):
        face = face_by_id.get(face_id)
        if face is None:
            continue
        c = _coords(face.polygon)
        if len(c) < 3:
            continue
        ax.add_patch(
            MplPolygon(
                c,
                closed=True,
                facecolor=DETECTED_FILL,
                edgecolor=DETECTED_EDGE,
                alpha=0.25,
                linewidth=0.6,
                zorder=3,
            )
        )
        if face.area_m2 >= id_min_area_m2:
            cx, cy = face.polygon.centroid.x, face.polygon.centroid.y
            ax.text(
                cx, cy, str(face_id),
                ha="center", va="center", fontsize=4, color="#1b5e20",
                fontweight="bold", zorder=5,
            )

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.axis("off")
    _autoscale(ax, result, segments)
    return ax


def render_all_detected_with_usage(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    *,
    title: str | None = None,
) -> "matplotlib.axes.Axes":
    """Diagnostic panel: all 618 detected — green=used in INT, gray=not used."""
    import matplotlib.pyplot as plt

    used_ids = assigned_face_ids(result.assignment)
    orphan_ids = {o.face_id for o in result.assignment.orphans}
    sliver_ids = {
        f.face_id for f in all_faces
        if f.face_id not in used_ids and f.face_id not in orphan_ids
    }

    if title is None:
        title = (
            f"All detected polygons ({len(all_faces)})\n"
            f"Green = {len(used_ids)} used in INT zones | "
            f"Gray = {len(sliver_ids)} slivers + {len(orphan_ids)} unassigned"
        )

    fig, ax = plt.subplots(figsize=(14, 10))
    _draw_linework(ax, segments)

    for face in all_faces:
        c = _coords(face.polygon)
        if len(c) < 3:
            continue
        if face.face_id in used_ids:
            ec, fc, alpha, lw = DETECTED_EDGE, DETECTED_FILL, 0.3, 0.7
        elif face.face_id in sliver_ids:
            ec, fc, alpha, lw = SLIVER_EDGE, "#f5f5f5", 0.15, 0.25
        else:
            ec, fc, alpha, lw = UNASSIGNED_EDGE, UNASSIGNED_FILL, 0.2, 0.4
        ax.add_patch(
            MplPolygon(c, closed=True, facecolor=fc, edgecolor=ec, alpha=alpha, linewidth=lw, zorder=3)
        )

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.axis("off")
    _autoscale(ax, result, segments)
    return ax


def render_zone_assignment(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    *,
    title: str = "③ Faces grouped by INT zone",
) -> "matplotlib.axes.Axes":
    import matplotlib.pyplot as plt

    used_ids = assigned_face_ids(result.assignment)
    face_by_id = {f.face_id: f for f in all_faces}
    label_by_face = {a.face_id: a.int_label for a in result.assignment.assignments}
    colors = _zone_color_map(result.zones)

    fig, ax = plt.subplots(figsize=(14, 10))
    _draw_linework(ax, segments)

    for face_id in sorted(used_ids):
        face = face_by_id.get(face_id)
        label = label_by_face.get(face_id)
        if face is None or label is None:
            continue
        c = _coords(face.polygon)
        if len(c) < 3:
            continue
        color = colors.get(label, "#888888")
        ax.add_patch(
            MplPolygon(
                c, closed=True, facecolor=color, edgecolor=color,
                alpha=0.35, linewidth=0.5, zorder=3,
            )
        )

    for zone in result.zones:
        if zone.polygon.is_empty:
            bay = next((b for b in result.geometry.bays if b.int_label == zone.label), None)
            if bay and bay.clipped_polygon and not bay.clipped_polygon.is_empty:
                cx, cy = bay.clipped_polygon.centroid.x, bay.clipped_polygon.centroid.y
            elif bay:
                cx, cy = bay.centroid
            else:
                continue
        else:
            cx, cy = zone.polygon.centroid.x, zone.polygon.centroid.y
        color = colors.get(zone.label, "#333333")
        ax.text(
            cx, cy, zone.label, ha="center", va="center",
            fontsize=7, fontweight="bold", color=color,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7, edgecolor="none"),
            zorder=6,
        )

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.axis("off")
    _autoscale(ax, result, segments)
    return ax


def render_zone_boundaries(
    result: IntZonePipelineResult,
    segments: list[LineString],
    *,
    title: str = "④ Final INT zone boundaries",
) -> "matplotlib.axes.Axes":
    import matplotlib.pyplot as plt

    colors = _zone_color_map(result.zones)
    fig, ax = plt.subplots(figsize=(14, 10))
    _draw_linework(ax, segments)

    for zone in result.zones:
        if zone.polygon.is_empty:
            continue
        c = _coords(zone.polygon)
        if len(c) < 3:
            continue
        color = colors.get(zone.label, "#333333")
        ax.add_patch(
            MplPolygon(
                c, closed=True, facecolor="none", edgecolor=color,
                linewidth=2.0, zorder=4,
            )
        )
        cx, cy = zone.polygon.centroid.x, zone.polygon.centroid.y
        ax.text(
            cx, cy, zone.label, ha="center", va="center",
            fontsize=7, fontweight="bold", color=color, zorder=6,
        )

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.axis("off")
    _autoscale(ax, result, segments)
    return ax


def render_detection_storyboard(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    out_path: Path,
    *,
    dpi: int = 150,
    include_all_detected_panel: bool = False,
) -> Path:
    """2×2 storyboard. Step 2 = faces used in INT zones (verified set)."""
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if include_all_detected_panel:
        fig, axes = plt.subplots(2, 2, figsize=(24, 18))
        panels = [
            (axes[0, 0], "original"),
            (axes[0, 1], "all_detected"),
            (axes[1, 0], "zones"),
            (axes[1, 1], "boundaries"),
        ]
    else:
        fig, axes = plt.subplots(2, 2, figsize=(24, 18))
        panels = [
            (axes[0, 0], "original"),
            (axes[0, 1], "used_faces"),
            (axes[1, 0], "zones"),
            (axes[1, 1], "boundaries"),
        ]

    used_ids = assigned_face_ids(result.assignment)
    face_by_id = {f.face_id: f for f in all_faces}
    label_by_face = {a.face_id: a.int_label for a in result.assignment.assignments}
    colors = _zone_color_map(result.zones)

    for ax, kind in panels:
        _draw_linework(ax, segments, zorder=1)
        slab = result.geometry.slab.polygon
        if kind == "original" and not slab.is_empty:
            ax.add_patch(
                MplPolygon(_coords(slab), closed=True, facecolor="none",
                           edgecolor=SLAB_EDGE, linewidth=1.0, linestyle="--", zorder=2)
            )
            ax.set_title("① Original plan", fontsize=11, fontweight="bold")
        elif kind == "used_faces":
            _draw_linework(ax, segments, faint=True, zorder=1)
            for face_id in sorted(used_ids):
                face = face_by_id.get(face_id)
                lbl = label_by_face.get(face_id)
                if face is None or lbl is None:
                    continue
                _draw_zone_colored_face(ax, face, lbl, colors, linewidth=0.7, fill_alpha=0.35)
            ax.set_title(
                f"② Detected pour areas ({len(used_ids)} cells)\n"
                f"Each coloured shape = one pour cell on the slab plan",
                fontsize=10, fontweight="bold",
            )
        elif kind == "all_detected":
            orphan_ids = {o.face_id for o in result.assignment.orphans}
            sliver_ids = {f.face_id for f in all_faces if f.face_id not in used_ids and f.face_id not in orphan_ids}
            for face in all_faces:
                c = _coords(face.polygon)
                if len(c) < 3:
                    continue
                if face.face_id in used_ids:
                    ec, fc, alpha, lw = DETECTED_EDGE, DETECTED_FILL, 0.35, 0.6
                elif face.face_id in sliver_ids:
                    ec, fc, alpha, lw = SLIVER_EDGE, "#f5f5f5", 0.1, 0.2
                else:
                    ec, fc, alpha, lw = UNASSIGNED_EDGE, UNASSIGNED_FILL, 0.15, 0.3
                ax.add_patch(MplPolygon(c, closed=True, facecolor=fc, edgecolor=ec, alpha=alpha, linewidth=lw, zorder=3))
            ax.set_title(
                f"② All detected ({len(all_faces)}) — green = INT input",
                fontsize=10, fontweight="bold",
            )
        elif kind == "zones":
            for face_id in sorted(used_ids):
                face = face_by_id.get(face_id)
                label = label_by_face.get(face_id)
                if face is None or label is None:
                    continue
                c = _coords(face.polygon)
                if len(c) < 3:
                    continue
                color = colors.get(label, "#888")
                ax.add_patch(MplPolygon(c, closed=True, facecolor=color, edgecolor=color,
                                        alpha=0.4, linewidth=0.4, zorder=3))
            for zone in result.zones:
                if zone.polygon.is_empty:
                    continue
                cx, cy = zone.polygon.centroid.x, zone.polygon.centroid.y
                ax.text(cx, cy, zone.label, ha="center", va="center", fontsize=6,
                        fontweight="bold", color=colors.get(zone.label, "#333"), zorder=6)
            ax.set_title("③ Grouped by INT zone", fontsize=11, fontweight="bold")
        elif kind == "boundaries":
            for zone in result.zones:
                if zone.polygon.is_empty:
                    continue
                c = _coords(zone.polygon)
                if len(c) < 3:
                    continue
                color = colors.get(zone.label, "#333")
                ax.add_patch(MplPolygon(c, closed=True, facecolor="none", edgecolor=color, linewidth=1.8, zorder=4))
                cx, cy = zone.polygon.centroid.x, zone.polygon.centroid.y
                ax.text(cx, cy, zone.label, ha="center", va="center", fontsize=6,
                        fontweight="bold", color=color, zorder=6)
            ax.set_title("④ Final zone boundaries", fontsize=11, fontweight="bold")

        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")
        _autoscale(ax, result, segments)

    fig.suptitle(
        f"INT zone detection — {result.geometry.frame.source_file}",
        fontsize=14, fontweight="bold", y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _bounds_with_padding(bounds: tuple[float, float, float, float], pad_ratio: float = 0.15) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = bounds
    pad_x = max((maxx - minx) * pad_ratio, 3000)
    pad_y = max((maxy - miny) * pad_ratio, 3000)
    return minx - pad_x, miny - pad_y, maxx + pad_x, maxy + pad_y


def _segment_in_bounds(seg: LineString, bounds: tuple[float, float, float, float]) -> bool:
    minx, miny, maxx, maxy = bounds
    mx = (seg.coords[0][0] + seg.coords[-1][0]) / 2
    my = (seg.coords[0][1] + seg.coords[-1][1]) / 2
    return minx <= mx <= maxx and miny <= my <= maxy


def _face_in_bounds(face: FaceData, bounds: tuple[float, float, float, float]) -> bool:
    minx, miny, maxx, maxy = bounds
    cx, cy = face.polygon.centroid.x, face.polygon.centroid.y
    return minx <= cx <= maxx and miny <= cy <= maxy


def pick_dense_zoom_targets(result: IntZonePipelineResult, *, count: int = 5) -> list[str]:
    """INT labels with most assigned faces — high-density zoom candidates."""
    ranked = sorted(
        [z for z in result.zones if z.face_count > 0],
        key=lambda z: z.face_count,
        reverse=True,
    )
    labels = [z.label for z in ranked[:count]]
    if len(labels) < count:
        labels.extend(z.label for z in result.zones if z.label not in labels)
    return labels[:count]


def _zone_zoom_bounds(zone) -> tuple[float, float, float, float]:
    if zone.polygon.is_empty:
        raise ValueError(f"Zone {zone.label} has no polygon for zoom")
    return _bounds_with_padding(zone.polygon.bounds, 0.12)


def render_step2_full_page(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    _zoom_labels: list[str],
    out_path: Path,
    *,
    dpi: int = CIVIL_DPI,
    sheet_num: int = 2,
    total_sheets: int = 9,
    date_str: str = "",
) -> Path:
    """Page 2 — detected pour blocks on original plan (black outline per cell)."""
    import matplotlib.pyplot as plt

    # MVP: show ALL auto-detected polygons, not INT-assigned subset only.
    detected_faces = sorted(all_faces, key=lambda f: f.face_id)

    fig, ax = plt.subplots(figsize=(24, 14))
    _draw_linework(ax, segments, faint=True, zorder=1)
    _draw_detected_block_outlines(ax, detected_faces, zorder=5)

    _autoscale(ax, result, segments)
    ax.axis("off")
    _maximize_plan_axes(fig, ax, top=0.92, bottom=0.04)
    ax.set_title(
        f"Each outlined box = one detected pour block on this plan ({len(detected_faces)} blocks)",
        fontsize=14,
        fontweight="bold",
        pad=10,
    )
    _apply_title_block(
        fig,
        drawing_title=result.geometry.frame.source_file,
        sheet_title="Detected Pour Areas",
        sheet_num=sheet_num,
        total_sheets=total_sheets,
        source_file=result.geometry.frame.source_file,
        date_str=date_str,
    )
    return _save_civil_fig(fig, out_path, dpi=dpi)


def render_step2b_detection_context(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    out_path: Path,
    *,
    dpi: int = CIVIL_DPI,
    sheet_num: int = 3,
    total_sheets: int = 9,
    date_str: str = "",
) -> Path:
    """Page 2b — green = pour areas used, gray = not used (visual legend only)."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    used_ids = assigned_face_ids(result.assignment)
    sliver_ids = _sliver_face_ids(all_faces, used_ids, result.assignment)

    fig, ax = plt.subplots(figsize=(24, 14))
    _draw_linework(ax, segments, faint=True, zorder=1)

    for face in all_faces:
        c = _coords(face.polygon)
        if len(c) < 3:
            continue
        if face.face_id in used_ids:
            ax.add_patch(
                MplPolygon(
                    c, closed=True, facecolor=DETECTED_FILL, edgecolor=DETECTED_EDGE,
                    alpha=0.35, linewidth=0.8, zorder=3,
                )
            )
        elif face.face_id in sliver_ids:
            ax.add_patch(
                MplPolygon(
                    c, closed=True, facecolor=SLIVER_FILL, edgecolor=SLIVER_EDGE,
                    alpha=0.4, linewidth=0.4, zorder=2,
                )
            )

    _autoscale(ax, result, segments)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(
        "Detection coverage on slab plan\nGreen = pour area used in INT zones  |  Gray = not used",
        fontsize=13, fontweight="bold", pad=14,
    )
    ax.legend(
        handles=[
            Patch(facecolor=DETECTED_FILL, edgecolor=DETECTED_EDGE, label="Pour area"),
            Patch(facecolor=SLIVER_FILL, edgecolor=SLIVER_EDGE, label="Not used"),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=2,
        fontsize=10,
        framealpha=0.95,
    )
    _apply_title_block(
        fig,
        drawing_title=result.geometry.frame.source_file,
        sheet_title="Detection Coverage",
        sheet_num=sheet_num,
        total_sheets=total_sheets,
        source_file=result.geometry.frame.source_file,
        date_str=date_str,
    )
    fig.subplots_adjust(bottom=0.08)
    return _save_civil_fig(fig, out_path, dpi=dpi)


def render_civil_zone_detail_page(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    zone_label: str,
    callout_letter: str,
    out_path: Path,
    *,
    dpi: int = CIVIL_DPI,
    sheet_num: int = 4,
    total_sheets: int = 9,
    date_str: str = "",
) -> Path:
    """Full-page INT zone detail — pour cells + INT label and SQM, no face IDs."""
    import matplotlib.pyplot as plt

    zone = next((z for z in result.zones if z.label == zone_label), None)
    if zone is None or zone.polygon.is_empty:
        raise ValueError(f"Cannot render detail for empty zone {zone_label}")

    used_ids = assigned_face_ids(result.assignment)
    label_by_face = _face_label_map(result.assignment)
    face_by_id = {f.face_id: f for f in all_faces}
    colors = _zone_color_map(result.zones)
    zone_color = colors.get(zone_label, "#333333")

    minx, miny, maxx, maxy = _zone_zoom_bounds(zone)
    fig, ax = plt.subplots(figsize=(24, 14))

    zoom_segs = [s for s in segments if _segment_in_bounds(s, (minx, miny, maxx, maxy))]
    if zoom_segs:
        seg_coords = [
            [(s.coords[0][0], s.coords[0][1]), (s.coords[-1][0], s.coords[-1][1])]
            for s in zoom_segs
        ]
        ax.add_collection(
            LineCollection(seg_coords, colors=SOURCE_LINE_FAINT, linewidths=0.4, alpha=0.7, zorder=1)
        )

    for face_id in zone.face_ids:
        face = face_by_id.get(face_id)
        label = label_by_face.get(face_id, zone_label)
        if face is None:
            continue
        _draw_zone_colored_face(ax, face, label, colors, linewidth=STEP2_LW_ZOOM, fill_alpha=0.45)

    if not zone.polygon.is_empty:
        ax.add_patch(
            MplPolygon(
                _coords(zone.polygon), closed=True,
                facecolor="none", edgecolor=zone_color, linewidth=BOUNDARY_LW_CIVIL, zorder=6,
            )
        )

    cx, cy = _zone_centroid(zone, result)
    ax.text(
        cx, cy, _zone_label_text(zone),
        ha="center", va="center", fontsize=14, fontweight="bold", color=zone_color, zorder=8,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.92, edgecolor=zone_color, linewidth=1.5),
    )

    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(
        f"Detail {callout_letter} — {zone_label} pour zone\n"
        f"{zone.face_count} detected pour cells within this zone",
        fontsize=13, fontweight="bold", pad=14,
    )
    _apply_title_block(
        fig,
        drawing_title=result.geometry.frame.source_file,
        sheet_title=f"Zone Detail — {zone_label}",
        sheet_num=sheet_num,
        total_sheets=total_sheets,
        source_file=result.geometry.frame.source_file,
        date_str=date_str,
    )
    fig.subplots_adjust(bottom=0.06)
    return _save_civil_fig(fig, out_path, dpi=dpi)


def render_civil_zone_detail_summary(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    zone_labels: list[str],
    start_letter: str,
    out_path: Path,
    *,
    dpi: int = CIVIL_DPI,
    sheet_num: int = 7,
    total_sheets: int = 9,
    date_str: str = "",
) -> Path:
    """2-up summary for remaining detail callout zones."""
    import matplotlib.pyplot as plt

    used_ids = assigned_face_ids(result.assignment)
    label_by_face = _face_label_map(result.assignment)
    face_by_id = {f.face_id: f for f in all_faces}
    colors = _zone_color_map(result.zones)

    n = len(zone_labels)
    fig, axes = plt.subplots(1, n, figsize=(12 * n, 10))
    if n == 1:
        axes = [axes]

    for idx, (ax, zone_label) in enumerate(zip(axes, zone_labels)):
        zone = next((z for z in result.zones if z.label == zone_label), None)
        if zone is None or zone.polygon.is_empty:
            ax.axis("off")
            continue

        letter = chr(ord(start_letter) + idx)
        minx, miny, maxx, maxy = _zone_zoom_bounds(zone)
        zoom_segs = [s for s in segments if _segment_in_bounds(s, (minx, miny, maxx, maxy))]
        if zoom_segs:
            seg_coords = [
                [(s.coords[0][0], s.coords[0][1]), (s.coords[-1][0], s.coords[-1][1])]
                for s in zoom_segs
            ]
            ax.add_collection(
                LineCollection(seg_coords, colors=SOURCE_LINE_FAINT, linewidths=0.35, alpha=0.6, zorder=1)
            )

        for face_id in zone.face_ids:
            face = face_by_id.get(face_id)
            lbl = label_by_face.get(face_id, zone_label)
            if face is None:
                continue
            _draw_zone_colored_face(ax, face, lbl, colors, linewidth=1.8, fill_alpha=0.4)

        zone_color = colors.get(zone_label, "#333")
        cx, cy = _zone_centroid(zone, result)
        ax.text(
            cx, cy, _zone_label_text(zone),
            ha="center", va="center", fontsize=11, fontweight="bold", color=zone_color, zorder=8,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, edgecolor=zone_color),
        )
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")
        ax.set_title(f"Detail {letter} — {zone_label}", fontsize=12, fontweight="bold")

    fig.suptitle(
        f"Additional zone detail — {result.geometry.frame.source_file}",
        fontsize=14, fontweight="bold", y=1.02,
    )
    _apply_title_block(
        fig,
        drawing_title=result.geometry.frame.source_file,
        sheet_title="Additional Zone Detail",
        sheet_num=sheet_num,
        total_sheets=total_sheets,
        source_file=result.geometry.frame.source_file,
        date_str=date_str,
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    return _save_civil_fig(fig, out_path, dpi=dpi)


def render_step2_zoom_page(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    zone_labels: list[str],
    out_path: Path,
    *,
    dpi: int = 200,
) -> Path:
    """Page 3 — 3–5 high-density zoom callouts with readable polygon IDs."""
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(zone_labels)
    cols = 3 if n >= 3 else n
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(8 * cols, 7 * rows))
    if n == 1:
        axes_flat = [axes]
    else:
        axes_flat = list(axes.flatten()) if rows > 1 or cols > 1 else [axes]

    used_ids = assigned_face_ids(result.assignment)
    sliver_ids = _sliver_face_ids(all_faces, used_ids, result.assignment)
    face_by_id = {f.face_id: f for f in all_faces}
    callout_letters = "ABCDE"

    for idx, label in enumerate(zone_labels):
        ax = axes_flat[idx]
        zone = next((z for z in result.zones if z.label == label), None)
        if zone is None or zone.polygon.is_empty:
            ax.axis("off")
            continue

        minx, miny, maxx, maxy = _zone_zoom_bounds(zone)
        zoom_segs = [s for s in segments if _segment_in_bounds(s, (minx, miny, maxx, maxy))]
        if zoom_segs:
            seg_coords = [
                [(s.coords[0][0], s.coords[0][1]), (s.coords[-1][0], s.coords[-1][1])]
                for s in zoom_segs
            ]
            ax.add_collection(
                LineCollection(seg_coords, colors=SOURCE_LINE_FAINT, linewidths=0.35, alpha=0.6, zorder=1)
            )

        for face in all_faces:
            if not _face_in_bounds(face, (minx, miny, maxx, maxy)):
                continue
            c = _coords(face.polygon)
            if len(c) < 3:
                continue
            if face.face_id in used_ids:
                ax.add_patch(
                    MplPolygon(
                        c, closed=True,
                        facecolor=DETECTED_FILL, edgecolor=DETECTED_EDGE,
                        alpha=DETECTED_FILL_ALPHA, linewidth=STEP2_LW_ZOOM, zorder=4,
                    )
                )
            elif face.face_id in sliver_ids:
                ax.add_patch(
                    MplPolygon(
                        c, closed=True,
                        facecolor=SLIVER_FILL, edgecolor=SLIVER_EDGE,
                        alpha=0.5, linewidth=0.8, zorder=2,
                    )
                )

        for fid in sorted(zone.face_ids):
            face = face_by_id.get(fid)
            if face is None or not _face_in_bounds(face, (minx, miny, maxx, maxy)):
                continue
            _draw_face_id_label(ax, face, fontsize=STEP2_ID_FONTSIZE_ZOOM)

        letter = callout_letters[idx] if idx < len(callout_letters) else str(idx + 1)
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")
        ax.set_title(
            f"Callout {letter} — {label}  ({zone.face_count} polygons)\n"
            f"Point at any green shape = one detected polygon in this INT zone",
            fontsize=11, fontweight="bold",
        )

    for j in range(n, len(axes_flat)):
        axes_flat[j].axis("off")

    fig.suptitle(
        f"Detected polygon detail — {result.geometry.frame.source_file}",
        fontsize=14, fontweight="bold", y=1.01,
    )
    fig.tight_layout()
    fig.savefig(out_path, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


def render_civil_zone_map_page(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    out_path: Path,
    *,
    dpi: int = CIVIL_DPI,
    sheet_num: int = 8,
    total_sheets: int = 9,
    date_str: str = "",
) -> Path:
    """INT zone colour map with SQM labels and legend strip."""
    import matplotlib.pyplot as plt

    used_ids = assigned_face_ids(result.assignment)
    face_by_id = {f.face_id: f for f in all_faces}
    label_by_face = _face_label_map(result.assignment)
    colors = _zone_color_map(result.zones)

    fig, ax = plt.subplots(figsize=(24, 14))
    _draw_linework(ax, segments, faint=True, zorder=1)

    for face_id in sorted(used_ids):
        face = face_by_id.get(face_id)
        label = label_by_face.get(face_id)
        if face is None or label is None:
            continue
        _draw_zone_colored_face(ax, face, label, colors, linewidth=0.6, fill_alpha=0.45)

    for zone in result.zones:
        if zone.polygon.is_empty and zone.area_m2 <= 0:
            continue
        cx, cy = _zone_centroid(zone, result)
        color = colors.get(zone.label, "#333333")
        ax.text(
            cx, cy, _zone_label_text(zone),
            ha="center", va="center", fontsize=8, fontweight="bold", color=color, zorder=7,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.85, edgecolor=color, linewidth=0.8),
        )

    _autoscale(ax, result, segments)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(
        "INT zone assignment — pour areas grouped by zone\nEach colour = one INT pour zone with area (m²)",
        fontsize=13, fontweight="bold", pad=14,
    )
    _draw_zone_legend_strip(ax, result.zones, colors, y=-0.06)
    _apply_title_block(
        fig,
        drawing_title=result.geometry.frame.source_file,
        sheet_title="INT Zone Map",
        sheet_num=sheet_num,
        total_sheets=total_sheets,
        source_file=result.geometry.frame.source_file,
        date_str=date_str,
    )
    fig.subplots_adjust(bottom=0.12)
    return _save_civil_fig(fig, out_path, dpi=dpi)


def render_civil_boundaries_page(
    result: IntZonePipelineResult,
    segments: list[LineString],
    out_path: Path,
    *,
    dpi: int = CIVIL_DPI,
    sheet_num: int = 9,
    total_sheets: int = 9,
    date_str: str = "",
) -> Path:
    """Final pour boundaries — bold outlines, INT + SQM, construction-issue style."""
    import matplotlib.pyplot as plt

    colors = _zone_color_map(result.zones)
    fig, ax = plt.subplots(figsize=(24, 14))
    _draw_linework(ax, segments, faint=True, zorder=1)

    for zone in result.zones:
        if zone.polygon.is_empty:
            continue
        c = _coords(zone.polygon)
        if len(c) < 3:
            continue
        color = colors.get(zone.label, "#333333")
        ax.add_patch(
            MplPolygon(
                c, closed=True, facecolor="none", edgecolor=color,
                linewidth=BOUNDARY_LW_CIVIL, zorder=5,
            )
        )
        cx, cy = _zone_centroid(zone, result)
        ax.text(
            cx, cy, _zone_label_text(zone),
            ha="center", va="center", fontsize=9, fontweight="bold", color=color, zorder=7,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, edgecolor=color),
        )

    _autoscale(ax, result, segments)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(
        "Final INT pour boundaries\nBold outlines show pour zone limits for site marking",
        fontsize=13, fontweight="bold", pad=14,
    )
    _draw_zone_legend_strip(ax, result.zones, colors, y=-0.04)
    _apply_title_block(
        fig,
        drawing_title=result.geometry.frame.source_file,
        sheet_title="Final Pour Boundaries",
        sheet_num=sheet_num,
        total_sheets=total_sheets,
        source_file=result.geometry.frame.source_file,
        date_str=date_str,
    )
    fig.subplots_adjust(bottom=0.10)
    return _save_civil_fig(fig, out_path, dpi=dpi)


def render_detection_page_set(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    out_dir: Path,
    file_key: str,
    *,
    dpi: int = CIVIL_DPI,
    zoom_count: int = 5,
    date_str: str = "",
) -> dict[str, Path]:
    """
    Civil-engineer page set (intermediate PNGs for PDF assembly):
      storyboard, detected, context, 3 detail pages, summary, zone map, boundaries
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom_labels = pick_dense_zoom_targets(result, count=zoom_count)
    total_sheets = 9
    detail_primary = zoom_labels[:3]
    detail_summary = zoom_labels[3:5]
    callout_letters = "ABCDE"

    paths: dict[str, Path] = {
        "page1_storyboard": out_dir / f"{file_key}_page1_storyboard.png",
        "page2_detected": out_dir / f"{file_key}_page2_detected_pour_areas.png",
        "page2b_context": out_dir / f"{file_key}_page2b_detection_coverage.png",
        "page3_summary": out_dir / f"{file_key}_page3_detail_summary.png",
        "page4_zones": out_dir / f"{file_key}_page4_int_zone_map.png",
        "page5_boundaries": out_dir / f"{file_key}_page5_final_boundaries.png",
    }
    for i, label in enumerate(detail_primary):
        paths[f"page3_detail_{i + 1}"] = out_dir / f"{file_key}_page3_detail_{label.replace('-', '_')}.png"

    render_detection_storyboard(
        result, all_faces, segments, paths["page1_storyboard"], dpi=dpi,
    )
    render_step2_full_page(
        result, all_faces, segments, zoom_labels, paths["page2_detected"],
        dpi=dpi, sheet_num=2, total_sheets=total_sheets, date_str=date_str,
    )
    render_step2b_detection_context(
        result, all_faces, segments, paths["page2b_context"],
        dpi=dpi, sheet_num=3, total_sheets=total_sheets, date_str=date_str,
    )

    for i, (label, letter) in enumerate(zip(detail_primary, callout_letters[:3])):
        key = f"page3_detail_{i + 1}"
        render_civil_zone_detail_page(
            result, all_faces, segments, label, letter, paths[key],
            dpi=dpi, sheet_num=4 + i, total_sheets=total_sheets, date_str=date_str,
        )

    if detail_summary:
        render_civil_zone_detail_summary(
            result, all_faces, segments, detail_summary, callout_letters[3],
            paths["page3_summary"],
            dpi=dpi, sheet_num=7, total_sheets=total_sheets, date_str=date_str,
        )

    render_civil_zone_map_page(
        result, all_faces, segments, paths["page4_zones"],
        dpi=dpi, sheet_num=8, total_sheets=total_sheets, date_str=date_str,
    )
    render_civil_boundaries_page(
        result, segments, paths["page5_boundaries"],
        dpi=dpi, sheet_num=9, total_sheets=total_sheets, date_str=date_str,
    )

    return paths


def render_step2_zoom(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    zone_label: str,
    out_path: Path,
    *,
    dpi: int = 200,
    show_all_detected: bool = True,
) -> Path:
    """
    Zoomed Step-2 panel for one INT zone area.
    Green outline = INT-input face. Gray = sliver (not used in zones).
    """
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    zone = next((z for z in result.zones if z.label == zone_label), None)
    bay = next((b for b in result.geometry.bays if b.int_label == zone_label), None)
    if zone is None and bay is None:
        raise ValueError(f"Unknown zone label: {zone_label}")

    if zone and not zone.polygon.is_empty:
        bounds = _bounds_with_padding(zone.polygon.bounds, 0.2)
    elif bay and bay.clipped_polygon and not bay.clipped_polygon.is_empty:
        bounds = _bounds_with_padding(bay.clipped_polygon.bounds, 0.2)
    elif bay:
        bounds = _bounds_with_padding(bay.polygon.bounds, 0.2)
    else:
        raise ValueError(f"No geometry for zoom: {zone_label}")

    used_ids = assigned_face_ids(result.assignment)
    orphan_ids = {o.face_id for o in result.assignment.orphans}
    sliver_ids = {
        f.face_id for f in all_faces
        if f.face_id not in used_ids and f.face_id not in orphan_ids
    }
    face_by_id = {f.face_id: f for f in all_faces}
    zone_face_ids = set(zone.face_ids) if zone else set()

    fig, ax = plt.subplots(figsize=(12, 9))
    minx, miny, maxx, maxy = bounds

    zoom_segs = [s for s in segments if _segment_in_bounds(s, bounds)]
    if zoom_segs:
        seg_coords = [
            [(s.coords[0][0], s.coords[0][1]), (s.coords[-1][0], s.coords[-1][1])]
            for s in zoom_segs
        ]
        ax.add_collection(
            LineCollection(seg_coords, colors=SOURCE_LINE, linewidths=0.5, alpha=0.9, zorder=1)
        )

    if show_all_detected:
        for face in all_faces:
            if not _face_in_bounds(face, bounds):
                continue
            c = _coords(face.polygon)
            if len(c) < 3:
                continue
            if face.face_id in used_ids:
                ec, fc, lw = DETECTED_EDGE, "none", 1.2
            else:
                ec, fc, lw = SLIVER_EDGE, "#f0f0f0", 0.4
            ax.add_patch(
                MplPolygon(c, closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
            )
    else:
        for face_id in zone_face_ids:
            face = face_by_id.get(face_id)
            if face is None or not _face_in_bounds(face, bounds):
                continue
            c = _coords(face.polygon)
            if len(c) < 3:
                continue
            ax.add_patch(
                MplPolygon(c, closed=True, facecolor="none", edgecolor=DETECTED_EDGE, linewidth=1.2, zorder=4)
            )

    for face_id in sorted(zone_face_ids):
        face = face_by_id.get(face_id)
        if face is None or not _face_in_bounds(face, bounds):
            continue
        cx, cy = face.polygon.centroid.x, face.polygon.centroid.y
        ax.text(cx, cy, str(face_id), ha="center", va="center", fontsize=8,
                color="#1b5e20", fontweight="bold", zorder=6,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.75, edgecolor="none"))

    n_in_view = sum(1 for f in all_faces if _face_in_bounds(f, bounds) and f.face_id in used_ids)
    n_sliver_in_view = sum(1 for f in all_faces if _face_in_bounds(f, bounds) and f.face_id in sliver_ids)
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.set_title(
        f"Step 2 zoom — {zone_label}\n"
        f"Green = INT-input polygons ({n_in_view} in view) | Gray = slivers ({n_sliver_in_view} in view)",
        fontsize=11, fontweight="bold",
    )
    fig.savefig(out_path, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out_path


def render_step2_zoom_composite(
    result: IntZonePipelineResult,
    all_faces: list[FaceData],
    segments: list[LineString],
    zone_labels: list[str],
    out_path: Path,
    *,
    dpi: int = 180,
) -> Path:
    """Single image with 1 full-plan Step 2 + N zoom panels for approval review."""
    import matplotlib.pyplot as plt

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_zoom = len(zone_labels)
    fig = plt.figure(figsize=(22, 6 + 5 * ((n_zoom + 1) // 2)))
    gs = fig.add_gridspec(1 + (n_zoom + 1) // 2, 2, height_ratios=[1.2] + [1] * ((n_zoom + 1) // 2))

    ax_full = fig.add_subplot(gs[0, :])
    used_ids = assigned_face_ids(result.assignment)
    face_by_id = {f.face_id: f for f in all_faces}
    _draw_linework(ax_full, segments)
    for face_id in sorted(used_ids):
        face = face_by_id.get(face_id)
        if face is None:
            continue
        c = _coords(face.polygon)
        if len(c) < 3:
            continue
        ax_full.add_patch(
            MplPolygon(c, closed=True, facecolor="none", edgecolor=DETECTED_EDGE, linewidth=0.4, zorder=3)
        )
    _autoscale(ax_full, result, segments)
    ax_full.set_aspect("equal", adjustable="box")
    ax_full.axis("off")
    ax_full.set_title(
        f"② Full plan — {len(used_ids)} INT-input polygons (green outlines)",
        fontsize=12, fontweight="bold",
    )

    for i, label in enumerate(zone_labels):
        row = 1 + i // 2
        col = i % 2
        ax = fig.add_subplot(gs[row, col])
        zone = next((z for z in result.zones if z.label == label), None)
        if zone is None or zone.polygon.is_empty:
            continue
        bounds = _bounds_with_padding(zone.polygon.bounds, 0.18)
        minx, miny, maxx, maxy = bounds
        zoom_segs = [s for s in segments if _segment_in_bounds(s, bounds)]
        if zoom_segs:
            seg_coords = [
                [(s.coords[0][0], s.coords[0][1]), (s.coords[-1][0], s.coords[-1][1])]
                for s in zoom_segs
            ]
            ax.add_collection(LineCollection(seg_coords, colors=SOURCE_LINE, linewidths=0.6, zorder=1))
        sliver_ids = {
            f.face_id for f in all_faces
            if f.face_id not in used_ids
            and f.face_id not in {o.face_id for o in result.assignment.orphans}
        }
        for face in all_faces:
            if not _face_in_bounds(face, bounds):
                continue
            c = _coords(face.polygon)
            if len(c) < 3:
                continue
            if face.face_id in used_ids:
                ec, fc, lw = DETECTED_EDGE, "none", 1.4
            else:
                ec, fc, lw = SLIVER_EDGE, "#ececec", 0.5
            ax.add_patch(MplPolygon(c, closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3))
        for fid in zone.face_ids:
            face = face_by_id.get(fid)
            if face is None or not _face_in_bounds(face, bounds):
                continue
            cx, cy = face.polygon.centroid.x, face.polygon.centroid.y
            ax.text(cx, cy, str(fid), ha="center", va="center", fontsize=9,
                    fontweight="bold", color="#1b5e20", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.12", facecolor="white", alpha=0.8, edgecolor="none"))
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")
        ax.set_title(f"Zoom — {label} ({zone.face_count} polygons)", fontsize=10, fontweight="bold")

    fig.suptitle(
        f"Step 2 approval sample — {result.geometry.frame.source_file}",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return out_path
