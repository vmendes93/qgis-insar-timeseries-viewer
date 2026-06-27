# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""PyQGIS tests for manual field mapping in the generic reader."""

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
QVariant = qgis_qtcore.QVariant

from insar_timeseries_viewer.insar_timeseries_reader import (  # noqa: E402
    DateField,
    LayerFieldMapping,
    LayerValidationError,
    inspect_layer,
    read_feature,
    scan_layer,
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
def manually_mapped_layer() -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:31983", "manual_mapping_fixture", "memory")
    assert layer.isValid()

    provider = layer.dataProvider()
    provider.addAttributes(
        [
            QgsField("custom_id", QVariant.String),
            QgsField("speed", QVariant.Double),
            QgsField("sigma", QVariant.Double),
            QgsField("orb", QVariant.String),
            QgsField("measure", QVariant.String),
            QgsField("missing_code", QVariant.Double),
            QgsField("obs_a", QVariant.Double),
            QgsField("obs_b", QVariant.Double),
            QgsField("obs_c", QVariant.String),
        ]
    )
    layer.updateFields()

    feature = QgsFeature(layer.fields())
    feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(320000.0, 7500000.0)))
    feature.setAttributes(
        [
            "M001",
            -12.5,
            0.8,
            "DESC",
            "mm",
            -9999.0,
            1.25,
            -9999.0,
            "bad",
        ]
    )

    ok, _ = provider.addFeatures([feature])
    assert ok
    layer.updateExtents()
    return layer


def _manual_mapping() -> LayerFieldMapping:
    return LayerFieldMapping(
        identifier_field="custom_id",
        component_key="vertical",
        velocity_field="speed",
        velocity_std_field="sigma",
        orbit_field="orb",
        displacement_unit_field="measure",
        sentinel_field="missing_code",
        date_fields=(
            DateField("obs_a", date(2024, 1, 1)),
            DateField("obs_b", date(2024, 2, 1)),
            DateField("obs_c", date(2024, 3, 1)),
        ),
    )


def test_manual_field_mapping_detects_schema(manually_mapped_layer):
    schema = inspect_layer(manually_mapped_layer, field_mapping=_manual_mapping())

    assert schema.component_key == "vertical"
    assert schema.component_label == "VERT"
    assert schema.identifier_field == "custom_id"
    assert schema.velocity_field == "speed"
    assert schema.velocity_std_field == "sigma"
    assert schema.orbit_field == "orb"
    assert schema.displacement_unit_field == "measure"
    assert schema.sentinel_field == "missing_code"
    assert [item.name for item in schema.date_fields] == ["obs_a", "obs_b", "obs_c"]


def test_manual_field_mapping_reads_feature(manually_mapped_layer):
    schema = inspect_layer(manually_mapped_layer, field_mapping=_manual_mapping())
    feature = next(manually_mapped_layer.getFeatures())

    series = read_feature(manually_mapped_layer, feature, schema=schema)

    assert series.identifier == "M001"
    assert series.component_key == "vertical"
    assert series.velocity == pytest.approx(-12.5)
    assert series.velocity_std == pytest.approx(0.8)
    assert series.acquisition_count == 3
    assert series.valid_count == 1
    assert series.missing_count == 1
    assert series.invalid_fields == ("obs_c",)
    assert series.cumulative_displacement == pytest.approx(1.25)


def test_manual_field_mapping_scan_counts(manually_mapped_layer):
    schema = inspect_layer(manually_mapped_layer, field_mapping=_manual_mapping())

    result = scan_layer(manually_mapped_layer, schema=schema)

    assert result.scanned_feature_count == 1
    assert result.features_with_valid_series == 1
    assert result.features_without_valid_series == 0
    assert result.total_observations == 3
    assert result.valid_observations == 1
    assert result.missing_observations == 1
    assert result.invalid_observations == 1


def test_manual_field_mapping_rejects_missing_field(manually_mapped_layer):
    mapping = LayerFieldMapping(
        identifier_field="does_not_exist",
        component_key="vertical",
        date_fields=(
            DateField("obs_a", date(2024, 1, 1)),
            DateField("obs_b", date(2024, 2, 1)),
        ),
    )

    with pytest.raises(LayerValidationError):
        inspect_layer(manually_mapped_layer, field_mapping=mapping)


def test_manual_field_mapping_rejects_unknown_component(manually_mapped_layer):
    mapping = LayerFieldMapping(
        component_key="north_south",
        date_fields=(
            DateField("obs_a", date(2024, 1, 1)),
            DateField("obs_b", date(2024, 2, 1)),
        ),
    )

    with pytest.raises(LayerValidationError):
        inspect_layer(manually_mapped_layer, field_mapping=mapping)
