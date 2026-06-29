# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Product/component-specific plot styles.

This module centralizes public, generic visual defaults for InSAR components.
It intentionally does not contain organization-specific branding.
"""

from __future__ import annotations

from dataclasses import dataclass

from .i18n import tr


@dataclass(frozen=True)
class PlotComponentStyle:
    """Visual style for a component family."""

    component_key: str
    primary_color: str
    y_axis_label_source: str
    sign_note_source: str


_GENERIC_STYLE = PlotComponentStyle(
    component_key="unknown",
    primary_color="black",
    y_axis_label_source="Displacement (mm)",
    sign_note_source="",
)

_COMPONENT_STYLES: dict[str, PlotComponentStyle] = {
    "los": PlotComponentStyle(
        component_key="los",
        primary_color="#1f77b4",
        y_axis_label_source="LOS displacement (mm)",
        sign_note_source="Positive values: toward satellite",
    ),
    "vertical": PlotComponentStyle(
        component_key="vertical",
        primary_color="#2ca02c",
        y_axis_label_source="Vertical displacement (mm)",
        sign_note_source="Negative: subsidence · Positive: uplift",
    ),
    "east_west": PlotComponentStyle(
        component_key="east_west",
        primary_color="#9467bd",
        y_axis_label_source="East-west displacement (mm)",
        sign_note_source="Negative: westward · Positive: eastward",
    ),
    "unknown": _GENERIC_STYLE,
}


def style_for_component_key(component_key: object) -> PlotComponentStyle:
    """Return the configured style for a schema component key."""

    key = str(component_key or "").strip().casefold()
    return _COMPONENT_STYLES.get(key, _GENERIC_STYLE)


def style_for_component_label(component_label: object) -> PlotComponentStyle:
    """Infer a style from a displayed component label.

    This keeps the plot controller independent from QGIS layer/schema objects.
    Labels such as ``LOS ASC`` and ``LOS DESC`` still resolve to the LOS style.
    """

    label = str(component_label or "").strip().casefold()
    normalized = label.replace("-", "_").replace(" ", "_")

    if normalized.startswith("los") or "line_of_sight" in normalized:
        return style_for_component_key("los")
    if normalized in {"vert", "vertical", "v"} or "vertical" in normalized:
        return style_for_component_key("vertical")
    if normalized in {"ew", "e_w", "east_west"} or "east_west" in normalized:
        return style_for_component_key("east_west")

    return _GENERIC_STYLE


def component_axis_label(component_label: object) -> str:
    """Return the localized y-axis label for a displayed component."""

    return tr(style_for_component_label(component_label).y_axis_label_source)


def component_sign_note(component_label: object) -> str:
    """Return the localized sign-convention note for a displayed component."""

    source = style_for_component_label(component_label).sign_note_source
    return tr(source) if source else ""
