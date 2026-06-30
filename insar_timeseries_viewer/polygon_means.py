# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Cálculo de séries médias independentes para feições poligonais.

Cada polígono define um grupo espacial próprio de pontos da camada InSAR.
Não há associação entre produtos, camadas ou valores de CODE.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
import time
from typing import Optional, Sequence, Tuple

from qgis.core import QgsFeature, QgsFeatureRequest, QgsSpatialIndex, QgsVectorLayer

from .i18n import tr
from .performance import log_performance
from .insar_timeseries_reader import (
    FeatureReadError,
    LayerSchema,
    LayerValidationError,
    read_feature,
)
from .spatial_selection import (
    SpatialSelectionError,
    point_ids_intersecting_polygon,
    polygon_in_target_crs,
)
from .timeseries_statistics import MeanSeriesError, MeanSeriesResult, calculate_mean_series


MAX_POLYGONS_PER_BATCH = 200


class PolygonMeanError(ValueError):
    """Erro de validação ou cálculo de médias por polígonos."""


@dataclass(frozen=True)
class PolygonMeanGroup:
    """Uma feição poligonal e a série média dos pontos que ela contém."""

    polygon_fid: int
    label: str
    point_ids: Tuple[int, ...]
    result: MeanSeriesResult

    @property
    def point_count(self) -> int:
        return len(self.point_ids)


@dataclass(frozen=True)
class PolygonMeanBatchResult:
    """Resultado consolidado de um processamento de múltiplos polígonos."""

    groups: Tuple[PolygonMeanGroup, ...]
    requested_polygon_count: int
    processed_polygon_count: int
    polygons_without_points: Tuple[int, ...]
    polygons_with_errors: Tuple[int, ...]
    error_messages: Tuple[str, ...]
    source_layer_id: str
    source_layer_name: str
    name_field: Optional[str]
    selected_only: bool

    @property
    def group_count(self) -> int:
        return len(self.groups)

    @property
    def skipped_count(self) -> int:
        return len(self.polygons_without_points) + len(self.polygons_with_errors)


def polygon_features_for_scope(
    layer: QgsVectorLayer,
    *,
    selected_only: bool,
) -> list[QgsFeature]:
    """Obtém os polígonos em ordem determinística de FID."""
    if layer is None or not layer.isValid():
        raise PolygonMeanError(tr("Escolha uma camada poligonal válida."))

    if selected_only:
        feature_ids = sorted(int(item) for item in layer.selectedFeatureIds())
        if not feature_ids:
            raise PolygonMeanError(
                tr("Nenhuma feição está selecionada na camada poligonal.")
            )
        request = QgsFeatureRequest().setFilterFids(feature_ids)
        features = list(layer.getFeatures(request))
    else:
        features = list(layer.getFeatures())

    features.sort(key=lambda feature: int(feature.id()))
    if not features:
        raise PolygonMeanError(tr("A camada poligonal não possui feições para processar."))
    if len(features) > MAX_POLYGONS_PER_BATCH:
        raise PolygonMeanError(
            tr(
                "O cálculo solicitado contém {count} polígonos. O limite de segurança desta versão é {limit}; selecione um subconjunto e use 'Somente selecionados'.",
                count=len(features),
                limit=MAX_POLYGONS_PER_BATCH,
            )
        )
    return features


def calculate_polygon_mean_groups(
    *,
    point_layer: QgsVectorLayer,
    point_schema: LayerSchema,
    polygon_layer: QgsVectorLayer,
    polygon_features: Sequence[QgsFeature],
    spatial_index: QgsSpatialIndex,
    name_field: Optional[str],
    common_interval: bool,
    reference_zero: bool,
    selected_only: bool,
    series_cache: Optional[dict[int, object]] = None,
) -> PolygonMeanBatchResult:
    """Calcula uma série média independente para cada polígono fornecido."""
    if point_layer is None or not point_layer.isValid():
        raise PolygonMeanError(tr("A camada pontual InSAR não está disponível."))
    if polygon_layer is None or not polygon_layer.isValid():
        raise PolygonMeanError(tr("A camada poligonal não está disponível."))
    if not polygon_features:
        raise PolygonMeanError(tr("Nenhum polígono foi fornecido para o cálculo."))

    operation_start = time.perf_counter()
    spatial_seconds = 0.0
    read_seconds = 0.0
    statistics_seconds = 0.0
    point_memberships = 0
    cache_hits = 0
    cache_misses = 0
    point_ids_seen = set()

    valid_name_field = _validated_name_field(polygon_layer, name_field)
    if series_cache is None:
        series_cache = {}
    raw_groups = []
    without_points = []
    with_errors = []
    error_messages = []

    for polygon_feature in polygon_features:
        polygon_fid = int(polygon_feature.id())
        try:
            if not polygon_feature.isValid() or not polygon_feature.hasGeometry():
                raise PolygonMeanError(tr("feição sem geometria poligonal válida"))

            spatial_start = time.perf_counter()
            target_geometry = polygon_in_target_crs(
                polygon_feature.geometry(),
                polygon_layer.crs(),
                point_layer,
            )
            point_ids = point_ids_intersecting_polygon(
                point_layer,
                target_geometry,
                spatial_index,
            )
            spatial_seconds += time.perf_counter() - spatial_start
            normalized_point_ids = [int(point_id) for point_id in point_ids]
            point_memberships += len(normalized_point_ids)
            if not normalized_point_ids:
                without_points.append(polygon_fid)
                continue

            for point_id in normalized_point_ids:
                point_ids_seen.add(point_id)

            missing_point_ids = [
                point_id
                for point_id in normalized_point_ids
                if point_id not in series_cache
            ]
            cache_hits += len(normalized_point_ids) - len(missing_point_ids)
            cache_misses += len(missing_point_ids)

            if missing_point_ids:
                read_start = time.perf_counter()
                _read_missing_series(
                    point_layer,
                    point_schema,
                    missing_point_ids,
                    series_cache,
                )
                read_seconds += time.perf_counter() - read_start

            series_list = []
            valid_point_ids = []
            point_errors = []
            for point_id in normalized_point_ids:
                cached = series_cache.get(point_id)
                if isinstance(cached, Exception):
                    point_errors.append(f"FID {point_id}: {cached}")
                else:
                    series_list.append(cached)
                    valid_point_ids.append(point_id)

            if not series_list:
                raise PolygonMeanError(
                    tr("nenhum dos pontos contidos possui série temporal válida")
                )

            statistics_start = time.perf_counter()
            result = calculate_mean_series(
                series_list,
                common_interval=common_interval,
                reference_zero=reference_zero,
                minimum_series=1,
            )
            statistics_seconds += time.perf_counter() - statistics_start
            label = _feature_label(
                polygon_feature,
                valid_name_field,
                result.series_count,
            )
            raw_groups.append(
                PolygonMeanGroup(
                    polygon_fid=polygon_fid,
                    label=label,
                    point_ids=tuple(valid_point_ids),
                    result=result,
                )
            )
            if point_errors:
                error_messages.append(
                    tr("Polígono FID {fid}: {count} ponto(s) ignorado(s) por erro de leitura.", fid=polygon_fid, count=len(point_errors))
                )
        except (PolygonMeanError, SpatialSelectionError, MeanSeriesError) as exc:
            with_errors.append(polygon_fid)
            error_messages.append(tr("Polígono FID {fid}: {error}", fid=polygon_fid, error=exc))
        except Exception as exc:
            with_errors.append(polygon_fid)
            error_messages.append(
                tr("Polígono FID {fid}: {kind}: {error}", fid=polygon_fid, kind=type(exc).__name__, error=exc)
            )

    groups = _disambiguate_labels(raw_groups)
    if not groups:
        if without_points and not with_errors:
            raise PolygonMeanError(
                tr("Nenhum dos polígonos processados contém pontos da camada InSAR.")
            )
        detail = error_messages[0] if error_messages else tr("resultado vazio")
        raise PolygonMeanError(
            tr("Nenhuma média poligonal pôde ser calculada: {detail}", detail=detail)
        )

    log_performance(
        "polygon mean spatial lookup",
        spatial_seconds,
        polygons=len(polygon_features),
        point_memberships=point_memberships,
    )
    log_performance(
        "polygon mean series reads",
        read_seconds,
        unique_points=len(point_ids_seen),
        cache_size=len(series_cache),
        cache_hits=cache_hits,
        cache_misses=cache_misses,
    )
    log_performance(
        "polygon mean statistics",
        statistics_seconds,
        groups=len(groups),
        point_memberships=point_memberships,
    )
    log_performance(
        "polygon mean calculation internal total",
        time.perf_counter() - operation_start,
        groups=len(groups),
        requested_polygons=len(polygon_features),
        point_memberships=point_memberships,
    )

    return PolygonMeanBatchResult(
        groups=tuple(groups),
        requested_polygon_count=len(polygon_features),
        processed_polygon_count=len(polygon_features),
        polygons_without_points=tuple(without_points),
        polygons_with_errors=tuple(with_errors),
        error_messages=tuple(error_messages),
        source_layer_id=polygon_layer.id(),
        source_layer_name=polygon_layer.name(),
        name_field=valid_name_field,
        selected_only=bool(selected_only),
    )


def _read_missing_series(
    point_layer: QgsVectorLayer,
    point_schema: LayerSchema,
    point_ids: Sequence[int],
    series_cache: dict[int, object],
) -> None:
    """Read missing point time series in batches instead of one getFeature call per ID."""

    unique_ids = list(dict.fromkeys(int(point_id) for point_id in point_ids))
    if not unique_ids:
        return

    fetched_ids = set()
    request = QgsFeatureRequest().setFilterFids(unique_ids)
    for point_feature in point_layer.getFeatures(request):
        point_id = int(point_feature.id())
        fetched_ids.add(point_id)
        try:
            series_cache[point_id] = read_feature(
                point_layer,
                point_feature,
                schema=point_schema,
            )
        except (FeatureReadError, LayerValidationError) as exc:
            series_cache[point_id] = exc

    for point_id in unique_ids:
        if point_id not in fetched_ids:
            series_cache[point_id] = FeatureReadError(
                tr("feição inválida ou removida")
            )


def _validated_name_field(
    layer: QgsVectorLayer,
    name_field: Optional[str],
) -> Optional[str]:
    if not name_field:
        return None
    return name_field if layer.fields().indexFromName(name_field) >= 0 else None


def _feature_label(
    feature: QgsFeature,
    name_field: Optional[str],
    point_count: int,
) -> str:
    if name_field:
        try:
            raw_value = feature[name_field]
        except (KeyError, TypeError):
            raw_value = None
        text = _nonempty_text(raw_value)
        if text is not None:
            return text
    noun = tr("ponto") if point_count == 1 else tr("pontos")
    return tr("Média de {count} {noun}", count=point_count, noun=noun)


def _nonempty_text(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.casefold() in {"null", "<null>", "none"}:
        return None
    return text


def _disambiguate_labels(
    groups: Sequence[PolygonMeanGroup],
) -> list[PolygonMeanGroup]:
    counts = Counter(group.label for group in groups)
    return [
        replace(
            group,
            label=(
                f"{group.label} [FID {group.polygon_fid}]"
                if counts[group.label] > 1
                else group.label
            ),
        )
        for group in groups
    ]
