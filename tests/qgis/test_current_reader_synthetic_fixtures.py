# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""PyQGIS integration tests for the generic reader against synthetic fixtures."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

qgis_core = pytest.importorskip("qgis.core")
QgsApplication = qgis_core.QgsApplication
QgsVectorLayer = qgis_core.QgsVectorLayer

from insar_timeseries_viewer.insar_timeseries_reader import (  # noqa: E402
    inspect_layer,
    read_feature,
    scan_layer,
)


pytestmark = pytest.mark.qgis

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "synthetic_insar"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"

EXPECTED_SCHEMAS = {
    "synthetic_los_ascending": {
        "component_key": "los",
        "component_label": "LOS",
        "identifier_field": "CODE",
        "velocity_field": "VEL",
        "velocity_std_field": "V_STDEV",
        "component_field": "COMPONENT",
        "orbit_field": "ORBIT",
        "displacement_unit_field": "UNIT",
        "sentinel_field": "NODATA",
    },
    "synthetic_los_descending": {
        "component_key": "los",
        "component_label": "LOS",
        "identifier_field": "POINT_ID",
        "velocity_field": "RATE_MM_Y",
        "velocity_std_field": "RATE_ERR",
        "component_field": "COMP",
        "orbit_field": "PASS",
        "displacement_unit_field": "UOM",
        "sentinel_field": "NODATA",
    },
    "synthetic_vertical": {
        "component_key": "vertical",
        "component_label": "VERT",
        "identifier_field": None,
        "velocity_field": None,
        "velocity_std_field": None,
        "component_field": None,
        "orbit_field": None,
        "displacement_unit_field": None,
        "sentinel_field": None,
    },
    "synthetic_east_west": {
        "component_key": "east_west",
        "component_label": "EW",
        "identifier_field": "STATION",
        "velocity_field": "MOTION",
        "velocity_std_field": "UNCERT",
        "component_field": "AXIS",
        "orbit_field": None,
        "displacement_unit_field": "UOM",
        "sentinel_field": "NODATA",
    },
}


@pytest.fixture(scope="session", autouse=True)
def qgis_application():
    """Ensure that a QGIS application exists for vector-layer integration tests.

    Do not call ``exitQgis()`` here. Some QGIS/PyQt builds can segfault when
    multiple test modules create session fixtures and tear down the same
    application instance.
    """

    app = QgsApplication.instance()

    if app is None:
        app = QgsApplication([], False)
        app.initQgis()

    yield app


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


@pytest.mark.parametrize("dataset_key, expected", EXPECTED_SCHEMAS.items())
def test_generic_reader_detects_synthetic_schema(manifest, dataset_key, expected):
    layer = _layer_for(dataset_key, manifest)

    schema = inspect_layer(layer)

    assert schema.component_key == expected["component_key"]
    assert schema.component_label == expected["component_label"]
    assert schema.identifier_field == expected["identifier_field"]
    assert schema.velocity_field == expected["velocity_field"]
    assert schema.velocity_std_field == expected["velocity_std_field"]
    assert schema.component_field == expected["component_field"]
    assert schema.orbit_field == expected["orbit_field"]
    assert schema.displacement_unit_field == expected["displacement_unit_field"]
    assert schema.sentinel_field == expected["sentinel_field"]
    assert schema.acquisition_count == 20
    assert schema.first_acquisition == date(2024, 1, 12)
    assert schema.last_acquisition == date(2025, 4, 12)
    assert [item.name for item in schema.date_fields] == manifest["dates"]["field_names"]


@pytest.mark.parametrize("dataset_key", sorted(EXPECTED_SCHEMAS))
def test_generic_reader_scans_synthetic_counts_with_declared_sentinels(manifest, dataset_key):
    layer = _layer_for(dataset_key, manifest)
    schema = inspect_layer(layer)

    result = scan_layer(layer, schema=schema)

    expected = manifest["datasets"][dataset_key]["expected_counts"]

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


def test_generic_reader_reads_reference_los_ascending_feature(manifest):
    layer = _layer_for("synthetic_los_ascending", manifest)
    schema = inspect_layer(layer)
    feature = _feature_by_identifier(layer, "CODE", "P04")

    series = read_feature(layer, feature, schema=schema)
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


def test_generic_reader_reads_reference_los_descending_feature(manifest):
    layer = _layer_for("synthetic_los_descending", manifest)
    schema = inspect_layer(layer)
    feature = _feature_by_identifier(layer, "POINT_ID", "P04")

    series = read_feature(layer, feature, schema=schema)
    reference = _reference_cell(manifest, "P04", "D20250412")

    assert series.identifier == "P04"
    assert series.component_key == "los"
    assert series.component_label == "LOS"
    assert series.acquisition_count == 20
    assert series.valid_count == 20
    assert series.missing_count == 0
    assert series.invalid_fields == ()
    assert series.cumulative_displacement == pytest.approx(
        reference["los_descending_mm"],
        abs=1e-3,
    )


def test_generic_reader_reads_reference_east_west_feature_in_source_unit(manifest):
    layer = _layer_for("synthetic_east_west", manifest)
    schema = inspect_layer(layer)
    feature = _feature_by_identifier(layer, "STATION", "P04")

    series = read_feature(layer, feature, schema=schema)
    reference = _reference_cell(manifest, "P04", "D20250412")

    assert series.identifier == "P04"
    assert series.component_key == "east_west"
    assert series.component_label == "EW"
    assert series.acquisition_count == 20
    assert series.valid_count == 20
    assert series.missing_count == 0
    assert series.invalid_fields == ()
    assert series.cumulative_displacement == pytest.approx(
        reference["east_west_stored_cm"],
        abs=1e-4,
    )
