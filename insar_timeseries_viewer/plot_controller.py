# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Preparação e renderização dos gráficos Matplotlib."""

from __future__ import annotations

from datetime import date
import math
from typing import Sequence, TYPE_CHECKING

import numpy as np
from matplotlib import rcParams
from matplotlib.dates import (
    AutoDateLocator,
    ConciseDateFormatter,
    DateFormatter,
    DayLocator,
    date2num,
)
from matplotlib.ticker import MultipleLocator

from .i18n import tr
from .plot_component_styles import (
    component_axis_label,
    style_for_component_label,
)
from .plot_settings import PlotSettings
from .timeseries_statistics import MeanSeriesResult

if TYPE_CHECKING:
    from .polygon_means import PolygonMeanGroup


MAX_X_TICKS = 600
MAX_Y_TICKS = 500
_GRID_LINESTYLES = {"solid": "-", "dashed": "--"}


def render_time_series(
    figure,
    series_list: Sequence,
    labels: Sequence[str],
    settings: PlotSettings,
    component_label: str,
) -> list[str]:
    """Desenha uma ou mais séries no mesmo eixo."""
    warnings: list[str] = []
    figure.clear()
    axes = figure.add_subplot(111)
    component_style = style_for_component_label(component_label)

    for index, (series, label) in enumerate(zip(series_list, labels)):
        color = _series_color(index, base_color=component_style.primary_color)
        _plot_one_series(axes, series, label, settings, color=color)
        if _trendline_applies(settings, index):
            if len(series_list) == 1:
                trend_label = _trendline_label_for_series(series)
            else:
                trend_label = f"{tr('Trendline')} — {label}"
            _plot_trendline(
                axes, series.dates, series.values, settings, label=trend_label
            )

    if settings.show_zero_line:
        axes.axhline(0.0, linewidth=0.8, linestyle="--", color="0.35", zorder=0.4)

    if len(series_list) == 1:
        axes.set_title(f"{series_list[0].identifier} — {component_label}")
    else:
        axes.set_title(
            tr(
                "{count} séries — {component}",
                count=len(series_list),
                component=component_label,
            )
        )

    _decorate_axis(
        axes,
        series_list,
        settings,
        warnings,
        add_x_warnings=True,
        component_label=component_label,
    )

    columns = 2 if len(series_list) >= 8 else 1
    _apply_legend(
        axes,
        settings,
        columns=columns,
        suppress_single_series=len(series_list) == 1,
    )

    return _deduplicate(warnings)


def render_separate_time_series(
    figure,
    series_list: Sequence,
    labels: Sequence[str],
    settings: PlotSettings,
    component_label: str,
) -> list[str]:
    """Desenha uma série por eixo, empilhando os gráficos verticalmente."""
    warnings: list[str] = []
    figure.clear()

    axes_grid = figure.subplots(
        nrows=len(series_list),
        ncols=1,
        squeeze=False,
        sharex=True,
    )
    axes_list = [row[0] for row in axes_grid]
    component_style = style_for_component_label(component_label)

    for index, (axes, series, label) in enumerate(
        zip(axes_list, series_list, labels)
    ):
        _plot_one_series(axes, series, label, settings, color=component_style.primary_color)
        if settings.show_trendline:
            _plot_trendline(
                axes, series.dates, series.values, settings, label=tr("Trendline")
            )
        if settings.show_zero_line:
            axes.axhline(
                0.0,
                linewidth=0.8,
                linestyle="--",
                color="0.35",
                zorder=0.4,
            )

        axes.set_title(f"{label} — {component_label}", loc="left", fontsize="medium")
        _decorate_axis(
            axes,
            series_list,
            settings,
            warnings,
            add_x_warnings=index == 0,
        )
        axes.tick_params(axis="x", labelbottom=True)
        _apply_legend(axes, settings)

    return _deduplicate(warnings)


def render_mean_time_series(
    figure,
    result: MeanSeriesResult,
    settings: PlotSettings,
    component_label: str,
) -> list[str]:
    """Desenha a média, sua dispersão e, opcionalmente, as séries de origem."""
    warnings: list[str] = []
    figure.clear()
    axes = figure.add_subplot(111)
    component_style = style_for_component_label(component_label)

    if settings.mean_show_individuals:
        for values in result.individual_values:
            numeric_values = _numeric_values(values)
            axes.plot(
                result.dates,
                numeric_values,
                linestyle="-",
                marker=None,
                linewidth=max(settings.line_width * 0.65, 0.5),
                color="0.60",
                alpha=0.40,
                zorder=1,
            )

    mean_values = _numeric_values(result.mean_values)
    std_values = _numeric_values(result.std_values)

    if settings.mean_show_dispersion:
        lower, upper = _dispersion_bounds(mean_values, std_values)
        axes.fill_between(
            result.dates,
            lower,
            upper,
            color=component_style.primary_color,
            alpha=0.14,
            label=tr("Média ± 1 desvio-padrão"),
            zorder=2,
        )

    line = axes.plot(
        result.dates,
        mean_values,
        label=tr("Média"),
        linestyle="-" if settings.show_lines else "None",
        marker="o" if settings.show_markers else None,
        color=component_style.primary_color,
        markersize=settings.marker_size,
        linewidth=settings.line_width,
        zorder=3,
    )[0]
    _tag_hover(
        line,
        result.dates,
        result.mean_values,
        tr("Média"),
        counts=result.counts,
    )

    if settings.show_trendline:
        _plot_trendline(
            axes, result.dates, result.mean_values, settings, label=tr("Trendline")
        )

    if settings.show_zero_line:
        axes.axhline(0.0, linewidth=0.8, linestyle="--", color="0.35", zorder=0.4)

    axes.set_title(tr("Média de {count} pontos — {component}", count=result.series_count, component=component_label))
    _decorate_axis_for_range(
        axes,
        result.first_valid_date,
        result.last_valid_date,
        settings,
        warnings,
        add_x_warnings=True,
        component_label=component_label,
    )

    _apply_legend(axes, settings)

    return _deduplicate(warnings)


def render_polygon_mean_series(
    figure,
    groups: Sequence[PolygonMeanGroup],
    settings: PlotSettings,
    component_label: str,
) -> list[str]:
    """Desenha uma curva média independente para cada polígono no mesmo eixo."""
    warnings: list[str] = []
    figure.clear()
    axes = figure.add_subplot(111)
    component_style = style_for_component_label(component_label)

    for index, group in enumerate(groups):
        color = _series_color(index, base_color=component_style.primary_color)
        _plot_mean_group(axes, group, settings, label=group.label, color=color)
        if _trendline_applies(settings, index):
            trend_label = (
                tr("Trendline")
                if len(groups) == 1
                else f"{tr('Trendline')} — {group.label}"
            )
            _plot_trendline(
                axes,
                group.result.dates,
                group.result.mean_values,
                settings,
                label=trend_label,
            )

    if settings.show_zero_line:
        axes.axhline(0.0, linewidth=0.8, linestyle="--", color="0.35", zorder=0.4)

    axes.set_title(tr("Médias de {count} polígonos — {component}", count=len(groups), component=component_label))
    x_start = min(group.result.first_valid_date for group in groups)
    x_end = max(group.result.last_valid_date for group in groups)
    _decorate_axis_for_range(
        axes,
        x_start,
        x_end,
        settings,
        warnings,
        add_x_warnings=True,
        component_label=component_label,
    )

    columns = 2 if len(groups) >= 8 else 1
    _apply_legend(axes, settings, columns=columns)

    return _deduplicate(warnings)


def render_separate_polygon_mean_series(
    figure,
    groups: Sequence[PolygonMeanGroup],
    settings: PlotSettings,
    component_label: str,
) -> list[str]:
    """Desenha uma média por polígono em eixos empilhados."""
    warnings: list[str] = []
    figure.clear()

    axes_grid = figure.subplots(
        nrows=len(groups),
        ncols=1,
        squeeze=False,
        sharex=True,
    )
    axes_list = [row[0] for row in axes_grid]
    component_style = style_for_component_label(component_label)
    x_start = min(group.result.first_valid_date for group in groups)
    x_end = max(group.result.last_valid_date for group in groups)

    for index, (axes, group) in enumerate(zip(axes_list, groups)):
        _plot_mean_group(axes, group, settings, label=tr("Média"), color=component_style.primary_color)
        if settings.show_trendline:
            _plot_trendline(
                axes,
                group.result.dates,
                group.result.mean_values,
                settings,
                label=tr("Trendline"),
            )
        if settings.show_zero_line:
            axes.axhline(
                0.0,
                linewidth=0.8,
                linestyle="--",
                color="0.35",
                zorder=0.4,
            )
        noun = tr("ponto") if group.point_count == 1 else tr("pontos")
        if group.label.casefold().startswith(("média de ", "mean of ")):
            title = f"{group.label} — {component_label}"
        else:
            title = (
                f"{group.label} — {tr('média de')} {group.point_count} {noun} — "
                f"{component_label}"
            )
        axes.set_title(title, loc="left", fontsize="medium")
        _decorate_axis_for_range(
            axes,
            x_start,
            x_end,
            settings,
            warnings,
            add_x_warnings=index == 0,
        )
        axes.tick_params(axis="x", labelbottom=True)
        if index < len(groups) - 1:
            axes.set_xlabel("")
        _apply_legend(axes, settings)

    return _deduplicate(warnings)


def _plot_mean_group(
    axes,
    group: PolygonMeanGroup,
    settings: PlotSettings,
    *,
    label: str,
    color: str,
) -> None:
    result = group.result
    mean_values = _numeric_values(result.mean_values)
    std_values = _numeric_values(result.std_values)

    line = axes.plot(
        result.dates,
        mean_values,
        label=label,
        linestyle="-" if settings.show_lines else "None",
        marker="o" if settings.show_markers else None,
        color=color,
        markersize=settings.marker_size,
        linewidth=settings.line_width,
        zorder=3,
    )[0]
    _tag_hover(
        line,
        result.dates,
        result.mean_values,
        group.label,
        counts=result.counts,
    )

    if settings.mean_show_individuals:
        for values in result.individual_values:
            axes.plot(
                result.dates,
                _numeric_values(values),
                linestyle="-",
                marker=None,
                linewidth=max(settings.line_width * 0.55, 0.45),
                color=color,
                alpha=0.16,
                zorder=1,
            )

    if settings.mean_show_dispersion:
        lower, upper = _dispersion_bounds(mean_values, std_values)
        axes.fill_between(
            result.dates,
            lower,
            upper,
            color=color,
            alpha=0.14,
            zorder=2,
        )


def render_message(figure, message: str) -> None:
    figure.clear()
    axes = figure.add_subplot(111)
    axes.set_axis_off()
    axes.text(
        0.5,
        0.5,
        message,
        horizontalalignment="center",
        verticalalignment="center",
        transform=axes.transAxes,
        wrap=True,
    )


def _plot_one_series(
    axes,
    series,
    label: str,
    settings: PlotSettings,
    *,
    color: str,
) -> None:
    values = _numeric_values(series.values)
    line = axes.plot(
        series.dates,
        values,
        label=label,
        linestyle="-" if settings.show_lines else "None",
        marker="o" if settings.show_markers else None,
        color=color,
        markersize=settings.marker_size,
        linewidth=settings.line_width,
        zorder=3,
    )[0]
    _tag_hover(line, series.dates, series.values, label)


def _trendline_label_for_series(series) -> str:
    velocity = getattr(series, "velocity", None)
    if velocity is None:
        return tr("Trendline")

    try:
        numeric_velocity = float(velocity)
    except (TypeError, ValueError):
        return tr("Trendline")

    if not math.isfinite(numeric_velocity):
        return tr("Trendline")

    return tr(
        "Trendline — VEL {value} mm/yr",
        value=f"{numeric_velocity:.1f}",
    )


def _plot_trendline(
    axes, dates, values, settings: PlotSettings, *, label: str = "Trendline"
) -> bool:
    valid = [
        (date2num(item_date), float(item_value))
        for item_date, item_value in zip(dates, values)
        if item_value is not None and math.isfinite(float(item_value))
    ]
    if len(valid) < 2:
        return False

    x_values = np.asarray([item[0] for item in valid], dtype=float)
    y_values = np.asarray([item[1] for item in valid], dtype=float)
    if np.ptp(x_values) <= 0:
        return False

    slope, intercept = np.polyfit(x_values, y_values, 1)
    endpoints = np.asarray([x_values.min(), x_values.max()])
    fitted = slope * endpoints + intercept
    line = axes.plot(
        endpoints,
        fitted,
        color="red",
        linestyle="-",
        linewidth=max(settings.line_width, 1.0),
        alpha=0.95,
        label=label,
        zorder=4,
    )[0]
    line._insar_is_trendline = True
    return True


def _apply_legend(
    axes,
    settings: PlotSettings,
    *,
    columns: int = 1,
    suppress_single_series: bool = False,
) -> None:
    """Aplica legenda normal ou mantém apenas a trendline quando necessário."""
    handles, labels = axes.get_legend_handles_labels()
    if not handles:
        return

    if settings.show_legend and not suppress_single_series:
        axes.legend(handles, labels, fontsize="small", ncol=max(int(columns), 1))
        return

    if settings.show_trendline:
        pairs = _trendline_legend_pairs(handles, labels)
        if pairs:
            trend_handles, trend_labels = zip(*pairs)
            axes.legend(
                trend_handles,
                trend_labels,
                fontsize="small",
                ncol=max(int(columns), 1),
            )


def _trendline_legend_pairs(handles, labels):
    pairs = []
    for handle, label in zip(handles, labels):
        is_trendline = getattr(handle, "_insar_is_trendline", False)
        if is_trendline or str(label).startswith("Trendline"):
            pairs.append((handle, label))
    return pairs


def _trendline_applies(settings: PlotSettings, index: int) -> bool:
    return settings.show_trendline and (
        settings.trendline_scope == "all" or index == 0
    )


def _decorate_axis(
    axes,
    all_series: Sequence,
    settings: PlotSettings,
    warnings: list[str],
    *,
    add_x_warnings: bool,
    component_label: str = "",
) -> None:
    x_start = min(item.first_valid_date for item in all_series)
    x_end = max(item.last_valid_date for item in all_series)
    _decorate_axis_for_range(
        axes,
        x_start,
        x_end,
        settings,
        warnings,
        add_x_warnings=add_x_warnings,
        component_label=component_label,
    )


def _decorate_axis_for_range(
    axes,
    x_start: date,
    x_end: date,
    settings: PlotSettings,
    warnings: list[str],
    *,
    add_x_warnings: bool,
    component_label: str = "",
) -> None:
    axes.set_xlabel(tr("Datas"))
    axes.set_ylabel(component_axis_label(component_label))
    _apply_gridlines(axes, settings)

    if settings.x_manual:
        manual_start = _parse_iso_date(settings.x_start)
        manual_end = _parse_iso_date(settings.x_end)
        if manual_start is None or manual_end is None:
            if add_x_warnings:
                warnings.append(tr("Período X manual ignorado: datas inválidas"))
        elif manual_start > manual_end:
            if add_x_warnings:
                warnings.append(tr("Período X manual ignorado: início posterior ao fim"))
        else:
            x_start, x_end = manual_start, manual_end
            axes.set_xlim(x_start, x_end)

    if settings.x_tick_days > 0:
        estimated_ticks = max((x_end - x_start).days, 0) / settings.x_tick_days + 1
        if estimated_ticks <= MAX_X_TICKS:
            locator = DayLocator(interval=settings.x_tick_days)
            axes.xaxis.set_major_locator(locator)
            axes.xaxis.set_major_formatter(DateFormatter("%d/%m/%Y"))
            axes.tick_params(axis="x", labelrotation=30)
        else:
            if add_x_warnings:
                warnings.append(
                    "Intervalo X ignorado porque geraria mais de "
                    f"{MAX_X_TICKS} ticks"
                )
            _apply_auto_date_axis(axes)
    else:
        _apply_auto_date_axis(axes)

    if settings.y_manual:
        if settings.y_min >= settings.y_max:
            warnings.append(
                tr("Limites Y manuais ignorados: mínimo deve ser menor que máximo")
            )
        else:
            axes.set_ylim(settings.y_min, settings.y_max)

    if settings.y_tick_interval > 0:
        y_min, y_max = axes.get_ylim()
        estimated_ticks = abs(y_max - y_min) / settings.y_tick_interval + 1
        if estimated_ticks <= MAX_Y_TICKS:
            axes.yaxis.set_major_locator(MultipleLocator(settings.y_tick_interval))
        else:
            warnings.append(
                "Intervalo Y ignorado porque geraria mais de "
                f"{MAX_Y_TICKS} ticks"
            )

    _apply_shaded_period(
        axes,
        settings,
        warnings,
        add_warning=add_x_warnings,
    )
    axes.margins(x=0.02, y=0.10)


def _apply_gridlines(axes, settings: PlotSettings) -> None:
    axes.grid(False)
    if settings.show_horizontal_grid:
        axes.yaxis.grid(
            True,
            color="black",
            linestyle=_GRID_LINESTYLES[settings.horizontal_grid_style],
            linewidth=0.55,
            alpha=0.30,
            zorder=0.2,
        )
    if settings.show_vertical_grid:
        axes.xaxis.grid(
            True,
            color="black",
            linestyle=_GRID_LINESTYLES[settings.vertical_grid_style],
            linewidth=0.55,
            alpha=0.30,
            zorder=0.2,
        )


def _apply_shaded_period(
    axes,
    settings: PlotSettings,
    warnings: list[str],
    *,
    add_warning: bool,
) -> None:
    if not settings.show_shaded_period:
        return
    start = _parse_iso_date(settings.shade_start)
    end = _parse_iso_date(settings.shade_end)
    if start is None or end is None:
        if add_warning:
            warnings.append(tr("Sombreamento ignorado: datas inválidas"))
        return
    if start > end:
        if add_warning:
            warnings.append(tr("Sombreamento ignorado: início posterior ao fim"))
        return

    current_xlim = axes.get_xlim()
    axes.axvspan(
        start,
        end,
        facecolor="#858585",
        edgecolor="none",
        alpha=settings.shade_opacity,
        zorder=0.1,
    )
    axes.set_xlim(current_xlim)


def _tag_hover(line, dates, values, label: str, *, counts=None) -> None:
    line._insar_hover_data = {
        "dates": tuple(dates),
        "values": tuple(values),
        "label": str(label),
        "counts": tuple(counts) if counts is not None else None,
    }


def _series_color(index: int, *, base_color: str = "black") -> str:
    if index == 0:
        return base_color
    colors = rcParams["axes.prop_cycle"].by_key().get("color", ["C0"])
    return colors[(index - 1) % len(colors)]


def _numeric_values(values) -> list[float]:
    return [value if value is not None else math.nan for value in values]


def _dispersion_bounds(mean_values, std_values):
    lower = [
        mean - std if math.isfinite(mean) and math.isfinite(std) else math.nan
        for mean, std in zip(mean_values, std_values)
    ]
    upper = [
        mean + std if math.isfinite(mean) and math.isfinite(std) else math.nan
        for mean, std in zip(mean_values, std_values)
    ]
    return lower, upper


def _apply_auto_date_axis(axes) -> None:
    locator = AutoDateLocator(minticks=4, maxticks=9)
    axes.xaxis.set_major_locator(locator)
    axes.xaxis.set_major_formatter(ConciseDateFormatter(locator))


def _parse_iso_date(value: str):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _deduplicate(messages: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(messages))
