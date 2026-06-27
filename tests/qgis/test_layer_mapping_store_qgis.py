# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""PyQGIS tests for persisted layer field mappings."""

from __future__ import annotations

from datetime import date

import pytest

qgis_core = pytest.importorskip("qgis.core")
qgis_qtcore = pytest.importorskip("qgis.PyQt.QtCore")

QgsApplication = qgis_core.QgsApplication
QgsFeature = qgis_core.QgsFeature
QgsField = qgis_core.QgsField
QgsGeometry = qgis_core.QgsGeometry
QgsPointXY = qgis_core.QgsPointXY
QgsVectorLayer = qgis_core.QgsVectorLayer
QMetaType = getattr(qgis_qtcore, "QMetaType", None)
QVariant = qgis_qtcore.QVariant


def _field_type(name: str, fallback_name: str):
    if QMetaType is not None:
        enum = getattr(QMetaType, "Type", QMetaType)
        field_type = getattr(enum, name, None)
        if field_type is not None:
            return field_type
    return getattr(QVariant, fallback_name)


FIELD_STRING = _field_type("QString", "String")
FIELD_DOUBLE = _field_type("Double", "Double")

from insar_timeseries_viewer.insar_timeseries_reader import (  # noqa: E402
    DateField,
    LayerFieldMapping,
    inspect_layer,
    read_feature,
)
from insar_timeseries_viewer.layer_mapping_store import (  # noqa: E402
    MAPPING_PROPERTY_KEY,
    clear_layer_field_mapping,
    load_layer_field_mapping,
    save_layer_field_mapping,
)


pytestmark = pytest.mark.qgis


@pytest.fixture(scope="session", autouse=True)
def qgis_application():
    app = QgsApplication.instance()
    if app is None:
        app = QgsApplication([], False)
        app.initQgis()
    yield app


@pytest.fixture()
def layer_with_custom_fields() -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:31983", "persisted_mapping_fixture", "memory")
    assert layer.isValid()

    provider = layer.dataProvider()
    provider.addAttributes(
        [
            QgsField("name_key", FIELD_STRING),
            QgsField("vel_any", FIELD_DOUBLE),
            QgsField("sigma_any", FIELD_DOUBLE),
            QgsField("nodata_any", FIELD_DOUBLE),
            QgsField("first_obs", FIELD_DOUBLE),
            QgsField("last_obs", FIELD_DOUBLE),
        ]
    )
    layer.updateFields()

    feature = QgsFeature(layer.fields())
    feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(320100.0, 7500100.0)))
    feature.setAttributes(["PERSISTED", 4.2, 0.3, -9999.0, 1.0, -9999.0])

    ok, _ = provider.addFeatures([feature])
    assert ok
    layer.updateExtents()

    return layer


def _mapping() -> LayerFieldMapping:
    return LayerFieldMapping(
        identifier_field="name_key",
        component_key="los",
        velocity_field="vel_any",
        velocity_std_field="sigma_any",
        sentinel_field="nodata_any",
        date_fields=(
            DateField("first_obs", date(2024, 1, 1)),
            DateField("last_obs", date(2024, 2, 1)),
        ),
    )


def test_save_load_and_clear_layer_field_mapping(layer_with_custom_fields):
    mapping = _mapping()

    assert load_layer_field_mapping(layer_with_custom_fields) is None

    save_layer_field_mapping(layer_with_custom_fields, mapping)

    assert layer_with_custom_fields.customProperty(MAPPING_PROPERTY_KEY, None)
    assert load_layer_field_mapping(layer_with_custom_fields) == mapping

    clear_layer_field_mapping(layer_with_custom_fields)

    assert load_layer_field_mapping(layer_with_custom_fields) is None


def test_loaded_layer_field_mapping_can_drive_reader(layer_with_custom_fields):
    save_layer_field_mapping(layer_with_custom_fields, _mapping())

    loaded_mapping = load_layer_field_mapping(layer_with_custom_fields)
    assert loaded_mapping is not None

    schema = inspect_layer(layer_with_custom_fields, field_mapping=loaded_mapping)
    feature = next(layer_with_custom_fields.getFeatures())
    series = read_feature(layer_with_custom_fields, feature, schema=schema)

    assert schema.component_key == "los"
    assert schema.identifier_field == "name_key"
    assert schema.velocity_field == "vel_any"
    assert schema.velocity_std_field == "sigma_any"
    assert schema.sentinel_field == "nodata_any"
    assert series.identifier == "PERSISTED"
    assert series.velocity == pytest.approx(4.2)
    assert series.velocity_std == pytest.approx(0.3)
    assert series.valid_count == 1
    assert series.missing_count == 1
    assert series.cumulative_displacement == pytest.approx(1.0)
