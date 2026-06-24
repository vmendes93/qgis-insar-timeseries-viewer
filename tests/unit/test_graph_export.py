from pathlib import Path

from insar_timeseries_viewer.graph_export import available_path, ensure_extension, sanitize_filename


def test_filename_sanitization():
    assert sanitize_filename('CODE: A/B*?') == "CODE_A_B"
    assert sanitize_filename('   ') == "grafico_insar"


def test_extension_and_non_overwrite(tmp_path):
    path = ensure_extension(tmp_path / "chart.txt", "png")
    assert path.suffix == ".png"
    path.write_text("x", encoding="utf-8")
    assert available_path(path) == Path(tmp_path / "chart_2.png")
