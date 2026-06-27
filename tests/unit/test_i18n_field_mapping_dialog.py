# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Translation coverage for the field mapping dialog."""

from __future__ import annotations

from insar_timeseries_viewer.i18n import initialize_locale, tr


def test_field_mapping_dialog_strings_translate_to_english():
    initialize_locale("en", log=False)

    assert tr("Configurar campos...") == "Configure fields..."
    assert tr("Configurar campos da camada") == "Configure layer fields"
    assert tr("Identificador:") == "Identifier:"
    assert tr("Campo de componente:") == "Component field:"
    assert tr("Velocidade:") == "Velocity:"
    assert tr("Incerteza da velocidade:") == "Velocity uncertainty:"
    assert tr("Órbita/passagem:") == "Orbit/pass:"
    assert tr("Unidade:") == "Unit:"
    assert tr("Sentinela NoData:") == "NoData sentinel:"
    assert tr("Campos temporais:") == "Temporal fields:"
    assert tr("Limpar mapeamento salvo") == "Clear saved mapping"


def test_temporal_summary_strings_translate_to_english():
    initialize_locale("en", log=False)

    assert (
        tr(
            "{count} campos DYYYYMMDD detectados. "
            "Cobertura: {first_date} a {last_date}. "
            "Campos: {fields}.",
            count=2,
            first_date="01/01/2024",
            last_date="01/02/2024",
            fields="D20240101, D20240201",
        )
        == "2 DYYYYMMDD fields detected. "
        "Coverage: 01/01/2024 to 01/02/2024. "
        "Fields: D20240101, D20240201."
    )

    assert (
        tr(
            "{count} campos DYYYYMMDD detectados. "
            "Cobertura: {first_date} a {last_date}. "
            "Primeiro campo: {first_field}; último campo: {last_field}. "
            "Primeiros: {first_names}. Últimos: {last_names}.",
            count=225,
            first_date="21/06/2019",
            last_date="30/12/2021",
            first_field="D20190621",
            last_field="D20211230",
            first_names="D20190621, D20190702, D20190724",
            last_names="D20211206, D20211217, D20211230",
        )
        == "225 DYYYYMMDD fields detected. "
        "Coverage: 21/06/2019 to 30/12/2021. "
        "First field: D20190621; last field: D20211230. "
        "First: D20190621, D20190702, D20190724. "
        "Last: D20211206, D20211217, D20211230."
    )


def test_manual_temporal_field_dialog_strings_translate_to_english():
    initialize_locale("en", log=False)

    assert tr("Modo dos campos temporais:") == "Temporal field mode:"
    assert (
        tr("Automático: detectar DYYYYMMDD")
        == "Automatic: detect DYYYYMMDD"
    )
    assert tr("Manual: usar tabela abaixo") == "Manual: use table below"
    assert tr("Usar") == "Use"
    assert tr("Campo") == "Field"
    assert tr("Data") == "Date"
    assert (
        tr(
            "No modo manual, marque os campos temporais e ajuste suas datas. "
            "No modo automático, o leitor usa campos DYYYYMMDD."
        )
        == "In manual mode, check temporal fields and adjust their dates. "
        "In automatic mode, the reader uses DYYYYMMDD fields."
    )


def test_temporal_table_ergonomics_strings_translate_to_english():
    initialize_locale("en", log=False)

    assert tr("Filtrar campos...") == "Filter fields..."
    assert tr("Selecionar campos DYYYYMMDD") == "Select DYYYYMMDD fields"
    assert tr("Limpar seleção temporal") == "Clear temporal selection"


def test_point_navigation_strings_translate_to_english():
    initialize_locale("en", log=False)

    assert tr("Aproximar do ponto") == "Zoom to point"
    assert (
        tr("Aproxima o mapa para a feição atualmente exibida no gráfico")
        == "Zooms the map to the feature currently shown in the chart"
    )
    assert tr("Limpar seleção") == "Clear selection"
    assert (
        tr("Remove a seleção atual da camada pontual")
        == "Clears the current selection from the point layer"
    )
    assert (
        tr("Nenhum ponto válido está disponível para aproximar.")
        == "No valid point is available to zoom to."
    )
    assert (
        tr("Mapa aproximado para FID {fid}.", fid=42)
        == "Map zoomed to FID 42."
    )


def test_single_series_title_strings_translate_to_english():
    initialize_locale("en", log=False)

    assert tr("CODE: {identifier}", identifier="TS1") == "CODE: TS1"
    assert tr("VEL: {value}", value="-12.3") == "VEL: -12.3"
    assert (
        tr("Cumulative Displacement: {value}", value="-10.2")
        == "Cumulative Displacement: -10.2"
    )
    assert tr("V_STDEV: {value}", value="0.4") == "V_STDEV: 0.4"
