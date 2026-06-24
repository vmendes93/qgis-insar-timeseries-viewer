from insar_timeseries_viewer.orbit_direction import (
    ORBIT_ASCENDING,
    ORBIT_DESCENDING,
    ORBIT_UNSPECIFIED,
    detect_orbit_direction,
    resolve_orbit_direction,
)


class Layer:
    def __init__(self, name, source=""):
        self._name = name
        self._source = source

    def name(self):
        return self._name

    def source(self):
        return self._source


def test_detect_separated_tokens_only():
    assert detect_orbit_direction("site ASC update") == ORBIT_ASCENDING
    assert detect_orbit_direction("track-DESC") == ORBIT_DESCENDING
    assert detect_orbit_direction("cascade") == ORBIT_UNSPECIFIED
    assert detect_orbit_direction("ASC DESC") == ORBIT_UNSPECIFIED


def test_layer_name_has_priority_over_source_filename():
    layer = Layer("Project ASC", "/tmp/project_DESC.shp")
    assert resolve_orbit_direction(layer) == ORBIT_ASCENDING


def test_source_filename_is_fallback():
    layer = Layer("Project", "/tmp/project_DESC.shp|layerid=0")
    assert resolve_orbit_direction(layer) == ORBIT_DESCENDING
