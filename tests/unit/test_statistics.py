from datetime import date
from types import SimpleNamespace

import pytest

from insar_timeseries_viewer.timeseries_statistics import MeanSeriesError, calculate_mean_series


def series(identifier, values, velocity=None, velocity_std=None):
    dates = tuple(date(2024, month, 1) for month in range(1, len(values) + 1))
    return SimpleNamespace(
        identifier=identifier,
        dates=dates,
        values=tuple(values),
        velocity=velocity,
        velocity_std=velocity_std,
    )


def test_common_interval_and_zero_reference():
    result = calculate_mean_series(
        [series("A", [5, 7, 9], 2, 0.2), series("B", [10, 13, 16], 3, 0.4)],
        common_interval=True,
        reference_zero=True,
    )
    assert result.mean_values == (0.0, 2.5, 5.0)
    assert result.counts == (2, 2, 2)
    assert result.mean_velocity == 2.5
    assert result.mean_velocity_std == pytest.approx(0.3)
    assert result.cumulative_displacement == 5.0


def test_union_mode_requires_two_valid_values_per_date():
    result = calculate_mean_series(
        [series("A", [0, 1, None]), series("B", [0, None, 4]), series("C", [0, 3, 6])],
        common_interval=False,
        reference_zero=False,
    )
    assert result.mean_values == (0.0, 2.0, 5.0)
    assert result.counts == (3, 2, 2)
    assert result.count_varies is True


def test_too_few_series_is_rejected():
    with pytest.raises(MeanSeriesError):
        calculate_mean_series([series("A", [0, 1])])
