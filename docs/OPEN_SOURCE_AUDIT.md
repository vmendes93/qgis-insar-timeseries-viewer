# Open-source conversion audit

Date: 2026-06-24

## Source reviewed

`visualizador_series_temporais_v1_0_1.zip`

The original archive is retained outside this repository for traceability and was not modified.

## Removed

- Organization logo asset and its original filename.
- Organization name and corporate e-mail address from code, metadata, HTML help, and Markdown documentation.
- Internal-use and internal-distribution notices.
- References to an internal support workflow and internal stable releases.

## Generalized

- Installable directory renamed to `insar_timeseries_viewer`.
- Main plugin class and Qt object identifiers standardized in English.
- Watermark feature changed to use the generic plugin icon and disabled by default.
- Metadata now points to the intended public GitHub repository and issue tracker.
- Documentation now describes generic InSAR point products rather than one supplier's products.

## Added

- GPL-2.0-or-later license and SPDX identifiers.
- Public contribution, security, support, and conduct policies.
- Synthetic GeoJSON test fixture.
- Unit and PyQGIS integration tests.
- Deterministic packaging and SHA-256 generation.
- Automated checks for prohibited references, absolute local paths, compiled files, and package structure.
- GitHub Actions for unit checks, packaging, and release attachments.

## Verification result

- Python compilation: passed.
- Unit tests: 17 passed.
- Release structure validation: passed.
- Corporate-reference scan: passed.
- Deterministic release archive: generated successfully.

## Remaining release gate

Before setting `experimental=False` or publishing in the official QGIS plugin directory, complete the cross-platform manual checklist and confirm that the copyright holder has authority to distribute the source under GPL-2.0-or-later.
