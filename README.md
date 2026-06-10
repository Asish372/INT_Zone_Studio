# DXF CAD Room Detection & Area Calculation

Python CLI tool that reads DXF CAD files, detects enclosed rooms/regions, calculates area and concrete volume, and exports annotated DXF plus Excel reports.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`

## Installation

```bash
cd Strtup
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

## Accuracy targets (PRD)

| Metric | Target |
|--------|--------|
| **Detection** | Detect every enclosed slab/room on clean drawings (≥ 90% near-term, 100% long-term; human review OK for edge cases) |
| **Area** | ≤ **0.05%** deviation from AutoCAD `AREA` command |

Tune in `config.yaml` under `accuracy`:

- `detection_mode: exhaustive` — maximize recall (default)
- `arc_segments: 64` — finer ARC approximation for area precision
- `area_decimals: 4` — Excel/report precision

## Configuration

Edit [`config.yaml`](config.yaml):

| Setting | Default | Description |
|---------|---------|-------------|
| `geometry.gap_threshold` | 500 | Max gap to auto-close (drawing units) |
| `geometry.slab_thickness` | 0.15 | Slab thickness in metres |
| `geometry.drawing_unit` | mm | Drawing units: `mm`, `cm`, or `m` |
| `geometry.min_area` | 1.0 | Ignore regions smaller than this (m²) |
| `layers.wall_layers` | WALL, S-WALL, BEAM | Layers to extract |
| `output.output_dir` | ./output | Output folder |

## DWG files

The tool accepts **DWG** as well as DXF. DWG is converted to DXF automatically using the free [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) (install on Windows, then re-run).

If ODA is not installed, open each DWG in AutoCAD and **Save As DXF**, then run the tool on the `.dxf` file.

```bash
# List layers in a DWG (to set wall_layers in config.yaml)
python main.py input/S111_A.dwg --list-layers

# Process all DWG/DXF in input/
python main.py input/ --batch
```

## Usage

```bash
# Single file (DXF or DWG)
python main.py input/your_drawing.dxf
python main.py input/your_drawing.dwg

# Alternative flag
python main.py --input input/your_drawing.dxf

# Custom settings
python main.py input/your_drawing.dxf --thickness 0.15 --gap 500 --prefix Room

# Batch folder
python main.py input/ --batch

# Custom config
python main.py --input drawing.dxf --config config.yaml
```

## Output

- `{name}_annotated.dxf` — original drawing plus `DETECTED_REGIONS` and `REGION_LABELS` layers
- `{name}_results.xlsx` — Region ID, area, perimeter, volume, centroid, totals
- `logs/run_YYYYMMDD_HHMMSS.log` — processing log

## Project structure

```
main.py              CLI entry point
config.yaml          User settings
src/
  parser.py          Load DXF
  extractor.py       Extract LINE/LWPOLYLINE/ARC
  gap_handler.py     Snap and close gaps
  detector.py        Polygonize regions
  calculator.py      Area, volume, labels
  exporter.py        DXF + Excel export
tests/               pytest suite
```

## Tests

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing
```

## Pipeline

```
DXF → parse → extract segments → snap/close gaps → polygonize →
calculate area/volume → export DXF + Excel
```

See [prd.md](prd.md) and [trd.md](trd.md) for full specifications.
