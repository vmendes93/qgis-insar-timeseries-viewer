from insar_timeseries_viewer.plot_presets import DEFAULT_PRESET_ID
from insar_timeseries_viewer.plot_settings import PlotSettings


def test_defaults_are_public_safe():
    settings = PlotSettings()
    assert settings.watermark_export is False
    assert settings.watermark_preview is False
    assert settings.plot_preset == DEFAULT_PRESET_ID


def test_normalization_clamps_invalid_values():
    settings = PlotSettings(
        plot_preset="invalid",
        display_mode="invalid",
        show_lines=False,
        show_markers=False,
        line_width=100,
        marker_size=-1,
        export_format="bmp",
        export_dpi=5000,
        watermark_position="somewhere",
        watermark_opacity=0,
    ).normalized()
    assert settings.plot_preset == DEFAULT_PRESET_ID
    assert settings.display_mode == "single"
    assert settings.show_markers is True
    assert settings.line_width == 10.0
    assert settings.marker_size == 1.0
    assert settings.export_format == "png"
    assert settings.export_dpi == 1200
    assert settings.watermark_position == "center"
    assert settings.watermark_opacity == 0.01
