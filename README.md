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
```

QGIS integration tests require a QGIS Python environment:

```bash
python -m pytest tests/qgis
```

## Release packaging

Create, validate, verify, and copy the versioned QGIS plugin package with:

```bash
./scripts/build_release.sh
```

The version is read automatically from:

```text
insar_timeseries_viewer/metadata.txt
```

The generated ZIP and SHA-256 checksum are first created in `dist/`.

By default, both files are also copied to the directory containing this repository. For the current project layout, that directory is:

```text
~/Documents/projects/time_series_viewer/
```

An alternative output directory may be supplied as the first argument:

```bash
./scripts/build_release.sh /path/to/output
```

Before preparing a new release:

1. Update `version` and `changelog` in `insar_timeseries_viewer/metadata.txt`.
2. Add the corresponding version section to `insar_timeseries_viewer/CHANGELOG.md`.
3. Run the unit tests and release validation.
4. Run `./scripts/build_release.sh`.

## Repository layout

```text
insar_timeseries_viewer/  QGIS-installable plugin source
scripts/                  Validation and packaging utilities
tests/unit/               Tests that run without QGIS
tests/qgis/               PyQGIS integration tests
tests/fixtures/           Synthetic, redistributable sample data
.github/                  Issue templates and CI workflows
dist/                     Generated release packages
```

## Release status

The current release version is defined in:

[`insar_timeseries_viewer/metadata.txt`](insar_timeseries_viewer/metadata.txt)

Release packages are generated with:

```bash
./scripts/build_release.sh
```

## License

GPL-2.0-or-later. See [`LICENSE`](LICENSE).
