# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Seleção, resumo e formatação de propriedades adicionais das feições.

O módulo não depende do QGIS. Ele recebe valores já extraídos das feições e
produz textos compactos para o painel e para os cabeçalhos exportados.
"""

from __future__ import annotations

from statistics import fmean
import math
from typing import Iterable, Optional, Sequence
from .i18n import tr


NULL_TEXTS = {"", "null", "<null>", "none", "nan", "na", "n/a"}


def property_field_candidates(schema) -> tuple[str, ...]:
    """Retorna campos gerais elegíveis, preservando a ordem da camada."""
    excluded = {
        item.casefold()
        for item in (
            schema.identifier_field,
            schema.velocity_field,
            schema.velocity_std_field,
        )
        if item
    }
    return tuple(
        field_name
        for field_name in schema.general_fields
        if field_name.casefold() not in excluded
    )


def summarize_values(values: Iterable, mode: str = "range") -> str:
    """Resume valores como valor único, média ou intervalo.

    ``mode`` pode ser:
    - ``single``: primeiro valor não nulo;
    - ``mean``: média para valores numéricos;
    - ``range``: mínimo–máximo para valores numéricos.

    Campos textuais mantêm o único valor quando todos concordam e retornam
    ``Vários valores`` quando há diversidade.
    """
    cleaned = [_clean_value(value) for value in values]
    cleaned = [value for value in cleaned if value is not None]
    if not cleaned:
        return "—"

    numeric = [_finite_number(value) for value in cleaned]
    if all(value is not None for value in numeric):
        numbers = [float(value) for value in numeric]
        if mode == "single":
            return format_number(numbers[0])
        if mode == "mean":
            return format_number(fmean(numbers))
        low = min(numbers)
        high = max(numbers)
        if math.isclose(low, high, rel_tol=1e-12, abs_tol=1e-12):
            return format_number(low)
        return f"{format_number(low)}–{format_number(high)}"

    texts = [str(value).strip() for value in cleaned]
    unique = list(dict.fromkeys(texts))
    if len(unique) == 1:
        return unique[0]
    if mode == "single":
        return unique[0]
    return tr("Vários valores")


def summarize_group_means(groups: Sequence[Sequence], mode: str = "range") -> str:
    """Resume médias numéricas de grupos independentes.

    Usado em médias por vários polígonos: cada polígono fornece uma média e o
    painel geral mostra o intervalo entre essas médias. Para campos textuais,
    cai no resumo normal dos valores de todos os grupos.
    """
    if not groups:
        return "—"

    group_numbers = []
    all_values = []
    numeric_groups = True
    for group in groups:
        cleaned = [_clean_value(value) for value in group]
        cleaned = [value for value in cleaned if value is not None]
        all_values.extend(cleaned)
        numbers = [_finite_number(value) for value in cleaned]
        if not cleaned or not all(value is not None for value in numbers):
            numeric_groups = False
            continue
        group_numbers.append(fmean(float(value) for value in numbers))

    if numeric_groups and group_numbers:
        return summarize_values(group_numbers, mode=mode)
    return summarize_values(all_values, mode="range")


def format_number(value: float) -> str:
    """Formata número sem zeros decimais desnecessários."""
    numeric = float(value)
    if math.isclose(numeric, round(numeric), abs_tol=1e-10):
        return str(int(round(numeric)))
    magnitude = abs(numeric)
    if magnitude >= 10000 or (0 < magnitude < 0.001):
        return f"{numeric:.4g}"
    return f"{numeric:.4f}".rstrip("0").rstrip(".")


def _clean_value(value):
    if value is None:
        return None
    text = str(value).strip()
    if text.casefold() in NULL_TEXTS:
        return None
    return value


def _finite_number(value) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None
