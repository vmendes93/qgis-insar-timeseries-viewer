# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unit tests for compact InSAR layer reports."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from insar_timeseries_viewer.i18n import initialize_locale
from insar_timeseries_viewer.layer_report import build_layer_report, format_layer_report


class _Layer:
    def name(self):
        return "Synthetic VERT"

    def featureCount(self):
        return 20

    def crs(self):
        return SimpleNamespace(authid=lambda: "EPSG:31983")


def _date_field(name, acquisition_date):
    return SimpleNamespace(name=name, acquisition_date=acquisition_date)


def _schema():
    return SimpleNamespace(
        component_label="VERT",
        date_fields=(
            _date_field("D20240101", date(2024, 1, 1)),
            _date_field("D20240201", date(2024, 2, 1)),
        ),
        first_acquisition=date(2024, 1, 1),
        last_acquisition=date(2024, 2, 1),
        identifier_field="CODE",
        velocity_field="VEL_V",
        velocity_std_field="V_STDEV_V",
        sentinel_field="NODATA",
        warnings=("ignored date-like field D20241301",),
    )


def test_build_layer_report_collects_schema_and_layer_metadata():
    report = build_layer_report(_Layer(), _schema())

    assert report.layer_name == "Synthetic VERT"
    assert report.feature_count == 20
    assert report.crs_authid == "EPSG:31983"
    assert report.component_label == "VERT"
    assert report.acquisition_count == 2
    assert report.first_temporal_field == "D20240101"
    assert report.last_temporal_field == "D20240201"
    assert report.identifier_field == "CODE"
    assert report.velocity_field == "VEL_V"
    assert report.velocity_std_field == "V_STDEV_V"
    assert report.sentinel_field == "NODATA"
    assert report.warnings == ("ignored date-like field D20241301",)


def test_format_layer_report_is_copyable_plain_text():
    initialize_locale("pt_BR", log=False)
    report = build_layer_report(_Layer(), _schema())

    text = format_layer_report(report)

    assert "Camada: Synthetic VERT" in text
    assert "Pontos: 20" in text
    assert "CRS: EPSG:31983" in text
    assert "Aquisições: 2 (01/01/2024 a 01/02/2024)" in text
    assert "Campos temporais: D20240101 … D20240201" in text
    assert "Avisos: 1" in text
    assert "- ignored date-like field D20241301" in text
