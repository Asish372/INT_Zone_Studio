"""Tests for automatic layer resolution."""

from __future__ import annotations

import ezdxf

from src.layer_resolver import resolve_wall_layers


def test_resolve_uses_configured_layers_when_present() -> None:
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (1000, 0), dxfattribs={"layer": "WALL"})
    msp.add_line((1000, 0), (1000, 1000), dxfattribs={"layer": "WALL"})
    msp.add_line((1000, 1000), (0, 1000), dxfattribs={"layer": "WALL"})
    msp.add_line((0, 1000), (0, 0), dxfattribs={"layer": "WALL"})

    config = {
        "layers": {"wall_layers": ["WALL"], "ignore_layers": ["TEXT"]},
    }
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    assert resolution.source == "configured"
    assert resolution.wall_layers == ["WALL"]
    assert resolution.configured_entity_count == 4


def test_resolve_auto_fallback_when_configured_empty() -> None:
    doc = ezdxf.new()
    msp = doc.modelspace()
    for i in range(5):
        msp.add_line((i * 100, 0), (i * 100 + 50, 0), dxfattribs={"layer": "S-FNDN-1"})
    msp.add_line((0, 0), (0, 100), dxfattribs={"layer": "A-WALL-1"})

    config = {
        "layers": {"wall_layers": ["WALL", "BEAM"], "ignore_layers": ["TEXT"]},
    }
    resolution = resolve_wall_layers(msp, config, auto_fallback=True)
    assert resolution.source == "auto_fallback"
    assert "S-FNDN-1" in resolution.wall_layers
    assert resolution.configured_entity_count == 0
    assert resolution.candidate_entity_count >= 5


def test_resolve_no_fallback_when_disabled() -> None:
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 0), dxfattribs={"layer": "S-BEAM-2"})

    config = {"layers": {"wall_layers": ["WALL"], "ignore_layers": []}}
    resolution = resolve_wall_layers(msp, config, auto_fallback=False)
    assert resolution.source == "configured"
    assert resolution.configured_entity_count == 0
    assert resolution.wall_layers == ["WALL"]
