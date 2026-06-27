# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""PyQGIS tests for the field mapping dialog."""

from __future__ import annotations

from datetime import date

import pytest

qgis_core = pytest.importorskip("qgis.core")
qgis_qtcore = pytest.importorskip("qgis.PyQt.QtCore")

QgsApplication = qgis_core.QgsApplication
QgsField = qgis_core.QgsField
QgsVectorLayer = qgis_core.QgsVectorLayer
QDate = qgis_qtcore.QDate
Qt = qgis_qtcore.Qt
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

from insar_timeseries_viewer.field_mapping_dialog import FieldMappingDialog  # noqa: E402
from insar_timeseries_viewer.insar_timeseries_reader import (  # noqa: E402
    DateField,
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
            QgsField("CODE_CUSTOM", FIELD_STRING),
            QgsField("COMP_CUSTOM", FIELD_STRING),
            QgsField("VEL_CUSTOM", FIELD_DOUBLE),
            QgsField("ERR_CUSTOM", FIELD_DOUBLE),
            QgsField("ORBIT_CUSTOM", FIELD_STRING),
            QgsField("UNIT_CUSTOM", FIELD_STRING),
            QgsField("NODATA_CUSTOM", FIELD_DOUBLE),
            QgsField("D20240101", FIELD_DOUBLE),
            QgsField("D20240201", FIELD_DOUBLE),
        ]
    )
    vector_layer.updateFields()
    return vector_layer


def _set_temporal_mode(dialog: FieldMappingDialog, mode: str) -> None:
    index = dialog.temporal_mode_combo.findData(mode)
    assert index >= 0
    dialog.temporal_mode_combo.setCurrentIndex(index)


def _temporal_row(dialog: FieldMappingDialog, field_name: str) -> int:
    row = dialog._temporal_row_by_field_name[field_name]
    assert row >= 0
    return row


def _set_temporal_checked(
    dialog: FieldMappingDialog,
    field_name: str,
    checked: bool,
) -> None:
    item = dialog.temporal_fields_table.item(_temporal_row(dialog, field_name), 0)
    item.setCheckState(Qt.Checked if checked else Qt.Unchecked)


def _set_temporal_date(
    dialog: FieldMappingDialog,
    field_name: str,
    qdate: QDate,
) -> None:
    date_edit = dialog.temporal_fields_table.cellWidget(
        _temporal_row(dialog, field_name),
        2,
    )
    date_edit.setDate(qdate)


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


def test_field_mapping_dialog_summarizes_detected_temporal_fields(layer):
    dialog = FieldMappingDialog(layer)

    summary = dialog.temporal_fields_summary()

    assert "2 DYYYYMMDD fields detected" in summary
    assert "Coverage: 01/01/2024 to 01/02/2024" in summary
    assert "Fields: D20240101, D20240201" in summary
    assert dialog.field_mapping().date_fields is None


def test_field_mapping_dialog_summarizes_many_temporal_fields_compactly(layer):
    provider = layer.dataProvider()
    provider.addAttributes(
        [
            QgsField("D20240301", FIELD_DOUBLE),
            QgsField("D20240401", FIELD_DOUBLE),
            QgsField("D20240501", FIELD_DOUBLE),
            QgsField("D20240601", FIELD_DOUBLE),
            QgsField("D20240701", FIELD_DOUBLE),
        ]
    )
    layer.updateFields()
    dialog = FieldMappingDialog(layer)

    summary = dialog.temporal_fields_summary()

    assert "7 DYYYYMMDD fields detected" in summary
    assert "Coverage: 01/01/2024 to 01/07/2024" in summary
    assert "First field: D20240101" in summary
    assert "last field: D20240701" in summary
    assert "First: D20240101, D20240201, D20240301" in summary
    assert "Last: D20240501, D20240601, D20240701" in summary
    assert "D20240401" not in summary


def test_field_mapping_dialog_manual_temporal_mode_exports_date_fields(layer):
    dialog = FieldMappingDialog(layer)

    _set_temporal_mode(dialog, "manual")
    mapping = dialog.field_mapping()

    assert mapping.date_fields == (
        DateField(name="D20240101", acquisition_date=date(2024, 1, 1)),
        DateField(name="D20240201", acquisition_date=date(2024, 2, 1)),
    )


def test_field_mapping_dialog_manual_temporal_mode_can_use_custom_field(layer):
    dialog = FieldMappingDialog(layer)

    _set_temporal_mode(dialog, "manual")
    _set_temporal_checked(dialog, "D20240101", False)
    _set_temporal_checked(dialog, "D20240201", False)
    _set_temporal_checked(dialog, "VEL_CUSTOM", True)
    _set_temporal_date(dialog, "VEL_CUSTOM", QDate(2024, 3, 15))

    mapping = dialog.field_mapping()

    assert mapping.date_fields == (
        DateField(name="VEL_CUSTOM", acquisition_date=date(2024, 3, 15)),
    )


def test_field_mapping_dialog_restores_manual_date_fields(layer):
    initial_mapping = LayerFieldMapping(
        date_fields=(
            DateField(name="D20240201", acquisition_date=date(2024, 2, 1)),
            DateField(name="CODE_CUSTOM", acquisition_date=date(2024, 3, 1)),
        )
    )

    dialog = FieldMappingDialog(layer, initial_mapping=initial_mapping)
    mapping = dialog.field_mapping()

    assert dialog.temporal_mode_combo.currentData() == "manual"
    assert mapping.date_fields == (
        DateField(name="D20240201", acquisition_date=date(2024, 2, 1)),
        DateField(name="CODE_CUSTOM", acquisition_date=date(2024, 3, 1)),
    )


def test_field_mapping_dialog_filters_temporal_table_rows(layer):
    dialog = FieldMappingDialog(layer)
    _set_temporal_mode(dialog, "manual")

    dialog.temporal_filter_edit.setText("vel")

    assert dialog.temporal_fields_table.isRowHidden(
        _temporal_row(dialog, "D20240101")
    )
    assert not dialog.temporal_fields_table.isRowHidden(
        _temporal_row(dialog, "VEL_CUSTOM")
    )


def test_field_mapping_dialog_selects_detected_temporal_fields(layer):
    dialog = FieldMappingDialog(layer)
    _set_temporal_mode(dialog, "manual")

    _set_temporal_checked(dialog, "D20240101", False)
    _set_temporal_checked(dialog, "VEL_CUSTOM", True)

    dialog.select_dyyyy_button.click()

    assert dialog.temporal_fields_table.item(
        _temporal_row(dialog, "D20240101"),
        0,
    ).checkState() == Qt.Checked
    assert dialog.temporal_fields_table.item(
        _temporal_row(dialog, "D20240201"),
        0,
    ).checkState() == Qt.Checked
    assert dialog.temporal_fields_table.item(
        _temporal_row(dialog, "VEL_CUSTOM"),
        0,
    ).checkState() == Qt.Unchecked


def test_field_mapping_dialog_clears_temporal_selection(layer):
    dialog = FieldMappingDialog(layer)
    _set_temporal_mode(dialog, "manual")

    dialog.clear_temporal_button.click()

    assert dialog.field_mapping().date_fields == ()
