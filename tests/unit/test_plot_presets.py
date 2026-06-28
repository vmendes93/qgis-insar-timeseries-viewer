from insar_timeseries_viewer.plot_presets import (
    CUSTOM_PRESET_ID,
    DEFAULT_PRESET_ID,
    PLOT_PRESET_IDS,
    apply_plot_preset,
    available_plot_presets,
    preset_by_id,
)
from insar_timeseries_viewer.plot_settings import PlotSettings


def test_preset_ids_are_unique_and_default_exists():
    presets = available_plot_presets()
    identifiers = [preset.identifier for preset in presets]
    assert len(identifiers) == len(set(identifiers))
    assert DEFAULT_PRESET_ID in identifiers
    assert CUSTOM_PRESET_ID not in identifiers
    assert PLOT_PRESET_IDS == set(identifiers)


def test_report_ready_preset_is_public_safe_and_export_ready():
    settings = PlotSettings(
        watermark_export=True,
        watermark_preview=True,
        export_dpi=72,
        show_markers=False,
    )

    apply_plot_preset(settings, "report_ready")

    assert settings.plot_preset == "report_ready"
    assert settings.show_markers is True
    assert settings.watermark_export is False
    assert settings.watermark_preview is False
    assert settings.export_dpi == 300
    assert settings.export_include_header is True


def test_dense_overlay_preset_reduces_clutter_but_keeps_markers():
    settings = PlotSettings()

    apply_plot_preset(settings, "dense_overlay")

    assert settings.show_markers is True
    assert settings.show_legend is False
    assert settings.marker_size < preset_by_id("report_ready").settings["marker_size"]
    assert settings.max_overlay_series > PlotSettings().max_overlay_series


def test_minimal_preset_disables_nonessential_export_header():
    settings = PlotSettings()

    apply_plot_preset(settings, "minimal")

    assert settings.plot_preset == "minimal"
    assert settings.export_include_header is False
    assert settings.show_horizontal_grid is False
    assert settings.show_vertical_grid is False


def test_unknown_preset_raises_value_error():
    settings = PlotSettings()

    try:
        apply_plot_preset(settings, "does_not_exist")
    except ValueError as exc:
        assert "Unknown plot preset" in str(exc)
    else:
        raise AssertionError("Unknown preset did not raise ValueError")
