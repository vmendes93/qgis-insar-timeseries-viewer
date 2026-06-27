# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Dialog mínimo para configurar mapeamento manual de campos."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from qgis.core import QgsVectorLayer

from .i18n import tr
from .insar_timeseries_reader import DATE_FIELD_PATTERN, LayerFieldMapping


_AUTO_VALUE = "__auto__"


class FieldMappingDialog(QDialog):
    """Configura metadados manuais de uma camada InSAR.

    Esta primeira versão não edita campos temporais customizados. Quando o
    usuário salva o mapeamento, ``date_fields`` permanece ``None`` e o leitor
    continua detectando datas pela convenção DYYYYMMDD.
    """

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
            date_fields=None,
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

    def request_clear_mapping(self) -> None:
        self._clear_requested = True
        self.accept()

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

        self.temporal_fields_note = QLabel(
            tr(
                "Nesta versão, campos temporais customizados ainda não são editados "
                "neste diálogo. O leitor usa automaticamente campos DYYYYMMDD."
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

    def temporal_fields_summary(self) -> str:
        detected_fields = self._detected_temporal_fields()
        if not detected_fields:
            return tr("Nenhum campo temporal DYYYYMMDD detectado.")

        first_field, first_date = detected_fields[0]
        last_field, last_date = detected_fields[-1]
        first_names = ", ".join(field_name for field_name, _date in detected_fields[:3])
        last_names = ", ".join(field_name for field_name, _date in detected_fields[-3:])

        if len(detected_fields) <= 6:
            listed_names = ", ".join(field_name for field_name, _date in detected_fields)
            return tr(
                "{count} campos DYYYYMMDD detectados. "
                "Cobertura: {first_date} a {last_date}. "
                "Campos: {fields}.",
                count=len(detected_fields),
                first_date=first_date,
                last_date=last_date,
                fields=listed_names,
            )

        return tr(
            "{count} campos DYYYYMMDD detectados. "
            "Cobertura: {first_date} a {last_date}. "
            "Primeiro campo: {first_field}; último campo: {last_field}. "
            "Primeiros: {first_names}. Últimos: {last_names}.",
            count=len(detected_fields),
            first_date=first_date,
            last_date=last_date,
            first_field=first_field,
            last_field=last_field,
            first_names=first_names,
            last_names=last_names,
        )

    def _detected_temporal_fields(self) -> tuple[tuple[str, str], ...]:
        detected_fields = []
        for field_name in self._field_names:
            match = DATE_FIELD_PATTERN.fullmatch(field_name)
            if match is None:
                continue

            try:
                acquisition_date = datetime.strptime(
                    match.group("date"),
                    "%Y%m%d",
                ).date()
            except ValueError:
                continue

            detected_fields.append((field_name, acquisition_date))

        detected_fields.sort(key=lambda item: item[1])

        return tuple(
            (field_name, f"{acquisition_date:%d/%m/%Y}")
            for field_name, acquisition_date in detected_fields
        )

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
