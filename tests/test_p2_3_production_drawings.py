"""P2.3 regression tests on production S111 drawing suite."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.converter import ensure_dxf, find_oda_converter
from src.detection_coverage import analyze_drawing_coverage
from src.parser import load_dxf

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# P2.2 baseline (logs/coverage_run_20260605_120043.json)
P2_2_BASELINE = {
    "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg": 618,
    "S111_A.dwg": 384,
    "S111_J.dwg": 389,
}

# P2.3 minimum floors — measured production gain on S111_J (+10)
P2_3_MIN_BLOCKS = {
    "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg": 618,
    "S111_A.dwg": 384,
    "S111_J.dwg": 399,
}

P2_3_MAX_BLOCKS = {
    "S111_A.dwg": 395,
}


def _load_config() -> dict:
    with (PROJECT_ROOT / "config.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _production_drawings() -> list[Path]:
    input_dir = PROJECT_ROOT / "input"
    if not input_dir.is_dir():
        return []
    return sorted({*input_dir.glob("*.dwg"), *input_dir.glob("*.DWG")})


def _drawing_id(path: Path) -> str:
    return path.name


@pytest.fixture(scope="module")
def production_config() -> dict:
    return _load_config()


@pytest.fixture(scope="module")
def cache_dir(production_config: dict) -> Path:
    output_dir = PROJECT_ROOT / production_config.get("output", {}).get("output_dir", "./output")
    path = output_dir / ".dxf_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


production_drawing_params = [
    pytest.param(p, id=_drawing_id(p))
    for p in _production_drawings()
]


@pytest.mark.parametrize("cad_path", production_drawing_params)
def test_p2_3_detected_blocks_meet_targets(
    cad_path: Path,
    production_config: dict,
    cache_dir: Path,
) -> None:
    """Validate P2.3 floor on each production drawing."""
    if cad_path.suffix.lower() == ".dwg" and not find_oda_converter():
        pytest.skip("ODA File Converter required for DWG inputs")

    dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
    doc = load_dxf(dxf_path)
    result = analyze_drawing_coverage(
        drawing_name=cad_path.name,
        source_path=str(cad_path),
        dxf_path=str(dxf_path),
        doc=doc,
        config=production_config,
    )

    assert result.error is None, result.error
    name = cad_path.name
    assert result.detected_count >= P2_3_MIN_BLOCKS[name], (
        f"{name}: detected {result.detected_count}, expected >= {P2_3_MIN_BLOCKS[name]}"
    )
    if name in P2_3_MAX_BLOCKS:
        assert result.detected_count <= P2_3_MAX_BLOCKS[name], (
            f"{name}: detected {result.detected_count}, regression cap {P2_3_MAX_BLOCKS[name]}"
        )


@pytest.mark.parametrize("cad_path", production_drawing_params)
def test_p2_3_improves_or_holds_vs_p2_2(
    cad_path: Path,
    production_config: dict,
    cache_dir: Path,
) -> None:
    """Each drawing must not fall below P2.2 baseline."""
    if cad_path.suffix.lower() == ".dwg" and not find_oda_converter():
        pytest.skip("ODA File Converter required for DWG inputs")

    dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
    doc = load_dxf(dxf_path)
    result = analyze_drawing_coverage(
        drawing_name=cad_path.name,
        source_path=str(cad_path),
        dxf_path=str(dxf_path),
        doc=doc,
        config=production_config,
    )

    baseline = P2_2_BASELINE[cad_path.name]
    assert result.detected_count >= baseline, (
        f"{cad_path.name}: P2.3={result.detected_count} below P2.2={baseline}"
    )


@pytest.mark.skipif(
    len(_production_drawings()) < 3,
    reason="Production DWG suite not present in input/",
)
def test_p2_3_total_blocks_gain(
    production_config: dict,
    cache_dir: Path,
) -> None:
    """Suite-level: P2.3 must hold or improve P2.2 total (1391)."""
    if not find_oda_converter():
        pytest.skip("ODA File Converter required for DWG inputs")

    total = 0
    for cad_path in _production_drawings():
        dxf_path = ensure_dxf(cad_path, cache_dir) if cad_path.suffix.lower() == ".dwg" else cad_path
        doc = load_dxf(dxf_path)
        result = analyze_drawing_coverage(
            drawing_name=cad_path.name,
            source_path=str(cad_path),
            dxf_path=str(dxf_path),
            doc=doc,
            config=production_config,
        )
        total += result.detected_count

    p2_2_total = sum(P2_2_BASELINE.values())
    assert total >= p2_2_total + 10, f"P2.3 total {total} < P2.2+10 ({p2_2_total + 10})"


def test_colinear_profile_enabled_in_config(production_config: dict) -> None:
    geom = production_config.get("geometry", {})
    assert geom.get("colinear_profile_match") is True
