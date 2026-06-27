# Release 1.1.0 — Test Plan

This document tracks the release-candidate validation for InSAR Time Series Viewer 1.1.0.

## Scope

Version 1.1.0 consolidates the first independent feature-complete workflow:

- robust field detection and manual field mapping;
- single, overlaid, separate, selected-mean, and polygon-mean time-series views;
- click-to-plot map interaction;
- active point highlighting and zoom;
- current chart export to PNG, SVG, and PDF;
- displayed data export to CSV;
- active-layer structural report;
- warning-free local quality gate and release validation.

## Required automated checks

Run from the repository root:

```bash
bash scripts/run_all_checks.sh
```

Expected result:

```text
Unit tests passed
QGIS tests passed
Ruff passed
Release validation passed
Bandit passed
detect-secrets passed
Flake8/QGIS scanner passed
```

Then build the release candidate:

```bash
bash scripts/build_release.sh
```

The build script must create a versioned ZIP and SHA-256 checksum, verify the checksum, and inspect the internal ZIP structure.

## Required manual QGIS checks

Use a clean QGIS profile when possible.

1. Install the generated ZIP through **Plugins → Manage and Install Plugins → Install from ZIP**.
2. Enable, disable, and re-enable the plugin.
3. Open the dock from the Vector menu and toolbar action.
4. Load LOS, VERT, and EW point layers.
5. Confirm the active-layer report shows layer name, point count, CRS, component, acquisition range, temporal fields, VEL/V_STDEV fields, NoData field, and schema warnings.
6. Confirm manual field mapping can be saved, loaded, cleared, and used to read a non-standard layer.
7. Test single-series mode with normal QGIS point selection.
8. Test click-to-plot in single-series mode: each click replaces the selected point.
9. Test click-to-plot in overlaid, separate, and mean modes: each click adds one point to the current selection.
10. Test active point marker, zoom-to-point, and clear-selection actions.
11. Test drawn-polygon selection and existing-polygon selection.
12. Test polygon means in overlaid and separate views.
13. Export PNG, SVG, and PDF charts.
14. Export displayed data to CSV from single, overlaid, separate, mean, and polygon-mean views.
15. Open exported CSV files in a spreadsheet application and confirm UTF-8 text, date fields, numeric columns, and missing values are readable.
16. Confirm the copied layer report is plain text and contains no local paths or private data.
17. Confirm no unexpected warnings appear in the QGIS Python console during normal use.

## Acceptance

The release candidate is acceptable when all automated checks pass, the ZIP installs without manual edits, and the manual QGIS checklist is complete on the target workstation.
