# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Detecção e persistência da direção orbital de camadas LOS."""

from __future__ import annotations

import hashlib
import os
import re

from .plot_settings import PROJECT_SCOPE


ORBIT_AUTO = "auto"
ORBIT_ASCENDING = "ascending"
ORBIT_DESCENDING = "descending"
ORBIT_UNSPECIFIED = "unspecified"
VALID_ORBIT_VALUES = {
    ORBIT_AUTO,
    ORBIT_ASCENDING,
    ORBIT_DESCENDING,
    ORBIT_UNSPECIFIED,
}

ORBIT_LABELS = {
    ORBIT_ASCENDING: "ASC",
    ORBIT_DESCENDING: "DESC",
    ORBIT_UNSPECIFIED: "",
}

_ASCENDING_TOKENS = {"A", "ASC", "ASCENDING", "ASCENDENTE"}
_DESCENDING_TOKENS = {"D", "DESC", "DESCENDING", "DESCENDENTE"}


def detect_orbit_direction(*texts: object) -> str:
    """Infere A/D ou ASC/DESC somente a partir de tokens separados."""
    found = set()
    for value in texts:
        if value is None:
            continue
        tokens = {
            token
            for token in re.split(r"[^A-Z0-9]+", str(value).upper())
            if token
        }
        if tokens & _ASCENDING_TOKENS:
            found.add(ORBIT_ASCENDING)
        if tokens & _DESCENDING_TOKENS:
            found.add(ORBIT_DESCENDING)

    if len(found) == 1:
        return found.pop()
    return ORBIT_UNSPECIFIED


def resolve_orbit_direction(layer, override: str = ORBIT_AUTO) -> str:
    """Retorna a direção efetiva para uma camada LOS."""
    if override in {ORBIT_ASCENDING, ORBIT_DESCENDING, ORBIT_UNSPECIFIED}:
        return override

    # O nome exibido da camada tem prioridade. O caminho é consultado apenas
    # quando o nome não contém um token inequívoco, evitando que nomes de
    # pastas como ``A`` ou ``D`` contaminem a detecção.
    detected = detect_orbit_direction(layer.name())
    if detected != ORBIT_UNSPECIFIED:
        return detected

    source = ""
    try:
        source = layer.source().split("|", 1)[0]
    except (AttributeError, RuntimeError):
        pass
    return detect_orbit_direction(os.path.basename(source))


def component_display_label(schema, layer, override: str = ORBIT_AUTO) -> str:
    if schema.component_key != "los":
        return schema.component_label
    direction = resolve_orbit_direction(layer, override)
    suffix = ORBIT_LABELS[direction]
    return f"LOS {suffix}" if suffix else "LOS"


def load_layer_orbit_override(project, layer_id: str) -> str:
    value = project.readEntry(
        PROJECT_SCOPE,
        _orbit_key(layer_id),
        ORBIT_AUTO,
    )[0]
    return value if value in VALID_ORBIT_VALUES else ORBIT_AUTO


def save_layer_orbit_override(project, layer_id: str, value: str) -> None:
    if value not in VALID_ORBIT_VALUES:
        value = ORBIT_AUTO
    project.writeEntry(PROJECT_SCOPE, _orbit_key(layer_id), value)


def _orbit_key(layer_id: str) -> str:
    digest = hashlib.sha1(layer_id.encode("utf-8")).hexdigest()
    return f"/orbitOverrides/layer_{digest}"
