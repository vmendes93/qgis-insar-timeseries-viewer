from insar_timeseries_viewer.insar_timeseries_reader import (
    LayerValidationError,
    _build_normalized_field_map,
    _coerce_numeric,
    _detect_component,
    _normalize_sentinels,
)


def test_component_detection():
    mapping = _build_normalized_field_map(["CODE", "VEL_V", "V_STDEV_V", "D20240101"])
    component = _detect_component(mapping)
    assert component.key == "vertical"
    assert component.label == "VERT"


def test_ambiguous_casefolded_fields_are_rejected():
    try:
        _build_normalized_field_map(["VEL", "vel"])
    except LayerValidationError:
        pass
    else:
        raise AssertionError("ambiguous fields should be rejected")


def test_numeric_coercion_and_sentinel_handling():
    sentinels = _normalize_sentinels([999])
    assert _coerce_numeric("1.5", sentinels) == (1.5, "valid")
    assert _coerce_numeric(999, sentinels) == (None, "missing")
    assert _coerce_numeric(float("nan"), sentinels) == (None, "missing")
    assert _coerce_numeric(float("inf"), sentinels) == (None, "invalid")
    assert _coerce_numeric("bad", sentinels) == (None, "invalid")
