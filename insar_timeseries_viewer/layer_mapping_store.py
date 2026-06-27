# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Persistência de mapeamentos manuais de campos em camadas QGIS.

O módulo mantém a serialização isolada da interface. A UI deverá construir um
``LayerFieldMapping`` e usar estas funções para salvar, ler ou limpar o
mapeamento associado a uma ``QgsVectorLayer`` via ``customProperty``.
"""

from __future__ import annotations

from datetime import date
import json
from typing import Any, Mapping, Optional

from .insar_timeseries_reader import DateField, LayerFieldMapping


MAPPING_PROPERTY_KEY = "insar_timeseries_viewer/layer_field_mapping"
MAPPING_SCHEMA_VERSION = 1


class LayerMappingStoreError(ValueError):
    """Erro ao serializar ou desserializar um mapeamento de camada."""


def mapping_to_dict(mapping: LayerFieldMapping) -> dict[str, Any]:
    """Converte ``LayerFieldMapping`` para um dicionário JSON-serializável."""

    return {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "identifier_field": mapping.identifier_field,
        "component_key": mapping.component_key,
        "component_field": mapping.component_field,
        "velocity_field": mapping.velocity_field,
        "velocity_std_field": mapping.velocity_std_field,
        "date_fields": _date_fields_to_list(mapping.date_fields),
        "orbit_field": mapping.orbit_field,
        "displacement_unit_field": mapping.displacement_unit_field,
        "sentinel_field": mapping.sentinel_field,
    }


def mapping_from_dict(data: Mapping[str, Any]) -> LayerFieldMapping:
    """Reconstrói ``LayerFieldMapping`` a partir de um dicionário."""

    if not isinstance(data, Mapping):
        raise LayerMappingStoreError("Mapping payload must be a dictionary.")

    version = data.get("schema_version")
    if version != MAPPING_SCHEMA_VERSION:
        raise LayerMappingStoreError(
            f"Unsupported layer mapping schema version: {version!r}."
        )

    return LayerFieldMapping(
        identifier_field=_optional_string(data, "identifier_field"),
        component_key=_optional_string(data, "component_key"),
        component_field=_optional_string(data, "component_field"),
        velocity_field=_optional_string(data, "velocity_field"),
        velocity_std_field=_optional_string(data, "velocity_std_field"),
        date_fields=_date_fields_from_list(data.get("date_fields")),
        orbit_field=_optional_string(data, "orbit_field"),
        displacement_unit_field=_optional_string(data, "displacement_unit_field"),
        sentinel_field=_optional_string(data, "sentinel_field"),
    )


def mapping_to_json(mapping: LayerFieldMapping) -> str:
    """Serializa ``LayerFieldMapping`` para JSON estável."""

    return json.dumps(mapping_to_dict(mapping), ensure_ascii=False, sort_keys=True)


def mapping_from_json(text: str) -> LayerFieldMapping:
    """Desserializa um ``LayerFieldMapping`` a partir de JSON."""

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LayerMappingStoreError("Invalid layer mapping JSON.") from exc

    return mapping_from_dict(data)


def save_layer_field_mapping(layer: Any, mapping: LayerFieldMapping) -> None:
    """Salva o mapeamento em ``layer.customProperty``."""

    layer.setCustomProperty(MAPPING_PROPERTY_KEY, mapping_to_json(mapping))


def load_layer_field_mapping(layer: Any) -> Optional[LayerFieldMapping]:
    """Lê o mapeamento salvo em ``layer.customProperty``.

    Retorna ``None`` quando não há mapeamento salvo.
    """

    raw_value = layer.customProperty(MAPPING_PROPERTY_KEY, None)
    if raw_value in (None, ""):
        return None

    return mapping_from_json(str(raw_value))


def clear_layer_field_mapping(layer: Any) -> None:
    """Remove o mapeamento salvo de uma camada."""

    layer.removeCustomProperty(MAPPING_PROPERTY_KEY)


def _date_fields_to_list(date_fields: Any) -> Optional[list[dict[str, str]]]:
    if date_fields is None:
        return None

    return [
        {
            "name": item.name,
            "acquisition_date": item.acquisition_date.isoformat(),
        }
        for item in date_fields
    ]


def _date_fields_from_list(value: Any) -> Optional[tuple[DateField, ...]]:
    if value is None:
        return None

    if not isinstance(value, list):
        raise LayerMappingStoreError("date_fields must be null or a list.")

    items = []
    for raw_item in value:
        if not isinstance(raw_item, Mapping):
            raise LayerMappingStoreError("Each date_fields item must be a dictionary.")

        raw_name = raw_item.get("name")
        raw_date = raw_item.get("acquisition_date")

        if not isinstance(raw_name, str) or not raw_name:
            raise LayerMappingStoreError("Each date field must have a non-empty name.")
        if not isinstance(raw_date, str):
            raise LayerMappingStoreError(
                "Each date field must have an acquisition_date string."
            )

        try:
            acquisition_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise LayerMappingStoreError(
                f"Invalid acquisition_date in date_fields: {raw_date!r}."
            ) from exc

        items.append(DateField(raw_name, acquisition_date))

    return tuple(items)


def _optional_string(data: Mapping[str, Any], key: str) -> Optional[str]:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise LayerMappingStoreError(f"{key} must be null or a string.")
    return value
