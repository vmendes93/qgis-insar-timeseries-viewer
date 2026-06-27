from pathlib import Path

import pytest

qgis = pytest.importorskip("qgis")
from qgis.core import QgsApplication, QgsVectorLayer  # noqa: E402

from insar_timeseries_viewer.insar_timeseries_reader import inspect_layer, read_feature  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def qgis_application():
    app = QgsApplication.instance()
    if app is None:
        app = QgsApplication([], False)
        app.initQgis()
    yield app


def test_synthetic_geojson_reader():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_los_points.geojson"
    layer = QgsVectorLayer(str(fixture), "synthetic_los", "ogr")
    assert layer.isValid()
    schema = inspect_layer(layer)
    assert schema.component_key == "los"
    assert schema.acquisition_count == 3

    feature = next(layer.getFeatures())
    data = read_feature(layer, feature, schema)
    assert data.identifier == "P001"
    assert data.valid_count == 3
    assert data.cumulative_displacement == -1.5
