from qgis.core import QgsFeature, QgsVectorLayer, QgsWkbTypes

from insar_timeseries_viewer.insar_timeseries_reader import inspect_layer, read_feature


class Field:
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name


class Layer(QgsVectorLayer):
    def __init__(self, field_names, *, layer_id="layer-1", name="LOS ASC"):
        self._fields = [Field(item) for item in field_names]
        self._id = layer_id
        self._name = name

    def isValid(self):
        return True

    def geometryType(self):
        return QgsWkbTypes.PointGeometry

    def fields(self):
        return self._fields

    def displayField(self):
        return "CODE"

    def id(self):
        return self._id

    def name(self):
        return self._name


class Feature(QgsFeature):
    def __init__(self, feature_id, values):
        self._feature_id = feature_id
        self._values = values

    def isValid(self):
        return True

    def id(self):
        return self._feature_id

    def __getitem__(self, key):
        return self._values[key]


def test_inspect_and_read_feature_end_to_end():
    layer = Layer(
        [
            "CODE",
            "VEL",
            "V_STDEV",
            "D20240301",
            "D20240101",
            "D20240201",
            "HEIGHT",
        ]
    )
    schema = inspect_layer(layer)

    assert schema.component_key == "los"
    assert schema.component_label == "LOS"
    assert schema.identifier_field == "CODE"
    assert [item.name for item in schema.date_fields] == [
        "D20240101",
        "D20240201",
        "D20240301",
    ]
    assert schema.general_fields == ("CODE", "VEL", "V_STDEV", "HEIGHT")

    feature = Feature(
        7,
        {
            "CODE": "P-007",
            "VEL": -12.5,
            "V_STDEV": 0.6,
            "D20240101": 0.0,
            "D20240201": 999.0,
            "D20240301": -2.4,
            "HEIGHT": 650.0,
        },
    )
    result = read_feature(layer, feature, schema)

    assert result.identifier == "P-007"
    assert result.velocity == -12.5
    assert result.velocity_std == 0.6
    assert result.values == (0.0, None, -2.4)
    assert result.valid_values == (0.0, -2.4)
    assert result.missing_count == 1
    assert result.cumulative_displacement == -2.4
