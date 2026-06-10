"""Convert DWG files to DXF for processing (requires ODA File Converter)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

ODA_WIN_PATHS = [
    r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
]


def find_oda_converter() -> Path | None:
    """Locate ODA File Converter executable on Windows."""
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

    Requires ODA File Converter: https://www.opendesign.com/guestfiles/oda_file_converter
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
        ezdxf.options.set("odafc-addon", "win_exec_path", str(oda))
        logger.info("Using ODA File Converter: %s", oda)
    elif not odafc.is_installed():
        raise RuntimeError(
            "ODA File Converter is not installed. Download from "
            "https://www.opendesign.com/guestfiles/oda_file_converter "
            "or export DWG to DXF manually in AutoCAD."
        )

    dxf_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = odafc.readfile(str(dwg_path))
        doc.saveas(str(dxf_path))
    except odafc.ODAFCNotInstalledError as exc:
        raise RuntimeError(
            "ODA File Converter not found by ezdxf. Set path in config or install from "
            "https://www.opendesign.com/guestfiles/oda_file_converter"
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
