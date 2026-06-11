# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

repo_root = Path(SPEC).resolve().parent.parent.parent

hiddenimports = (
    collect_submodules("desktop")
    + collect_submodules("src")
    + [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "multipart",
        "openpyxl",
        "ezdxf",
        "ezdxf.acc",
        "ezdxf.addons",
        "shapely",
        "shapely.geometry",
        "networkx",
        "yaml",
    ]
)

datas = [(str(repo_root / "config.yaml"), ".")]

for pkg in ("ezdxf", "shapely"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

a = Analysis(
    [str(repo_root / "desktop" / "engine_sidecar" / "standalone_main.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "pytest",
        "tkinter",
        "src.zone_engine.detection_visualize",
        "src.zone_engine.grid_frame_visualize",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="int-zone-engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="int-zone-engine",
)
