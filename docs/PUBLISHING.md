# Publishing workflow

## 1. Complete release validation

Run:

```bash
python -m ruff check insar_timeseries_viewer tests scripts
python -m pytest tests/unit
python scripts/validate_release.py
python scripts/package_plugin.py
```

Complete the manual checks in `insar_timeseries_viewer/VALIDATION_CHECKLIST.md`. Change `experimental=True` to `False` only after Windows and Linux validation.

## 2. Version and changelog

Update the version in:

- `insar_timeseries_viewer/metadata.txt`;
- `pyproject.toml`;
- `insar_timeseries_viewer/CHANGELOG.md`;
- packaged HTML help when the displayed version changes.

Commit the release, create an annotated tag such as `v1.0.0`, and push the tag.

## 3. GitHub Release

Create a GitHub Release using the matching tag. The `release.yml` workflow validates the version, builds a deterministic ZIP and checksum, and attaches both files to the release.

## 4. Official QGIS plugin directory

The official directory requires a public repository, issue tracker, homepage, compatible license, minimal documentation, a valid installable ZIP, and an OSGeo account. Add `OSGEO_USER` and `OSGEO_PASSWORD` repository secrets only when official publishing is approved.

The repository already includes `.qgis-plugin-ci`; a maintainer can use:

```bash
python -m pip install qgis-plugin-ci
qgis-plugin-ci package 1.0.0
```

For official deployment, follow the current qgis-plugin-ci release documentation and never commit OSGeo credentials.
