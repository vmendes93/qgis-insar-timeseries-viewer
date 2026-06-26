# Changelog

All notable changes to this project are documented in this file. The format is based on Keep a Changelog and the project follows Semantic Versioning.

## [Unreleased]

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
