# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""PyQGIS tests for layer schema resolution service."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pytest

qgis_core = pytest.importorskip("qgis.core")
qgis_qtcore = pytest.importorskip("qgis.PyQt.QtCore")

QgsApplication = qgis_core.QgsApplication
QgsFeature = qgis_core.QgsFeature
QgsField = qgis_core.QgsField
QgsGeometry = qgis_core.QgsGeometry
QgsPointXY = qgis_core.QgsPointXY
QgsVectorLayer = qgis_core.QgsVectorLayer
QVariant = qgis_qtcore.QVariant

from insar_timeseries_viewer.insar_timeseries_reader import (  # noqa: E402
    DateField,
    LayerFieldMapping,
    read_feature,
)
from insar_timeseries_viewer.layer_mapping_store import (  # noqa: E402
    MAPPING_PROPERTY_KEY,
    save_layer_field_mapping,
)
from insar_timeseries_viewer.layer_schema_service import (  # noqa: E402
    SOURCE_AUTO_DETECTED,
    SOURCE_EXPLICIT_MAPPING,
    SOURCE_SAVED_MAPPING,
    SavedLayerMappingError,
    resolve_layer_schema,
)


pytestmark = pytest.mark.qgis

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "synthetic_insar"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"


@pytest.fixture(scope="session", autouse=True)
def qgis_application():
    app = QgsApplication.instance()
    if app is None:
        app = QgsApplication([], False)
        app.initQgis()
    yield app


@pytest.fixture(scope="session")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _fixture_layer(dataset_key: str, manifest: dict) -> QgsVectorLayer:
    dataset = manifest["datasets"][dataset_key]
    stem = dataset["filename_stem"]
    path = FIXTURE_ROOT / f"{stem}.shp"

    layer = QgsVectorLayer(str(path), stem, "ogr")
    assert layer.isValid(), f"Fixture layer is invalid: {path}"
    return layer


@pytest.fixture()
def custom_layer() -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:31983", "schema_service_custom", "memory")
    assert layer.isValid()

    provider = layer.dataProvider()
    provider.addAttributes(
        [
            QgsField("name_key", QVariant.String),
            QgsField("vel_any", QVariant.Double),
            QgsField("sigma_any", QVariant.Double),
            QgsField("nodata_any", QVariant.Double),
            QgsField("first_obs", QVariant.Double),
            QgsField("last_obs", QVariant.Double),
        ]
    )
    layer.updateFields()

    feature = QgsFeature(layer.fields())
    feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(320200.0, 7500200.0)))
    feature.setAttributes(["SCHEMA_SERVICE", -3.5, 0.2, -9999.0, 2.0, -9999.0])

    ok, _ = provider.addFeatures([feature])
    assert ok
    layer.updateExtents()

    return layer


def _custom_mapping() -> LayerFieldMapping:
    return LayerFieldMapping(
        identifier_field="name_key",
        component_key="east_west",
        velocity_field="vel_any",
        velocity_std_field="sigma_any",
        sentinel_field="nodata_any",
        date_fields=(
            DateField("first_obs", date(2024, 1, 1)),
            DateField("last_obs", date(2024, 2, 1)),
        ),
    )


def test_resolve_layer_schema_uses_automatic_detection_for_unmapped_fixture(manifest):
    layer = _fixture_layer("synthetic_los_ascending", manifest)

    resolution = resolve_layer_schema(layer)

    assert resolution.source == SOURCE_AUTO_DETECTED
    assert resolution.field_mapping is None
    assert resolution.schema.component_key == "los"
    assert resolution.schema.identifier_field == "CODE"


def test_resolve_layer_schema_uses_saved_mapping(custom_layer):
    save_layer_field_mapping(custom_layer, _custom_mapping())

    resolution = resolve_layer_schema(custom_layer)

    assert resolution.source == SOURCE_SAVED_MAPPING
    assert resolution.field_mapping == _custom_mapping()
    assert resolution.schema.component_key == "east_west"
    assert resolution.schema.identifier_field == "name_key"
    assert resolution.schema.velocity_field == "vel_any"

    feature = next(custom_layer.getFeatures())
    series = read_feature(custom_layer, feature, schema=resolution.schema)

    assert series.identifier == "SCHEMA_SERVICE"
    assert series.velocity == pytest.approx(-3.5)
    assert series.velocity_std == pytest.approx(0.2)
    assert series.valid_count == 1
    assert series.missing_count == 1
    assert series.cumulative_displacement == pytest.approx(2.0)


def test_resolve_layer_schema_explicit_mapping_can_bypass_saved_mapping(custom_layer):
    bad_saved_mapping = LayerFieldMapping(
        identifier_field="does_not_exist",
        component_key="los",
        date_fields=(
            DateField("first_obs", date(2024, 1, 1)),
            DateField("last_obs", date(2024, 2, 1)),
        ),
    )
    save_layer_field_mapping(custom_layer, bad_saved_mapping)

    resolution = resolve_layer_schema(custom_layer, field_mapping=_custom_mapping())

    assert resolution.source == SOURCE_EXPLICIT_MAPPING
    assert resolution.field_mapping == _custom_mapping()
    assert resolution.schema.component_key == "east_west"


def test_resolve_layer_schema_reports_broken_saved_mapping(custom_layer):
    custom_layer.setCustomProperty(MAPPING_PROPERTY_KEY, "{broken json")

    with pytest.raises(SavedLayerMappingError):
        resolve_layer_schema(custom_layer)
