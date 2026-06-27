# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unit tests for layer mapping serialization."""

from __future__ import annotations

from datetime import date
import json

import pytest

from insar_timeseries_viewer.insar_timeseries_reader import DateField, LayerFieldMapping
from insar_timeseries_viewer.layer_mapping_store import (
    MAPPING_SCHEMA_VERSION,
    LayerMappingStoreError,
    mapping_from_dict,
    mapping_from_json,
    mapping_to_dict,
    mapping_to_json,
)


def _full_mapping() -> LayerFieldMapping:
    return LayerFieldMapping(
        identifier_field="point_name",
        component_key="vertical",
        component_field="component",
        velocity_field="vel_custom",
        velocity_std_field="vel_sigma",
        date_fields=(
            DateField("obs_a", date(2024, 1, 1)),
            DateField("obs_b", date(2024, 2, 1)),
        ),
        orbit_field="orbit_name",
        displacement_unit_field="unit_name",
        sentinel_field="nodata_value",
    )


def test_mapping_to_dict_contains_schema_version():
    data = mapping_to_dict(_full_mapping())

    assert data["schema_version"] == MAPPING_SCHEMA_VERSION
    assert data["identifier_field"] == "point_name"
    assert data["component_key"] == "vertical"
    assert data["date_fields"] == [
        {"name": "obs_a", "acquisition_date": "2024-01-01"},
        {"name": "obs_b", "acquisition_date": "2024-02-01"},
    ]


def test_mapping_dict_roundtrip():
    mapping = _full_mapping()

    restored = mapping_from_dict(mapping_to_dict(mapping))

    assert restored == mapping


def test_mapping_json_roundtrip_is_stable():
    mapping = _full_mapping()

    text = mapping_to_json(mapping)
    restored = mapping_from_json(text)

    assert restored == mapping
    assert json.loads(text)["schema_version"] == MAPPING_SCHEMA_VERSION


def test_empty_mapping_roundtrip():
    mapping = LayerFieldMapping()

    restored = mapping_from_json(mapping_to_json(mapping))

    assert restored == mapping
    assert restored.date_fields is None


def test_mapping_from_dict_rejects_unknown_version():
    data = mapping_to_dict(_full_mapping())
    data["schema_version"] = 999

    with pytest.raises(LayerMappingStoreError):
        mapping_from_dict(data)


def test_mapping_from_dict_rejects_invalid_date_field_payload():
    data = mapping_to_dict(_full_mapping())
    data["date_fields"] = [{"name": "obs_a", "acquisition_date": "not-a-date"}]

    with pytest.raises(LayerMappingStoreError):
        mapping_from_dict(data)


def test_mapping_from_json_rejects_invalid_json():
    with pytest.raises(LayerMappingStoreError):
        mapping_from_json("{bad json")
