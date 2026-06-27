#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Canonical local quality gate for development.
#
# This intentionally includes QGIS-backed tests, which require a local QGIS
# Python installation. GitHub Actions runs the portable subset separately.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

QGIS_PYTHONPATH="${QGIS_PYTHONPATH:-/usr/share/qgis/python}"

echo
echo "============================================"
echo "Local quality gate: InSAR Time Series Viewer"
echo "============================================"
echo "Repository: $ROOT_DIR"
echo "QGIS_PYTHONPATH: $QGIS_PYTHONPATH"

echo
echo "[1/4] Unit tests"
python3 -m pytest tests/unit

echo
echo "[2/4] QGIS tests"
PYTHONPATH="$QGIS_PYTHONPATH" python3 -m pytest tests/qgis

echo
echo "[3/4] Ruff"
python3 -m ruff check scripts tests insar_timeseries_viewer

echo
echo "[4/5] Release validation"
python3 scripts/validate_release.py

echo
echo "[5/5] Security and QGIS style"
bash scripts/run_quality_checks.sh

echo
echo "Local quality gate passed."
