# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Reusable visual presets for time-series plots.

The presets intentionally change only visual and export settings. They do not
change layer field mappings, selected layers, selected features, or date/manual
axis ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_PRESET_ID = "report_ready"
CUSTOM_PRESET_ID = "custom"


@dataclass(frozen=True)
class PlotPreset:
    """Named collection of visual/export settings."""

    identifier: str
    label_pt: str
    label_en: str
    description_pt: str
    settings: dict[str, Any]


PLOT_PRESETS: tuple[PlotPreset, ...] = (
    PlotPreset(
        identifier="report_ready",
        label_pt="Pronto para relatório",
        label_en="Report-ready",
        description_pt=(
            "Figura técnica conservadora, com cabeçalho, marcadores, grade "
            "horizontal e exportação PNG em 300 DPI."
        ),
        settings={
            "show_lines": True,
            "show_markers": True,
            "show_zero_line": True,
            "show_legend": True,
            "show_hover": True,
            "line_width": 1.35,
            "marker_size": 3.2,
            "max_overlay_series": 20,
            "show_trendline": False,
            "trendline_scope": "primary",
            "show_horizontal_grid": True,
            "show_vertical_grid": False,
            "horizontal_grid_style": "dashed",
            "vertical_grid_style": "dashed",
            "mean_show_dispersion": True,
            "mean_show_individuals": False,
            "export_format": "png",
            "export_width_cm": 24.0,
            "export_height_cm": 14.0,
            "export_dpi": 300,
            "export_transparent": False,
            "export_include_header": True,
            "watermark_export": False,
            "watermark_preview": False,
            "watermark_opacity": 0.08,
            "watermark_position": "center",
            "watermark_scale": 0.45,
        },
    ),
    PlotPreset(
        identifier="exploration",
        label_pt="Exploração",
        label_en="Exploration",
        description_pt=(
            "Configuração equilibrada para inspeção interativa dentro do QGIS, "
            "mantendo hover e grades completas."
        ),
        settings={
            "show_lines": True,
            "show_markers": True,
            "show_zero_line": True,
            "show_legend": True,
            "show_hover": True,
            "line_width": 1.15,
            "marker_size": 3.0,
            "max_overlay_series": 30,
            "show_trendline": False,
            "trendline_scope": "primary",
            "show_horizontal_grid": True,
            "show_vertical_grid": True,
            "horizontal_grid_style": "dashed",
            "vertical_grid_style": "dashed",
            "mean_show_dispersion": True,
            "mean_show_individuals": False,
            "export_format": "png",
            "export_width_cm": 24.0,
            "export_height_cm": 14.0,
            "export_dpi": 200,
            "export_transparent": False,
            "export_include_header": True,
            "watermark_export": False,
            "watermark_preview": False,
            "watermark_opacity": 0.08,
            "watermark_position": "center",
            "watermark_scale": 0.45,
        },
    ),
    PlotPreset(
        identifier="dense_overlay",
        label_pt="Sobreposição densa",
        label_en="Dense overlay",
        description_pt=(
            "Reduz espessura, marcadores e legenda para muitos pontos "
            "selecionados no mesmo gráfico."
        ),
        settings={
            "show_lines": True,
            "show_markers": True,
            "show_zero_line": True,
            "show_legend": False,
            "show_hover": True,
            "line_width": 0.80,
            "marker_size": 2.0,
            "max_overlay_series": 80,
            "show_trendline": False,
            "trendline_scope": "primary",
            "show_horizontal_grid": True,
            "show_vertical_grid": False,
            "horizontal_grid_style": "dashed",
            "vertical_grid_style": "dashed",
            "mean_show_dispersion": True,
            "mean_show_individuals": False,
            "export_format": "png",
            "export_width_cm": 28.0,
            "export_height_cm": 16.0,
            "export_dpi": 300,
            "export_transparent": False,
            "export_include_header": True,
            "watermark_export": False,
            "watermark_preview": False,
            "watermark_opacity": 0.08,
            "watermark_position": "center",
            "watermark_scale": 0.45,
        },
    ),
    PlotPreset(
        identifier="presentation",
        label_pt="Apresentação",
        label_en="Presentation",
        description_pt=(
            "Linhas e marcadores maiores para slides, reuniões e leitura em tela."
        ),
        settings={
            "show_lines": True,
            "show_markers": True,
            "show_zero_line": True,
            "show_legend": True,
            "show_hover": True,
            "line_width": 2.0,
            "marker_size": 4.5,
            "max_overlay_series": 20,
            "show_trendline": False,
            "trendline_scope": "primary",
            "show_horizontal_grid": True,
            "show_vertical_grid": False,
            "horizontal_grid_style": "dashed",
            "vertical_grid_style": "dashed",
            "mean_show_dispersion": True,
            "mean_show_individuals": False,
            "export_format": "png",
            "export_width_cm": 28.0,
            "export_height_cm": 16.0,
            "export_dpi": 200,
            "export_transparent": False,
            "export_include_header": True,
            "watermark_export": False,
            "watermark_preview": False,
            "watermark_opacity": 0.08,
            "watermark_position": "center",
            "watermark_scale": 0.45,
        },
    ),
    PlotPreset(
        identifier="minimal",
        label_pt="Mínimo",
        label_en="Minimal",
        description_pt=(
            "Figura limpa para layouts maiores, com menos grade, sem legenda "
            "por padrão e sem cabeçalho exportado."
        ),
        settings={
            "show_lines": True,
            "show_markers": True,
            "show_zero_line": True,
            "show_legend": False,
            "show_hover": True,
            "line_width": 1.0,
            "marker_size": 2.6,
            "max_overlay_series": 20,
            "show_trendline": False,
            "trendline_scope": "primary",
            "show_horizontal_grid": False,
            "show_vertical_grid": False,
            "horizontal_grid_style": "dashed",
            "vertical_grid_style": "dashed",
            "mean_show_dispersion": False,
            "mean_show_individuals": False,
            "export_format": "png",
            "export_width_cm": 20.0,
            "export_height_cm": 12.0,
            "export_dpi": 300,
            "export_transparent": False,
            "export_include_header": False,
            "watermark_export": False,
            "watermark_preview": False,
            "watermark_opacity": 0.08,
            "watermark_position": "center",
            "watermark_scale": 0.45,
        },
    ),
)

PLOT_PRESET_IDS = {preset.identifier for preset in PLOT_PRESETS}
KNOWN_PRESET_IDS = PLOT_PRESET_IDS | {CUSTOM_PRESET_ID}


def available_plot_presets() -> tuple[PlotPreset, ...]:
    """Return presets in UI order."""

    return PLOT_PRESETS


def preset_by_id(identifier: str) -> PlotPreset:
    """Return a preset by identifier."""

    for preset in PLOT_PRESETS:
        if preset.identifier == identifier:
            return preset
    raise ValueError(f"Unknown plot preset: {identifier}")


def apply_plot_preset(settings, identifier: str):
    """Apply a visual/export preset to an existing PlotSettings-like object."""

    preset = preset_by_id(identifier)
    for key, value in preset.settings.items():
        setattr(settings, key, value)
    settings.plot_preset = preset.identifier
    normalizer = getattr(settings, "normalized", None)
    if callable(normalizer):
        normalizer()
    return settings
