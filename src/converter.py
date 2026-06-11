"""Convert DWG files to DXF for processing (ODA File Converter)."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

ODA_WIN_PATHS = [
    r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
]


def _bundled_oda_candidates() -> list[Path]:
    candidates: list[Path] = []

    env_path = os.environ.get("INT_ZONE_ODA_PATH")
    if env_path:
        candidates.append(Path(env_path))

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        install_root = exe_dir.parent.parent
        candidates.extend(
            [
                install_root / "oda" / "ODAFileConverter.exe",
                exe_dir / "oda" / "ODAFileConverter.exe",
                exe_dir.parent / "oda" / "ODAFileConverter.exe",
            ]
        )

    data_dir = os.environ.get("INT_ZONE_DATA_DIR")
    if data_dir:
        candidates.append(Path(data_dir) / "oda" / "ODAFileConverter.exe")

    repo_root = Path(__file__).resolve().parents[1]
    candidates.append(
        repo_root
        / "desktop"
        / "studio"
        / "src-tauri"
        / "resources"
        / "oda"
        / "ODAFileConverter.exe"
    )

    return candidates


def _prepare_oda_runtime(oda: Path) -> None:
    """Ensure ODA DLLs resolve when the converter runs as a subprocess."""
    oda_dir = str(oda.resolve().parent)
    os.environ["INT_ZONE_ODA_PATH"] = str(oda)
    path = os.environ.get("PATH", "")
    if oda_dir.casefold() not in path.casefold():
        os.environ["PATH"] = oda_dir + os.pathsep + path


def find_oda_converter() -> Path | None:
    """Locate ODA File Converter executable (bundled or system install)."""
    for path in _bundled_oda_candidates():
        if path.is_file():
            return path

    for path_str in ODA_WIN_PATHS:
        path = Path(path_str)
        if path.is_file():
            return path

    found = shutil.which("ODAFileConverter")
    if found:
        return Path(found)
    return None


def dwg_to_dxf(dwg_path: Path, dxf_path: Path) -> Path:
    """
    Convert a DWG file to DXF using ezdxf's ODA File Converter addon.
    """
    if not dwg_path.is_file():
        raise FileNotFoundError(f"DWG file not found: {dwg_path}")

    try:
        import ezdxf
        from ezdxf.addons import odafc
    except ImportError as exc:
        raise RuntimeError(
            "DWG support requires ezdxf ODA addon. Install ezdxf>=1.1 and ODA File Converter."
        ) from exc

    oda = find_oda_converter()
    if oda:
        _prepare_oda_runtime(oda)
        ezdxf.options.set("odafc-addon", "win_exec_path", str(oda))
        logger.info("Using ODA File Converter: %s", oda)
    elif not odafc.is_installed():
        raise RuntimeError(
            "ODA File Converter was not found. Reinstall INT Zone Studio or export DWG to DXF."
        )

    dxf_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = odafc.readfile(str(dwg_path))
        doc.saveas(str(dxf_path))
    except odafc.ODAFCNotInstalledError as exc:
        raise RuntimeError(
            "ODA File Converter was not found. Reinstall INT Zone Studio or export DWG to DXF."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to convert {dwg_path.name} to DXF: {exc}") from exc

    logger.info("Converted DWG to DXF: %s -> %s", dwg_path.name, dxf_path.name)
    return dxf_path


def ensure_dxf(cad_path: Path, cache_dir: Path) -> Path:
    """
    Return a DXF path for processing.

    If input is already DXF, return as-is. If DWG, convert to cache_dir.
    """
    suffix = cad_path.suffix.lower()
    if suffix == ".dxf":
        return cad_path
    if suffix == ".dwg":
        cached = cache_dir / f"{cad_path.stem}.dxf"
        if cached.is_file() and cached.stat().st_mtime >= cad_path.stat().st_mtime:
            logger.info("Using cached DXF: %s", cached.name)
            return cached
        return dwg_to_dxf(cad_path, cached)
    raise ValueError(f"Unsupported file type '{suffix}'. Use .dxf or .dwg")
