# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Cálculos estatísticos para conjuntos de séries temporais InSAR.

Este módulo não conhece camadas QGIS, geometrias ou relações entre produtos.
Ele recebe somente séries já lidas da seleção atual da mesma camada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from statistics import fmean, pstdev
from typing import Optional, Sequence, Tuple
from .i18n import tr


class MeanSeriesError(ValueError):
    """Erro ao preparar a média das séries selecionadas."""


@dataclass(frozen=True)
class MeanSeriesResult:
    """Resultado alinhado da média de várias séries temporais."""

    dates: Tuple[date, ...]
    mean_values: Tuple[Optional[float], ...]
    std_values: Tuple[Optional[float], ...]
    counts: Tuple[int, ...]
    individual_values: Tuple[Tuple[Optional[float], ...], ...]
    series_count: int
    common_interval: bool
    reference_zero: bool
    first_valid_date: date
    last_valid_date: date
    valid_count: int
    mean_velocity: Optional[float]
    mean_velocity_std: Optional[float]
    cumulative_displacement: float

    @property
    def acquisition_count(self) -> int:
        return len(self.dates)

    @property
    def minimum_count(self) -> int:
        valid_counts = [
            count
            for count, value in zip(self.counts, self.mean_values)
            if value is not None
        ]
        return min(valid_counts) if valid_counts else 0

    @property
    def maximum_count(self) -> int:
        valid_counts = [
            count
            for count, value in zip(self.counts, self.mean_values)
            if value is not None
        ]
        return max(valid_counts) if valid_counts else 0

    @property
    def count_varies(self) -> bool:
        return self.minimum_count != self.maximum_count


def calculate_mean_series(
    series_list: Sequence,
    *,
    common_interval: bool = True,
    reference_zero: bool = True,
    minimum_series: int = 2,
) -> MeanSeriesResult:
    """Alinha e calcula a média das séries aquisição por aquisição.

    Quando ``common_interval`` é verdadeiro, a média só existe nas datas em
    que todas as séries possuem valor válido. As datas internas sem cobertura
    completa permanecem como lacunas para não sugerir continuidade artificial.

    Quando é falso, a média usa os valores disponíveis em cada aquisição, mas
    exige no mínimo dois pontos. ``counts`` registra o N efetivamente usado.

    Com ``reference_zero``, cada série é deslocada pelo seu valor de referência
    antes da média. No intervalo comum, todas usam a primeira aquisição válida
    comum. No modo por disponibilidade, cada série usa sua primeira aquisição
    válida própria.
    """

    minimum_series = max(int(minimum_series), 1)
    if len(series_list) < minimum_series:
        if minimum_series == 1:
            raise MeanSeriesError(tr("Nenhuma série válida foi fornecida para a média."))
        raise MeanSeriesError(
            tr("Selecione pelo menos {count} pontos para calcular a média.", count=minimum_series)
        )

    value_maps = []
    complete_date_set = set()
    for series in series_list:
        mapping = {}
        for acquisition_date, raw_value in zip(series.dates, series.values):
            complete_date_set.add(acquisition_date)
            value = _finite_float_or_none(raw_value)
            if value is not None:
                mapping[acquisition_date] = value
        if not mapping:
            raise MeanSeriesError(
                tr("A série {identifier} não possui observações válidas.", identifier=getattr(series, "identifier", tr("sem identificação")))
            )
        value_maps.append(mapping)

    ordered_dates = sorted(complete_date_set)
    if not ordered_dates:
        raise MeanSeriesError(tr("As séries selecionadas não possuem datas de aquisição."))

    if common_interval:
        fully_covered_dates = [
            item_date
            for item_date in ordered_dates
            if all(item_date in mapping for mapping in value_maps)
        ]
        if not fully_covered_dates:
            raise MeanSeriesError(
                tr("Não existe nenhuma aquisição válida comum a todos os pontos selecionados.")
            )
        range_start = fully_covered_dates[0]
        range_end = fully_covered_dates[-1]
        result_dates = [
            item_date
            for item_date in ordered_dates
            if range_start <= item_date <= range_end
        ]
        baseline_dates = [range_start] * len(value_maps)
    else:
        range_start = min(min(mapping) for mapping in value_maps)
        range_end = max(max(mapping) for mapping in value_maps)
        result_dates = [
            item_date
            for item_date in ordered_dates
            if range_start <= item_date <= range_end
        ]
        baseline_dates = [min(mapping) for mapping in value_maps]

    baselines = []
    for mapping, baseline_date in zip(value_maps, baseline_dates):
        baselines.append(mapping[baseline_date] if reference_zero else 0.0)

    individual_rows = []
    for mapping, baseline in zip(value_maps, baselines):
        individual_rows.append(
            tuple(
                mapping[item_date] - baseline if item_date in mapping else None
                for item_date in result_dates
            )
        )

    mean_values = []
    std_values = []
    counts = []
    required_count = (
        len(series_list) if common_interval else min(2, len(series_list))
    )

    for column_index, _item_date in enumerate(result_dates):
        column_values = [
            row[column_index]
            for row in individual_rows
            if row[column_index] is not None
        ]
        count = len(column_values)
        counts.append(count)
        if count < required_count:
            mean_values.append(None)
            std_values.append(None)
            continue

        mean_values.append(fmean(column_values))
        # Dispersão populacional dos pontos efetivamente selecionados na data.
        std_values.append(pstdev(column_values) if count >= 2 else 0.0)

    valid_indexes = [
        index for index, value in enumerate(mean_values) if value is not None
    ]
    if not valid_indexes:
        if common_interval:
            raise MeanSeriesError(
                tr("Não foi possível calcular a média no intervalo comum selecionado.")
            )
        raise MeanSeriesError(
            tr("Não há aquisições com pelo menos dois pontos válidos para calcular a média.")
        )

    first_index = valid_indexes[0]
    last_index = valid_indexes[-1]
    velocities = [
        value
        for value in (_finite_float_or_none(item.velocity) for item in series_list)
        if value is not None
    ]
    velocity_stds = [
        value
        for value in (
            _finite_float_or_none(item.velocity_std) for item in series_list
        )
        if value is not None
    ]

    return MeanSeriesResult(
        dates=tuple(result_dates),
        mean_values=tuple(mean_values),
        std_values=tuple(std_values),
        counts=tuple(counts),
        individual_values=tuple(individual_rows),
        series_count=len(series_list),
        common_interval=bool(common_interval),
        reference_zero=bool(reference_zero),
        first_valid_date=result_dates[first_index],
        last_valid_date=result_dates[last_index],
        valid_count=len(valid_indexes),
        mean_velocity=fmean(velocities) if velocities else None,
        mean_velocity_std=fmean(velocity_stds) if velocity_stds else None,
        cumulative_displacement=float(mean_values[last_index]),
    )


def _finite_float_or_none(value) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None
