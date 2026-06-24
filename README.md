# QGIS InSAR Time Series Viewer

[![CI](https://github.com/vmendes93/qgis-insar-timeseries-viewer/actions/workflows/ci.yml/badge.svg)](https://github.com/vmendes93/qgis-insar-timeseries-viewer/actions/workflows/ci.yml)
[![License: GPL-2.0-or-later](https://img.shields.io/badge/License-GPL--2.0--or--later-blue.svg)](LICENSE)

Open-source QGIS plugin for exploring, comparing, averaging, and exporting point-based InSAR displacement time series.

The installable source is in [`insar_timeseries_viewer/`](insar_timeseries_viewer/README.md).

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check insar_timeseries_viewer tests scripts
python -m pytest tests/unit
python scripts/validate_release.py
python scripts/package_plugin.py
```

QGIS integration tests require a QGIS Python environment:

```bash
python -m pytest tests/qgis
```

## Repository layout

```text
insar_timeseries_viewer/  QGIS-installable plugin source
scripts/                  validation and packaging utilities
tests/unit/               tests that run without QGIS
tests/qgis/               PyQGIS integration tests
tests/fixtures/           synthetic, redistributable sample data
.github/                  issue templates and CI workflows
```

## Release status

Version 1.0.0 is prepared as an open-source release candidate. The plugin remains marked experimental until the cross-platform checklist in [`VALIDATION_CHECKLIST.md`](insar_timeseries_viewer/VALIDATION_CHECKLIST.md) is completed.

## License

GPL-2.0-or-later. See [`LICENSE`](LICENSE).
