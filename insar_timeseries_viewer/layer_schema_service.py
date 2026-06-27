# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Resolução de esquema InSAR para camadas QGIS.

Este módulo centraliza a decisão entre usar um ``LayerFieldMapping`` salvo na
camada, um mapeamento explícito informado pela UI ou a detecção automática do
leitor. A interface gráfica deve chamar este serviço em vez de acessar
``customProperty`` diretamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .i18n import tr
from .insar_timeseries_reader import (
    LayerFieldMapping,
    LayerSchema,
    LayerValidationError,
    inspect_layer,
)
from .layer_mapping_store import (
    LayerMappingStoreError,
    load_layer_field_mapping,
)


SOURCE_AUTO_DETECTED = "auto_detected"
SOURCE_SAVED_MAPPING = "saved_mapping"
SOURCE_EXPLICIT_MAPPING = "explicit_mapping"


class LayerSchemaServiceError(RuntimeError):
    """Erro-base da camada de resolução de esquema."""


class SavedLayerMappingError(LayerSchemaServiceError):
    """O mapeamento salvo existe, mas não pôde ser usado."""


@dataclass(frozen=True)
class LayerSchemaResolution:
    """Resultado da resolução de esquema de uma camada."""

    schema: LayerSchema
    source: str
    field_mapping: Optional[LayerFieldMapping]


def resolve_layer_schema(
    layer: Any,
    field_mapping: Optional[LayerFieldMapping] = None,
    use_saved_mapping: bool = True,
) -> LayerSchemaResolution:
    """Resolve o esquema de série temporal de uma camada.

    Prioridade:

    1. ``field_mapping`` explícito, quando informado;
    2. mapeamento salvo na camada, quando ``use_saved_mapping`` é ``True``;
    3. detecção automática por aliases e campos DYYYYMMDD.
    """

    if field_mapping is not None:
        schema = inspect_layer(layer, field_mapping=field_mapping)
        return LayerSchemaResolution(
            schema=schema,
            source=SOURCE_EXPLICIT_MAPPING,
            field_mapping=field_mapping,
        )

    if use_saved_mapping:
        saved_mapping = _load_saved_mapping(layer)
        if saved_mapping is not None:
            schema = _inspect_with_saved_mapping(layer, saved_mapping)
            return LayerSchemaResolution(
                schema=schema,
                source=SOURCE_SAVED_MAPPING,
                field_mapping=saved_mapping,
            )

    schema = inspect_layer(layer)
    return LayerSchemaResolution(
        schema=schema,
        source=SOURCE_AUTO_DETECTED,
        field_mapping=None,
    )


def _load_saved_mapping(layer: Any) -> Optional[LayerFieldMapping]:
    try:
        return load_layer_field_mapping(layer)
    except LayerMappingStoreError as exc:
        raise SavedLayerMappingError(
            tr("O mapeamento salvo da camada não pôde ser lido.")
        ) from exc


def _inspect_with_saved_mapping(
    layer: Any,
    saved_mapping: LayerFieldMapping,
) -> LayerSchema:
    try:
        return inspect_layer(layer, field_mapping=saved_mapping)
    except LayerValidationError as exc:
        raise SavedLayerMappingError(
            tr("O mapeamento salvo da camada não é compatível com os campos atuais.")
        ) from exc
