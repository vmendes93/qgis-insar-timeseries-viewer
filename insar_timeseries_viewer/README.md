# InSAR Time Series Viewer

InSAR Time Series Viewer is an open-source QGIS plugin for inspecting and exporting displacement time series stored in point-layer attributes.

## Main features

- Automatic recognition of acquisition fields named `DYYYYMMDD`.
- Detection of LOS (`VEL`/`V_STDEV`), vertical (`VEL_V`/`V_STDEV_V`), and east-west (`VEL_E`/`V_STDEV_E`) products.
- Single, overlaid, vertically separated, selected-mean, and polygon-mean charts.
- Click-to-plot map interaction with display-mode-aware point selection.
- Active point highlighting, zoom-to-point, and clear-selection controls.
- Means for selected points and independent means for polygon features.
- Drawn-polygon and existing-polygon spatial selection.
- Missing-value handling for null values, `NaN`, and the `999` sentinel.
- Interactive hover, linear trendlines, shaded periods, configurable axes, and gridlines.
- PNG, SVG, and PDF chart export with optional headers and a generic plugin watermark.
- CSV export for the currently displayed time-series data.
- Active-layer report with copyable schema and acquisition metadata.
- Manual field mapping for non-standard point layers.
- Warning-free local quality gate and release validation workflow.
- English interface with Brazilian Portuguese localization.

## Quick start

1. Install the release ZIP through **Plugins → Manage and Install Plugins → Install from ZIP**.
2. Load a compatible InSAR point layer.
3. Open **Vector → Time Series Viewer → InSAR Time Series Viewer**.
4. Select one or more points or use a polygon-selection workflow.
5. Choose a display mode and configure the chart.
6. Use click-to-plot, spatial selection, or QGIS selection tools to choose points.
7. Review the active-layer report when validating a dataset.
8. Export the current figure or displayed data when required.

## Documentation

- [Installation](INSTALLATION.md)
- [Data requirements](DATA_REQUIREMENTS.md)
- [User guide](USER_GUIDE.md)
- [Technical reference](TECHNICAL_REFERENCE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Release validation](VALIDATION_CHECKLIST.md)
- [Changelog](CHANGELOG.md)

Packaged help is also available from **Help → Plugins → InSAR Time Series Viewer Help**.

## Compatibility

- QGIS metadata range: 3.34–3.99.
- Runtime dependencies supplied by QGIS: PyQGIS, Qt, Matplotlib, and NumPy.
- Target platforms: Windows, Linux, and macOS.

## Data rule

`CODE` is a display label only. It is never used to associate points, components, layers, or products.

## License

GPL-2.0-or-later. See `LICENSE`.
