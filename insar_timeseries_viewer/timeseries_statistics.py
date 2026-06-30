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
from statistics import fmean
from typing import Optional, Sequence, Tuple

import numpy as np

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

    A implementação usa NumPy para reduzir o custo de médias grandes, mantendo
    a mesma interface pública e os mesmos campos do resultado.
    """

    minimum_series = max(int(minimum_series), 1)
    if len(series_list) < minimum_series:
        if minimum_series == 1:
            raise MeanSeriesError(tr("Nenhuma série válida foi fornecida para a média."))
        raise MeanSeriesError(
            tr("Selecione pelo menos {count} pontos para calcular a média.", count=minimum_series)
        )

    ordered_dates = _ordered_dates_for_series(series_list)
    if not ordered_dates:
        raise MeanSeriesError(tr("As séries selecionadas não possuem datas de aquisição."))

    value_matrix = _series_value_matrix(series_list, ordered_dates)

    valid_by_series = ~np.isnan(value_matrix)
    if not np.all(valid_by_series.any(axis=1)):
        invalid_index = int(np.flatnonzero(~valid_by_series.any(axis=1))[0])
        invalid_series = series_list[invalid_index]
        raise MeanSeriesError(
            tr(
                "A série {identifier} não possui observações válidas.",
                identifier=getattr(
                    invalid_series,
                    "identifier",
                    tr("sem identificação"),
                ),
            )
        )

    if common_interval:
        fully_covered_columns = np.flatnonzero(valid_by_series.all(axis=0))
        if fully_covered_columns.size == 0:
            raise MeanSeriesError(
                tr("Não existe nenhuma aquisição válida comum a todos os pontos selecionados.")
            )
        first_column = int(fully_covered_columns[0])
        last_column = int(fully_covered_columns[-1])
        baseline_columns = np.full(len(series_list), first_column, dtype=int)
    else:
        first_valid_columns = np.argmax(valid_by_series, axis=1)
        last_valid_columns = (
            value_matrix.shape[1] - 1 - np.argmax(valid_by_series[:, ::-1], axis=1)
        )
        first_column = int(first_valid_columns.min())
        last_column = int(last_valid_columns.max())
        baseline_columns = first_valid_columns.astype(int)

    result_dates = tuple(ordered_dates[first_column: last_column + 1])
    result_values = value_matrix[:, first_column: last_column + 1].copy()

    if reference_zero:
        baselines = value_matrix[np.arange(len(series_list)), baseline_columns]
        result_values = result_values - baselines[:, np.newaxis]

    counts_array = np.sum(~np.isnan(result_values), axis=0)
    required_count = (
        len(series_list) if common_interval else min(2, len(series_list))
    )
    valid_columns = counts_array >= required_count

    mean_array = np.full(result_values.shape[1], np.nan, dtype=float)
    std_array = np.full(result_values.shape[1], np.nan, dtype=float)
    if np.any(valid_columns):
        with np.errstate(invalid="ignore"):
            mean_array[valid_columns] = np.nanmean(
                result_values[:, valid_columns],
                axis=0,
            )
            std_array[valid_columns] = np.nanstd(
                result_values[:, valid_columns],
                axis=0,
            )

    valid_indexes = np.flatnonzero(~np.isnan(mean_array))
    if valid_indexes.size == 0:
        if common_interval:
            raise MeanSeriesError(
                tr("Não foi possível calcular a média no intervalo comum selecionado.")
            )
        raise MeanSeriesError(
            tr("Não há aquisições com pelo menos dois pontos válidos para calcular a média.")
        )

    mean_values = tuple(_none_if_nan(value) for value in mean_array)
    std_values = tuple(_none_if_nan(value) for value in std_array)
    counts = tuple(int(value) for value in counts_array)
    individual_rows = tuple(
        tuple(_none_if_nan(value) for value in row)
        for row in result_values
    )

    first_index = int(valid_indexes[0])
    last_index = int(valid_indexes[-1])

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
        dates=result_dates,
        mean_values=mean_values,
        std_values=std_values,
        counts=counts,
        individual_values=individual_rows,
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


def _ordered_dates_for_series(series_list: Sequence) -> tuple:
    complete_date_set = set()
    for series in series_list:
        complete_date_set.update(series.dates)
    return tuple(sorted(complete_date_set))


def _series_value_matrix(series_list: Sequence, ordered_dates: Sequence) -> np.ndarray:
    date_index = {item_date: index for index, item_date in enumerate(ordered_dates)}
    matrix = np.full((len(series_list), len(ordered_dates)), np.nan, dtype=float)

    for row_index, series in enumerate(series_list):
        for acquisition_date, raw_value in zip(series.dates, series.values):
            value = _finite_float_or_none(raw_value)
            if value is not None:
                matrix[row_index, date_index[acquisition_date]] = value

    return matrix


def _none_if_nan(value) -> Optional[float]:
    numeric = float(value)
    return None if math.isnan(numeric) else numeric


def _finite_float_or_none(value) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None
