# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unit tests for CSV time-series export helpers."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from insar_timeseries_viewer.timeseries_csv_export import (
    CSV_COLUMNS,
    mean_rows,
    polygon_group_rows,
    series_rows,
    write_csv,
)


def _series():
    return SimpleNamespace(
        feature_id=7,
        identifier="P001",
        component_label="LOS ASC",
        velocity=-12.5,
        velocity_std=0.4,
        dates=(date(2024, 1, 1), date(2024, 2, 1)),
        values=(0.0, None),
        cumulative_displacement=-3.2,
        missing_count=1,
        valid_count=1,
    )


def _mean_result():
    return SimpleNamespace(
        dates=(date(2024, 1, 1), date(2024, 2, 1)),
        mean_values=(0.0, -2.0),
        std_values=(0.0, 0.5),
        counts=(3, 2),
        series_count=3,
        mean_velocity=-8.5,
        mean_velocity_std=0.6,
        cumulative_displacement=-2.0,
        valid_count=2,
    )


def test_series_rows_include_all_acquisitions_and_metadata():
    rows = series_rows(_series(), label="Point P001")

    assert len(rows) == 2
    assert tuple(rows[0]) == CSV_COLUMNS
    assert rows[0]["record_type"] == "series"
    assert rows[0]["series_label"] == "Point P001"
    assert rows[0]["feature_id"] == 7
    assert rows[0]["identifier"] == "P001"
    assert rows[0]["date"] == "2024-01-01"
    assert rows[0]["displacement_mm"] == 0.0
    assert rows[1]["displacement_mm"] is None
    assert rows[0]["velocity_mm_per_year"] == -12.5
    assert rows[0]["missing_observation_count"] == 1


def test_mean_rows_include_counts_std_and_point_ids():
    rows = mean_rows(
        _mean_result(),
        label="Mean of 3 points",
        component_label="VERT",
        point_ids=(3, 5, 7),
    )

    assert len(rows) == 2
    assert rows[1]["record_type"] == "mean"
    assert rows[1]["displacement_mm"] == -2.0
    assert rows[1]["source_count"] == 2
    assert rows[1]["std_mm"] == 0.5
    assert rows[1]["point_ids"] == "3;5;7"


def test_polygon_group_rows_mark_polygon_metadata():
    group = SimpleNamespace(
        polygon_fid=12,
        label="Block A",
        point_ids=(1, 2),
        result=_mean_result(),
    )

    rows = polygon_group_rows((group,), component_label="EW")

    assert len(rows) == 2
    assert rows[0]["record_type"] == "polygon_mean"
    assert rows[0]["polygon_fid"] == 12
    assert rows[0]["polygon_label"] == "Block A"
    assert rows[0]["point_ids"] == "1;2"


def test_write_csv_uses_header_and_blank_for_missing_values(tmp_path):
    target = tmp_path / "export.csv"

    written = write_csv(target, series_rows(_series()))

    assert written == 2
    text = target.read_text(encoding="utf-8-sig")
    assert text.splitlines()[0].startswith("record_type,series_label,feature_id")
    assert "2024-02-01," in text
