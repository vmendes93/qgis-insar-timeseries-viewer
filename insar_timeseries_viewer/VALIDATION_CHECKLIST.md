# Release Validation Checklist — v1.1.0

Run this checklist in clean QGIS profiles on Linux and Windows before publishing a release ZIP.

## Automated checks

- [ ] Python compilation succeeds.
- [ ] Unit tests succeed.
- [ ] QGIS integration tests succeed.
- [ ] Metadata validation succeeds through `scripts/validate_release.py`.
- [ ] Local quality gate completes without warnings.
- [ ] No organization-specific names, e-mail domains, absolute paths, credentials, or internal notices remain.
- [ ] Release ZIP contains one top-level `insar_timeseries_viewer` directory.
- [ ] `metadata.txt`, `__init__.py`, and extensionless `LICENSE` are included.

## Installation and lifecycle

- [ ] Install from ZIP without manual edits.
- [ ] Enable, disable, and re-enable the plugin.
- [ ] Open, close, and reopen the dock.
- [ ] Confirm toolbar, Vector menu, and Help menu actions.
- [ ] Confirm the active-layer report can be refreshed and copied.
- [ ] Open packaged English and Portuguese help.

## Data recognition

- [ ] Load sanitized LOS ASC and DESC point layers.
- [ ] Load vertical and east-west point layers.
- [ ] Confirm acquisition count and date range.
- [ ] Confirm `999` and null values are ignored.
- [ ] Confirm malformed or duplicate date fields are rejected clearly.
- [ ] Save, reload, and clear manual field mappings.

## Display and spatial workflows

- [ ] Single, overlaid, and separate series.
- [ ] Click-to-plot in single, overlaid, separate, and mean modes.
- [ ] Active point marker, zoom-to-point, and clear-selection controls.
- [ ] Selected-point mean with union/common dates and zero referencing.
- [ ] Dispersion band and individual background series.
- [ ] Drawn-polygon selection and selected-feature polygon workflows.
- [ ] Polygon and point layers in different CRSs.
- [ ] Independent overlaid and separate polygon means.

## Styling and export

- [ ] Hover inspection.
- [ ] Solid red trendline and legend entry.
- [ ] Independent horizontal and vertical grid controls.
- [ ] Shaded period, manual limits, and tick intervals.
- [ ] Additional attributes in the panel and export header.
- [ ] PNG, SVG, and PDF export.
- [ ] CSV export for single, overlaid, separate, mean, and polygon-mean views.
- [ ] Generic watermark is opt-in and contains no third-party branding.
- [ ] Existing files are not silently overwritten.

## Cross-platform acceptance

- [ ] QGIS 3.34 LTR on Windows.
- [ ] QGIS 3.44 on Linux.
- [ ] No platform-specific paths are embedded in source or documentation.
