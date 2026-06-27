# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Dialog mínimo para configurar mapeamento manual de campos."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from qgis.PyQt.QtCore import QDate, Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from qgis.core import QgsVectorLayer

from .i18n import tr
from .insar_timeseries_reader import DATE_FIELD_PATTERN, DateField, LayerFieldMapping


_AUTO_VALUE = "__auto__"
_TEMPORAL_MODE_AUTO = "auto"
_TEMPORAL_MODE_MANUAL = "manual"


class FieldMappingDialog(QDialog):
    """Configura metadados manuais de uma camada InSAR."""

    def __init__(
        self,
        layer: QgsVectorLayer,
        initial_mapping: Optional[LayerFieldMapping] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("Configurar campos da camada"))
        self.setModal(True)

        self.layer = layer
        self._field_names = tuple(field.name() for field in layer.fields())
        self._clear_requested = False
        self._temporal_row_by_field_name: dict[str, int] = {}

        self._build_ui()
        if initial_mapping is not None:
            self.set_mapping(initial_mapping)

    @property
    def clear_requested(self) -> bool:
        return self._clear_requested

    def field_mapping(self) -> LayerFieldMapping:
        return LayerFieldMapping(
            identifier_field=self._combo_data(self.identifier_combo),
            component_key=self._combo_data(self.component_key_combo),
            component_field=self._combo_data(self.component_field_combo),
            velocity_field=self._combo_data(self.velocity_combo),
            velocity_std_field=self._combo_data(self.velocity_std_combo),
            date_fields=self._selected_manual_date_fields(),
            orbit_field=self._combo_data(self.orbit_combo),
            displacement_unit_field=self._combo_data(self.unit_combo),
            sentinel_field=self._combo_data(self.sentinel_combo),
        )

    def set_mapping(self, mapping: LayerFieldMapping) -> None:
        self._set_combo_data(self.identifier_combo, mapping.identifier_field)
        self._set_combo_data(self.component_key_combo, mapping.component_key)
        self._set_combo_data(self.component_field_combo, mapping.component_field)
        self._set_combo_data(self.velocity_combo, mapping.velocity_field)
        self._set_combo_data(self.velocity_std_combo, mapping.velocity_std_field)
        self._set_combo_data(self.orbit_combo, mapping.orbit_field)
        self._set_combo_data(self.unit_combo, mapping.displacement_unit_field)
        self._set_combo_data(self.sentinel_combo, mapping.sentinel_field)

        if mapping.date_fields is None:
            self._set_combo_data(self.temporal_mode_combo, _TEMPORAL_MODE_AUTO)
        else:
            self._set_combo_data(self.temporal_mode_combo, _TEMPORAL_MODE_MANUAL)
            self._apply_manual_date_fields(mapping.date_fields)

        self._sync_temporal_table_enabled()

    def request_clear_mapping(self) -> None:
        self._clear_requested = True
        self.accept()

    def temporal_fields_summary(self) -> str:
        detected_fields = self._detected_temporal_fields()
        if not detected_fields:
            return tr("Nenhum campo temporal DYYYYMMDD detectado.")

        first_field, first_date = detected_fields[0]
        last_field, last_date = detected_fields[-1]
        first_names = ", ".join(field_name for field_name, _date in detected_fields[:3])
        last_names = ", ".join(field_name for field_name, _date in detected_fields[-3:])
        first_date_text = f"{first_date:%d/%m/%Y}"
        last_date_text = f"{last_date:%d/%m/%Y}"

        if len(detected_fields) <= 6:
            listed_names = ", ".join(field_name for field_name, _date in detected_fields)
            return tr(
                "{count} campos DYYYYMMDD detectados. "
                "Cobertura: {first_date} a {last_date}. "
                "Campos: {fields}.",
                count=len(detected_fields),
                first_date=first_date_text,
                last_date=last_date_text,
                fields=listed_names,
            )

        return tr(
            "{count} campos DYYYYMMDD detectados. "
            "Cobertura: {first_date} a {last_date}. "
            "Primeiro campo: {first_field}; último campo: {last_field}. "
            "Primeiros: {first_names}. Últimos: {last_names}.",
            count=len(detected_fields),
            first_date=first_date_text,
            last_date=last_date_text,
            first_field=first_field,
            last_field=last_field,
            first_names=first_names,
            last_names=last_names,
        )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        explanation = QLabel(
            tr(
                "Configure campos opcionais da camada selecionada. "
                "Campos deixados como automáticos continuarão sendo detectados "
                "por aliases. As datas ainda usam campos DYYYYMMDD."
            )
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        form = QFormLayout()
        self.component_key_combo = self._build_component_combo()
        self.identifier_combo = self._build_field_combo()
        self.component_field_combo = self._build_field_combo()
        self.velocity_combo = self._build_field_combo()
        self.velocity_std_combo = self._build_field_combo()
        self.orbit_combo = self._build_field_combo()
        self.unit_combo = self._build_field_combo()
        self.sentinel_combo = self._build_field_combo()

        form.addRow(tr("Componente:"), self.component_key_combo)
        form.addRow(tr("Identificador:"), self.identifier_combo)
        form.addRow(tr("Campo de componente:"), self.component_field_combo)
        form.addRow(tr("Velocidade:"), self.velocity_combo)
        form.addRow(tr("Incerteza da velocidade:"), self.velocity_std_combo)
        form.addRow(tr("Órbita/passagem:"), self.orbit_combo)
        form.addRow(tr("Unidade:"), self.unit_combo)
        form.addRow(tr("Sentinela NoData:"), self.sentinel_combo)
        layout.addLayout(form)

        self.temporal_fields_title = QLabel(tr("Campos temporais:"))
        layout.addWidget(self.temporal_fields_title)

        self.temporal_fields_label = QLabel(self.temporal_fields_summary())
        self.temporal_fields_label.setWordWrap(True)
        layout.addWidget(self.temporal_fields_label)

        temporal_form = QFormLayout()
        self.temporal_mode_combo = self._build_temporal_mode_combo()
        self.temporal_mode_combo.currentIndexChanged.connect(
            self._sync_temporal_table_enabled
        )
        temporal_form.addRow(tr("Modo dos campos temporais:"), self.temporal_mode_combo)
        layout.addLayout(temporal_form)

        self.temporal_fields_table = self._build_temporal_fields_table()
        layout.addWidget(self.temporal_fields_table)

        self.temporal_fields_note = QLabel(
            tr(
                "No modo manual, marque os campos temporais e ajuste suas datas. "
                "No modo automático, o leitor usa campos DYYYYMMDD."
            )
        )
        self.temporal_fields_note.setWordWrap(True)
        layout.addWidget(self.temporal_fields_note)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        self.clear_button = QPushButton(tr("Limpar mapeamento salvo"))
        self.button_box.addButton(
            self.clear_button,
            QDialogButtonBox.ResetRole,
        )

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.clear_button.clicked.connect(self.request_clear_mapping)
        layout.addWidget(self.button_box)

        self._sync_temporal_table_enabled()

    def _build_component_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(tr("Automático"), _AUTO_VALUE)
        combo.addItem("LOS", "los")
        combo.addItem("VERT", "vertical")
        combo.addItem("EW", "east_west")
        combo.addItem(tr("Genérica"), "unknown")
        return combo

    def _build_field_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(tr("Automático"), _AUTO_VALUE)
        for field_name in self._field_names:
            combo.addItem(field_name, field_name)
        return combo

    def _build_temporal_mode_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.addItem(
            tr("Automático: detectar DYYYYMMDD"),
            _TEMPORAL_MODE_AUTO,
        )
        combo.addItem(
            tr("Manual: usar tabela abaixo"),
            _TEMPORAL_MODE_MANUAL,
        )
        return combo

    def _build_temporal_fields_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([tr("Usar"), tr("Campo"), tr("Data")])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setMaximumHeight(240)

        ordered_fields = self._ordered_temporal_table_fields()
        table.setRowCount(len(ordered_fields))
        self._temporal_row_by_field_name = {}

        for row, field_name in enumerate(ordered_fields):
            self._temporal_row_by_field_name[field_name] = row
            detected_date = self._date_from_field_name(field_name)

            use_item = QTableWidgetItem("")
            use_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            use_item.setCheckState(Qt.Checked if detected_date is not None else Qt.Unchecked)
            table.setItem(row, 0, use_item)

            field_item = QTableWidgetItem(field_name)
            field_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, 1, field_item)

            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd")
            if detected_date is None:
                date_edit.setDate(QDate.currentDate())
            else:
                date_edit.setDate(
                    QDate(detected_date.year, detected_date.month, detected_date.day)
                )
            table.setCellWidget(row, 2, date_edit)

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _ordered_temporal_table_fields(self) -> tuple[str, ...]:
        detected_fields = self._detected_temporal_fields()
        detected_names = {field_name for field_name, _date in detected_fields}
        remaining_names = tuple(
            field_name
            for field_name in self._field_names
            if field_name not in detected_names
        )
        return tuple(field_name for field_name, _date in detected_fields) + remaining_names

    def _detected_temporal_fields(self) -> tuple[tuple[str, date], ...]:
        detected_fields = []
        for field_name in self._field_names:
            acquisition_date = self._date_from_field_name(field_name)
            if acquisition_date is None:
                continue
            detected_fields.append((field_name, acquisition_date))

        detected_fields.sort(key=lambda item: item[1])
        return tuple(detected_fields)

    @staticmethod
    def _date_from_field_name(field_name: str) -> Optional[date]:
        match = DATE_FIELD_PATTERN.fullmatch(field_name)
        if match is None:
            return None

        try:
            return datetime.strptime(match.group("date"), "%Y%m%d").date()
        except ValueError:
            return None

    def _sync_temporal_table_enabled(self) -> None:
        enabled = self._combo_data(self.temporal_mode_combo) == _TEMPORAL_MODE_MANUAL
        self.temporal_fields_table.setEnabled(enabled)

    def _selected_manual_date_fields(self) -> Optional[tuple[DateField, ...]]:
        if self._combo_data(self.temporal_mode_combo) != _TEMPORAL_MODE_MANUAL:
            return None

        date_fields = []
        for row in range(self.temporal_fields_table.rowCount()):
            use_item = self.temporal_fields_table.item(row, 0)
            field_item = self.temporal_fields_table.item(row, 1)
            date_edit = self.temporal_fields_table.cellWidget(row, 2)
            if use_item is None or field_item is None or date_edit is None:
                continue
            if use_item.checkState() != Qt.Checked:
                continue

            date_fields.append(
                DateField(
                    name=field_item.text(),
                    acquisition_date=date_edit.date().toPyDate(),
                )
            )

        date_fields.sort(key=lambda item: item.acquisition_date)
        return tuple(date_fields)

    def _apply_manual_date_fields(self, date_fields: object) -> None:
        for row in range(self.temporal_fields_table.rowCount()):
            item = self.temporal_fields_table.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.Unchecked)

        for date_field in date_fields:
            row = self._temporal_row_by_field_name.get(date_field.name)
            if row is None:
                continue

            use_item = self.temporal_fields_table.item(row, 0)
            if use_item is not None:
                use_item.setCheckState(Qt.Checked)

            date_edit = self.temporal_fields_table.cellWidget(row, 2)
            if date_edit is not None:
                acquisition_date = date_field.acquisition_date
                date_edit.setDate(
                    QDate(
                        acquisition_date.year,
                        acquisition_date.month,
                        acquisition_date.day,
                    )
                )

    @staticmethod
    def _combo_data(combo: QComboBox) -> Optional[str]:
        value = combo.currentData()
        if value == _AUTO_VALUE:
            return None
        return value

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: Optional[str]) -> None:
        lookup_value = _AUTO_VALUE if value is None else value
        index = combo.findData(lookup_value)
        if index >= 0:
            combo.setCurrentIndex(index)
