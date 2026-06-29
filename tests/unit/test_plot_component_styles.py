from insar_timeseries_viewer.i18n import initialize_locale
from insar_timeseries_viewer.plot_component_styles import (
    component_axis_label,
    component_sign_note,
    style_for_component_key,
    style_for_component_label,
)


def test_component_key_styles_are_distinct_and_generic_fallback():
    assert style_for_component_key("los").primary_color != "black"
    assert style_for_component_key("vertical").primary_color != "black"
    assert style_for_component_key("east_west").primary_color != "black"
    assert style_for_component_key("does_not_exist").primary_color == "black"


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
