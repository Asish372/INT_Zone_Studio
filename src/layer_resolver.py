"""Resolve wall/slab layers: configured names or auto-discovered candidates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ezdxf.layouts import Modelspace

from src.extractor import SUPPORTED_TYPES, extract_entities

IGNORE_LAYER_HINTS = (
    "DIM",
    "TEXT",
    "HATCH",
    "DEFPOINT",
    "ANNOTATION",
    "NOTE",
    "GRID",
    "AXIS",
    "TITLE",
    "VIEWPORT",
    "NO_PLOT",
)


@dataclass
class LayerResolution:
    """Result of layer resolution for one drawing."""

    wall_layers: list[str]
    source: str  # "configured" | "auto_fallback"
    configured_entity_count: int
    candidate_entity_count: int
    layer_ranking: list[tuple[str, int]]


def _is_ignored_layer(name: str) -> bool:
    upper = name.upper()
    return any(hint in upper for hint in IGNORE_LAYER_HINTS)


def scan_layer_geometry_counts(msp: Modelspace) -> dict[str, int]:
    """Count LINE/LWPOLYLINE/ARC/POLYLINE entities per layer."""
    counts: Counter[str] = Counter()
    for entity in msp:
        if entity.dxftype() not in SUPPORTED_TYPES:
            continue
        layer = entity.dxf.layer or "0"
        counts[layer] += 1
    return dict(counts)


def suggest_candidate_wall_layers(
    layer_geometry_counts: dict[str, int],
    min_entities: int = 4,
) -> list[str]:
    """Rank layers by boundary geometry density; exclude annotation-style layers."""
    candidates: list[str] = []
    for layer, count in layer_geometry_counts.items():
        if count < min_entities:
            continue
        if _is_ignored_layer(layer):
            continue
        candidates.append(layer)
    return sorted(candidates, key=lambda name: (-layer_geometry_counts[name], name))


def rank_layers_by_geometry(msp: Modelspace) -> list[tuple[str, int]]:
    """All layers with boundary geometry, highest count first."""
    counts = scan_layer_geometry_counts(msp)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def resolve_wall_layers(
    msp: Modelspace,
    config: dict,
    *,
    auto_fallback: bool = True,
) -> LayerResolution:
    """
    Use configured wall_layers when they contain geometry; otherwise auto-discover.

    Auto-fallback ranks layers by LINE/LWPOLYLINE/ARC density and excludes
    annotation layers (DIM, TEXT, GRID, etc.).
    """
    layers_cfg = config.get("layers", {})
    configured = list(layers_cfg.get("wall_layers", []))
    ignore_layers = list(layers_cfg.get("ignore_layers", []))

    geometry_counts = scan_layer_geometry_counts(msp)
    ranking = sorted(geometry_counts.items(), key=lambda item: (-item[1], item[0]))

    configured_entities = extract_entities(msp, configured, ignore_layers)
    configured_count = len(configured_entities)

    if configured_count > 0:
        return LayerResolution(
            wall_layers=configured,
            source="configured",
            configured_entity_count=configured_count,
            candidate_entity_count=configured_count,
            layer_ranking=ranking,
        )

    candidates = suggest_candidate_wall_layers(geometry_counts)
    candidate_entities = extract_entities(msp, candidates, ignore_layers) if candidates else []
    candidate_count = len(candidate_entities)

    if auto_fallback and candidates and candidate_count > 0:
        return LayerResolution(
            wall_layers=candidates,
            source="auto_fallback",
            configured_entity_count=0,
            candidate_entity_count=candidate_count,
            layer_ranking=ranking,
        )

    return LayerResolution(
        wall_layers=configured,
        source="configured",
        configured_entity_count=0,
        candidate_entity_count=candidate_count,
        layer_ranking=ranking,
    )
