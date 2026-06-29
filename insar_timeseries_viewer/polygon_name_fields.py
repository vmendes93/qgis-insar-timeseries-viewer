# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Name-field suggestion helpers for polygon mean labels."""

from __future__ import annotations

from typing import Sequence


NAME_FIELD_PRIORITIES: tuple[str, ...] = (
    "name",
    "nome",
    "code",
    "codigo",
    "código",
    "id",
    "label",
    "title",
    "titulo",
    "setor",
    "sector",
    "area",
    "zona",
    "zone",
)


def suggest_name_field(field_names: Sequence[str]) -> str | None:
    """Suggest the most likely polygon name field."""

    normalized = {str(name).casefold(): str(name) for name in field_names}
    for candidate in NAME_FIELD_PRIORITIES:
        if candidate in normalized:
            return normalized[candidate]

    for candidate in NAME_FIELD_PRIORITIES:
        for field_name in field_names:
            text = str(field_name)
            if candidate in text.casefold():
                return text

    return None
