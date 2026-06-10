"""P1 — Block detection coverage instrumentation and miss taxonomy."""

from __future__ import annotations

import json
import logging
import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace
from shapely.geometry import LineString, MultiLineString, Point, Polygon

from src.detector import filter_polygons, polygonize_regions, remove_duplicates
from src.extractor import SUPPORTED_TYPES, entity_to_segments
from src.gap_handler import _round_point
from src.geometry_precision import normalize_polygon
from src.layer_resolver import LayerResolution, resolve_wall_layers
from src.parser import get_modelspace
from src.units import scale_factor
from src.validation_diagnostics import (
    GapRecord,
    TaggedSegment,
    analyze_gaps,
    detect_from_tagged,
    explain_within_threshold_unclosed,
    extract_tagged_segments,
    scan_modelspace,
    snap_tagged_endpoints,
)

logger = logging.getLogger(__name__)

# Canonical miss taxonomy (P1)
MISS_NONE = "none"
MISS_GAP_BLOCKED = "gap_blocked_closure"
MISS_LAYER_SELECTION = "layer_selection_miss"
MISS_UNSUPPORTED_ENTITY = "unsupported_entity_miss"
MISS_PAIRING_CONFLICT = "pairing_conflict_miss"
MISS_BEARING_MISMATCH = "bearing_mismatch_miss"
MISS_UNKNOWN_UNRESOLVED = "unknown_unresolved"

MISS_CATEGORIES = (
    MISS_NONE,
    MISS_GAP_BLOCKED,
    MISS_LAYER_SELECTION,
    MISS_UNSUPPORTED_ENTITY,
    MISS_PAIRING_CONFLICT,
    MISS_BEARING_MISMATCH,
    MISS_UNKNOWN_UNRESOLVED,
)

DetectionStatus = Literal["detected", "missed", "at_risk"]

GAP_STATUS_TO_CATEGORY: dict[str, str] = {
    "within_threshold_unclosed": MISS_GAP_BLOCKED,
    "large_gap_manual_review": MISS_GAP_BLOCKED,
    "above_threshold_close": MISS_GAP_BLOCKED,
    "orphan_endpoint": MISS_UNKNOWN_UNRESOLVED,
}

UNSUPPORTED_BOUNDARY_TYPES = frozenset(
    {"INSERT", "CIRCLE", "ELLIPSE", "SPLINE", "HATCH", "DIMENSION", "MTEXT", "TEXT"}
)

INSERT_PROXIMITY_RADIUS = 1500.0  # drawing units


@dataclass
class CoverageRecord:
    """One detected block or classified miss event."""

    drawing: str
    block_id: str
    layer: str
    entity_type: str
    detection_status: DetectionStatus
    miss_category: str
    confidence: float
    reason: str
    centroid_x: float | None = None
    centroid_y: float | None = None
    area_m2: float | None = None
    evidence: str | None = None


@dataclass
class DrawingCoverageResult:
    """Coverage analysis for a single drawing."""

    drawing: str
    source_path: str
    dxf_path: str
    layer_source: str
    records: list[CoverageRecord] = field(default_factory=list)
    detected_count: int = 0
    missed_count: int = 0
    at_risk_count: int = 0
    miss_by_category: dict[str, int] = field(default_factory=dict)
    open_endpoints_after_close: int = 0
    gaps_closed: int = 0
    configured_entities: int = 0
    unsupported_entity_counts: dict[str, int] = field(default_factory=dict)
    error: str | None = None


def _gap_status_to_miss_category(status: str, failure_reason: str | None = None) -> str:
    if failure_reason == "greedy_pairing_conflict":
        return MISS_PAIRING_CONFLICT
    if failure_reason == "bearing_mismatch_suspected":
        return MISS_BEARING_MISMATCH
    return GAP_STATUS_TO_CATEGORY.get(status, MISS_GAP_BLOCKED)


def _polygon_primary_layer(tagged: list[TaggedSegment], polygon: Polygon) -> str:
    """Infer dominant boundary layer for a detected polygon."""
    layer_lengths: Counter[str] = Counter()
    boundary = polygon.boundary
    for item in tagged:
        seg = item.line
        try:
            inter = seg.intersection(boundary)
        except Exception:
            continue
        if inter.is_empty:
            continue
        length = getattr(inter, "length", 0.0)
        if length > 1e-6:
            layer_lengths[item.layer] += length
    if not layer_lengths:
        return "mixed"
    return layer_lengths.most_common(1)[0][0]


def _polygon_entity_types(tagged: list[TaggedSegment], polygon: Polygon) -> str:
    """Return comma-separated entity types contributing to polygon boundary."""
    # Tagged segments come from supported types only; report the pipeline source.
    layers = _polygon_primary_layer(tagged, polygon)
    if layers == "mixed":
        return "LINE/LWPOLYLINE/ARC"
    return "LINE/LWPOLYLINE/ARC/POLYLINE"


def _area_m2(polygon: Polygon, unit: str) -> float | None:
    normalized = normalize_polygon(polygon)
    if normalized is None:
        return None
    scale = scale_factor(unit)
    return normalized.area * (scale**2)


def _collect_insert_points(msp: Modelspace) -> list[tuple[float, float, str]]:
    points: list[tuple[float, float, str]] = []
    for entity in msp:
        if entity.dxftype() != "INSERT":
            continue
        insert = entity.dxf.insert
        layer = entity.dxf.layer or "0"
        points.append((insert.x, insert.y, layer))
    return points


def _nearest_insert_distance(
    x: float, y: float, inserts: list[tuple[float, float, str]]
) -> tuple[float, str | None]:
    best_dist = float("inf")
    best_layer: str | None = None
    for ix, iy, layer in inserts:
        dist = math.hypot(x - ix, y - iy)
        if dist < best_dist:
            best_dist = dist
            best_layer = layer
    return best_dist, best_layer


def _layer_miss_records(
    drawing: str,
    resolution: LayerResolution,
    layer_geometry_counts: dict[str, int],
    configured_layers: list[str],
) -> list[CoverageRecord]:
    records: list[CoverageRecord] = []

    if resolution.configured_entity_count == 0 and configured_layers:
        records.append(
            CoverageRecord(
                drawing=drawing,
                block_id="layer-miss-configured-empty",
                layer=",".join(configured_layers),
                entity_type="layer_config",
                detection_status="missed",
                miss_category=MISS_LAYER_SELECTION,
                confidence=0.95,
                reason=(
                    "Configured wall_layers contain zero boundary entities; "
                    f"detection used {resolution.source}."
                ),
                evidence=json.dumps(
                    {
                        "configured_layers": configured_layers,
                        "layer_source": resolution.source,
                        "fallback_layers": resolution.wall_layers[:8],
                    }
                ),
            )
        )

    selected = {name.upper() for name in resolution.wall_layers}
    for layer, count in sorted(layer_geometry_counts.items(), key=lambda x: -x[1]):
        if count < 4:
            continue
        if layer.upper() in selected:
            continue
        upper = layer.upper()
        if any(h in upper for h in ("DIM", "TEXT", "HATCH", "GRID", "ANNO", "NOTE")):
            continue
        records.append(
            CoverageRecord(
                drawing=drawing,
                block_id=f"layer-miss-excluded-{layer}",
                layer=layer,
                entity_type="layer_geometry",
                detection_status="at_risk",
                miss_category=MISS_LAYER_SELECTION,
                confidence=0.6,
                reason=(
                    f"Layer has {count} boundary entities but is excluded from "
                    "active detection set."
                ),
                evidence=json.dumps({"boundary_entity_count": count}),
            )
        )
    return records


def _entity_support_miss_records(
    drawing: str,
    entity_type_counts: dict[str, int],
    gap_records: list[GapRecord],
    inserts: list[tuple[float, float, str]],
) -> list[CoverageRecord]:
    records: list[CoverageRecord] = []

    unsupported_total = sum(
        entity_type_counts.get(t, 0) for t in UNSUPPORTED_BOUNDARY_TYPES
    )
    if unsupported_total > 0:
        records.append(
            CoverageRecord(
                drawing=drawing,
                block_id="entity-miss-unsupported-summary",
                layer="*",
                entity_type=",".join(
                    sorted(
                        t
                        for t in UNSUPPORTED_BOUNDARY_TYPES
                        if entity_type_counts.get(t, 0) > 0
                    )
                ),
                detection_status="at_risk",
                miss_category=MISS_UNSUPPORTED_ENTITY,
                confidence=0.7,
                reason=(
                    f"{unsupported_total} unsupported entities present in modelspace; "
                    "boundary geometry may be hidden in block references."
                ),
                evidence=json.dumps(
                    {t: entity_type_counts.get(t, 0) for t in UNSUPPORTED_BOUNDARY_TYPES
                     if entity_type_counts.get(t, 0) > 0}
                ),
            )
        )

    gap_points: list[tuple[float, float, str, str]] = []
    for gap in gap_records:
        if gap.status in ("orphan_endpoint", "within_threshold_unclosed", "large_gap_manual_review"):
            gap_points.append(
                (gap.endpoint_a_x, gap.endpoint_a_y, gap.layer_a, gap.status)
            )
            if not math.isnan(gap.endpoint_b_x):
                gap_points.append(
                    (gap.endpoint_b_x, gap.endpoint_b_y, gap.layer_b, gap.status)
                )

    seen: set[tuple[float, float]] = set()
    idx = 0
    for x, y, layer, status in gap_points:
        key = _round_point(x, y)
        if key in seen:
            continue
        seen.add(key)
        dist, insert_layer = _nearest_insert_distance(x, y, inserts)
        if dist > INSERT_PROXIMITY_RADIUS:
            continue
        idx += 1
        records.append(
            CoverageRecord(
                drawing=drawing,
                block_id=f"entity-miss-insert-near-gap-{idx:03d}",
                layer=insert_layer or layer,
                entity_type="INSERT",
                detection_status="at_risk",
                miss_category=MISS_UNSUPPORTED_ENTITY,
                confidence=0.75,
                reason=(
                    f"INSERT within {dist:.1f} units of unresolved gap endpoint "
                    f"({status})."
                ),
                centroid_x=x,
                centroid_y=y,
                evidence=json.dumps(
                    {"gap_status": status, "insert_distance": round(dist, 2)}
                ),
            )
        )
    return records


def _gap_miss_records(
    drawing: str,
    gap_records: list[GapRecord],
    gap_failure_details: list[Any],
) -> list[CoverageRecord]:
    records: list[CoverageRecord] = []
    failure_by_point: dict[tuple[float, float], str] = {}
    for detail in gap_failure_details:
        key = (_round_point(detail.endpoint_a_x, detail.endpoint_a_y))
        failure_by_point[key] = detail.failure_reason

    for i, gap in enumerate(gap_records, start=1):
        if gap.status == "within_threshold_unclosed":
            status: DetectionStatus = "missed"
            confidence = 0.85
        elif gap.status in ("large_gap_manual_review", "above_threshold_close"):
            status = "at_risk"
            confidence = 0.7
        elif gap.status == "orphan_endpoint":
            status = "at_risk"
            confidence = 0.65
        else:
            status = "at_risk"
            confidence = 0.5

        failure_reason = failure_by_point.get(
            _round_point(gap.endpoint_a_x, gap.endpoint_a_y)
        )
        miss_cat = _gap_status_to_miss_category(gap.status, failure_reason)

        cx = gap.endpoint_a_x
        cy = gap.endpoint_a_y
        if not math.isnan(gap.endpoint_b_x):
            cx = (gap.endpoint_a_x + gap.endpoint_b_x) / 2
            cy = (gap.endpoint_a_y + gap.endpoint_b_y) / 2

        reason_parts = [f"Gap status: {gap.status}"]
        if not math.isnan(gap.gap_distance):
            reason_parts.append(f"distance={gap.gap_distance}")
        if failure_reason:
            reason_parts.append(f"failure_reason={failure_reason}")

        records.append(
            CoverageRecord(
                drawing=drawing,
                block_id=f"gap-miss-{i:04d}",
                layer=f"{gap.layer_a}|{gap.layer_b}".strip("|"),
                entity_type="gap_endpoint",
                detection_status=status,
                miss_category=miss_cat,
                confidence=confidence,
                reason="; ".join(reason_parts),
                centroid_x=cx,
                centroid_y=cy,
                evidence=json.dumps(
                    {
                        "status": gap.status,
                        "within_threshold": gap.within_current_threshold,
                        "layer_a": gap.layer_a,
                        "layer_b": gap.layer_b,
                        "failure_reason": failure_reason,
                    }
                ),
            )
        )
    return records


def _detected_block_records(
    drawing: str,
    polygons: list[Polygon],
    tagged: list[TaggedSegment],
    unit: str,
) -> list[CoverageRecord]:
    records: list[CoverageRecord] = []
    for i, poly in enumerate(polygons, start=1):
        normalized = normalize_polygon(poly)
        if normalized is None:
            continue
        cx, cy = normalized.centroid.x, normalized.centroid.y
        primary_layer = _polygon_primary_layer(tagged, normalized)
        records.append(
            CoverageRecord(
                drawing=drawing,
                block_id=f"detected-{i:04d}",
                layer=primary_layer,
                entity_type=_polygon_entity_types(tagged, normalized),
                detection_status="detected",
                miss_category=MISS_NONE,
                confidence=0.9,
                reason="Polygonized from snapped/closed segment network.",
                centroid_x=cx,
                centroid_y=cy,
                area_m2=_area_m2(normalized, unit),
            )
        )
    return records


def _unresolved_region_records(
    drawing: str,
    open_after: int,
    tagged: list[TaggedSegment],
) -> list[CoverageRecord]:
    """Emit one summary record per drawing for unresolved open topology."""
    if open_after <= 0:
        return []
    return [
        CoverageRecord(
            drawing=drawing,
            block_id="unresolved-open-topology",
            layer="*",
            entity_type="topology",
            detection_status="at_risk",
            miss_category=MISS_UNKNOWN_UNRESOLVED,
            confidence=0.8,
            reason=(
                f"{open_after} free endpoints remain after gap closure; "
                "one or more blocks may be unclosed."
            ),
            evidence=json.dumps({"open_endpoints_after_close": open_after}),
        )
    ]


def analyze_drawing_coverage(
    drawing_name: str,
    source_path: str,
    dxf_path: str,
    doc: Drawing,
    config: dict[str, Any],
) -> DrawingCoverageResult:
    """Run P1 coverage instrumentation for one drawing."""
    result = DrawingCoverageResult(
        drawing=drawing_name,
        source_path=source_path,
        dxf_path=dxf_path,
        layer_source="",
    )

    try:
        msp = get_modelspace(doc)
        layers_cfg = config.get("layers", {})
        geometry_cfg = config.get("geometry", {})
        accuracy_cfg = config.get("accuracy", {})
        ignore_layers = list(layers_cfg.get("ignore_layers", []))
        configured_layers = list(layers_cfg.get("wall_layers", []))
        unit = geometry_cfg.get("drawing_unit", "mm")
        gap_threshold = float(geometry_cfg.get("gap_threshold", 500))
        snap_tol = float(geometry_cfg.get("snap_tolerance", 1))
        max_angle = float(geometry_cfg.get("max_gap_angle", 30))
        arc_segments = int(accuracy_cfg.get("arc_segments", 64))

        resolution = resolve_wall_layers(msp, config, auto_fallback=True)
        result.layer_source = resolution.source
        result.configured_entities = resolution.configured_entity_count

        (
            _total,
            entity_type_counts,
            _layer_entity_counts,
            layer_geometry_counts,
        ) = scan_modelspace(msp)

        result.unsupported_entity_counts = {
            t: entity_type_counts.get(t, 0)
            for t in UNSUPPORTED_BOUNDARY_TYPES
            if entity_type_counts.get(t, 0) > 0
        }

        tagged = extract_tagged_segments(
            msp, resolution.wall_layers, ignore_layers, arc_segments
        )
        if not tagged:
            result.error = "No boundary segments after layer resolution"
            result.records.append(
                CoverageRecord(
                    drawing=drawing_name,
                    block_id="layer-miss-no-segments",
                    layer=",".join(resolution.wall_layers) or "none",
                    entity_type="layer_config",
                    detection_status="missed",
                    miss_category=MISS_LAYER_SELECTION,
                    confidence=0.99,
                    reason="No extractable boundary segments for detection.",
                )
            )
            return result

        snapped = snap_tagged_endpoints(tagged, snap_tol)
        gap_records = analyze_gaps(snapped, drawing_name, gap_threshold)
        gap_failures = explain_within_threshold_unclosed(
            snapped, drawing_name, gap_threshold, max_angle
        )

        polygons, _raw_n, _invalid, _open_before, gaps_closed, open_after = (
            detect_from_tagged(tagged, config)
        )
        result.open_endpoints_after_close = open_after
        result.gaps_closed = gaps_closed

        records: list[CoverageRecord] = []
        records.extend(_detected_block_records(drawing_name, polygons, tagged, unit))
        records.extend(
            _layer_miss_records(
                drawing_name, resolution, layer_geometry_counts, configured_layers
            )
        )
        records.extend(_gap_miss_records(drawing_name, gap_records, gap_failures))
        inserts = _collect_insert_points(msp)
        records.extend(
            _entity_support_miss_records(
                drawing_name, entity_type_counts, gap_records, inserts
            )
        )
        records.extend(_unresolved_region_records(drawing_name, open_after, tagged))

        result.records = records
        result.detected_count = sum(1 for r in records if r.detection_status == "detected")
        result.missed_count = sum(1 for r in records if r.detection_status == "missed")
        result.at_risk_count = sum(1 for r in records if r.detection_status == "at_risk")

        miss_counts: Counter[str] = Counter()
        for rec in records:
            if rec.miss_category != MISS_NONE:
                miss_counts[rec.miss_category] += 1
        result.miss_by_category = dict(miss_counts)

        logger.info(
            "Coverage %s: detected=%d missed=%d at_risk=%d categories=%s",
            drawing_name,
            result.detected_count,
            result.missed_count,
            result.at_risk_count,
            result.miss_by_category,
        )
    except Exception as exc:
        result.error = str(exc)
        logger.exception("Coverage analysis failed for %s: %s", drawing_name, exc)

    return result


def records_to_rows(records: list[CoverageRecord]) -> list[dict[str, Any]]:
    return [asdict(r) for r in records]


def render_coverage_report_markdown(
    results: list[DrawingCoverageResult],
    config: dict[str, Any],
) -> str:
    """Build detection_coverage_report.md content."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    geometry = config.get("geometry", {})
    layers = config.get("layers", {})

    lines = [
        "# Detection Coverage Report (P2.5)",
        "",
        f"**Generated:** {ts}  ",
        "**Phase:** P2.5 — tier-2 structural threshold + P2.3 profile matching  ",
        "",
        "## Executive summary",
        "",
        "| Drawing | Detected | Missed | At risk | Open endpoints | Layer source |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]

    for res in results:
        if res.error and res.detected_count == 0:
            lines.append(
                f"| {res.drawing} | ERROR | — | — | — | {res.error[:40]} |"
            )
        else:
            lines.append(
                f"| {res.drawing} | {res.detected_count} | {res.missed_count} | "
                f"{res.at_risk_count} | {res.open_endpoints_after_close} | "
                f"{res.layer_source} |"
            )

    lines.extend(
        [
            "",
            "## Run configuration",
            "",
            "| Setting | Value |",
            "| --- | --- |",
            f"| gap_threshold | {geometry.get('gap_threshold')} |",
            f"| snap_tolerance | {geometry.get('snap_tolerance')} |",
            f"| configured wall_layers | {', '.join(layers.get('wall_layers', []))} |",
            f"| detection_mode | {config.get('accuracy', {}).get('detection_mode')} |",
            f"| colinear_profile_match | {geometry.get('colinear_profile_match')} |",
            f"| tier2_threshold_enabled | {geometry.get('tier2_threshold_enabled')} |",
            f"| tier2_gap_threshold | {geometry.get('tier2_gap_threshold')} |",
            "",
            "## Miss category totals",
            "",
            "| Category | Count |",
            "| --- | ---: |",
        ]
    )

    global_miss: Counter[str] = Counter()
    for res in results:
        global_miss.update(res.miss_by_category)
    for cat, count in sorted(global_miss.items(), key=lambda x: -x[1]):
        lines.append(f"| {cat} | {count} |")

    for res in results:
        lines.extend(["", f"## {res.drawing}", ""])
        if res.error:
            lines.append(f"**Error:** {res.error}")
            lines.append("")

        lines.extend(
            [
                "### Summary",
                "",
                f"- Layer source: `{res.layer_source}`",
                f"- Detected blocks: **{res.detected_count}**",
                f"- Missed events: **{res.missed_count}**",
                f"- At-risk events: **{res.at_risk_count}**",
                f"- Gaps closed: {res.gaps_closed}",
                f"- Open endpoints after close: {res.open_endpoints_after_close}",
                "",
            ]
        )

        if res.unsupported_entity_counts:
            lines.append("### Unsupported entity exposure")
            lines.append("")
            for etype, count in sorted(
                res.unsupported_entity_counts.items(), key=lambda x: -x[1]
            ):
                lines.append(f"- `{etype}`: {count}")
            lines.append("")

        if res.miss_by_category:
            lines.append("### Misses by category")
            lines.append("")
            lines.append("| Category | Count |")
            lines.append("| --- | ---: |")
            for cat, count in sorted(res.miss_by_category.items(), key=lambda x: -x[1]):
                lines.append(f"| {cat} | {count} |")
            lines.append("")

        miss_rows = [
            r
            for r in res.records
            if r.detection_status in ("missed", "at_risk")
            and r.miss_category != MISS_NONE
        ][:30]
        if miss_rows:
            lines.append("### Sample miss / at-risk records (first 30)")
            lines.append("")
            lines.append(
                "| block_id | status | category | layer | entity | confidence | reason |"
            )
            lines.append("| --- | --- | --- | --- | --- | ---: | --- |")
            for r in miss_rows:
                reason = r.reason[:60] + ("…" if len(r.reason) > 60 else "")
                lines.append(
                    f"| {r.block_id} | {r.detection_status} | {r.miss_category} | "
                    f"{r.layer} | {r.entity_type} | {r.confidence:.2f} | {reason} |"
                )
            lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- `detected` rows represent polygonized blocks from the current pipeline.",
            "- `missed` / `at_risk` rows are diagnostic events, not ground-truth FN labels.",
            "- P2.5 adds unified dual-threshold matching: tier-1 ≤ 500 mm, tier-2 501–1000 mm on structural whitelist only.",
            "- P2.3 colinear 150/180 mm profile pre-pass + micro-gap resolver + P2.1 global matching.",
            "- P2.2 iterative close → renode → re-extract (max 3 passes) remains enabled.",
            "- Gap diagnostics skip same-segment pairs.",
            "- See `before_vs_after_p2_5.md` for P2.3 vs P2.5 comparison.",
            "",
        ]
    )
    return "\n".join(lines)


def write_coverage_excel(path: Path, results: list[DrawingCoverageResult]) -> None:
    """Write coverage_metrics.xlsx with per-record and summary sheets."""
    import pandas as pd

    all_records: list[dict[str, Any]] = []
    for res in results:
        all_records.extend(records_to_rows(res.records))

    summary_rows = []
    for res in results:
        row: dict[str, Any] = {
            "Drawing": res.drawing,
            "Layer source": res.layer_source,
            "Detected blocks": res.detected_count,
            "Missed events": res.missed_count,
            "At-risk events": res.at_risk_count,
            "Open endpoints after close": res.open_endpoints_after_close,
            "Gaps closed": res.gaps_closed,
            "Configured entities": res.configured_entities,
            "Error": res.error or "",
        }
        for cat in MISS_CATEGORIES:
            if cat != MISS_NONE:
                row[f"miss_{cat}"] = res.miss_by_category.get(cat, 0)
        summary_rows.append(row)

    category_rows = []
    for res in results:
        for cat, count in res.miss_by_category.items():
            category_rows.append(
                {"Drawing": res.drawing, "Miss category": cat, "Count": count}
            )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(all_records).to_excel(writer, sheet_name="CoverageRecords", index=False)
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="DrawingSummary", index=False)
        if category_rows:
            pd.DataFrame(category_rows).to_excel(
                writer, sheet_name="MissByCategory", index=False
            )


def write_coverage_log(path: Path, results: list[DrawingCoverageResult], config: dict) -> None:
    """Write structured JSON log for coverage run."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "P2.5_tier2_structural_threshold",
        "config_snapshot": {
            "gap_threshold": config.get("geometry", {}).get("gap_threshold"),
            "tier2_threshold_enabled": config.get("geometry", {}).get("tier2_threshold_enabled"),
            "tier2_gap_threshold": config.get("geometry", {}).get("tier2_gap_threshold"),
            "tier2_structural_layers": config.get("geometry", {}).get("tier2_structural_layers"),
            "colinear_profile_match": config.get("geometry", {}).get("colinear_profile_match"),
            "iterative_gap_close": config.get("geometry", {}).get("iterative_gap_close"),
            "iterative_max_passes": config.get("geometry", {}).get("iterative_max_passes"),
            "wall_layers": config.get("layers", {}).get("wall_layers"),
            "detection_mode": config.get("accuracy", {}).get("detection_mode"),
        },
        "drawings": [
            {
                "drawing": r.drawing,
                "layer_source": r.layer_source,
                "detected_count": r.detected_count,
                "missed_count": r.missed_count,
                "at_risk_count": r.at_risk_count,
                "miss_by_category": r.miss_by_category,
                "open_endpoints_after_close": r.open_endpoints_after_close,
                "unsupported_entity_counts": r.unsupported_entity_counts,
                "error": r.error,
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
