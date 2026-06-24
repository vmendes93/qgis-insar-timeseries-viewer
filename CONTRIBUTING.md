# Contributing

## Development setup

Use Python 3.9 or newer for unit tooling. Runtime behavior must also be tested inside a supported QGIS installation.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows, activate with `.venv\Scripts\Activate.ps1`.

## Quality checks

Before opening a pull request, run:

```bash
python -m ruff check insar_timeseries_viewer tests scripts
python -m pytest tests/unit
python scripts/validate_release.py
```

Changes affecting PyQGIS behavior must also run `python -m pytest tests/qgis` from a QGIS Python environment and complete the relevant manual checks.

## Pull requests

Keep changes focused, add or update tests, update the changelog for user-visible changes, and avoid committing client data, credentials, exported products, or generated archives.

## Commit style

Use concise imperative messages, preferably following Conventional Commits, for example:

```text
fix: ignore non-finite temporal values
feat: add polygon mean export option
docs: clarify LOS orbit detection
```
