# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""CSV export helpers for displayed InSAR time-series data."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable, Sequence


CSV_COLUMNS = (
    "record_type",
    "series_label",
    "feature_id",
    "identifier",
    "component",
    "date",
    "displacement_mm",
    "velocity_mm_per_year",
    "velocity_std_mm_per_year",
    "cumulative_displacement_mm",
    "valid_observation_count",
    "missing_observation_count",
    "source_count",
    "std_mm",
    "polygon_fid",
    "polygon_label",
    "point_ids",
)


def series_rows(series, *, label: str | None = None) -> list[dict[str, object]]:
    """Return one CSV row per acquisition of an individual series."""
    series_label = label or getattr(series, "identifier", "")
    rows = []
    for acquisition_date, value in zip(series.dates, series.values):
        rows.append(
            _base_row(
                record_type="series",
                series_label=series_label,
                component=getattr(series, "component_label", ""),
                acquisition_date=acquisition_date,
                displacement=value,
                velocity=getattr(series, "velocity", None),
                velocity_std=getattr(series, "velocity_std", None),
                cumulative=getattr(series, "cumulative_displacement", None),
                valid_count=getattr(series, "valid_count", ""),
                feature_id=getattr(series, "feature_id", ""),
                identifier=getattr(series, "identifier", ""),
                missing_count=getattr(series, "missing_count", ""),
            )
        )
    return rows


def mean_rows(
    result,
    *,
    label: str,
    component_label: str,
    record_type: str = "mean",
    point_ids: Sequence[int] = (),
    polygon_fid: object = "",
    polygon_label: str = "",
) -> list[dict[str, object]]:
    """Return one CSV row per acquisition of a mean time-series result."""
    rows = []
    point_ids_text = ";".join(str(item) for item in point_ids)
    for acquisition_date, value, std_value, count in zip(
        result.dates,
        result.mean_values,
        result.std_values,
        result.counts,
    ):
        row = _base_row(
            record_type=record_type,
            series_label=label,
            component=component_label,
            acquisition_date=acquisition_date,
            displacement=value,
            velocity=getattr(result, "mean_velocity", None),
            velocity_std=getattr(result, "mean_velocity_std", None),
            cumulative=getattr(result, "cumulative_displacement", None),
            valid_count=getattr(result, "valid_count", ""),
            source_count=count,
            std_value=std_value,
            polygon_fid=polygon_fid,
            polygon_label=polygon_label,
            point_ids=point_ids_text,
        )
        rows.append(row)
    return rows


def polygon_group_rows(groups, *, component_label: str) -> list[dict[str, object]]:
    """Return CSV rows for displayed polygon mean groups."""
    rows = []
    for group in groups:
        rows.extend(
            mean_rows(
                group.result,
                label=group.label,
                component_label=component_label,
                record_type="polygon_mean",
                point_ids=group.point_ids,
                polygon_fid=group.polygon_fid,
                polygon_label=group.label,
            )
        )
    return rows


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> int:
    """Write rows to ``path`` and return the number of data rows written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_value(row.get(column)) for column in CSV_COLUMNS})
            row_count += 1
    return row_count


def _base_row(
    *,
    record_type: str,
    series_label: str,
    component: str,
    acquisition_date,
    displacement,
    velocity,
    velocity_std,
    cumulative,
    valid_count,
    feature_id: object = "",
    identifier: object = "",
    missing_count: object = "",
    source_count: object = "",
    std_value: object = "",
    polygon_fid: object = "",
    polygon_label: str = "",
    point_ids: str = "",
) -> dict[str, object]:
    return {
        "record_type": record_type,
        "series_label": series_label,
        "feature_id": feature_id,
        "identifier": identifier,
        "component": component,
        "date": acquisition_date.isoformat(),
        "displacement_mm": displacement,
        "velocity_mm_per_year": velocity,
        "velocity_std_mm_per_year": velocity_std,
        "cumulative_displacement_mm": cumulative,
        "valid_observation_count": valid_count,
        "missing_observation_count": missing_count,
        "source_count": source_count,
        "std_mm": std_value,
        "polygon_fid": polygon_fid,
        "polygon_label": polygon_label,
        "point_ids": point_ids,
    }


def _csv_value(value) -> object:
    if value is None:
        return ""
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value
