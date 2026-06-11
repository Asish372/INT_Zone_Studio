# Contributing to INT Zone Studio

Thank you for your interest in INT Zone Studio. This project is open source under the [MIT License](LICENSE).

## Current phase: Pilot Evaluation Build v1

The `pilot-v1` / `v0.1.0-pilot.1` line is in **pilot validation mode**. The priority is learning from real slab-drawing workflows with structural engineers, not expanding feature scope.

### What we welcome

- Bug reports with reproducible steps (crashes, data loss, export failures)
- Pull requests for crash fixes, data-loss fixes, and small UX clarity improvements
- Documentation improvements
- Test coverage for existing behavior

### What we are deferring

- New menus or major features (Recent Projects, AI recovery, cloud sync, etc.)
- Detection algorithm changes without a linked pilot failure case
- Large refactors

Please read [PILOT_V1.md](PILOT_V1.md) before proposing workflow changes.

## Development setup

See the [README](README.md#development) for Python, Node, and Tauri setup.

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Pull request checklist

1. Describe the problem and how you verified the fix.
2. Run `pytest tests/ -v` and note results.
3. Keep changes focused — one concern per PR when possible.
4. Do not commit secrets, `.env` files, or local `output/` artifacts.

## Feedback from pilot sessions

Use [PILOT_FEEDBACK.md](PILOT_FEEDBACK.md) and `pilot_metrics_template.csv` as templates. Open a GitHub Issue with the drawing type (sanitized), steps, and whether gap-guided recovery was useful.

## Contact

**Asish Bindhani** — [LinkedIn](https://www.linkedin.com/in/asish372)
