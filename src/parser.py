"""Module 1: DXF file loading and layer inspection."""

from __future__ import annotations

import logging
from pathlib import Path

import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace

logger = logging.getLogger(__name__)


def load_dxf(filepath: str | Path) -> Drawing:
    """Open a DXF file and return the ezdxf document."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"DXF file not found: {path}")

    try:
        doc = ezdxf.readfile(str(path))
    except ezdxf.DXFStructureError as exc:
        logger.error("Corrupted or invalid DXF structure: %s", path)
        raise ezdxf.DXFStructureError(f"Invalid DXF file: {path}") from exc

    version = doc.dxfversion
    if version and version < "AC1015":
        logger.warning("DXF version %s may have limited support", version)

    logger.info("Loaded DXF: %s (version %s)", path.name, version)
    return doc


def get_modelspace(doc: Drawing) -> Modelspace:
    """Return the model space layout for entity iteration."""
    return doc.modelspace()


def list_layers(doc: Drawing) -> list[str]:
    """Return all layer names present in the DXF file."""
    return [layer.dxf.name for layer in doc.layers]
