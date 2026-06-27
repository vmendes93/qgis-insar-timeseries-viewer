# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""PyQGIS integration tests for the current reader against synthetic fixtures.

These tests intentionally document the reader state before the Block 1 generic
reader refactor:

* the canonical LOS ascending fixture must be readable by the existing reader;
* the non-canonical synthetic layouts must still fail until alias detection and
  manual mapping are implemented.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

qgis_core = pytest.importorskip("qgis.core")
QgsApplication = qgis_core.QgsApplication
QgsVectorLayer = qgis_core.QgsVectorLayer

from insar_timeseries_viewer.insar_timeseries_reader import (  # noqa: E402
    LayerValidationError,
    inspect_layer,
    read_feature,
    scan_layer,
)


pytestmark = pytest.mark.qgis

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "synthetic_insar"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"

ALL_SYNTHETIC_SENTINELS = (999.0, -9999.0, -32768.0)


@pytest.fixture(scope="session", autouse=True)
def qgis_application():
    """Ensure that a QGIS application exists for vector-layer integration tests."""

    app = QgsApplication.instance()
    owns_app = False

    if app is None:
        app = QgsApplication([], False)
        app.initQgis()
        owns_app = True

    yield app

    if owns_app:
        app.exitQgis()


@pytest.fixture(scope="session")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _layer_for(dataset_key: str, manifest: dict) -> QgsVectorLayer:
    dataset = manifest["datasets"][dataset_key]
    stem = dataset["filename_stem"]
    path = FIXTURE_ROOT / f"{stem}.shp"

    layer = QgsVectorLayer(str(path), stem, "ogr")
    assert layer.isValid(), f"Fixture layer is invalid: {path}"
    return layer


def _feature_by_identifier(layer: QgsVectorLayer, field_name: str, identifier: str):
    for feature in layer.getFeatures():
        if str(feature[field_name]) == identifier:
            return feature

    raise AssertionError(f"Feature {identifier!r} was not found in {layer.name()!r}")


def _reference_cell(manifest: dict, point_id: str, date_field: str) -> dict:
    for cell in manifest["reference_values"]["cells"]:
        if cell["point_id"] == point_id and cell["date_field"] == date_field:
            return cell

    raise AssertionError(f"Reference cell {point_id!r} / {date_field!r} was not found")


def test_current_reader_detects_canonical_los_ascending_schema(manifest):
    layer = _layer_for("synthetic_los_ascending", manifest)

    schema = inspect_layer(layer)

    assert schema.component_key == "los"
    assert schema.component_label == "LOS"
    assert schema.identifier_field == "CODE"
    assert schema.velocity_field == "VEL"
    assert schema.velocity_std_field == "V_STDEV"
    assert schema.acquisition_count == 20
    assert schema.first_acquisition == date(2024, 1, 12)
    assert schema.last_acquisition == date(2025, 4, 12)
    assert [item.name for item in schema.date_fields] == manifest["dates"]["field_names"]


def test_current_reader_scans_canonical_los_ascending_counts(manifest):
    layer = _layer_for("synthetic_los_ascending", manifest)
    schema = inspect_layer(layer)

    result = scan_layer(
        layer,
        schema=schema,
        missing_sentinels=ALL_SYNTHETIC_SENTINELS,
    )

    expected = manifest["datasets"]["synthetic_los_ascending"]["expected_counts"]

    assert result.scanned_feature_count == expected["features"]
    assert result.features_with_valid_series == expected["features"]
    assert result.features_without_valid_series == 0
    assert result.total_observations == expected["observations"]
    assert result.valid_observations == expected["valid"]
    assert result.missing_observations == expected["missing"]
    assert result.invalid_observations == expected["invalid"]
    assert result.earliest_valid_date == date(2024, 1, 12)
    assert result.latest_valid_date == date(2025, 4, 12)
    assert result.truncated is False


def test_current_reader_reads_reference_los_ascending_feature(manifest):
    layer = _layer_for("synthetic_los_ascending", manifest)
    schema = inspect_layer(layer)
    feature = _feature_by_identifier(layer, "CODE", "P04")

    series = read_feature(
        layer,
        feature,
        schema=schema,
        missing_sentinels=ALL_SYNTHETIC_SENTINELS,
    )

    reference = _reference_cell(manifest, "P04", "D20250412")

    assert series.identifier == "P04"
    assert series.component_key == "los"
    assert series.component_label == "LOS"
    assert series.acquisition_count == 20
    assert series.valid_count == 20
    assert series.missing_count == 0
    assert series.invalid_fields == ()
    assert series.first_valid_date == date(2024, 1, 12)
    assert series.last_valid_date == date(2025, 4, 12)
    assert series.cumulative_displacement == pytest.approx(
        reference["los_ascending_mm"],
        abs=1e-3,
    )


@pytest.mark.parametrize(
    "dataset_key",
    [
        "synthetic_los_descending",
        "synthetic_vertical",
        "synthetic_east_west",
    ],
)
def test_current_reader_rejects_noncanonical_synthetic_layouts(manifest, dataset_key):
    """Document the current pre-refactor limitation.

    These fixtures are expected to become readable after Block 1 adds generic
    alias detection and manual field mapping.
    """

    layer = _layer_for(dataset_key, manifest)

    with pytest.raises(LayerValidationError):
        inspect_layer(layer)
