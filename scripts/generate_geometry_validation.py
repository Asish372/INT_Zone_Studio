#!/usr/bin/env python3
"""Generate geometry-based INT zone validation overlays and engineering report.

Evidence is derived from actual polygons, face assignments, and rendered overlays —
not from PASS/REVIEW/FAIL gate status alone.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import yaml
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import LineString, Polygon

from src.extractor import extract_all_segments, extract_entities
from src.layer_resolver import resolve_wall_layers
from src.parser import get_modelspace, load_dxf
from src.units import scale_factor
from src.zone_engine import build_int_zone_pipeline, detect_faces_from_modelspace
from src.zone_engine.face_assigner import filter_sliver_faces, polygons_to_faces
from src.zone_engine.models import IntZoneData, IntZonePipelineResult

OUT_DIR = PROJECT_ROOT / "output" / "geometry_validation"
DPI = 300

DRAWINGS = [
    {
        "file_key": "S111_A",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_A.dxf",
        "manifest": PROJECT_ROOT / "reference" / "s111_a_zones_manifest.yaml",
    },
    {
        "file_key": "S111_J",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "S111_J.dxf",
        "manifest": PROJECT_ROOT / "reference" / "j33b_zones_manifest.yaml",
    },
    {
        "file_key": "6276.S111-WAREHOUSE_SLAB_PLAN-Rev_F",
        "dxf": PROJECT_ROOT / "output" / ".dxf_cache" / "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dxf",
        "manifest": PROJECT_ROOT / "reference" / "j33a_zones_manifest.yaml",
    },
]

# Distinct fill colors for INT zones (cycle)
ZONE_COLORS = [
    "#e8f4fd", "#fdebd0", "#e8f8f5", "#f5eef8", "#fef9e7", "#ebf5fb",
    "#fdf2e9", "#eafaf1", "#f4ecf7", "#fef5e7", "#ebf5fb", "#fdebd0",
]


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _coords(poly: Polygon) -> list[tuple[float, float]]:
    if poly.is_empty:
        return []
    return list(poly.exterior.coords)


def extract_source_segments(msp, config) -> list[LineString]:
    layers_cfg = config.get("layers", {})
    ignore_layers = layers_cfg.get("ignore_layers", [])
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    entities = extract_entities(msp, resolution.wall_layers, ignore_layers)
    arc_segments = int(config.get("accuracy", {}).get("arc_segments", 64))
    return extract_all_segments(entities, arc_segments=arc_segments)


def _labels_in_gate_detail(detail: str, labels: list[str]) -> list[str]:
    """Match INT labels exactly — avoid INT-1 matching inside INT-18."""
    import re

    found: list[str] = []
    for label in labels:
        if re.search(rf"\b{re.escape(label)}\b", detail):
            found.append(label)
    return found


def flagged_zones_from_gates(result: IntZonePipelineResult) -> dict[str, set[str]]:
    """Map gate name -> zone labels mentioned in REVIEW/FAIL detail strings."""
    flagged: dict[str, set[str]] = defaultdict(set)
    all_labels = [z.label for z in result.zones]
    for gate in result.readiness:
        if gate.status not in ("REVIEW", "FAIL"):
            continue
        for label in _labels_in_gate_detail(gate.detail, all_labels):
            flagged[gate.name].add(label)
        if gate.name == "manifest_area" and gate.status == "FAIL" and result.manifest:
            for cmp in result.manifest.comparisons:
                if cmp.within_tolerance is False:
                    flagged[gate.name].add(cmp.label)
    return flagged


def all_flagged_labels(flagged: dict[str, set[str]]) -> set[str]:
    out: set[str] = set()
    for labels in flagged.values():
        out.update(labels)
    return out


def classify_issue(
    zone_label: str,
    gate_name: str,
    zone: IntZoneData,
    manifest_row: dict | None,
) -> str:
    manifest_area = manifest_row.get("area_sqm") if manifest_row else None
    if gate_name == "zone_face_coverage" and zone.face_count == 0:
        if manifest_area is not None and float(manifest_area) == 0.0:
            return "Empty expected zone"
        return "Engine defect"
    if gate_name == "manifest_area":
        return "Manifest variance"
    if gate_name == "union_vs_clipped_bay":
        if zone.face_count == 0:
            return "Empty expected zone"
        if zone.bay_coverage_pct < 5.0 and zone.area_m2 > 0:
            return "Geometry ambiguity"
        return "Geometry ambiguity"
    if gate_name == "face_sum_vs_union":
        return "Geometry ambiguity"
    if gate_name == "orphan_faces":
        return "Engine defect"
    return "Geometry ambiguity"


def explain_flag(
    zone_label: str,
    gate_name: str,
    zone: IntZoneData,
    manifest_row: dict | None,
) -> str:
    if gate_name == "zone_face_coverage":
        if manifest_row and float(manifest_row.get("area_sqm") or -1) == 0.0:
            return (
                f"{zone_label}: no micro-faces assigned; manifest expects 0.00 m² "
                f"(placeholder/grid cell only)."
            )
        return f"{zone_label}: no faces assigned but manifest expects non-zero area."

    if gate_name == "union_vs_clipped_bay":
        return (
            f"{zone_label}: union area {zone.area_m2:.2f} m² covers only "
            f"{zone.bay_coverage_pct:.1f}% of clipped bay ({zone.clipped_bay_area_m2:.2f} m²). "
            f"Bay cell is larger than detected pour geometry."
        )

    if gate_name == "face_sum_vs_union":
        drift_pct = (
            abs(zone.face_sum_area_m2 - zone.area_m2) / zone.area_m2 * 100
            if zone.area_m2 > 1e-6
            else 0.0
        )
        return (
            f"{zone_label}: face sum {zone.face_sum_area_m2:.2f} m² vs union "
            f"{zone.area_m2:.2f} m² (Δ {drift_pct:.1f}%). "
            f"Assigned faces overlap or extend beyond union boundary."
        )

    if gate_name == "manifest_area" and manifest_row:
        computed = zone.area_m2
        expected = float(manifest_row.get("area_sqm") or 0)
        delta_pct = abs(computed - expected) / expected * 100 if expected else 0
        return (
            f"{zone_label}: computed {computed:.2f} m² vs manifest {expected:.2f} m² "
            f"(Δ {delta_pct:.3f}%)."
        )

    return f"{zone_label}: flagged by gate `{gate_name}`."


def render_full_overlay(
    result: IntZonePipelineResult,
    all_faces: list,
    segments: list[LineString],
    flagged_labels: set[str],
    out_path: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(20, 14))

    # Layer 1: source linework
    if segments:
        seg_coords = [[(s.coords[0][0], s.coords[0][1]), (s.coords[-1][0], s.coords[-1][1])] for s in segments]
        ax.add_collection(
            LineCollection(seg_coords, colors="#555555", linewidths=0.25, alpha=0.7, zorder=1)
        )

    # Layer 2: slab outline
    slab = result.geometry.slab.polygon
    if not slab.is_empty:
        ax.add_patch(
            MplPolygon(_coords(slab), closed=True, facecolor="none", edgecolor="#1a5276", linewidth=1.5, zorder=2)
        )

    # Layer 3: micro-faces (all pre-sliver)
    face_patches = []
    for face in all_faces:
        c = _coords(face.polygon)
        if len(c) >= 3:
            face_patches.append(MplPolygon(c, closed=True))
    if face_patches:
        ax.add_collection(
            PatchCollection(
                face_patches,
                facecolor="#aed6f1",
                edgecolor="#5dade2",
                alpha=0.35,
                linewidths=0.15,
                zorder=3,
            )
        )

    # Layer 4: clipped bay grid (dashed)
    for bay in result.geometry.bays:
        target = bay.clipped_polygon if bay.clipped_polygon and not bay.clipped_polygon.is_empty else bay.polygon
        if target.is_empty:
            continue
        c = _coords(target)
        if len(c) >= 3:
            ax.add_patch(
                MplPolygon(
                    c,
                    closed=True,
                    facecolor="none",
                    edgecolor="#cccccc",
                    linewidth=0.4,
                    linestyle="--",
                    zorder=4,
                )
            )

    # Layer 5: INT zone unions
    for i, zone in enumerate(result.zones):
        if zone.polygon.is_empty:
            continue
        c = _coords(zone.polygon)
        if len(c) < 3:
            continue
        is_flagged = zone.label in flagged_labels
        edge = "#c0392b" if is_flagged else "#2471a3"
        lw = 2.5 if is_flagged else 1.2
        fc = "#f5b7b1" if is_flagged else ZONE_COLORS[i % len(ZONE_COLORS)]
        alpha = 0.65 if is_flagged else 0.45
        ax.add_patch(
            MplPolygon(c, closed=True, facecolor=fc, edgecolor=edge, linewidth=lw, alpha=alpha, zorder=5)
        )

    # Layer 6: labels
    for zone in result.zones:
        if zone.polygon.is_empty:
            # label at bay centroid for empty zones
            bay = next((b for b in result.geometry.bays if b.int_label == zone.label), None)
            if bay and bay.clipped_polygon and not bay.clipped_polygon.is_empty:
                cx, cy = bay.clipped_polygon.centroid.x, bay.clipped_polygon.centroid.y
            elif bay:
                cx, cy = bay.centroid
            else:
                continue
        else:
            cx, cy = zone.polygon.centroid.x, zone.polygon.centroid.y
        color = "#c0392b" if zone.label in flagged_labels else "#1b2631"
        weight = "bold" if zone.label in flagged_labels else "normal"
        ax.text(cx, cy, zone.label, ha="center", va="center", fontsize=6, fontweight=weight, color=color, zorder=7)

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(
        f"Geometry validation — {result.geometry.frame.source_file}\n"
        f"Gray=source linework | Blue fills=micro-faces | Solid=INT unions | Red=flagged zones",
        fontsize=11,
    )
    _autoscale(ax, result, segments)
    fig.savefig(out_path, format="png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def render_flagged_zoom(
    result: IntZonePipelineResult,
    all_faces: list,
    segments: list[LineString],
    zone_label: str,
    out_path: Path,
) -> None:
    import matplotlib.pyplot as plt

    zone = next((z for z in result.zones if z.label == zone_label), None)
    bay = next((b for b in result.geometry.bays if b.int_label == zone_label), None)
    if zone is None:
        return

    if not zone.polygon.is_empty:
        bounds = zone.polygon.bounds
    elif bay and bay.clipped_polygon and not bay.clipped_polygon.is_empty:
        bounds = bay.clipped_polygon.bounds
    elif bay:
        bounds = bay.polygon.bounds
    else:
        return

    minx, miny, maxx, maxy = bounds
    pad_x = max((maxx - minx) * 0.35, 5000)
    pad_y = max((maxy - miny) * 0.35, 5000)

    fig, ax = plt.subplots(figsize=(10, 8))

    seg_coords = []
    for s in segments:
        mid_x = (s.coords[0][0] + s.coords[-1][0]) / 2
        mid_y = (s.coords[0][1] + s.coords[-1][1]) / 2
        if minx - pad_x <= mid_x <= maxx + pad_x and miny - pad_y <= mid_y <= maxy + pad_y:
            seg_coords.append([(s.coords[0][0], s.coords[0][1]), (s.coords[-1][0], s.coords[-1][1])])
    if seg_coords:
        ax.add_collection(LineCollection(seg_coords, colors="#444444", linewidths=0.4, zorder=1))

    assigned_ids = set(zone.face_ids)
    for face in all_faces:
        if face.face_id not in assigned_ids:
            continue
        c = _coords(face.polygon)
        if len(c) >= 3:
            ax.add_patch(
                MplPolygon(c, closed=True, facecolor="#85c1e9", edgecolor="#2874a6", alpha=0.6, linewidth=0.5, zorder=3)
            )

    if bay:
        target = bay.clipped_polygon if bay.clipped_polygon and not bay.clipped_polygon.is_empty else bay.polygon
        if not target.is_empty:
            ax.add_patch(
                MplPolygon(
                    _coords(target),
                    closed=True,
                    facecolor="none",
                    edgecolor="#e67e22",
                    linewidth=1.5,
                    linestyle="--",
                    zorder=4,
                )
            )

    if not zone.polygon.is_empty:
        ax.add_patch(
            MplPolygon(
                _coords(zone.polygon),
                closed=True,
                facecolor="#f1948a",
                edgecolor="#c0392b",
                alpha=0.5,
                linewidth=2.0,
                zorder=5,
            )
        )

    area_txt = f"{zone.area_m2:.2f} m²" if zone.area_m2 else "EMPTY"
    ax.text(
        0.02,
        0.98,
        f"{zone_label} | {area_txt} | {zone.face_count} faces",
        transform=ax.transAxes,
        va="top",
        fontsize=10,
        fontweight="bold",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )

    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(f"Flagged zone detail — {zone_label}")
    fig.savefig(out_path, format="png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


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


def assess_geometry_correctness(
    result: IntZonePipelineResult,
    manifest: dict,
    flagged: dict[str, set[str]],
) -> tuple[bool, str]:
    """Engineering judgment from geometry + manifest, not gate PASS status."""
    manifest_zones = {z["label"]: z for z in manifest.get("zones", [])}
    issues: list[str] = []

    for zone in result.zones:
        row = manifest_zones.get(zone.label, {})
        expected_area = row.get("area_sqm")
        if expected_area is not None and float(expected_area) == 0.0 and zone.face_count == 0:
            continue  # expected empty
        if zone.face_count == 0 and expected_area and float(expected_area) > 0:
            issues.append(f"{zone.label} empty but manifest expects {expected_area} m²")

    if result.manifest:
        for cmp in result.manifest.comparisons:
            if cmp.manifest_area_sqm is None:
                continue
            if float(cmp.manifest_area_sqm) == 0.0:
                continue
            if cmp.within_tolerance is False:
                issues.append(
                    f"{cmp.label} area {cmp.computed_area_sqm:.2f} vs manifest "
                    f"{cmp.manifest_area_sqm:.2f} (Δ {cmp.delta_pct:.3f}%)"
                )

    # Low bay coverage on non-empty zones with substantial manifest area
    for zone in result.zones:
        row = manifest_zones.get(zone.label, {})
        exp = float(row.get("area_sqm") or 0)
        if exp > 10 and zone.bay_coverage_pct < 5 and zone.area_m2 > 0:
            issues.append(
                f"{zone.label} union covers {zone.bay_coverage_pct:.1f}% of bay "
                f"but manifest area is {exp:.1f} m² — verify overlay"
            )

    if not issues:
        return True, "All non-empty zones have assigned geometry consistent with manifest areas."
    return False, "; ".join(issues[:8]) + ("..." if len(issues) > 8 else "")


def process_drawing(item: dict, config: dict) -> dict:
    file_key = item["file_key"]
    dxf_path = item["dxf"]
    manifest_path = item["manifest"]
    manifest = load_yaml(manifest_path)
    manifest_zones = {z["label"]: z for z in manifest.get("zones", [])}

    out_sub = OUT_DIR / file_key
    out_sub.mkdir(parents=True, exist_ok=True)

    doc = load_dxf(dxf_path)
    msp = get_modelspace(doc)
    unit_scale = scale_factor(config.get("geometry", {}).get("drawing_unit", "mm"))
    expected = manifest.get("zone_count_expected")

    result = build_int_zone_pipeline(
        msp,
        config,
        source_file=dxf_path.name,
        unit_scale_m=unit_scale,
        expected_int_count=int(expected) if expected is not None else None,
        manifest_path=manifest_path,
    )

    polygons = detect_faces_from_modelspace(msp, config)
    all_faces = polygons_to_faces(polygons, unit_scale_m=unit_scale)
    sliver_max = float(config.get("zone_engine", {}).get("sliver_max_m2", 1.0))
    _, sliver_count = filter_sliver_faces(all_faces, sliver_max_m2=sliver_max)
    segments = extract_source_segments(msp, config)

    flagged = flagged_zones_from_gates(result)
    flagged_labels = all_flagged_labels(flagged)

    overlay_path = out_sub / f"{file_key}_full_overlay.png"
    render_full_overlay(result, all_faces, segments, flagged_labels, overlay_path)

    zoom_paths: dict[str, str] = {}
    for label in sorted(flagged_labels):
        zoom_path = out_sub / f"{file_key}_{label.replace('-', '_')}_flagged.png"
        render_flagged_zoom(result, all_faces, segments, label, zoom_path)
        zoom_paths[label] = str(zoom_path.relative_to(PROJECT_ROOT))

    zone_details = []
    for zone in result.zones:
        zone_details.append(
            {
                "label": zone.label,
                "area_m2": round(zone.area_m2, 4),
                "face_count": zone.face_count,
                "face_ids": zone.face_ids,
                "face_sum_m2": round(zone.face_sum_area_m2, 4),
                "clipped_bay_m2": round(zone.clipped_bay_area_m2, 4),
                "bay_coverage_pct": round(zone.bay_coverage_pct, 2),
                "polygon_empty": zone.polygon.is_empty,
                "manifest_area_m2": manifest_zones.get(zone.label, {}).get("area_sqm"),
                "flagged": zone.label in flagged_labels,
            }
        )

    flag_explanations = []
    for gate_name, labels in sorted(flagged.items()):
        for label in sorted(labels):
            zone = next(z for z in result.zones if z.label == label)
            row = manifest_zones.get(label)
            flag_explanations.append(
                {
                    "zone": label,
                    "gate": gate_name,
                    "category": classify_issue(label, gate_name, zone, row),
                    "explanation": explain_flag(label, gate_name, zone, row),
                }
            )

    zone_count_ok = len(result.zones) == int(expected or len(result.zones))
    geom_ok, geom_note = assess_geometry_correctness(result, manifest, flagged)
    manifest_ok = True
    if result.manifest and result.manifest.zones_with_manifest_area:
        manifest_ok = (
            result.manifest.zones_within_tolerance == result.manifest.zones_with_manifest_area
        )

    empty_zones = [z.label for z in result.zones if z.face_count == 0]
    manifest_mismatches = []
    if result.manifest:
        for cmp in result.manifest.comparisons:
            if cmp.within_tolerance is False:
                manifest_mismatches.append(
                    {
                        "label": cmp.label,
                        "computed": cmp.computed_area_sqm,
                        "manifest": cmp.manifest_area_sqm,
                        "delta_pct": cmp.delta_pct,
                    }
                )

    ready = zone_count_ok and geom_ok and manifest_ok and result.assignment.orphan_count == 0

    return {
        "file_key": file_key,
        "source": dxf_path.name,
        "overlay": str(overlay_path.relative_to(PROJECT_ROOT)),
        "zoom_paths": zoom_paths,
        "micro_faces_total": len(all_faces),
        "sliver_count": sliver_count,
        "faces_post_sliver": result.assignment.total_faces,
        "zone_count": len(result.zones),
        "expected_zone_count": expected,
        "orphan_count": result.assignment.orphan_count,
        "empty_zones": empty_zones,
        "manifest_mismatches": manifest_mismatches,
        "flag_explanations": flag_explanations,
        "zone_details": zone_details,
        "geometry_assessment": geom_note,
        "acceptance": {
            "zone_count_correct": zone_count_ok,
            "geometry_correct": geom_ok,
            "manifest_correct": manifest_ok,
            "ready_for_acceptance": ready,
        },
    }


def render_markdown_report(results: list[dict]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Geometry Validation Report",
        "",
        f"**Generated:** {ts}  ",
        "**Evidence basis:** Rendered polygon overlays and face assignments — not automated gate PASS status.",
        "",
        "## Acceptance summary",
        "",
        "| File | Zone Count Correct | Geometry Correct | Manifest Correct | Ready For Acceptance |",
        "| --- | --- | --- | --- | --- |",
    ]

    for r in results:
        acc = r["acceptance"]
        lines.append(
            f"| {r['file_key']} | "
            f"{'Yes' if acc['zone_count_correct'] else 'No'} | "
            f"{'Yes' if acc['geometry_correct'] else 'No'} | "
            f"{'Yes' if acc['manifest_correct'] else 'No'} | "
            f"{'Yes' if acc['ready_for_acceptance'] else 'No'} |"
        )

    for r in results:
        lines.extend(
            [
                "",
                f"## {r['file_key']}",
                "",
                f"**Source:** `{r['source']}`  ",
                f"**Full overlay:** `{r['overlay']}`",
                "",
                "### Metrics",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Micro-faces (pre-sliver) | {r['micro_faces_total']} |",
                f"| Slivers filtered | {r['sliver_count']} |",
                f"| Faces post-sliver | {r['faces_post_sliver']} |",
                f"| INT zones | {r['zone_count']} (expected {r['expected_zone_count']}) |",
                f"| Orphan faces | {r['orphan_count']} |",
                f"| Empty zones | {', '.join(r['empty_zones']) or 'none'} |",
                "",
                f"**Engineering assessment:** {r['geometry_assessment']}",
                "",
            ]
        )

        if r["manifest_mismatches"]:
            lines.extend(["### Manifest mismatches", ""])
            for m in r["manifest_mismatches"]:
                lines.append(
                    f"- **{m['label']}**: computed {m['computed']:.2f} m² vs manifest "
                    f"{m['manifest']:.2f} m² (Δ {m['delta_pct']:.3f}%)"
                )
            lines.append("")

        if r["flag_explanations"]:
            lines.extend(["### REVIEW / FAIL zone analysis", ""])
            lines.extend(
                [
                    "| Zone | Gate | Category | Explanation | Zoom |",
                    "| --- | --- | --- | --- | --- |",
                ]
            )
            for fe in r["flag_explanations"]:
                zoom = r["zoom_paths"].get(fe["zone"], "—")
                lines.append(
                    f"| {fe['zone']} | {fe['gate']} | {fe['category']} | {fe['explanation']} | `{zoom}` |"
                )
            lines.append("")

        lines.extend(["### All INT zones", ""])
        lines.extend(
            [
                "| INT | Area (m²) | Faces | Face IDs | Face sum (m²) | Bay (m²) | Flagged |",
                "| --- | ---: | ---: | --- | ---: | ---: | --- |",
            ]
        )
        for zd in r["zone_details"]:
            ids = ", ".join(str(i) for i in zd["face_ids"][:12])
            if len(zd["face_ids"]) > 12:
                ids += f" (+{len(zd['face_ids']) - 12})"
            lines.append(
                f"| {zd['label']} | {zd['area_m2']:.2f} | {zd['face_count']} | "
                f"{ids or '—'} | {zd['face_sum_m2']:.2f} | {zd['clipped_bay_m2']:.2f} | "
                f"{'**YES**' if zd['flagged'] else 'no'} |"
            )

    lines.extend(
        [
            "",
            "## Methodology",
            "",
            "1. **Source linework** — wall-layer segments from resolved CAD layers.",
            "2. **Micro-faces** — all polygonized regions before sliver filter (blue fill).",
            "3. **INT unions** — unary union of assigned faces per bay label (solid fill).",
            "4. **Flagged zones** — any zone referenced in a REVIEW or FAIL gate detail (red outline).",
            "5. **Acceptance** — based on visual geometry consistency with manifest, not gate PASS counts.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    config = load_yaml(PROJECT_ROOT / "config.yaml")

    results = []
    for item in DRAWINGS:
        print(f"Validating geometry: {item['file_key']}...")
        results.append(process_drawing(item, config))

    report_md = render_markdown_report(results)
    report_path = OUT_DIR / "GEOMETRY_VALIDATION_REPORT.md"
    report_path.write_text(report_md, encoding="utf-8")

    json_path = OUT_DIR / "geometry_validation_data.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\nWrote {report_path}")
    print(f"Wrote {json_path}")
    for r in results:
        print(f"  Overlay: {r['overlay']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
