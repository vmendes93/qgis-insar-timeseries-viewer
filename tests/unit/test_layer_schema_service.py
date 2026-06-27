# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Unit tests for layer schema resolution control flow."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from insar_timeseries_viewer.insar_timeseries_reader import (
    LayerFieldMapping,
    LayerValidationError,
)
from insar_timeseries_viewer.layer_mapping_store import LayerMappingStoreError
from insar_timeseries_viewer import layer_schema_service as service
from insar_timeseries_viewer.layer_schema_service import (
    SOURCE_AUTO_DETECTED,
    SOURCE_EXPLICIT_MAPPING,
    SOURCE_SAVED_MAPPING,
    SavedLayerMappingError,
    resolve_layer_schema,
)


class DummyLayer:
    pass


def test_resolve_layer_schema_uses_auto_detection_without_saved_mapping(monkeypatch):
    layer = DummyLayer()
    schema = SimpleNamespace(name="auto")

    monkeypatch.setattr(service, "load_layer_field_mapping", lambda _layer: None)
    monkeypatch.setattr(service, "inspect_layer", lambda _layer: schema)

    result = resolve_layer_schema(layer)

    assert result.schema is schema
    assert result.source == SOURCE_AUTO_DETECTED
    assert result.field_mapping is None


def test_resolve_layer_schema_uses_saved_mapping(monkeypatch):
    layer = DummyLayer()
    mapping = LayerFieldMapping(component_key="los")
    schema = SimpleNamespace(name="saved")

    monkeypatch.setattr(service, "load_layer_field_mapping", lambda _layer: mapping)

    def fake_inspect_layer(_layer, field_mapping=None):
        assert field_mapping is mapping
        return schema

    monkeypatch.setattr(service, "inspect_layer", fake_inspect_layer)

    result = resolve_layer_schema(layer)

    assert result.schema is schema
    assert result.source == SOURCE_SAVED_MAPPING
    assert result.field_mapping is mapping


def test_resolve_layer_schema_explicit_mapping_takes_precedence(monkeypatch):
    layer = DummyLayer()
    explicit_mapping = LayerFieldMapping(component_key="vertical")
    schema = SimpleNamespace(name="explicit")

    def fail_load(_layer):
        raise AssertionError("Saved mapping should not be loaded.")

    def fake_inspect_layer(_layer, field_mapping=None):
        assert field_mapping is explicit_mapping
        return schema

    monkeypatch.setattr(service, "load_layer_field_mapping", fail_load)
    monkeypatch.setattr(service, "inspect_layer", fake_inspect_layer)

    result = resolve_layer_schema(layer, field_mapping=explicit_mapping)

    assert result.schema is schema
    assert result.source == SOURCE_EXPLICIT_MAPPING
    assert result.field_mapping is explicit_mapping


def test_resolve_layer_schema_can_ignore_saved_mapping(monkeypatch):
    layer = DummyLayer()
    schema = SimpleNamespace(name="auto")

    def fail_load(_layer):
        raise AssertionError("Saved mapping should not be loaded.")

    monkeypatch.setattr(service, "load_layer_field_mapping", fail_load)
    monkeypatch.setattr(service, "inspect_layer", lambda _layer: schema)

    result = resolve_layer_schema(layer, use_saved_mapping=False)

    assert result.schema is schema
    assert result.source == SOURCE_AUTO_DETECTED
    assert result.field_mapping is None


def test_resolve_layer_schema_wraps_broken_saved_mapping_json(monkeypatch):
    layer = DummyLayer()

    def broken_load(_layer):
        raise LayerMappingStoreError("broken")

    monkeypatch.setattr(service, "load_layer_field_mapping", broken_load)

    with pytest.raises(SavedLayerMappingError):
        resolve_layer_schema(layer)


def test_resolve_layer_schema_wraps_invalid_saved_mapping(monkeypatch):
    layer = DummyLayer()
    mapping = LayerFieldMapping(component_key="los")

    monkeypatch.setattr(service, "load_layer_field_mapping", lambda _layer: mapping)

    def broken_inspect(_layer, field_mapping=None):
        raise LayerValidationError("bad fields")

    monkeypatch.setattr(service, "inspect_layer", broken_inspect)

    with pytest.raises(SavedLayerMappingError):
        resolve_layer_schema(layer)
