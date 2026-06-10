"""End-to-end integration tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_pipeline_on_sample_dxf(sample_dxf_path: Path) -> None:
    """Run main.py on a generated sample DXF."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), str(sample_dxf_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "Regions detected" in result.stdout

    output_dir = PROJECT_ROOT / "output"
    assert (output_dir / "room_annotated.dxf").is_file()
    assert (output_dir / "room_results.xlsx").is_file()
