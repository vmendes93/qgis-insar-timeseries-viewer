# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""PyQGIS tests for the field mapping dialog."""

from __future__ import annotations

import pytest

qgis_core = pytest.importorskip("qgis.core")
qgis_qtcore = pytest.importorskip("qgis.PyQt.QtCore")

QgsApplication = qgis_core.QgsApplication
QgsField = qgis_core.QgsField
QgsVectorLayer = qgis_core.QgsVectorLayer
QVariant = qgis_qtcore.QVariant

from insar_timeseries_viewer.field_mapping_dialog import FieldMappingDialog  # noqa: E402
from insar_timeseries_viewer.insar_timeseries_reader import (  # noqa: E402
    LayerFieldMapping,
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
def layer() -> QgsVectorLayer:
    vector_layer = QgsVectorLayer("Point?crs=EPSG:31983", "dialog_layer", "memory")
    assert vector_layer.isValid()

    provider = vector_layer.dataProvider()
    provider.addAttributes(
        [
            QgsField("CODE_CUSTOM", QVariant.String),
            QgsField("COMP_CUSTOM", QVariant.String),
            QgsField("VEL_CUSTOM", QVariant.Double),
            QgsField("ERR_CUSTOM", QVariant.Double),
            QgsField("ORBIT_CUSTOM", QVariant.String),
            QgsField("UNIT_CUSTOM", QVariant.String),
            QgsField("NODATA_CUSTOM", QVariant.Double),
            QgsField("D20240101", QVariant.Double),
            QgsField("D20240201", QVariant.Double),
        ]
    )
    vector_layer.updateFields()
    return vector_layer


def test_field_mapping_dialog_returns_empty_mapping_by_default(layer):
    dialog = FieldMappingDialog(layer)

    mapping = dialog.field_mapping()

    assert mapping == LayerFieldMapping()


def test_field_mapping_dialog_restores_initial_mapping(layer):
    initial_mapping = LayerFieldMapping(
        identifier_field="CODE_CUSTOM",
        component_key="los",
        component_field="COMP_CUSTOM",
        velocity_field="VEL_CUSTOM",
        velocity_std_field="ERR_CUSTOM",
        orbit_field="ORBIT_CUSTOM",
        displacement_unit_field="UNIT_CUSTOM",
        sentinel_field="NODATA_CUSTOM",
    )

    dialog = FieldMappingDialog(layer, initial_mapping=initial_mapping)

    assert dialog.field_mapping() == initial_mapping


def test_field_mapping_dialog_marks_clear_request(layer):
    dialog = FieldMappingDialog(layer)

    assert dialog.clear_requested is False

    dialog.request_clear_mapping()

    assert dialog.clear_requested is True
