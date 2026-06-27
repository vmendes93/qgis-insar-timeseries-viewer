# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Dialog mínimo para configurar mapeamento manual de campos."""

from __future__ import annotations

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
from .insar_timeseries_reader import LayerFieldMapping


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
