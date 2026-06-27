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
bash scripts/run_all_checks.sh
```

Changes affecting PyQGIS behavior must still be validated from a QGIS Python environment when the local environment cannot run `tests/qgis`. Complete the relevant manual checks before requesting review or preparing a release.

## Pull requests

Keep changes focused, add or update tests, update the changelog for user-visible changes, and avoid committing client data, credentials, exported products, or generated archives.

## Commit style

Use concise imperative messages, preferably following Conventional Commits, for example:

```text
fix: ignore non-finite temporal values
feat: add polygon mean export option
docs: clarify LOS orbit detection
```
