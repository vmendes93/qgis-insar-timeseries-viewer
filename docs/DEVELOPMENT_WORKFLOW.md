# Development workflow

This repository uses two quality gates.

## GitHub Actions

GitHub Actions runs on pushes to `main` and `develop`, and on pull requests.
It checks the portable test and packaging subset:

- unit tests on supported Python versions;
- Ruff;
- source compilation;
- release structure validation;
- Bandit;
- detect-secrets;
- Flake8 rules compatible with the QGIS plugin scanner;
- installable plugin package build.

## Local quality gate

Some tests require a local QGIS Python installation and cannot be treated as
portable GitHub Actions jobs without a dedicated QGIS runner. Before pushing
plugin code, run:

```bash
bash scripts/run_all_checks.sh
```

The script runs:

```bash
python3 -m pytest tests/unit
PYTHONPATH="${QGIS_PYTHONPATH:-/usr/share/qgis/python}" python3 -m pytest tests/qgis
python3 -m ruff check scripts tests insar_timeseries_viewer
bash scripts/run_quality_checks.sh
```

To install the local pre-push hook:

```bash
bash scripts/install_git_hooks.sh
```

The hook blocks `git push` unless the full local quality gate passes.

## Required rule

Do not push after a partial validation. A change is push-ready only when:

```bash
bash scripts/run_all_checks.sh
```

passes from the repository root, and GitHub Actions is green for the pushed
commit.
