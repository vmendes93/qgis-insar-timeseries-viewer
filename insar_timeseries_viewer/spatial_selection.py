# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Ferramentas de seleção espacial por polígono para o plugin."""

from __future__ import annotations

from typing import Iterable, Optional

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor, QCursor
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsSpatialIndex,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand

from .i18n import tr


SELECTION_REPLACE = "replace"
SELECTION_ADD = "add"
SELECTION_REMOVE = "remove"
VALID_SELECTION_OPERATIONS = {
    SELECTION_REPLACE,
    SELECTION_ADD,
    SELECTION_REMOVE,
}


class SpatialSelectionError(ValueError):
    """Erro de validação ou execução da seleção espacial."""


class PolygonCaptureTool(QgsMapTool):
    """Captura um polígono simples no canvas do QGIS.

    Botão esquerdo adiciona vértices, botão direito conclui e Esc cancela.
    A geometria emitida usa o SRC de destino atual do canvas.
    """

    polygonCompleted = pyqtSignal(object)
    canceled = pyqtSignal()

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self._points = []
        self._rubber_band = QgsRubberBand(
            self.canvas,
            QgsWkbTypes.PolygonGeometry,
        )
        self._configure_rubber_band(self._rubber_band, temporary=True)
        self.setCursor(QCursor(Qt.CrossCursor))

    @staticmethod
    def _configure_rubber_band(rubber_band, *, temporary: bool) -> None:
        stroke = QColor(220, 70, 50, 230 if temporary else 255)
        fill = QColor(220, 70, 50, 55 if temporary else 45)
        try:
            rubber_band.setStrokeColor(stroke)
        except AttributeError:
            rubber_band.setColor(stroke)
        try:
            rubber_band.setFillColor(fill)
        except AttributeError:
            pass
        rubber_band.setWidth(2)

    def activate(self) -> None:
        super().activate()
        self.setCursor(QCursor(Qt.CrossCursor))

    def canvasReleaseEvent(self, event) -> None:
        if event.button() == Qt.RightButton:
            self.finish()
            return
        if event.button() != Qt.LeftButton:
            return

        point = event.mapPoint()
        if not self._points or not self._same_point(self._points[-1], point):
            self._points.append(point)
        self._redraw()

    def canvasMoveEvent(self, event) -> None:
        if not self._points:
            return
        self._redraw(preview_point=event.mapPoint())

    def canvasDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            # O evento de clique precedente normalmente já inseriu o vértice.
            self.finish()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.cancel()
            event.accept()
            return
        super().keyPressEvent(event)

    def finish(self) -> None:
        unique_points = self._unique_points(self._points)
        if len(unique_points) < 3:
            return

        ring = list(unique_points)
        if not self._same_point(ring[0], ring[-1]):
            ring.append(ring[0])
        geometry = QgsGeometry.fromPolygonXY([ring])
        self.reset()
        self.polygonCompleted.emit(geometry)

    def cancel(self) -> None:
        self.reset()
        self.canceled.emit()

    def reset(self) -> None:
        self._points = []
        self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self) -> None:
        had_unfinished_geometry = bool(self._points)
        self.reset()
        super().deactivate()
        if had_unfinished_geometry:
            self.canceled.emit()

    def dispose(self) -> None:
        self.reset()
        try:
            self.canvas.scene().removeItem(self._rubber_band)
        except (AttributeError, RuntimeError):
            pass
        self._rubber_band = None

    def _redraw(self, preview_point=None) -> None:
        if self._rubber_band is None:
            return
        points = list(self._points)
        if preview_point is not None:
            if not points or not self._same_point(points[-1], preview_point):
                points.append(preview_point)

        self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        for index, point in enumerate(points):
            self._rubber_band.addPoint(point, index == len(points) - 1)
        self._rubber_band.show()

    @staticmethod
    def _same_point(first, second) -> bool:
        return first.x() == second.x() and first.y() == second.y()

    @classmethod
    def _unique_points(cls, points):
        unique = []
        for point in points:
            if not any(cls._same_point(point, existing) for existing in unique):
                unique.append(point)
        return unique


def configure_persistent_rubber_band(rubber_band: QgsRubberBand) -> None:
    """Aplica a aparência da última área concluída."""
    PolygonCaptureTool._configure_rubber_band(rubber_band, temporary=False)


def validate_polygon_geometry(geometry: QgsGeometry) -> QgsGeometry:
    """Retorna uma cópia poligonal válida ou lança erro compreensível."""
    if geometry is None or geometry.isEmpty():
        raise SpatialSelectionError(tr("O polígono está vazio."))

    result = QgsGeometry(geometry)
    if QgsWkbTypes.geometryType(result.wkbType()) != QgsWkbTypes.PolygonGeometry:
        raise SpatialSelectionError(tr("A geometria fornecida não é poligonal."))

    try:
        is_valid = result.isGeosValid()
    except Exception:
        is_valid = True

    if not is_valid:
        try:
            repaired = result.makeValid()
        except Exception as exc:
            raise SpatialSelectionError(
                tr("O polígono é inválido e não pôde ser reparado: {error}", error=exc)
            ) from exc
        if (
            repaired is None
            or repaired.isEmpty()
            or QgsWkbTypes.geometryType(repaired.wkbType())
            != QgsWkbTypes.PolygonGeometry
        ):
            raise SpatialSelectionError(
                tr("O polígono é inválido e o reparo não produziu uma área poligonal.")
            )
        result = repaired

    return result


def polygon_in_target_crs(
    geometry: QgsGeometry,
    source_crs: QgsCoordinateReferenceSystem,
    target_layer: QgsVectorLayer,
    project: Optional[QgsProject] = None,
) -> QgsGeometry:
    """Valida e transforma o polígono para o SRC da camada de pontos."""
    result = validate_polygon_geometry(geometry)
    target_crs = target_layer.crs()

    if source_crs is None or not source_crs.isValid():
        raise SpatialSelectionError(tr("O SRC de origem do polígono não é válido."))
    if target_crs is None or not target_crs.isValid():
        raise SpatialSelectionError(tr("O SRC da camada de pontos não é válido."))

    if source_crs != target_crs:
        try:
            transform = QgsCoordinateTransform(
                source_crs,
                target_crs,
                project or QgsProject.instance(),
            )
            result.transform(transform)
        except (QgsCsException, RuntimeError, ValueError) as exc:
            raise SpatialSelectionError(
                tr("Não foi possível reprojetar o polígono para a camada de pontos: {error}", error=exc)
            ) from exc

    return validate_polygon_geometry(result)


def build_point_spatial_index(layer: QgsVectorLayer) -> QgsSpatialIndex:
    """Constrói um índice espacial sem solicitar atributos desnecessários."""
    request = QgsFeatureRequest().setNoAttributes()
    return QgsSpatialIndex(layer.getFeatures(request))


def point_ids_intersecting_polygon(
    layer: QgsVectorLayer,
    polygon: QgsGeometry,
    spatial_index: QgsSpatialIndex,
) -> list[int]:
    """Retorna IDs dos pontos que intersectam a área, incluindo a borda."""
    if layer is None or not layer.isValid():
        raise SpatialSelectionError(tr("A camada de pontos não está disponível."))
    if layer.geometryType() != QgsWkbTypes.PointGeometry:
        raise SpatialSelectionError(tr("A camada de destino não é pontual."))

    area = validate_polygon_geometry(polygon)
    candidate_ids = spatial_index.intersects(area.boundingBox())
    if not candidate_ids:
        return []

    request = QgsFeatureRequest().setFilterFids(candidate_ids).setNoAttributes()
    matching_ids = []
    for feature in layer.getFeatures(request):
        if not feature.hasGeometry():
            continue
        feature_geometry = feature.geometry()
        if feature_geometry is None or feature_geometry.isEmpty():
            continue
        if area.intersects(feature_geometry):
            matching_ids.append(int(feature.id()))
    return sorted(matching_ids)


def resulting_selection_ids(
    current_ids: Iterable[int],
    area_ids: Iterable[int],
    operation: str,
) -> list[int]:
    """Calcula a seleção final sem depender dos enums de seleção do QGIS."""
    if operation not in VALID_SELECTION_OPERATIONS:
        raise SpatialSelectionError(tr("Operação de seleção desconhecida: {operation}", operation=operation))

    current = {int(item) for item in current_ids}
    found = {int(item) for item in area_ids}
    if operation == SELECTION_REPLACE:
        result = found
    elif operation == SELECTION_ADD:
        result = current | found
    else:
        result = current - found
    return sorted(result)
