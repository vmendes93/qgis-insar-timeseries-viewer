# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Leitura e validação de séries temporais InSAR em camadas vetoriais do QGIS.

O módulo não relaciona camadas entre si. Campos identificadores e metadados
como velocidade, incerteza, componente, órbita, unidade e sentinelas são
tratados como opcionais sempre que a estrutura temporal mínima for válida.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import math
import re
from typing import Any, Iterable, Optional, Sequence, Tuple

from qgis.core import NULL, QgsFeature, QgsVectorLayer, QgsWkbTypes

from .i18n import tr


DATE_FIELD_PATTERN = re.compile(r"^D(?P<date>\d{8})$")
POSSIBLE_DATE_FIELD_PATTERN = re.compile(r"^D\d")
DEFAULT_MISSING_SENTINELS: Tuple[float, ...] = (999.0,)

IDENTIFIER_FIELD_ALIASES: Tuple[str, ...] = (
    "CODE",
    "POINT_ID",
    "POINTID",
    "STATION",
    "ID",
    "PS_ID",
    "TARGET_ID",
)
COMPONENT_FIELD_ALIASES: Tuple[str, ...] = (
    "COMPONENT",
    "COMP",
    "AXIS",
    "DIRECTION",
)
ORBIT_FIELD_ALIASES: Tuple[str, ...] = (
    "ORBIT",
    "PASS",
    "ORBIT_DIR",
    "ORBIT_DIRECTION",
)
DISPLACEMENT_UNIT_FIELD_ALIASES: Tuple[str, ...] = (
    "UNIT",
    "UOM",
    "UNITS",
    "DISP_UNIT",
)
SENTINEL_FIELD_ALIASES: Tuple[str, ...] = (
    "NODATA",
    "NO_DATA",
    "NULL_VALUE",
    "MISSING",
    "MISSING_VALUE",
)


class InsarReaderError(Exception):
    """Erro-base do leitor de séries temporais InSAR."""


class LayerValidationError(InsarReaderError):
    """A camada não possui uma estrutura compatível com o leitor."""


class FeatureReadError(InsarReaderError):
    """Uma feição não pôde ser convertida em série temporal."""


@dataclass(frozen=True)
class ComponentDefinition:
    key: str
    label: str
    velocity_field_aliases: Tuple[str, ...]
    velocity_std_field_aliases: Tuple[str, ...]
    value_aliases: Tuple[str, ...]
    name_aliases: Tuple[str, ...]


# Os nomes são avaliados sem distinguir maiúsculas de minúsculas, mas o nome
# real do campo da camada é preservado no esquema resultante.
COMPONENT_DEFINITIONS: Tuple[ComponentDefinition, ...] = (
    ComponentDefinition(
        key="vertical",
        label="VERT",
        velocity_field_aliases=(
            "VEL_V",
            "V_VEL",
            "VEL_VERT",
            "VERT_VEL",
            "VERT_RATE",
            "RATE_V",
            "RATE_VERT",
            "UP_RATE",
        ),
        velocity_std_field_aliases=(
            "V_STDEV_V",
            "STD_VEL_V",
            "VEL_V_STD",
            "VERT_ERR",
            "VERT_UNC",
            "RATE_ERR_V",
        ),
        value_aliases=("VERT", "VERTICAL", "V", "UP", "Z", "U"),
        name_aliases=("VERT", "VERTICAL", "UP", "Z"),
    ),
    ComponentDefinition(
        key="east_west",
        label="EW",
        velocity_field_aliases=(
            "VEL_E",
            "VEL_EW",
            "EW_VEL",
            "EAST_VEL",
            "MOTION",
            "RATE_E",
            "RATE_EW",
            "EAST_RATE",
        ),
        velocity_std_field_aliases=(
            "V_STDEV_E",
            "STD_VEL_E",
            "VEL_E_STD",
            "EW_ERR",
            "EW_UNC",
            "RATE_ERR_E",
            "UNCERT",
        ),
        value_aliases=("EW", "E-W", "EAST_WEST", "EAST-WEST", "EAST WEST", "HORIZONTAL_EW"),
        name_aliases=("EW", "E-W", "EAST_WEST", "EAST-WEST", "EAST WEST"),
    ),
    ComponentDefinition(
        key="los",
        label="LOS",
        velocity_field_aliases=(
            "VEL",
            "VEL_LOS",
            "LOS_VEL",
            "VELOCITY",
            "RATE",
            "RATE_MM_Y",
        ),
        velocity_std_field_aliases=(
            "V_STDEV",
            "VEL_STD",
            "STD_VEL",
            "LOS_ERR",
            "LOS_UNC",
            "RATE_ERR",
        ),
        value_aliases=("LOS", "LINE_OF_SIGHT", "LINE-OF-SIGHT", "LINE OF SIGHT"),
        name_aliases=("LOS", "LINE_OF_SIGHT", "LINE-OF-SIGHT", "LINE OF SIGHT"),
    ),
)
UNKNOWN_COMPONENT = ComponentDefinition(
    key="unknown",
    label="TS",
    velocity_field_aliases=(),
    velocity_std_field_aliases=(),
    value_aliases=(),
    name_aliases=(),
)


@dataclass(frozen=True)
class DateField:
    name: str
    acquisition_date: date


@dataclass(frozen=True)
class LayerSchema:
    """Descrição consolidada dos campos relevantes de uma camada."""

    layer_id: str
    layer_name: str
    component_key: str
    component_label: str
    identifier_field: Optional[str]
    velocity_field: Optional[str]
    velocity_std_field: Optional[str]
    date_fields: Tuple[DateField, ...]
    general_fields: Tuple[str, ...]
    warnings: Tuple[str, ...]
    component_field: Optional[str] = None
    orbit_field: Optional[str] = None
    displacement_unit_field: Optional[str] = None
    sentinel_field: Optional[str] = None

    @property
    def acquisition_count(self) -> int:
        return len(self.date_fields)

    @property
    def first_acquisition(self) -> date:
        return self.date_fields[0].acquisition_date

    @property
    def last_acquisition(self) -> date:
        return self.date_fields[-1].acquisition_date


@dataclass(frozen=True)
class TimeSeriesData:
    """Série temporal extraída de uma única feição."""

    feature_id: int
    identifier: str
    component_key: str
    component_label: str
    velocity: Optional[float]
    velocity_std: Optional[float]
    dates: Tuple[date, ...]
    values: Tuple[Optional[float], ...]
    valid_dates: Tuple[date, ...]
    valid_values: Tuple[float, ...]
    first_valid_date: date
    last_valid_date: date
    cumulative_displacement: float
    missing_count: int
    invalid_fields: Tuple[str, ...]

    @property
    def valid_count(self) -> int:
        return len(self.valid_values)

    @property
    def acquisition_count(self) -> int:
        return len(self.dates)


@dataclass(frozen=True)
class LayerScanResult:
    """Resultado de uma varredura diagnóstica da camada inteira."""

    scanned_feature_count: int
    features_with_valid_series: int
    features_without_valid_series: int
    total_observations: int
    valid_observations: int
    missing_observations: int
    invalid_observations: int
    earliest_valid_date: Optional[date]
    latest_valid_date: Optional[date]
    truncated: bool


def inspect_layer(layer: QgsVectorLayer) -> LayerSchema:
    """Valida uma camada e identifica seu esquema de série temporal.

    A função identifica campos temporais DYYYYMMDD e tenta detectar metadados
    comuns por aliases. Apenas geometria de ponto e ao menos dois campos
    temporais válidos são obrigatórios.
    """

    _validate_vector_point_layer(layer)

    field_names = tuple(field.name() for field in layer.fields())
    if not field_names:
        raise LayerValidationError(tr("A camada não possui campos de atributos."))

    normalized_fields = _build_normalized_field_map(field_names)
    warnings = []
    parsed_date_fields = []
    rejected_date_like_fields = []

    for field_name in field_names:
        match = DATE_FIELD_PATTERN.fullmatch(field_name)
        if not match:
            if POSSIBLE_DATE_FIELD_PATTERN.match(field_name):
                rejected_date_like_fields.append(field_name)
            continue

        raw_date = match.group("date")
        try:
            acquisition_date = datetime.strptime(raw_date, "%Y%m%d").date()
        except ValueError:
            rejected_date_like_fields.append(field_name)
            continue

        parsed_date_fields.append(DateField(field_name, acquisition_date))

    parsed_date_fields.sort(key=lambda item: item.acquisition_date)

    if len(parsed_date_fields) < 2:
        raise LayerValidationError(
            tr("A camada precisa ter pelo menos dois campos temporais válidos no formato DYYYYMMDD.")
        )

    duplicate_dates = _find_duplicate_dates(parsed_date_fields)
    if duplicate_dates:
        formatted = ", ".join(d.strftime("%Y-%m-%d") for d in duplicate_dates)
        raise LayerValidationError(
            tr("Foram encontradas datas de aquisição duplicadas: {dates}", dates=formatted)
        )

    if rejected_date_like_fields:
        warnings.append(
            tr("Campos parecidos com datas foram ignorados por não seguirem uma data DYYYYMMDD válida: {fields}", fields=", ".join(rejected_date_like_fields))
        )

    component_field = _find_field(normalized_fields, COMPONENT_FIELD_ALIASES)
    orbit_field = _find_field(normalized_fields, ORBIT_FIELD_ALIASES)
    displacement_unit_field = _find_field(normalized_fields, DISPLACEMENT_UNIT_FIELD_ALIASES)
    sentinel_field = _find_field(normalized_fields, SENTINEL_FIELD_ALIASES)

    component = _detect_component(layer, normalized_fields, component_field)
    actual_velocity_field = _find_field(normalized_fields, component.velocity_field_aliases)
    actual_velocity_std_field = _find_field(normalized_fields, component.velocity_std_field_aliases)

    if component.key == "unknown":
        warnings.append(
            tr("A componente InSAR não pôde ser identificada automaticamente; a série será tratada como genérica.")
        )
    if actual_velocity_field is None:
        warnings.append(
            tr("Nenhum campo de velocidade foi identificado automaticamente; a velocidade será deixada vazia.")
        )
    if actual_velocity_std_field is None:
        warnings.append(
            tr("Nenhum campo de incerteza da velocidade foi identificado automaticamente; a incerteza será deixada vazia.")
        )

    identifier_field = _find_field(normalized_fields, IDENTIFIER_FIELD_ALIASES)
    if identifier_field is None:
        warnings.append(
            tr("Nenhum campo identificador foi encontrado; o ID interno da feição será usado como rótulo.")
        )

    temporal_names = {item.name for item in parsed_date_fields}
    general_fields = tuple(name for name in field_names if name not in temporal_names)

    return LayerSchema(
        layer_id=layer.id(),
        layer_name=layer.name(),
        component_key=component.key,
        component_label=component.label,
        identifier_field=identifier_field,
        velocity_field=actual_velocity_field,
        velocity_std_field=actual_velocity_std_field,
        date_fields=tuple(parsed_date_fields),
        general_fields=general_fields,
        warnings=tuple(warnings),
        component_field=component_field,
        orbit_field=orbit_field,
        displacement_unit_field=displacement_unit_field,
        sentinel_field=sentinel_field,
    )


def read_feature(
    layer: QgsVectorLayer,
    feature: QgsFeature,
    schema: Optional[LayerSchema] = None,
    missing_sentinels: Sequence[float] = DEFAULT_MISSING_SENTINELS,
) -> TimeSeriesData:
    """Extrai a série temporal de uma feição.

    Valores NULL, None, NaN e os sentinelas informados são convertidos para
    ausência de dado. Valores não numéricos inesperados são registrados em
    ``invalid_fields`` e também não entram na série válida.
    """

    _validate_vector_point_layer(layer)

    if feature is None or not feature.isValid():
        raise FeatureReadError(tr("A feição recebida é inválida."))

    schema = schema or inspect_layer(layer)
    _validate_schema_layer(schema, layer)

    sentinel_values = _sentinels_for_feature(feature, schema, missing_sentinels)

    velocity = None
    if schema.velocity_field is not None:
        velocity, _ = _coerce_numeric(
            _feature_value(feature, schema.velocity_field), sentinel_values
        )

    velocity_std = None
    if schema.velocity_std_field is not None:
        velocity_std, _ = _coerce_numeric(
            _feature_value(feature, schema.velocity_std_field), sentinel_values
        )

    dates = []
    values = []
    valid_dates = []
    valid_values = []
    missing_count = 0
    invalid_fields = []

    for date_field in schema.date_fields:
        raw_value = _feature_value(feature, date_field.name)
        numeric_value, status = _coerce_numeric(raw_value, sentinel_values)

        dates.append(date_field.acquisition_date)
        values.append(numeric_value)

        if status == "valid":
            valid_dates.append(date_field.acquisition_date)
            valid_values.append(numeric_value)
        elif status == "missing":
            missing_count += 1
        else:
            invalid_fields.append(date_field.name)

    if not valid_values:
        raise FeatureReadError(
            tr("A feição de ID {fid} não possui nenhuma observação temporal válida.", fid=feature.id())
        )

    identifier = _feature_identifier(feature, schema)

    return TimeSeriesData(
        feature_id=feature.id(),
        identifier=identifier,
        component_key=schema.component_key,
        component_label=schema.component_label,
        velocity=velocity,
        velocity_std=velocity_std,
        dates=tuple(dates),
        values=tuple(values),
        valid_dates=tuple(valid_dates),
        valid_values=tuple(valid_values),
        first_valid_date=valid_dates[0],
        last_valid_date=valid_dates[-1],
        cumulative_displacement=valid_values[-1],
        missing_count=missing_count,
        invalid_fields=tuple(invalid_fields),
    )


def scan_layer(
    layer: QgsVectorLayer,
    schema: Optional[LayerSchema] = None,
    missing_sentinels: Sequence[float] = DEFAULT_MISSING_SENTINELS,
    max_features: Optional[int] = None,
) -> LayerScanResult:
    """Percorre a camada para produzir estatísticas diagnósticas.

    Esta varredura é destinada a testes e validação. O visualizador não deverá
    percorrer toda a camada sempre que o usuário selecionar um ponto.
    """

    _validate_vector_point_layer(layer)
    schema = schema or inspect_layer(layer)
    _validate_schema_layer(schema, layer)

    if max_features is not None and max_features <= 0:
        raise ValueError(tr("max_features deve ser maior que zero ou None."))

    scanned_feature_count = 0
    features_with_valid_series = 0
    features_without_valid_series = 0
    total_observations = 0
    valid_observations = 0
    missing_observations = 0
    invalid_observations = 0
    earliest_valid_date = None
    latest_valid_date = None
    truncated = False

    for feature in layer.getFeatures():
        if max_features is not None and scanned_feature_count >= max_features:
            truncated = True
            break

        scanned_feature_count += 1
        feature_has_valid_value = False
        sentinel_values = _sentinels_for_feature(feature, schema, missing_sentinels)

        for date_field in schema.date_fields:
            total_observations += 1
            raw_value = _feature_value(feature, date_field.name)
            _, status = _coerce_numeric(raw_value, sentinel_values)

            if status == "valid":
                valid_observations += 1
                feature_has_valid_value = True
                current_date = date_field.acquisition_date
                if earliest_valid_date is None or current_date < earliest_valid_date:
                    earliest_valid_date = current_date
                if latest_valid_date is None or current_date > latest_valid_date:
                    latest_valid_date = current_date
            elif status == "missing":
                missing_observations += 1
            else:
                invalid_observations += 1

        if feature_has_valid_value:
            features_with_valid_series += 1
        else:
            features_without_valid_series += 1

    return LayerScanResult(
        scanned_feature_count=scanned_feature_count,
        features_with_valid_series=features_with_valid_series,
        features_without_valid_series=features_without_valid_series,
        total_observations=total_observations,
        valid_observations=valid_observations,
        missing_observations=missing_observations,
        invalid_observations=invalid_observations,
        earliest_valid_date=earliest_valid_date,
        latest_valid_date=latest_valid_date,
        truncated=truncated,
    )


def _validate_vector_point_layer(layer: QgsVectorLayer) -> None:
    if layer is None:
        raise LayerValidationError(tr("Nenhuma camada foi fornecida."))

    if not isinstance(layer, QgsVectorLayer):
        raise LayerValidationError(tr("A camada precisa ser uma QgsVectorLayer."))

    if not layer.isValid():
        raise LayerValidationError(tr("A camada vetorial é inválida."))

    if layer.geometryType() != QgsWkbTypes.PointGeometry:
        raise LayerValidationError(tr("A camada precisa possuir geometria de ponto."))


def _build_normalized_field_map(field_names: Iterable[str]) -> dict[str, str]:
    normalized = {}
    duplicates = []

    for field_name in field_names:
        key = field_name.casefold()
        if key in normalized:
            duplicates.append(field_name)
        else:
            normalized[key] = field_name

    if duplicates:
        raise LayerValidationError(
            tr("Há nomes de campos ambíguos quando ignoramos maiúsculas e minúsculas: {fields}", fields=", ".join(duplicates))
        )

    return normalized


def _find_field(normalized_fields: dict[str, str], aliases: Sequence[str]) -> Optional[str]:
    for alias in aliases:
        field_name = normalized_fields.get(alias.casefold())
        if field_name is not None:
            return field_name
    return None


def _detect_component(
    layer_or_normalized_fields: Any,
    normalized_fields: Optional[dict[str, str]] = None,
    component_field: Optional[str] = None,
) -> ComponentDefinition:
    """Detecta a componente InSAR por campo, aliases ou nome de camada.

    A assinatura também aceita o formato histórico interno
    ``_detect_component(normalized_fields)`` para manter compatibilidade com os
    testes unitários existentes enquanto a API pública do leitor evolui.
    """

    if normalized_fields is None and isinstance(layer_or_normalized_fields, dict):
        layer = None
        normalized_fields = layer_or_normalized_fields
    else:
        layer = layer_or_normalized_fields

    if component_field is not None and layer is not None:
        matches = _component_matches_from_values(layer, component_field)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            labels = ", ".join(item.label for item in matches)
            raise LayerValidationError(
                tr("O campo de componente contém valores ambíguos: {labels}.", labels=labels)
            )

    matches = []
    for definition in COMPONENT_DEFINITIONS:
        velocity_field = _find_field(normalized_fields, definition.velocity_field_aliases)
        velocity_std_field = _find_field(normalized_fields, definition.velocity_std_field_aliases)
        if velocity_field is not None or velocity_std_field is not None:
            matches.append(definition)

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        labels = ", ".join(item.label for item in matches)
        raise LayerValidationError(
            tr("A camada contém campos de velocidade compatíveis com mais de uma componente e é ambígua: {labels}.", labels=labels)
        )

    if layer is not None:
        name_matches = [
            definition
            for definition in COMPONENT_DEFINITIONS
            if _text_matches_aliases(layer.name(), definition.name_aliases)
        ]
        if len(name_matches) == 1:
            return name_matches[0]
        if len(name_matches) > 1:
            labels = ", ".join(item.label for item in name_matches)
            raise LayerValidationError(
                tr("O nome da camada sugere mais de uma componente e é ambíguo: {labels}.", labels=labels)
            )

    return UNKNOWN_COMPONENT


def _component_matches_from_values(
    layer: QgsVectorLayer,
    component_field: str,
    max_features: int = 25,
) -> Tuple[ComponentDefinition, ...]:
    matches = []
    seen_keys = set()

    for index, feature in enumerate(layer.getFeatures()):
        if index >= max_features:
            break
        raw_value = _feature_value(feature, component_field)
        if _is_null(raw_value):
            continue
        text = str(raw_value).strip()
        if not text:
            continue
        for definition in COMPONENT_DEFINITIONS:
            if definition.key in seen_keys:
                continue
            if _text_matches_aliases(text, definition.value_aliases):
                matches.append(definition)
                seen_keys.add(definition.key)

    return tuple(matches)


def _text_matches_aliases(text: str, aliases: Sequence[str]) -> bool:
    normalized_text = _normalize_alias_text(text)
    return any(_normalize_alias_text(alias) in normalized_text for alias in aliases)


def _normalize_alias_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def _find_duplicate_dates(date_fields: Sequence[DateField]) -> Tuple[date, ...]:
    seen = set()
    duplicates = []

    for item in date_fields:
        if item.acquisition_date in seen:
            duplicates.append(item.acquisition_date)
        else:
            seen.add(item.acquisition_date)

    return tuple(duplicates)


def _validate_schema_layer(schema: LayerSchema, layer: QgsVectorLayer) -> None:
    if schema.layer_id != layer.id():
        raise LayerValidationError(
            tr("O esquema informado pertence a outra camada. Gere um novo esquema com inspect_layer(layer).")
        )


def _sentinels_for_feature(
    feature: QgsFeature,
    schema: LayerSchema,
    missing_sentinels: Sequence[float],
) -> Tuple[float, ...]:
    values = list(_normalize_sentinels(missing_sentinels))

    if schema.sentinel_field is not None:
        raw_value = _feature_value(feature, schema.sentinel_field)
        numeric_value, status = _coerce_numeric(raw_value, ())
        if status == "valid" and numeric_value is not None:
            values.append(numeric_value)

    return tuple(dict.fromkeys(values))


def _normalize_sentinels(values: Sequence[float]) -> Tuple[float, ...]:
    normalized = []
    for value in values:
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(tr("Sentinela inválido: {value}", value=repr(value))) from exc
        if not math.isfinite(numeric):
            raise ValueError(tr("Sentinela deve ser finito: {value}", value=repr(value)))
        normalized.append(numeric)
    return tuple(normalized)


def _coerce_numeric(
    value: Any,
    sentinels: Sequence[float],
) -> Tuple[Optional[float], str]:
    if _is_null(value):
        return None, "missing"

    if isinstance(value, str):
        value = value.strip()
        if not value or value.casefold() in {"null", "none", "nan", "n/a"}:
            return None, "missing"

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None, "invalid"

    if math.isnan(numeric):
        return None, "missing"

    if math.isinf(numeric):
        return None, "invalid"

    for sentinel in sentinels:
        if math.isclose(numeric, sentinel, rel_tol=0.0, abs_tol=1e-12):
            return None, "missing"

    return numeric, "valid"


def _is_null(value: Any) -> bool:
    if value is None:
        return True

    try:
        if value == NULL:
            return True
    except (TypeError, ValueError):
        pass

    # Compatibilidade defensiva com objetos QVariant eventualmente retornados
    # por provedores diferentes.
    is_null_method = getattr(value, "isNull", None)
    if callable(is_null_method):
        try:
            return bool(is_null_method())
        except Exception:
            return False

    return False


def _feature_value(feature: QgsFeature, field_name: str) -> Any:
    try:
        return feature[field_name]
    except (KeyError, IndexError) as exc:
        raise FeatureReadError(
            tr("A feição não possui o campo esperado: {field}.", field=field_name)
        ) from exc


def _feature_identifier(feature: QgsFeature, schema: LayerSchema) -> str:
    if schema.identifier_field:
        raw_value = _feature_value(feature, schema.identifier_field)
        if not _is_null(raw_value):
            text = str(raw_value).strip()
            if text:
                return text

    return f"FID {feature.id()}"
