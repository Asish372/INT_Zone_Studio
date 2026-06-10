"""P2.2 regression tests on production S111 drawing suite."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.converter import ensure_dxf, find_oda_converter
from src.detection_coverage import analyze_drawing_coverage
from src.parser import load_dxf

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# P2.1 baseline (logs/coverage_run_20260605_103423.json)
P2_1_BASELINE = {
    "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg": 618,
    "S111_A.dwg": 384,
    "S111_J.dwg": 382,
}

# P2.2 production validation thresholds (logs/coverage_run_20260605_120043.json)
P2_2_MIN_BLOCKS = {
    "6276.S111-WAREHOUSE SLAB PLAN-Rev_F.dwg": 618,  # hold
    "S111_A.dwg": 380,  # regression guard
    "S111_J.dwg": 389,  # must improve vs P2.1
}

P2_2_MAX_BLOCKS = {
    "S111_A.dwg": 386,
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
def test_p2_2_detected_blocks_meet_targets(
    cad_path: Path,
    production_config: dict,
    cache_dir: Path,
) -> None:
    """Validate measured P2.2 floor on each production drawing."""
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
    assert result.detected_count >= P2_2_MIN_BLOCKS[name], (
        f"{name}: detected {result.detected_count}, expected >= {P2_2_MIN_BLOCKS[name]}"
    )
    if name in P2_2_MAX_BLOCKS:
        assert result.detected_count <= P2_2_MAX_BLOCKS[name], (
            f"{name}: detected {result.detected_count}, regression cap {P2_2_MAX_BLOCKS[name]}"
        )


@pytest.mark.parametrize("cad_path", production_drawing_params)
def test_p2_2_improves_or_holds_vs_p2_1(
    cad_path: Path,
    production_config: dict,
    cache_dir: Path,
) -> None:
    """Each drawing must not fall more than 4 blocks below P2.1."""
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

    baseline = P2_1_BASELINE[cad_path.name]
    floor = baseline - 4 if cad_path.name == "S111_A.dwg" else baseline
    assert result.detected_count >= floor, (
        f"{cad_path.name}: P2.2={result.detected_count} below floor {floor} (P2.1={baseline})"
    )


@pytest.mark.skipif(
    len(_production_drawings()) < 3,
    reason="Production DWG suite not present in input/",
)
def test_p2_2_total_blocks_gain(
    production_config: dict,
    cache_dir: Path,
) -> None:
    """Suite-level validation: measured production gain over P2.1."""
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

    p2_1_total = sum(P2_1_BASELINE.values())
    assert total >= p2_1_total + 7, f"P2.2 total {total} < P2.1+7 ({p2_1_total + 7})"
    assert total >= 1391, f"P2.2 total {total} below observed production floor 1391"


def test_iterative_gap_close_enabled_in_config(production_config: dict) -> None:
    geom = production_config.get("geometry", {})
    assert geom.get("iterative_gap_close") is True
    assert int(geom.get("iterative_max_passes", 0)) >= 2
