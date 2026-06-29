from insar_timeseries_viewer.i18n import initialize_locale
from insar_timeseries_viewer.plot_component_styles import (
    component_axis_label,
    component_sign_note,
    style_for_component_key,
    style_for_component_label,
)


def test_component_key_styles_have_generic_fallback():
    assert style_for_component_key("los").component_key == "los"
    assert style_for_component_key("vertical").component_key == "vertical"
    assert style_for_component_key("east_west").component_key == "east_west"
    assert style_for_component_key("does_not_exist").component_key == "unknown"


def test_component_label_inference_handles_los_orbit_suffixes():
    assert style_for_component_label("LOS").component_key == "los"
    assert style_for_component_label("LOS ASC").component_key == "los"
    assert style_for_component_label("LOS DESC").component_key == "los"


def test_component_label_inference_handles_vertical_and_east_west():
    assert style_for_component_label("VERT").component_key == "vertical"
    assert style_for_component_label("Vertical").component_key == "vertical"
    assert style_for_component_label("EW").component_key == "east_west"
    assert style_for_component_label("East-west").component_key == "east_west"


def test_component_axis_labels_default_to_english():
    initialize_locale("en", log=False)
    assert component_axis_label("LOS") == "LOS displacement (mm)"
    assert component_axis_label("VERT") == "Vertical displacement (mm)"
    assert component_axis_label("EW") == "East-west displacement (mm)"


def test_component_axis_labels_translate_to_pt_br():
    initialize_locale("pt_BR", log=False)
    try:
        assert component_axis_label("LOS") == "Deslocamento LOS (mm)"
        assert component_axis_label("VERT") == "Deslocamento vertical (mm)"
        assert component_axis_label("EW") == "Deslocamento leste-oeste (mm)"
        assert "subsidência" in component_sign_note("VERT")
    finally:
        initialize_locale("en", log=False)


def test_component_sign_notes_default_to_english():
    initialize_locale("en", log=False)
    assert component_sign_note("LOS") == "Positive values: toward satellite"
    assert component_sign_note("VERT") == "Negative: subsidence · Positive: uplift"
    assert component_sign_note("EW") == "Negative: westward · Positive: eastward"
    assert component_sign_note("unknown") == ""
