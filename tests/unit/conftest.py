"""Minimal stubs for unit tests that do not require a QGIS installation."""

from __future__ import annotations

import sys
import types


def _tr(text: str, **kwargs) -> str:
    return text.format(**kwargs) if kwargs else text


i18n = types.ModuleType("insar_timeseries_viewer.i18n")
i18n.tr = _tr
i18n.initialize_locale = lambda **_kwargs: "en"
i18n.translate_widget_tree = lambda _root: None
sys.modules.setdefault("insar_timeseries_viewer.i18n", i18n)

qgis = types.ModuleType("qgis")
qgis_core = types.ModuleType("qgis.core")


class QgsVectorLayer:
    pass


class QgsFeature:
    pass


class QgsWkbTypes:
    PointGeometry = 0
    LineGeometry = 1
    PolygonGeometry = 2


class _Null:
    def __eq__(self, other):
        return isinstance(other, _Null)


qgis_core.NULL = _Null()
qgis_core.QgsVectorLayer = QgsVectorLayer
qgis_core.QgsFeature = QgsFeature
qgis_core.QgsWkbTypes = QgsWkbTypes
qgis.core = qgis_core
sys.modules.setdefault("qgis", qgis)
sys.modules.setdefault("qgis.core", qgis_core)
