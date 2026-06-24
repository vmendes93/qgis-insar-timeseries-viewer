# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Configurações de visualização persistidas no projeto QGIS."""

from __future__ import annotations

from dataclasses import dataclass


PROJECT_SCOPE = "VisualizadorSeriesTemporais"
PROJECT_PREFIX = "/plot"


@dataclass
class PlotSettings:
    """Opções usadas pelo renderizador e pela interação do gráfico."""

    display_mode: str = "single"
    show_lines: bool = True
    show_markers: bool = True
    show_zero_line: bool = True
    show_legend: bool = True
    show_hover: bool = True
    line_width: float = 1.15
    marker_size: float = 3.0
    max_overlay_series: int = 20

    show_trendline: bool = False
    trendline_scope: str = "primary"

    show_horizontal_grid: bool = True
    show_vertical_grid: bool = True
    horizontal_grid_style: str = "dashed"
    vertical_grid_style: str = "dashed"

    show_shaded_period: bool = False
    shade_start: str = ""
    shade_end: str = ""
    shade_opacity: float = 0.14

    y_manual: bool = False
    y_min: float = -100.0
    y_max: float = 100.0
    y_tick_interval: float = 0.0
    x_manual: bool = False
    x_start: str = ""
    x_end: str = ""
    x_tick_days: int = 0

    mean_common_interval: bool = True
    mean_reference_zero: bool = True
    mean_show_dispersion: bool = True
    mean_show_individuals: bool = False

    show_additional_properties_panel: bool = True
    export_additional_properties: bool = True

    export_format: str = "png"
    export_width_cm: float = 24.0
    export_height_cm: float = 14.0
    export_dpi: int = 200
    export_transparent: bool = False
    export_include_header: bool = True
    export_last_dir: str = ""

    watermark_export: bool = False
    watermark_preview: bool = False
    watermark_opacity: float = 0.08
    watermark_position: str = "center"
    watermark_scale: float = 0.45

    def normalized(self) -> "PlotSettings":
        """Retorna a própria instância após normalizar opções simples."""
        if self.display_mode not in {
            "single",
            "overlay",
            "separate",
            "mean",
            "polygon_means_overlay",
            "polygon_means_separate",
        }:
            self.display_mode = "single"
        if not self.show_lines and not self.show_markers:
            self.show_markers = True
        self.line_width = min(max(float(self.line_width), 0.1), 10.0)
        self.marker_size = min(max(float(self.marker_size), 1.0), 20.0)
        self.max_overlay_series = min(max(int(self.max_overlay_series), 2), 200)
        if self.trendline_scope not in {"primary", "all"}:
            self.trendline_scope = "primary"
        if self.horizontal_grid_style not in {"solid", "dashed"}:
            self.horizontal_grid_style = "dashed"
        if self.vertical_grid_style not in {"solid", "dashed"}:
            self.vertical_grid_style = "dashed"
        self.shade_opacity = min(max(float(self.shade_opacity), 0.01), 0.80)
        self.y_tick_interval = max(float(self.y_tick_interval), 0.0)
        self.x_tick_days = min(max(int(self.x_tick_days), 0), 3650)
        if self.export_format not in {"png", "svg", "pdf"}:
            self.export_format = "png"
        self.export_width_cm = min(max(float(self.export_width_cm), 8.0), 100.0)
        self.export_height_cm = min(max(float(self.export_height_cm), 6.0), 100.0)
        self.export_dpi = min(max(int(self.export_dpi), 72), 1200)
        self.watermark_opacity = min(max(float(self.watermark_opacity), 0.01), 1.0)
        if self.watermark_position not in {
            "center",
            "lower_right",
            "lower_left",
            "upper_right",
            "upper_left",
        }:
            self.watermark_position = "center"
        self.watermark_scale = min(max(float(self.watermark_scale), 0.10), 1.50)
        return self

    @classmethod
    def load(cls, project) -> "PlotSettings":
        """Lê configurações do projeto atual, usando padrões quando ausentes."""
        defaults = cls()
        settings = cls(
            display_mode=_read_text(project, "display_mode", defaults.display_mode),
            show_lines=_read_bool(project, "show_lines", defaults.show_lines),
            show_markers=_read_bool(project, "show_markers", defaults.show_markers),
            show_zero_line=_read_bool(project, "show_zero_line", defaults.show_zero_line),
            show_legend=_read_bool(project, "show_legend", defaults.show_legend),
            show_hover=_read_bool(project, "show_hover", defaults.show_hover),
            line_width=_read_double(project, "line_width", defaults.line_width),
            marker_size=_read_double(project, "marker_size", defaults.marker_size),
            max_overlay_series=_read_int(
                project, "max_overlay_series", defaults.max_overlay_series
            ),
            show_trendline=_read_bool(
                project, "show_trendline", defaults.show_trendline
            ),
            trendline_scope=_read_text(
                project, "trendline_scope", defaults.trendline_scope
            ),
            show_horizontal_grid=_read_bool(
                project, "show_horizontal_grid", defaults.show_horizontal_grid
            ),
            show_vertical_grid=_read_bool(
                project, "show_vertical_grid", defaults.show_vertical_grid
            ),
            horizontal_grid_style=_read_text(
                project, "horizontal_grid_style", defaults.horizontal_grid_style
            ),
            vertical_grid_style=_read_text(
                project, "vertical_grid_style", defaults.vertical_grid_style
            ),
            show_shaded_period=_read_bool(
                project, "show_shaded_period", defaults.show_shaded_period
            ),
            shade_start=_read_text(project, "shade_start", defaults.shade_start),
            shade_end=_read_text(project, "shade_end", defaults.shade_end),
            shade_opacity=_read_double(
                project, "shade_opacity", defaults.shade_opacity
            ),
            y_manual=_read_bool(project, "y_manual", defaults.y_manual),
            y_min=_read_double(project, "y_min", defaults.y_min),
            y_max=_read_double(project, "y_max", defaults.y_max),
            y_tick_interval=_read_double(
                project, "y_tick_interval", defaults.y_tick_interval
            ),
            x_manual=_read_bool(project, "x_manual", defaults.x_manual),
            x_start=_read_text(project, "x_start", defaults.x_start),
            x_end=_read_text(project, "x_end", defaults.x_end),
            x_tick_days=_read_int(project, "x_tick_days", defaults.x_tick_days),
            mean_common_interval=_read_bool(
                project, "mean_common_interval", defaults.mean_common_interval
            ),
            mean_reference_zero=_read_bool(
                project, "mean_reference_zero", defaults.mean_reference_zero
            ),
            mean_show_dispersion=_read_bool(
                project, "mean_show_dispersion", defaults.mean_show_dispersion
            ),
            mean_show_individuals=_read_bool(
                project, "mean_show_individuals", defaults.mean_show_individuals
            ),
            show_additional_properties_panel=_read_bool(
                project,
                "show_additional_properties_panel",
                defaults.show_additional_properties_panel,
            ),
            export_additional_properties=_read_bool(
                project,
                "export_additional_properties",
                defaults.export_additional_properties,
            ),
            export_format=_read_text(project, "export_format", defaults.export_format),
            export_width_cm=_read_double(
                project, "export_width_cm", defaults.export_width_cm
            ),
            export_height_cm=_read_double(
                project, "export_height_cm", defaults.export_height_cm
            ),
            export_dpi=_read_int(project, "export_dpi", defaults.export_dpi),
            export_transparent=_read_bool(
                project, "export_transparent", defaults.export_transparent
            ),
            export_include_header=_read_bool(
                project, "export_include_header", defaults.export_include_header
            ),
            export_last_dir=_read_text(
                project, "export_last_dir", defaults.export_last_dir
            ),
            watermark_export=_read_bool(
                project, "watermark_export", defaults.watermark_export
            ),
            watermark_preview=_read_bool(
                project, "watermark_preview", defaults.watermark_preview
            ),
            watermark_opacity=_read_double(
                project, "watermark_opacity", defaults.watermark_opacity
            ),
            watermark_position=_read_text(
                project, "watermark_position", defaults.watermark_position
            ),
            watermark_scale=_read_double(
                project, "watermark_scale", defaults.watermark_scale
            ),
        )
        return settings.normalized()

    def save(self, project) -> None:
        """Grava as opções no projeto QGIS atual."""
        self.normalized()
        for key in (
            "show_lines",
            "show_markers",
            "show_zero_line",
            "show_legend",
            "show_hover",
            "show_trendline",
            "show_horizontal_grid",
            "show_vertical_grid",
            "show_shaded_period",
            "y_manual",
            "x_manual",
            "mean_common_interval",
            "mean_reference_zero",
            "mean_show_dispersion",
            "mean_show_individuals",
            "show_additional_properties_panel",
            "export_additional_properties",
            "export_transparent",
            "export_include_header",
            "watermark_export",
            "watermark_preview",
        ):
            _write_bool(project, key, getattr(self, key))

        for key in (
            "line_width",
            "marker_size",
            "shade_opacity",
            "y_min",
            "y_max",
            "y_tick_interval",
            "export_width_cm",
            "export_height_cm",
            "watermark_opacity",
            "watermark_scale",
        ):
            _write_double(project, key, getattr(self, key))

        for key in (
            "display_mode",
            "trendline_scope",
            "horizontal_grid_style",
            "vertical_grid_style",
            "shade_start",
            "shade_end",
            "export_format",
            "export_last_dir",
            "watermark_position",
            "x_start",
            "x_end",
        ):
            project.writeEntry(
                PROJECT_SCOPE,
                f"{PROJECT_PREFIX}/{key}",
                getattr(self, key),
            )

        for key in ("export_dpi", "max_overlay_series", "x_tick_days"):
            project.writeEntry(
                PROJECT_SCOPE,
                f"{PROJECT_PREFIX}/{key}",
                int(getattr(self, key)),
            )


def _read_bool(project, key: str, default: bool) -> bool:
    return project.readBoolEntry(
        PROJECT_SCOPE, f"{PROJECT_PREFIX}/{key}", default
    )[0]


def _read_double(project, key: str, default: float) -> float:
    return project.readDoubleEntry(
        PROJECT_SCOPE, f"{PROJECT_PREFIX}/{key}", default
    )[0]


def _read_int(project, key: str, default: int) -> int:
    return project.readNumEntry(
        PROJECT_SCOPE, f"{PROJECT_PREFIX}/{key}", default
    )[0]


def _read_text(project, key: str, default: str) -> str:
    return project.readEntry(
        PROJECT_SCOPE, f"{PROJECT_PREFIX}/{key}", default
    )[0]


def _write_bool(project, key: str, value: bool) -> None:
    writer = getattr(project, "writeEntryBool", None)
    if writer is not None:
        writer(PROJECT_SCOPE, f"{PROJECT_PREFIX}/{key}", bool(value))
    else:
        project.writeEntry(PROJECT_SCOPE, f"{PROJECT_PREFIX}/{key}", bool(value))


def _write_double(project, key: str, value: float) -> None:
    writer = getattr(project, "writeEntryDouble", None)
    if writer is not None:
        writer(PROJECT_SCOPE, f"{PROJECT_PREFIX}/{key}", float(value))
    else:
        project.writeEntry(PROJECT_SCOPE, f"{PROJECT_PREFIX}/{key}", float(value))
