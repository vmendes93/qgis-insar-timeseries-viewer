# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Layer report helpers for the InSAR Time Series Viewer dock."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .i18n import tr


@dataclass(frozen=True)
class LayerReport:
    """Compact diagnostic report for a loaded InSAR point layer."""

    layer_name: str
    feature_count: Optional[int]
    crs_authid: str
    component_label: str
    acquisition_count: int
    first_acquisition: date
    last_acquisition: date
    identifier_field: Optional[str]
    velocity_field: Optional[str]
    velocity_std_field: Optional[str]
    sentinel_field: Optional[str]
    first_temporal_field: str
    last_temporal_field: str
    warnings: tuple[str, ...]


def build_layer_report(layer, schema, *, component_label: Optional[str] = None) -> LayerReport:
    """Build a lightweight report from a QGIS layer and a resolved schema."""
    date_fields = tuple(schema.date_fields)
    return LayerReport(
        layer_name=_safe_layer_name(layer),
        feature_count=_safe_feature_count(layer),
        crs_authid=_safe_crs_authid(layer),
        component_label=component_label or getattr(schema, "component_label", "—"),
        acquisition_count=len(date_fields),
        first_acquisition=schema.first_acquisition,
        last_acquisition=schema.last_acquisition,
        identifier_field=getattr(schema, "identifier_field", None),
        velocity_field=getattr(schema, "velocity_field", None),
        velocity_std_field=getattr(schema, "velocity_std_field", None),
        sentinel_field=getattr(schema, "sentinel_field", None),
        first_temporal_field=date_fields[0].name if date_fields else "—",
        last_temporal_field=date_fields[-1].name if date_fields else "—",
        warnings=tuple(getattr(schema, "warnings", ()) or ()),
    )


def format_layer_report(report: LayerReport) -> str:
    """Return a copyable plain-text report."""
    rows = [
        tr("Camada: {value}", value=report.layer_name),
        tr("Pontos: {value}", value=_format_count(report.feature_count)),
        tr("CRS: {value}", value=report.crs_authid),
        tr("Componente: {value}", value=report.component_label),
        tr(
            "Aquisições: {count} ({start} a {end})",
            count=report.acquisition_count,
            start=f"{report.first_acquisition:%d/%m/%Y}",
            end=f"{report.last_acquisition:%d/%m/%Y}",
        ),
        tr(
            "Campos temporais: {first} … {last}",
            first=report.first_temporal_field,
            last=report.last_temporal_field,
        ),
        tr("Campo identificador: {value}", value=_format_optional(report.identifier_field)),
        tr("Campo VEL: {value}", value=_format_optional(report.velocity_field)),
        tr("Campo V_STDEV: {value}", value=_format_optional(report.velocity_std_field)),
        tr("Campo NoData: {value}", value=_format_optional(report.sentinel_field)),
    ]
    if report.warnings:
        rows.append(tr("Avisos: {count}", count=len(report.warnings)))
        rows.extend(f"- {warning}" for warning in report.warnings)
    else:
        rows.append(tr("Avisos: nenhum"))
    return "\n".join(rows)


def _safe_layer_name(layer) -> str:
    try:
        return str(layer.name())
    except (AttributeError, RuntimeError):
        return "—"


def _safe_feature_count(layer) -> Optional[int]:
    try:
        count = int(layer.featureCount())
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None
    return count if count >= 0 else None


def _safe_crs_authid(layer) -> str:
    try:
        authid = layer.crs().authid()
    except (AttributeError, RuntimeError):
        return "—"
    return str(authid or "—")


def _format_optional(value) -> str:
    text = "" if value is None else str(value)
    return text if text else "—"


def _format_count(value: Optional[int]) -> str:
    return "—" if value is None else str(value)
