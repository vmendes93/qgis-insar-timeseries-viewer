# Changelog

All notable changes to this project are documented in this file. The format is based on Keep a Changelog and the project follows Semantic Versioning.

## [Unreleased]

## [1.1.0] - 2026-06-27

### Added

- Added click-to-plot map interaction with display-mode-aware selection behavior.
- Added active point highlighting, zoom-to-point, and clear-selection controls.
- Added CSV export for displayed single, overlaid, separate, mean, and polygon-mean time-series data.
- Added active-layer structural report with copyable metadata.
- Added manual field-mapping workflow for non-standard layers.
- Added release-candidate test plan for version 1.1.0.

### Changed

- Refined graph headers, trendline labeling, grid appearance, and export layout.
- Extended the local quality gate to run release validation before security and QGIS style scans.
- Promoted pytest deprecation warnings to errors to keep the test suite warning-free.

### Fixed

- Fixed click-to-plot button activation for valid active layers.
- Fixed QGIS test fixtures to avoid deprecated field-type construction.

## [1.0.3] - 2026-06-26

### Added

- Added permanent Bandit, detect-secrets, and QGIS-compatible Flake8 checks to the CI and local release workflow.

### Changed

- Promoted the plugin from experimental to stable.

### Fixed

- Resolved all reported Bandit and QGIS repository Flake8 findings.

## [1.0.2] - 2026-06-26

### Fixed

- Published the SHA-1 non-security-use correction in a new package version for a fresh QGIS repository security scan.

## [1.0.1] - 2026-06-26

### Fixed

- Declared the SHA-1 layer-key digest as non-security use, preserving existing project compatibility while satisfying security scanning requirements.

## [1.0.0] - 2026-06-26

### Added

- Public repository metadata and project documentation.
- GPL-2.0-or-later license.
- Sanitized synthetic test data and automated release validation.
- Generic optional plugin watermark using the bundled plugin icon.
- Complete English runtime translations for automatic tick labels and area-selection feedback.
- Automated tests for runtime localization and clean CI environments.

### Changed

- Renamed the installable Python package to `insar_timeseries_viewer`.
- Standardized public-facing project names and identifiers in English.
- Disabled watermark export by default.

### Removed

- Organization-specific branding, logo assets, support addresses, and internal-distribution notices.
