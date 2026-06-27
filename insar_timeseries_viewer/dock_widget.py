# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Painel acoplável do visualizador de séries temporais InSAR."""

from __future__ import annotations

from collections import Counter
from datetime import date
import html
import json
import math
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from qgis.PyQt.QtCore import QDate, QTimer, Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel as _QtQLabel,
    QMessageBox,
    QLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    QgsCoordinateTransform,
    QgsCsException,
    QgsGeometry,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsRubberBand

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:  # compatibilidade com instalações Matplotlib mais antigas
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.dates import date2num
from matplotlib.figure import Figure

from .field_mapping_dialog import FieldMappingDialog
from .i18n import tr, translate_widget_tree
from .insar_timeseries_reader import (
    FeatureReadError,
    LayerSchema,
    LayerValidationError,
    TimeSeriesData,
    read_feature,
)
from .layer_mapping_store import (
    LayerMappingStoreError,
    clear_layer_field_mapping,
    load_layer_field_mapping,
    save_layer_field_mapping,
)
from .layer_schema_service import SavedLayerMappingError, resolve_layer_schema
from .orbit_direction import (
    ORBIT_ASCENDING,
    ORBIT_AUTO,
    ORBIT_DESCENDING,
    ORBIT_UNSPECIFIED,
    component_display_label,
    load_layer_orbit_override,
    save_layer_orbit_override,
)
from .plot_controller import (
    render_mean_time_series,
    render_message,
    render_polygon_mean_series,
    render_separate_polygon_mean_series,
    render_separate_time_series,
    render_time_series,
)
from .plot_settings import PlotSettings, PROJECT_SCOPE
from .additional_properties import (
    property_field_candidates,
    summarize_group_means,
    summarize_values,
)
from .graph_export import (
    add_export_header,
    apply_watermark,
    available_path,
    ensure_extension,
    sanitize_filename,
    save_figure,
)
from .timeseries_statistics import (
    MeanSeriesError,
    MeanSeriesResult,
    calculate_mean_series,
)
from .polygon_means import (
    PolygonMeanBatchResult,
    PolygonMeanError,
    calculate_polygon_mean_groups,
    polygon_features_for_scope,
)
from .spatial_selection import (
    PolygonCaptureTool,
    SELECTION_ADD,
    SELECTION_REMOVE,
    SELECTION_REPLACE,
    SpatialSelectionError,
    build_point_spatial_index,
    configure_persistent_rubber_band,
    point_ids_intersecting_polygon,
    polygon_in_target_crs,
    resulting_selection_ids,
)


class QLabel(_QtQLabel):
    """QLabel that translates plugin-owned text at assignment time."""

    def __init__(self, text="", parent=None, *args, **kwargs):
        super().__init__(tr(text), parent, *args, **kwargs)

    def setText(self, text) -> None:
        super().setText(tr(text))


UI_SETTINGS_VISIBLE_KEY = "/ui/settings_panel_visible"
UI_SETTINGS_WIDTH_KEY = "/ui/settings_panel_width"
DEFAULT_SETTINGS_PANEL_WIDTH = 330
ADDITIONAL_FIELDS_PREFIX = "/additional_fields"


class TimeSeriesDockWidget(QDockWidget):
    """Mostra uma ou várias séries da seleção da camada escolhida."""

    def __init__(self, iface, parent=None):
        super().__init__(tr("Séries Temporais InSAR"), parent)
        self.setObjectName("insarTimeSeriesViewerDockWidget")
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.iface = iface
        self.project = QgsProject.instance()
        self.settings = PlotSettings.load(self.project)
        self.current_layer: Optional[QgsVectorLayer] = None
        self.current_schema: Optional[LayerSchema] = None
        self.current_feature_id: Optional[int] = None
        self.current_orbit_override = ORBIT_AUTO
        self._refreshing_layers = False
        self._updating_controls = False
        self._settings_panel_visible = True
        self._settings_panel_width = DEFAULT_SETTINGS_PANEL_WIDTH
        self._polygon_capture_tool = None
        self._previous_map_tool = None
        self._area_rubber_band = None
        self._active_feature_rubber_band = None
        self._has_displayed_area = False
        self._point_spatial_index = None
        self._polygon_mean_batch: Optional[PolygonMeanBatchResult] = None
        self._displayed_mode: Optional[str] = None
        self._displayed_series: list[TimeSeriesData] = []
        self._displayed_labels: list[str] = []
        self._displayed_mean_result: Optional[MeanSeriesResult] = None
        self._displayed_mean_source_series: list[TimeSeriesData] = []
        self._displayed_polygon_groups = []
        self._additional_field_checks: dict[str, QCheckBox] = {}

        self._build_ui()
        self._connect_global_signals()
        self.refresh_layers()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(6, 6, 6, 6)
        container_layout.setSpacing(6)

        self._build_header_controls(container_layout)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("insarTimeSeriesViewerSplitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        self.visualization_panel = QWidget()
        self.settings_panel = QFrame()
        self.settings_panel.setFrameShape(QFrame.StyledPanel)
        self.settings_panel.setMinimumWidth(280)
        self.settings_panel.setMaximumWidth(460)

        self._build_visualization_panel()
        self._build_settings_panel()

        self.splitter.addWidget(self.visualization_panel)
        self.splitter.addWidget(self.settings_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        container_layout.addWidget(self.splitter, 1)

        self.setWidget(container)
        self.resize(1080, 680)
        self._load_ui_state()
        self._sync_controls_from_settings()
        self._clear_feature_info()
        translate_widget_tree(self)
        self._show_plot_message(tr("Selecione uma camada InSAR compatível."))
        QTimer.singleShot(0, self._restore_splitter_sizes)

    def _build_header_controls(self, parent_layout: QVBoxLayout) -> None:
        layer_row = QHBoxLayout()
        layer_row.addWidget(QLabel("Camada:"))
        self.layer_combo = QComboBox()
        self.layer_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layer_combo.currentIndexChanged.connect(self._on_layer_combo_changed)
        layer_row.addWidget(self.layer_combo, 1)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setToolTip("Atualizar a lista de camadas compatíveis")
        self.refresh_button.clicked.connect(self.refresh_layers)
        layer_row.addWidget(self.refresh_button)

        self.configure_fields_button = QPushButton("Configurar campos...")
        self.configure_fields_button.setToolTip(
            "Configurar mapeamento manual dos campos da camada"
        )
        self.configure_fields_button.clicked.connect(self._configure_layer_fields)
        layer_row.addWidget(self.configure_fields_button)

        parent_layout.addLayout(layer_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Modo:"))
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItem("Série única", "single")
        self.display_mode_combo.addItem("Séries sobrepostas", "overlay")
        self.display_mode_combo.addItem("Séries separadas", "separate")
        self.display_mode_combo.addItem("Média das séries", "mean")
        self.display_mode_combo.addItem(
            "Médias por polígonos — sobrepostas", "polygon_means_overlay"
        )
        self.display_mode_combo.addItem(
            "Médias por polígonos — separadas", "polygon_means_separate"
        )
        self.display_mode_combo.currentIndexChanged.connect(
            self._on_plot_settings_changed
        )
        mode_row.addWidget(self.display_mode_combo)
        mode_row.addStretch(1)
        self.selection_count_label = QLabel("0 selecionadas")
        mode_row.addWidget(self.selection_count_label)

        self.zoom_feature_button = QPushButton("Aproximar do ponto")
        self.zoom_feature_button.setToolTip(
            "Aproxima o mapa para a feição atualmente exibida no gráfico"
        )
        self.zoom_feature_button.setEnabled(False)
        self.zoom_feature_button.clicked.connect(self._zoom_to_current_feature)
        mode_row.addWidget(self.zoom_feature_button)

        self.clear_selection_button = QPushButton("Limpar seleção")
        self.clear_selection_button.setToolTip(
            "Remove a seleção atual da camada pontual"
        )
        self.clear_selection_button.setEnabled(False)
        self.clear_selection_button.clicked.connect(self._clear_current_selection)
        mode_row.addWidget(self.clear_selection_button)

        self.settings_toggle_button = QToolButton()
        self.settings_toggle_button.setText("Configurações")
        self.settings_toggle_button.setToolTip(
            "Mostrar ou ocultar as configurações ao lado do gráfico"
        )
        self.settings_toggle_button.setCheckable(True)
        self.settings_toggle_button.setChecked(True)
        self.settings_toggle_button.toggled.connect(
            self._on_settings_panel_toggled
        )
        mode_row.addWidget(self.settings_toggle_button)
        parent_layout.addLayout(mode_row)

        self.layer_info = QLabel("Nenhuma camada compatível selecionada.")
        self.layer_info.setWordWrap(True)
        parent_layout.addWidget(self.layer_info)

    def _build_visualization_panel(self) -> None:
        main_layout = QVBoxLayout(self.visualization_panel)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(8)

        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(12)
        info_grid.setVerticalSpacing(3)

        self.value_identifier = self._value_label()
        self.value_component = self._value_label()
        self.value_velocity = self._value_label()
        self.value_velocity_std = self._value_label()
        self.value_cumulative = self._value_label()
        self.value_coverage = self._value_label()
        self.value_additional_properties = self._value_label()
        self.value_additional_properties.setWordWrap(True)

        self.caption_identifier = QLabel("Ponto/série:")
        self.caption_component = QLabel("Componente:")
        self.caption_velocity = QLabel("VEL:")
        self.caption_velocity_std = QLabel("V_STDEV:")
        self.caption_cumulative = QLabel("Desloc. acumulado:")
        self.caption_coverage = QLabel("Cobertura válida:")
        self.caption_additional_properties = QLabel("Propriedades adicionais:")
        self.caption_additional_properties.setAlignment(Qt.AlignRight | Qt.AlignTop)
        rows = (
            (self.caption_identifier, self.value_identifier),
            (self.caption_component, self.value_component),
            (self.caption_velocity, self.value_velocity),
            (self.caption_velocity_std, self.value_velocity_std),
            (self.caption_cumulative, self.value_cumulative),
            (self.caption_coverage, self.value_coverage),
            (self.caption_additional_properties, self.value_additional_properties),
        )
        for row, (caption_widget, value_widget) in enumerate(rows):
            caption_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            info_grid.addWidget(caption_widget, row, 0)
            info_grid.addWidget(value_widget, row, 1)
        info_grid.setColumnStretch(1, 1)
        main_layout.addLayout(info_grid)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        self.figure = Figure(figsize=(7.0, 4.5), dpi=100, constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(280)
        self.canvas.setMinimumWidth(420)
        self._hover_connection_id = self.canvas.mpl_connect(
            "motion_notify_event", self._on_canvas_hover
        )

        # O contêiner rolável permite empilhar vários subgráficos sem reduzir
        # cada um a uma faixa ilegível. Nos modos único/sobreposto ele se
        # comporta como uma área de gráfico comum.
        self.chart_scroll_area = QScrollArea()
        self.chart_scroll_area.setFrameShape(QFrame.NoFrame)
        self.chart_scroll_area.setWidgetResizable(True)
        self.chart_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chart_container = QWidget()
        chart_layout = QVBoxLayout(self.chart_container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        chart_layout.setSpacing(0)
        chart_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        chart_layout.addWidget(self.canvas)
        self.chart_scroll_area.setWidget(self.chart_container)
        main_layout.addWidget(self.chart_scroll_area, 1)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(self.status_label)

    def _build_settings_panel(self) -> None:
        outer_layout = QVBoxLayout(self.settings_panel)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 6, 6)
        header_label = QLabel("Configurações do gráfico")
        header_label.setStyleSheet("font-weight: 600;")
        header_layout.addWidget(header_label)
        header_layout.addStretch(1)
        self.hide_settings_button = QToolButton()
        self.hide_settings_button.setText("Ocultar")
        self.hide_settings_button.setToolTip("Recolher o painel de configurações")
        self.hide_settings_button.clicked.connect(
            lambda: self.settings_toggle_button.setChecked(False)
        )
        header_layout.addWidget(self.hide_settings_button)
        outer_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        settings_container = QWidget()
        layout = QVBoxLayout(settings_container)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(10)

        orbit_group = QGroupBox("LOS")
        orbit_form = QFormLayout(orbit_group)
        self.orbit_combo = QComboBox()
        self.orbit_combo.addItem("Automática", ORBIT_AUTO)
        self.orbit_combo.addItem("Ascendente", ORBIT_ASCENDING)
        self.orbit_combo.addItem("Descendente", ORBIT_DESCENDING)
        self.orbit_combo.addItem("Não especificada", ORBIT_UNSPECIFIED)
        self.orbit_combo.currentIndexChanged.connect(
            self._on_orbit_override_changed
        )
        orbit_form.addRow("Direção desta camada:", self.orbit_combo)
        self.orbit_hint = QLabel(
            "No modo automático, a direção é inferida por tokens A/D ou ASC/DESC "
            "no nome ou caminho da camada."
        )
        self.orbit_hint.setWordWrap(True)
        orbit_form.addRow(self.orbit_hint)
        layout.addWidget(orbit_group)

        area_group = QGroupBox("Seleção por área")
        area_layout = QVBoxLayout(area_group)
        area_layout.setSpacing(6)

        draw_row = QHBoxLayout()
        self.draw_area_button = QPushButton("Desenhar área no mapa")
        self.draw_area_button.setToolTip(
            "Clique com o botão esquerdo para adicionar vértices; "
            "botão direito conclui e Esc cancela"
        )
        self.draw_area_button.clicked.connect(self._start_polygon_capture)
        draw_row.addWidget(self.draw_area_button, 1)
        self.clear_area_button = QPushButton("Limpar área")
        self.clear_area_button.setToolTip(
            "Remove o polígono temporário do mapa sem alterar a seleção de pontos"
        )
        self.clear_area_button.clicked.connect(self._clear_drawn_area)
        draw_row.addWidget(self.clear_area_button)
        area_layout.addLayout(draw_row)

        draw_hint = QLabel(
            "Desenho: botão esquerdo adiciona vértices, botão direito conclui e Esc cancela."
        )
        draw_hint.setWordWrap(True)
        area_layout.addWidget(draw_hint)

        polygon_form = QFormLayout()
        self.polygon_layer_combo = QComboBox()
        self.polygon_layer_combo.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.polygon_layer_combo.currentIndexChanged.connect(
            self._on_polygon_layer_changed
        )
        polygon_form.addRow("Camada poligonal:", self.polygon_layer_combo)

        self.use_selected_polygon_button = QPushButton(
            "Usar polígono selecionado"
        )
        self.use_selected_polygon_button.clicked.connect(
            self._use_selected_polygon_feature
        )
        polygon_form.addRow(self.use_selected_polygon_button)

        self.area_operation_combo = QComboBox()
        self.area_operation_combo.addItem("Substituir seleção", SELECTION_REPLACE)
        self.area_operation_combo.addItem("Adicionar à seleção", SELECTION_ADD)
        self.area_operation_combo.addItem("Remover da seleção", SELECTION_REMOVE)
        polygon_form.addRow("Operação:", self.area_operation_combo)
        area_layout.addLayout(polygon_form)

        self.area_status_label = QLabel("Nenhuma área aplicada nesta sessão.")
        self.area_status_label.setWordWrap(True)
        self.area_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        area_layout.addWidget(self.area_status_label)
        layout.addWidget(area_group)

        polygon_mean_group = QGroupBox("Médias por polígonos")
        polygon_mean_layout = QVBoxLayout(polygon_mean_group)
        polygon_mean_form = QFormLayout()

        self.polygon_mean_scope_combo = QComboBox()
        self.polygon_mean_scope_combo.addItem("Todos os polígonos", "all")
        self.polygon_mean_scope_combo.addItem("Somente selecionados", "selected")
        polygon_mean_form.addRow("Processar:", self.polygon_mean_scope_combo)

        self.polygon_name_field_combo = QComboBox()
        self.polygon_name_field_combo.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        polygon_mean_form.addRow("Campo do nome:", self.polygon_name_field_combo)

        self.polygon_mean_view_combo = QComboBox()
        self.polygon_mean_view_combo.addItem("Médias sobrepostas", "overlay")
        self.polygon_mean_view_combo.addItem("Médias separadas", "separate")
        polygon_mean_form.addRow("Visualização:", self.polygon_mean_view_combo)
        polygon_mean_layout.addLayout(polygon_mean_form)

        self.calculate_polygon_means_button = QPushButton(
            "Calcular médias por polígonos"
        )
        self.calculate_polygon_means_button.clicked.connect(
            self._calculate_polygon_means
        )
        polygon_mean_layout.addWidget(self.calculate_polygon_means_button)

        self.clear_polygon_means_button = QPushButton(
            "Voltar aos pontos selecionados"
        )
        self.clear_polygon_means_button.clicked.connect(
            self._clear_polygon_mean_results
        )
        polygon_mean_layout.addWidget(self.clear_polygon_means_button)

        polygon_mean_note = QLabel(
            "Usa a camada poligonal escolhida em Seleção por área. Cada polígono "
            "gera uma média independente; polígonos sobrepostos podem compartilhar pontos."
        )
        polygon_mean_note.setWordWrap(True)
        polygon_mean_layout.addWidget(polygon_mean_note)

        self.polygon_mean_status_label = QLabel(
            "Nenhuma média poligonal calculada nesta sessão."
        )
        self.polygon_mean_status_label.setWordWrap(True)
        self.polygon_mean_status_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        polygon_mean_layout.addWidget(self.polygon_mean_status_label)
        layout.addWidget(polygon_mean_group)

        appearance_group = QGroupBox("Aparência das séries")
        appearance_form = QFormLayout(appearance_group)
        self.show_lines_check = QCheckBox("Mostrar linhas")
        self.show_markers_check = QCheckBox("Mostrar marcadores")
        self.show_zero_line_check = QCheckBox("Mostrar referência em zero")
        self.show_legend_check = QCheckBox("Mostrar legenda em séries sobrepostas e na média")
        self.show_hover_check = QCheckBox("Mostrar dados ao passar o cursor")
        for widget in (
            self.show_lines_check,
            self.show_markers_check,
            self.show_zero_line_check,
            self.show_legend_check,
            self.show_hover_check,
        ):
            widget.toggled.connect(self._on_plot_settings_changed)
            appearance_form.addRow(widget)

        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.1, 10.0)
        self.line_width_spin.setDecimals(2)
        self.line_width_spin.setSingleStep(0.1)
        self.line_width_spin.valueChanged.connect(self._on_plot_settings_changed)
        appearance_form.addRow("Espessura da linha:", self.line_width_spin)

        self.marker_size_spin = QDoubleSpinBox()
        self.marker_size_spin.setRange(1.0, 20.0)
        self.marker_size_spin.setDecimals(1)
        self.marker_size_spin.setSingleStep(0.5)
        self.marker_size_spin.valueChanged.connect(self._on_plot_settings_changed)
        appearance_form.addRow("Tamanho dos marcadores:", self.marker_size_spin)

        self.max_series_spin = QSpinBox()
        self.max_series_spin.setRange(2, 200)
        self.max_series_spin.valueChanged.connect(self._on_plot_settings_changed)
        appearance_form.addRow("Máximo de pontos/séries:", self.max_series_spin)
        layout.addWidget(appearance_group)

        trend_group = QGroupBox("Trendline")
        trend_form = QFormLayout(trend_group)
        self.show_trendline_check = QCheckBox("Mostrar regressão linear")
        self.show_trendline_check.setToolTip(
            "Traça uma regressão linear vermelha sólida usando apenas valores válidos"
        )
        self.show_trendline_check.toggled.connect(self._on_plot_settings_changed)
        trend_form.addRow(self.show_trendline_check)
        self.trendline_scope_combo = QComboBox()
        self.trendline_scope_combo.addItem("Série principal", "primary")
        self.trendline_scope_combo.addItem("Todas as séries", "all")
        self.trendline_scope_combo.currentIndexChanged.connect(
            self._on_plot_settings_changed
        )
        trend_form.addRow("Aplicar a:", self.trendline_scope_combo)
        trend_note = QLabel(
            "A trendline é calculada localmente e não substitui o VEL fornecido pelo produto."
        )
        trend_note.setWordWrap(True)
        trend_form.addRow(trend_note)
        layout.addWidget(trend_group)

        grid_group = QGroupBox("Gridlines")
        grid_form = QFormLayout(grid_group)
        self.horizontal_grid_check = QCheckBox("Mostrar gridlines horizontais")
        self.horizontal_grid_check.toggled.connect(self._on_plot_settings_changed)
        grid_form.addRow(self.horizontal_grid_check)
        self.horizontal_grid_style_combo = QComboBox()
        self.horizontal_grid_style_combo.addItem("Sólida", "solid")
        self.horizontal_grid_style_combo.addItem("Tracejada", "dashed")
        self.horizontal_grid_style_combo.currentIndexChanged.connect(
            self._on_plot_settings_changed
        )
        grid_form.addRow("Estilo horizontal:", self.horizontal_grid_style_combo)

        self.vertical_grid_check = QCheckBox("Mostrar gridlines verticais")
        self.vertical_grid_check.toggled.connect(self._on_plot_settings_changed)
        grid_form.addRow(self.vertical_grid_check)
        self.vertical_grid_style_combo = QComboBox()
        self.vertical_grid_style_combo.addItem("Sólida", "solid")
        self.vertical_grid_style_combo.addItem("Tracejada", "dashed")
        self.vertical_grid_style_combo.currentIndexChanged.connect(
            self._on_plot_settings_changed
        )
        grid_form.addRow("Estilo vertical:", self.vertical_grid_style_combo)
        grid_note = QLabel("As gridlines usam cor preta com opacidade discreta.")
        grid_note.setWordWrap(True)
        grid_form.addRow(grid_note)
        layout.addWidget(grid_group)

        shade_group = QGroupBox("Período sombreado")
        shade_form = QFormLayout(shade_group)
        self.show_shaded_period_check = QCheckBox("Mostrar faixa cinza")
        self.show_shaded_period_check.toggled.connect(self._on_plot_settings_changed)
        shade_form.addRow(self.show_shaded_period_check)
        self.shade_start_edit = self._date_edit()
        self.shade_end_edit = self._date_edit()
        self.shade_start_edit.dateChanged.connect(self._on_plot_settings_changed)
        self.shade_end_edit.dateChanged.connect(self._on_plot_settings_changed)
        shade_form.addRow("Data inicial:", self.shade_start_edit)
        shade_form.addRow("Data final:", self.shade_end_edit)
        self.shade_opacity_spin = QSpinBox()
        self.shade_opacity_spin.setRange(1, 80)
        self.shade_opacity_spin.setSuffix(" %")
        self.shade_opacity_spin.valueChanged.connect(self._on_plot_settings_changed)
        shade_form.addRow("Opacidade:", self.shade_opacity_spin)
        layout.addWidget(shade_group)

        self.mean_group = QGroupBox("Média das séries")
        mean_form = QFormLayout(self.mean_group)
        self.mean_common_interval_check = QCheckBox(
            "Usar somente aquisições comuns a todos os pontos"
        )
        self.mean_reference_zero_check = QCheckBox(
            "Referenciar cada série em zero antes da média"
        )
        self.mean_show_dispersion_check = QCheckBox(
            "Mostrar média ± 1 desvio-padrão"
        )
        self.mean_show_individuals_check = QCheckBox(
            "Mostrar séries individuais ao fundo"
        )
        for widget in (
            self.mean_common_interval_check,
            self.mean_reference_zero_check,
            self.mean_show_dispersion_check,
            self.mean_show_individuals_check,
        ):
            widget.toggled.connect(self._on_plot_settings_changed)
            mean_form.addRow(widget)
        mean_note = QLabel(
            "Sem o intervalo comum, a média usa os valores disponíveis em cada "
            "aquisição e exige pelo menos dois pontos. O N utilizado pode variar."
        )
        mean_note.setWordWrap(True)
        mean_form.addRow(mean_note)
        layout.addWidget(self.mean_group)

        additional_group = QGroupBox("Propriedades adicionais")
        additional_layout = QVBoxLayout(additional_group)
        self.show_additional_panel_check = QCheckBox(
            "Mostrar propriedades selecionadas no painel"
        )
        self.show_additional_panel_check.toggled.connect(
            self._on_plot_settings_changed
        )
        additional_layout.addWidget(self.show_additional_panel_check)

        self.export_additional_properties_check = QCheckBox(
            "Incluir propriedades selecionadas no cabeçalho exportado"
        )
        self.export_additional_properties_check.toggled.connect(
            self._on_plot_settings_changed
        )
        additional_layout.addWidget(self.export_additional_properties_check)

        additional_note = QLabel(
            "Os campos disponíveis são lidos da camada atual. Em séries individuais "
            "é mostrado o valor da feição; em médias, a média dos campos numéricos."
        )
        additional_note.setWordWrap(True)
        additional_layout.addWidget(additional_note)

        field_buttons = QHBoxLayout()
        self.select_all_additional_button = QPushButton("Selecionar todos")
        self.select_all_additional_button.clicked.connect(
            lambda: self._set_all_additional_fields(True)
        )
        field_buttons.addWidget(self.select_all_additional_button)
        self.clear_additional_button = QPushButton("Limpar")
        self.clear_additional_button.clicked.connect(
            lambda: self._set_all_additional_fields(False)
        )
        field_buttons.addWidget(self.clear_additional_button)
        additional_layout.addLayout(field_buttons)

        self.additional_fields_scroll = QScrollArea()
        self.additional_fields_scroll.setWidgetResizable(True)
        self.additional_fields_scroll.setFrameShape(QFrame.StyledPanel)
        self.additional_fields_scroll.setMinimumHeight(90)
        self.additional_fields_scroll.setMaximumHeight(190)
        self.additional_fields_container = QWidget()
        self.additional_fields_layout = QVBoxLayout(self.additional_fields_container)
        self.additional_fields_layout.setContentsMargins(6, 4, 6, 4)
        self.additional_fields_layout.setSpacing(2)
        self.additional_fields_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.additional_fields_scroll.setWidget(self.additional_fields_container)
        additional_layout.addWidget(self.additional_fields_scroll)
        layout.addWidget(additional_group)

        y_group = QGroupBox("Eixo Y")
        y_form = QFormLayout(y_group)
        self.y_manual_check = QCheckBox("Usar limites manuais")
        self.y_manual_check.toggled.connect(self._on_plot_settings_changed)
        y_form.addRow(self.y_manual_check)

        self.y_min_spin = self._axis_double_spin()
        self.y_max_spin = self._axis_double_spin()
        self.y_min_spin.valueChanged.connect(self._on_plot_settings_changed)
        self.y_max_spin.valueChanged.connect(self._on_plot_settings_changed)
        y_form.addRow("Mínimo:", self.y_min_spin)
        y_form.addRow("Máximo:", self.y_max_spin)

        self.y_tick_spin = QDoubleSpinBox()
        self.y_tick_spin.setRange(0.0, 1_000_000.0)
        self.y_tick_spin.setDecimals(2)
        self.y_tick_spin.setSingleStep(1.0)
        self.y_tick_spin.setSpecialValueText(tr("Automático"))
        self.y_tick_spin.valueChanged.connect(self._on_plot_settings_changed)
        y_form.addRow("Intervalo dos ticks:", self.y_tick_spin)
        layout.addWidget(y_group)

        x_group = QGroupBox("Eixo X")
        x_form = QFormLayout(x_group)
        self.x_manual_check = QCheckBox("Usar período manual")
        self.x_manual_check.toggled.connect(self._on_plot_settings_changed)
        x_form.addRow(self.x_manual_check)

        self.x_start_edit = self._date_edit()
        self.x_end_edit = self._date_edit()
        self.x_start_edit.dateChanged.connect(self._on_plot_settings_changed)
        self.x_end_edit.dateChanged.connect(self._on_plot_settings_changed)
        x_form.addRow("Data inicial:", self.x_start_edit)
        x_form.addRow("Data final:", self.x_end_edit)

        self.x_tick_days_spin = QSpinBox()
        self.x_tick_days_spin.setRange(0, 3650)
        self.x_tick_days_spin.setSpecialValueText(tr("Automático"))
        self.x_tick_days_spin.valueChanged.connect(self._on_plot_settings_changed)
        x_form.addRow("Intervalo dos ticks (dias):", self.x_tick_days_spin)
        layout.addWidget(x_group)

        export_group = QGroupBox("Exportação")
        export_layout = QVBoxLayout(export_group)
        export_form = QFormLayout()

        self.export_format_combo = QComboBox()
        self.export_format_combo.addItem("PNG", "png")
        self.export_format_combo.addItem("SVG", "svg")
        self.export_format_combo.addItem("PDF", "pdf")
        self.export_format_combo.currentIndexChanged.connect(
            self._on_plot_settings_changed
        )
        export_form.addRow("Formato:", self.export_format_combo)

        self.export_width_spin = QDoubleSpinBox()
        self.export_width_spin.setRange(8.0, 100.0)
        self.export_width_spin.setDecimals(1)
        self.export_width_spin.setSingleStep(1.0)
        self.export_width_spin.setSuffix(" cm")
        self.export_width_spin.valueChanged.connect(self._on_plot_settings_changed)
        export_form.addRow("Largura:", self.export_width_spin)

        self.export_height_spin = QDoubleSpinBox()
        self.export_height_spin.setRange(6.0, 100.0)
        self.export_height_spin.setDecimals(1)
        self.export_height_spin.setSingleStep(1.0)
        self.export_height_spin.setSuffix(" cm")
        self.export_height_spin.valueChanged.connect(self._on_plot_settings_changed)
        export_form.addRow("Altura:", self.export_height_spin)

        self.export_dpi_spin = QSpinBox()
        self.export_dpi_spin.setRange(72, 1200)
        self.export_dpi_spin.setSingleStep(25)
        self.export_dpi_spin.setSuffix(" DPI")
        self.export_dpi_spin.valueChanged.connect(self._on_plot_settings_changed)
        export_form.addRow("Resolução:", self.export_dpi_spin)

        self.export_header_check = QCheckBox(
            "Incluir cabeçalho com os dados da série"
        )
        self.export_header_check.toggled.connect(self._on_plot_settings_changed)
        export_form.addRow(self.export_header_check)

        self.export_transparent_check = QCheckBox("Fundo transparente")
        self.export_transparent_check.toggled.connect(
            self._on_plot_settings_changed
        )
        export_form.addRow(self.export_transparent_check)

        self.watermark_export_check = QCheckBox(
            "Incluir marca d'água do plugin na exportação"
        )
        self.watermark_export_check.toggled.connect(
            self._on_plot_settings_changed
        )
        export_form.addRow(self.watermark_export_check)

        self.watermark_preview_check = QCheckBox(
            "Mostrar marca d'água também na visualização"
        )
        self.watermark_preview_check.toggled.connect(
            self._on_plot_settings_changed
        )
        export_form.addRow(self.watermark_preview_check)

        self.watermark_opacity_spin = QSpinBox()
        self.watermark_opacity_spin.setRange(1, 60)
        self.watermark_opacity_spin.setSuffix(" %")
        self.watermark_opacity_spin.valueChanged.connect(
            self._on_plot_settings_changed
        )
        export_form.addRow("Opacidade:", self.watermark_opacity_spin)

        self.watermark_position_combo = QComboBox()
        self.watermark_position_combo.addItem("Centro", "center")
        self.watermark_position_combo.addItem("Inferior direito", "lower_right")
        self.watermark_position_combo.addItem("Inferior esquerdo", "lower_left")
        self.watermark_position_combo.addItem("Superior direito", "upper_right")
        self.watermark_position_combo.addItem("Superior esquerdo", "upper_left")
        self.watermark_position_combo.currentIndexChanged.connect(
            self._on_plot_settings_changed
        )
        export_form.addRow("Posição do logo:", self.watermark_position_combo)

        self.watermark_scale_spin = QSpinBox()
        self.watermark_scale_spin.setRange(10, 150)
        self.watermark_scale_spin.setSuffix(" %")
        self.watermark_scale_spin.valueChanged.connect(
            self._on_plot_settings_changed
        )
        export_form.addRow("Tamanho do logo:", self.watermark_scale_spin)
        export_layout.addLayout(export_form)

        self.export_current_button = QPushButton("Salvar gráfico atual...")
        self.export_current_button.clicked.connect(self._export_current_graph)
        export_layout.addWidget(self.export_current_button)

        self.export_batch_button = QPushButton(
            "Salvar séries/médias separadamente..."
        )
        self.export_batch_button.setToolTip(
            "Cria um arquivo individual para cada série ou média poligonal exibida"
        )
        self.export_batch_button.clicked.connect(self._export_batch_graphs)
        export_layout.addWidget(self.export_batch_button)

        export_note = QLabel(
            "O cabeçalho usa os nomes literais VEL/V_STDEV da camada. PNG usa o DPI; "
            "SVG e PDF permanecem vetoriais, com o logo raster incorporado."
        )
        export_note.setWordWrap(True)
        export_layout.addWidget(export_note)
        layout.addWidget(export_group)

        self.reset_settings_button = QPushButton(
            "Restaurar configurações padrão do gráfico"
        )
        self.reset_settings_button.clicked.connect(self._reset_plot_settings)
        layout.addWidget(self.reset_settings_button)

        persistence_note = QLabel(
            "As configurações são aplicadas imediatamente e armazenadas no projeto QGIS."
        )
        persistence_note.setWordWrap(True)
        layout.addWidget(persistence_note)
        layout.addStretch(1)

        scroll.setWidget(settings_container)
        outer_layout.addWidget(scroll, 1)

    def _load_ui_state(self) -> None:
        self._settings_panel_visible = self.project.readBoolEntry(
            PROJECT_SCOPE,
            UI_SETTINGS_VISIBLE_KEY,
            True,
        )[0]
        width = self.project.readNumEntry(
            PROJECT_SCOPE,
            UI_SETTINGS_WIDTH_KEY,
            DEFAULT_SETTINGS_PANEL_WIDTH,
        )[0]
        self._settings_panel_width = min(max(int(width), 280), 460)
        self._set_settings_panel_visible(
            self._settings_panel_visible,
            persist=False,
        )

    def _save_settings_panel_visible(self, visible: bool) -> None:
        writer = getattr(self.project, "writeEntryBool", None)
        if writer is not None:
            writer(PROJECT_SCOPE, UI_SETTINGS_VISIBLE_KEY, bool(visible))
        else:
            self.project.writeEntry(
                PROJECT_SCOPE,
                UI_SETTINGS_VISIBLE_KEY,
                bool(visible),
            )

    def _on_settings_panel_toggled(self, visible: bool) -> None:
        self._set_settings_panel_visible(visible, persist=True)

    def _set_settings_panel_visible(
        self,
        visible: bool,
        *,
        persist: bool,
    ) -> None:
        visible = bool(visible)
        self._settings_panel_visible = visible
        self.settings_panel.setVisible(visible)
        self.settings_toggle_button.blockSignals(True)
        self.settings_toggle_button.setChecked(visible)
        self.settings_toggle_button.blockSignals(False)
        self.settings_toggle_button.setText(
            tr("Ocultar configurações") if visible else tr("Mostrar configurações")
        )
        if visible:
            QTimer.singleShot(0, self._restore_splitter_sizes)
        if persist:
            self._save_settings_panel_visible(visible)

    def _restore_splitter_sizes(self) -> None:
        if not self._settings_panel_visible or not self.settings_panel.isVisible():
            return
        total = self.splitter.width()
        if total <= 0:
            return
        right = min(max(self._settings_panel_width, 280), 460)
        right = min(right, max(280, total - 420))
        left = max(total - right, 420)
        self.splitter.setSizes([left, right])

    def _on_splitter_moved(self, _position: int, _index: int) -> None:
        if not self._settings_panel_visible:
            return
        sizes = self.splitter.sizes()
        if len(sizes) != 2 or sizes[1] < 280:
            return
        width = min(max(int(sizes[1]), 280), 460)
        if width == self._settings_panel_width:
            return
        self._settings_panel_width = width
        self.project.writeEntry(
            PROJECT_SCOPE,
            UI_SETTINGS_WIDTH_KEY,
            width,
        )

    @staticmethod
    def _value_label() -> QLabel:
        label = QLabel("—")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    @staticmethod
    def _axis_double_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-1_000_000_000.0, 1_000_000_000.0)
        spin.setDecimals(2)
        spin.setSingleStep(10.0)
        return spin

    @staticmethod
    def _date_edit() -> QDateEdit:
        edit = QDateEdit()
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd/MM/yyyy")
        edit.setDateRange(QDate(1900, 1, 1), QDate(2200, 12, 31))
        return edit

    # ------------------------------------------------------------ lifecycle
    def _connect_global_signals(self) -> None:
        self.project.layersAdded.connect(self.refresh_layers)
        self.project.layersRemoved.connect(self.refresh_layers)
        self.project.cleared.connect(self._on_project_cleared)
        self.project.readProject.connect(self._on_project_read)
        self.iface.currentLayerChanged.connect(self._on_active_layer_changed)

    def shutdown(self) -> None:
        self._clear_active_feature_marker(remove=True)
        self._dispose_area_tools()
        self._disconnect_current_layer()
        for signal, slot in (
            (self.project.layersAdded, self.refresh_layers),
            (self.project.layersRemoved, self.refresh_layers),
            (self.project.cleared, self._on_project_cleared),
            (self.project.readProject, self._on_project_read),
            (self.iface.currentLayerChanged, self._on_active_layer_changed),
        ):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass

    def _on_project_cleared(self, *_args) -> None:
        self._clear_drawn_area(update_status=False)
        self._clear_active_feature_marker()
        self._point_spatial_index = None
        self._polygon_mean_batch = None
        self.settings = PlotSettings()
        self._load_ui_state()
        self._sync_controls_from_settings()
        self.refresh_layers()

    def _on_project_read(self, *_args) -> None:
        self._clear_drawn_area(update_status=False)
        self._clear_active_feature_marker()
        self._point_spatial_index = None
        self._polygon_mean_batch = None
        self.settings = PlotSettings.load(self.project)
        self._load_ui_state()
        self._sync_controls_from_settings()
        self.refresh_layers()

    # -------------------------------------------------------------- layers
    def refresh_layers(self, *_args) -> None:
        if self._refreshing_layers:
            return

        self._refreshing_layers = True
        try:
            previous_layer_id = self._selected_layer_id()
            active_layer = self.iface.activeLayer()
            active_layer_id = active_layer.id() if active_layer is not None else None

            compatible = []
            for layer in self.project.mapLayers().values():
                if not self._is_point_vector_layer(layer):
                    continue
                try:
                    schema = resolve_layer_schema(layer).schema
                except (LayerValidationError, SavedLayerMappingError):
                    continue
                override = load_layer_orbit_override(self.project, layer.id())
                label = component_display_label(schema, layer, override)
                compatible.append((layer.name().casefold(), layer, schema, label))

            compatible.sort(key=lambda item: item[0])

            self.layer_combo.blockSignals(True)
            self.layer_combo.clear()
            self.layer_combo.addItem(tr("— selecione uma camada —"), None)
            for _, layer, _schema, component_label in compatible:
                self.layer_combo.addItem(
                    f"{layer.name()} [{component_label}]", layer.id()
                )

            target_id = None
            available_ids = {layer.id() for _, layer, _, _ in compatible}
            if previous_layer_id in available_ids:
                target_id = previous_layer_id
            elif active_layer_id in available_ids:
                target_id = active_layer_id
            elif len(compatible) == 1:
                target_id = compatible[0][1].id()

            index = self.layer_combo.findData(target_id)
            self.layer_combo.setCurrentIndex(index if index >= 0 else 0)
            self.layer_combo.blockSignals(False)
            self._activate_layer_by_id(target_id)
            self._refresh_polygon_layers()

            if not compatible:
                self.status_label.setText(
                    "Nenhuma camada pontual compatível foi encontrada no projeto."
                )
        finally:
            self._refreshing_layers = False

    def _on_active_layer_changed(self, layer) -> None:
        if self._refreshing_layers or layer is None:
            return
        index = self.layer_combo.findData(layer.id())
        if index >= 0 and index != self.layer_combo.currentIndex():
            self.layer_combo.setCurrentIndex(index)

    def _on_layer_combo_changed(self, _index: int) -> None:
        if not self._refreshing_layers:
            self._activate_layer_by_id(self._selected_layer_id())

    def _configure_layer_fields(self) -> None:
        layer = self.current_layer
        if layer is None:
            layer_id = self._selected_layer_id()
            layer = self.project.mapLayer(layer_id) if layer_id else None
        if layer is None:
            active_layer = self.iface.activeLayer()
            layer = active_layer if self._is_point_vector_layer(active_layer) else None

        if not self._is_point_vector_layer(layer):
            QMessageBox.warning(
                self,
                tr("Configurar campos"),
                tr("Selecione uma camada pontual antes de configurar campos."),
            )
            return

        try:
            initial_mapping = load_layer_field_mapping(layer)
        except LayerMappingStoreError as exc:
            QMessageBox.warning(
                self,
                tr("Configurar campos"),
                tr(
                    "O mapeamento salvo não pôde ser lido e será ignorado: {error}",
                    error=str(exc),
                ),
            )
            initial_mapping = None

        dialog = FieldMappingDialog(layer, initial_mapping, self)
        if dialog.exec() != QDialog.Accepted:
            return

        if dialog.clear_requested:
            clear_layer_field_mapping(layer)
            self.status_label.setText(
                tr("Mapeamento manual removido da camada {layer}.", layer=layer.name())
            )
        else:
            save_layer_field_mapping(layer, dialog.field_mapping())
            self.status_label.setText(
                tr("Mapeamento de campos salvo para {layer}.", layer=layer.name())
            )

        self.refresh_layers()

    def _selected_layer_id(self):
        return self.layer_combo.currentData()

    def _activate_layer_by_id(self, layer_id) -> None:
        current_id = self._current_layer_id_safe()
        if current_id is not None and current_id == layer_id:
            self._update_from_current_selection()
            return

        self._disconnect_current_layer()
        self.current_layer = None
        self.current_schema = None
        self.current_feature_id = None
        self.current_orbit_override = ORBIT_AUTO
        self._point_spatial_index = None
        self._polygon_mean_batch = None
        if hasattr(self, "polygon_mean_status_label"):
            self._set_polygon_mean_status(
                "Nenhuma média poligonal calculada nesta sessão."
            )

        if not layer_id:
            self.layer_info.setText("Nenhuma camada compatível selecionada.")
            self.selection_count_label.setText("0 selecionadas")
            self._sync_orbit_control()
            self._refresh_additional_property_fields()
            self._clear_feature_info()
            self._clear_active_feature_marker()
            self._show_plot_message(tr("Selecione uma camada InSAR compatível."))
            self.status_label.setText("")
            self._update_area_control_states()
            self._update_selection_action_states()
            return

        layer = self.project.mapLayer(layer_id)
        if not self._is_point_vector_layer(layer):
            self._show_layer_error("A camada escolhida não está mais disponível.")
            return

        try:
            schema = resolve_layer_schema(layer).schema
        except (LayerValidationError, SavedLayerMappingError) as exc:
            self._show_layer_error(str(exc))
            return

        self.current_layer = layer
        self.current_schema = schema
        self.current_orbit_override = load_layer_orbit_override(
            self.project, layer.id()
        )
        self.current_layer.selectionChanged.connect(self._on_selection_changed)
        self.current_layer.updatedFields.connect(self._on_layer_fields_changed)
        self.current_layer.featureAdded.connect(self._invalidate_spatial_index)
        self.current_layer.featureDeleted.connect(self._invalidate_spatial_index)
        self.current_layer.geometryChanged.connect(self._invalidate_spatial_index)

        self._sync_orbit_control()
        self._sync_x_dates_for_schema(schema)
        self._refresh_additional_property_fields()
        self._update_layer_info()
        self._update_area_control_states()
        self._update_from_current_selection()

    def _update_layer_info(self) -> None:
        if self.current_layer is None or self.current_schema is None:
            return
        schema = self.current_schema
        component_label = self._effective_component_label()
        self.caption_velocity.setText(f"{schema.velocity_field}:")
        self.caption_velocity_std.setText(f"{schema.velocity_std_field}:")
        self.layer_info.setText(
            tr(
                "{component} · {count} aquisições · {start} a {end}",
                component=component_label,
                count=schema.acquisition_count,
                start=f"{schema.first_acquisition:%d/%m/%Y}",
                end=f"{schema.last_acquisition:%d/%m/%Y}",
            )
        )

    def _disconnect_current_layer(self) -> None:
        self._clear_active_feature_marker()
        if self.current_layer is None:
            return
        try:
            self.current_layer.selectionChanged.disconnect(self._on_selection_changed)
        except (AttributeError, TypeError, RuntimeError):
            pass
        try:
            self.current_layer.updatedFields.disconnect(self._on_layer_fields_changed)
        except (AttributeError, TypeError, RuntimeError):
            pass
        for signal_name in ("featureAdded", "featureDeleted", "geometryChanged"):
            try:
                getattr(self.current_layer, signal_name).disconnect(
                    self._invalidate_spatial_index
                )
            except (AttributeError, TypeError, RuntimeError):
                pass
        self._point_spatial_index = None

    def _current_layer_id_safe(self):
        if self.current_layer is None:
            return None
        try:
            return self.current_layer.id()
        except RuntimeError:
            return None

    def _on_layer_fields_changed(self) -> None:
        layer_id = self._current_layer_id_safe()
        self._disconnect_current_layer()
        self.current_layer = None
        self.current_schema = None
        self.current_feature_id = None
        self.refresh_layers()
        index = self.layer_combo.findData(layer_id)
        if index >= 0:
            self.layer_combo.setCurrentIndex(index)

    @staticmethod
    def _is_point_vector_layer(layer) -> bool:
        return (
            isinstance(layer, QgsVectorLayer) and
            layer.isValid() and
            layer.geometryType() == QgsWkbTypes.PointGeometry
        )

    @staticmethod
    def _is_polygon_vector_layer(layer) -> bool:
        return (
            isinstance(layer, QgsVectorLayer) and
            layer.isValid() and
            layer.geometryType() == QgsWkbTypes.PolygonGeometry
        )

    # ----------------------------------------------- additional properties
    def _additional_fields_project_key(self, layer_id: str) -> str:
        return f"{ADDITIONAL_FIELDS_PREFIX}/{layer_id}"

    def _load_additional_field_names(self) -> list[str]:
        layer = self.current_layer
        if layer is None:
            return []
        raw = self.project.readEntry(
            PROJECT_SCOPE,
            self._additional_fields_project_key(layer.id()),
            "[]",
        )[0]
        try:
            values = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(values, list):
            return []
        return [str(value) for value in values]

    def _save_additional_field_names(self) -> None:
        layer = self.current_layer
        if layer is None:
            return
        self.project.writeEntry(
            PROJECT_SCOPE,
            self._additional_fields_project_key(layer.id()),
            json.dumps(self._selected_additional_fields(), ensure_ascii=False),
        )

    def _selected_additional_fields(self) -> list[str]:
        return [
            field_name
            for field_name, checkbox in self._additional_field_checks.items()
            if checkbox.isChecked()
        ]

    def _refresh_additional_property_fields(self) -> None:
        if not hasattr(self, "additional_fields_layout"):
            return

        while self.additional_fields_layout.count():
            item = self.additional_fields_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._additional_field_checks = {}

        schema = self.current_schema
        candidates = property_field_candidates(schema) if schema is not None else ()
        selected = set(self._load_additional_field_names())

        if not candidates:
            message = QLabel("Nenhum campo adicional disponível na camada atual.")
            message.setWordWrap(True)
            self.additional_fields_layout.addWidget(message)
        else:
            for field_name in candidates:
                checkbox = QCheckBox(field_name)
                checkbox.setChecked(field_name in selected)
                checkbox.toggled.connect(self._on_additional_field_toggled)
                self.additional_fields_layout.addWidget(checkbox)
                self._additional_field_checks[field_name] = checkbox
            self.additional_fields_layout.addStretch(1)

        available = bool(candidates)
        self.select_all_additional_button.setEnabled(available)
        self.clear_additional_button.setEnabled(available)
        self.additional_fields_scroll.setEnabled(available)
        self._update_axis_control_states()
        self._update_additional_properties_info()

    def _on_additional_field_toggled(self, _checked: bool) -> None:
        if self._updating_controls:
            return
        self._save_additional_field_names()
        self._update_from_current_selection()

    def _set_all_additional_fields(self, checked: bool) -> None:
        self._updating_controls = True
        try:
            for checkbox in self._additional_field_checks.values():
                checkbox.setChecked(bool(checked))
        finally:
            self._updating_controls = False
        self._save_additional_field_names()
        self._update_from_current_selection()

    def _property_values_for_ids(
        self,
        feature_ids: Sequence[int],
        field_names: Sequence[str],
    ) -> dict[str, list]:
        values = {field_name: [] for field_name in field_names}
        layer = self.current_layer
        if layer is None or not field_names:
            return values
        for feature_id in dict.fromkeys(int(item) for item in feature_ids):
            feature = layer.getFeature(feature_id)
            if feature is None or not feature.isValid():
                continue
            for field_name in field_names:
                try:
                    values[field_name].append(feature[field_name])
                except (KeyError, TypeError):
                    values[field_name].append(None)
        return values

    def _additional_property_summaries_for_ids(
        self,
        feature_ids: Sequence[int],
        *,
        mode: str,
    ) -> list[tuple[str, str]]:
        field_names = self._selected_additional_fields()
        values = self._property_values_for_ids(feature_ids, field_names)
        return [
            (field_name, summarize_values(values[field_name], mode=mode))
            for field_name in field_names
        ]

    def _additional_property_summaries_for_groups(
        self,
        groups,
    ) -> list[tuple[str, str]]:
        field_names = self._selected_additional_fields()
        if not field_names:
            return []
        grouped_values = {field_name: [] for field_name in field_names}
        for group in groups:
            values = self._property_values_for_ids(group.point_ids, field_names)
            for field_name in field_names:
                grouped_values[field_name].append(values[field_name])
        return [
            (
                field_name,
                summarize_group_means(grouped_values[field_name], mode="range"),
            )
            for field_name in field_names
        ]

    def _current_additional_property_summaries(self) -> list[tuple[str, str]]:
        mode = self._displayed_mode or self.settings.display_mode
        if mode == "mean" and self._displayed_mean_source_series:
            return self._additional_property_summaries_for_ids(
                [item.feature_id for item in self._displayed_mean_source_series],
                mode="mean",
            )
        if mode in {"polygon_means_overlay", "polygon_means_separate"}:
            groups = self._displayed_polygon_groups
            if len(groups) == 1:
                return self._additional_property_summaries_for_ids(
                    groups[0].point_ids,
                    mode="mean",
                )
            return self._additional_property_summaries_for_groups(groups)
        if len(self._displayed_series) == 1:
            return self._additional_property_summaries_for_ids(
                [self._displayed_series[0].feature_id],
                mode="single",
            )
        if self._displayed_series:
            return self._additional_property_summaries_for_ids(
                [item.feature_id for item in self._displayed_series],
                mode="range",
            )
        return []

    def _update_additional_properties_info(self) -> None:
        if not hasattr(self, "caption_additional_properties"):
            return
        summaries = self._current_additional_property_summaries()
        visible = bool(
            self.settings.show_additional_properties_panel and summaries
        )
        self.caption_additional_properties.setVisible(visible)
        self.value_additional_properties.setVisible(visible)
        if not visible:
            self.value_additional_properties.setText("—")
            return
        rows = [
            f"<b>{html.escape(field_name)}:</b> {html.escape(value)}"
            for field_name, value in summaries
        ]
        self.value_additional_properties.setText("<br>".join(rows))

    def _additional_header_suffix_for_ids(
        self,
        feature_ids: Sequence[int],
        *,
        mode: str,
    ) -> str:
        if not self.settings.export_additional_properties:
            return ""
        summaries = self._additional_property_summaries_for_ids(
            feature_ids,
            mode=mode,
        )
        return "".join(
            f" | {field_name}: {value}" for field_name, value in summaries
        )

    def _additional_header_suffix_for_groups(self, groups) -> str:
        if not self.settings.export_additional_properties:
            return ""
        summaries = self._additional_property_summaries_for_groups(groups)
        return "".join(
            f" | {field_name}: {value}" for field_name, value in summaries
        )

    # ------------------------------------------------------ spatial selection
    def _refresh_polygon_layers(self) -> None:
        previous_id = self.polygon_layer_combo.currentData()
        polygon_layers = [
            layer
            for layer in self.project.mapLayers().values()
            if self._is_polygon_vector_layer(layer)
        ]
        polygon_layers.sort(key=lambda layer: layer.name().casefold())

        self.polygon_layer_combo.blockSignals(True)
        self.polygon_layer_combo.clear()
        self.polygon_layer_combo.addItem(tr("— selecione uma camada —"), None)
        for layer in polygon_layers:
            self.polygon_layer_combo.addItem(layer.name(), layer.id())
        index = self.polygon_layer_combo.findData(previous_id)
        self.polygon_layer_combo.setCurrentIndex(index if index >= 0 else 0)
        current_id = self.polygon_layer_combo.currentData()
        self.polygon_layer_combo.blockSignals(False)
        if previous_id != current_id:
            self._polygon_mean_batch = None
            self._set_polygon_mean_status(
                "Nenhuma média poligonal calculada para esta camada."
            )
        self._refresh_polygon_name_fields()
        self._update_area_control_states()

    def _on_polygon_layer_changed(self, *_args) -> None:
        self._polygon_mean_batch = None
        self._refresh_polygon_name_fields()
        self._set_polygon_mean_status(
            "Nenhuma média poligonal calculada para esta camada."
        )
        self._update_area_control_states()
        if self.settings.display_mode in {
            "polygon_means_overlay",
            "polygon_means_separate",
        }:
            self._update_from_current_selection()

    def _refresh_polygon_name_fields(self) -> None:
        previous = self.polygon_name_field_combo.currentData()
        layer_id = self.polygon_layer_combo.currentData()
        layer = self.project.mapLayer(layer_id) if layer_id else None

        self.polygon_name_field_combo.blockSignals(True)
        self.polygon_name_field_combo.clear()
        self.polygon_name_field_combo.addItem(
            tr("— sem campo: usar Média de X pontos —"), None
        )
        field_names = []
        if self._is_polygon_vector_layer(layer):
            field_names = [field.name() for field in layer.fields()]
            for field_name in field_names:
                self.polygon_name_field_combo.addItem(field_name, field_name)

        target = previous if previous in field_names else self._suggest_name_field(field_names)
        index = self.polygon_name_field_combo.findData(target)
        self.polygon_name_field_combo.setCurrentIndex(index if index >= 0 else 0)
        self.polygon_name_field_combo.blockSignals(False)

    @staticmethod
    def _suggest_name_field(field_names: Sequence[str]):
        priorities = (
            "nome",
            "name",
            "label",
            "titulo",
            "title",
            "setor",
            "area",
            "zona",
        )
        normalized = {name.casefold(): name for name in field_names}
        for candidate in priorities:
            if candidate in normalized:
                return normalized[candidate]
        for candidate in priorities:
            for field_name in field_names:
                if candidate in field_name.casefold():
                    return field_name
        return None

    def _update_area_control_states(self, *_args) -> None:
        target_available = (
            self.current_layer is not None and
            self.current_schema is not None and
            self._is_point_vector_layer(self.current_layer)
        )
        capture_active = (
            self._polygon_capture_tool is not None and
            self.iface.mapCanvas().mapTool() is self._polygon_capture_tool
        )
        self.draw_area_button.setEnabled(target_available and not capture_active)
        self.clear_area_button.setEnabled(self._has_displayed_area)
        polygon_available = bool(self.polygon_layer_combo.currentData())
        self.use_selected_polygon_button.setEnabled(
            target_available and polygon_available
        )
        self.calculate_polygon_means_button.setEnabled(
            target_available and polygon_available
        )
        self.clear_polygon_means_button.setEnabled(
            self._polygon_mean_batch is not None
        )
        self.polygon_name_field_combo.setEnabled(polygon_available)
        self.polygon_mean_scope_combo.setEnabled(polygon_available)
        self.polygon_mean_view_combo.setEnabled(polygon_available)

    def _set_area_status(self, message: str, *, error: bool = False) -> None:
        self.area_status_label.setText(tr(message))
        self.area_status_label.setStyleSheet(
            "color: #d9534f;" if error else ""
        )

    def _set_polygon_mean_status(self, message: str, *, error: bool = False) -> None:
        self.polygon_mean_status_label.setText(tr(message))
        self.polygon_mean_status_label.setStyleSheet(
            "color: #d9534f;" if error else ""
        )

    def _calculate_polygon_means(self, *_args) -> None:
        point_layer = self.current_layer
        point_schema = self.current_schema
        polygon_layer_id = self.polygon_layer_combo.currentData()
        polygon_layer = (
            self.project.mapLayer(polygon_layer_id) if polygon_layer_id else None
        )
        if point_layer is None or point_schema is None:
            self._set_polygon_mean_status(
                "Selecione primeiro uma camada pontual InSAR compatível.",
                error=True,
            )
            return
        if not self._is_polygon_vector_layer(polygon_layer):
            self._set_polygon_mean_status(
                "Escolha uma camada poligonal válida.", error=True
            )
            return

        selected_only = self.polygon_mean_scope_combo.currentData() == "selected"
        try:
            features = polygon_features_for_scope(
                polygon_layer,
                selected_only=selected_only,
            )
            if self._point_spatial_index is None:
                self._set_polygon_mean_status(
                    "Construindo índice espacial da camada de pontos..."
                )
                self._point_spatial_index = build_point_spatial_index(point_layer)

            batch = calculate_polygon_mean_groups(
                point_layer=point_layer,
                point_schema=point_schema,
                polygon_layer=polygon_layer,
                polygon_features=features,
                spatial_index=self._point_spatial_index,
                name_field=self.polygon_name_field_combo.currentData(),
                common_interval=self.settings.mean_common_interval,
                reference_zero=self.settings.mean_reference_zero,
                selected_only=selected_only,
            )
        except PolygonMeanError as exc:
            self._polygon_mean_batch = None
            self._set_polygon_mean_status(str(exc), error=True)
            self._update_area_control_states()
            if self.settings.display_mode in {
                "polygon_means_overlay",
                "polygon_means_separate",
            }:
                self._update_from_current_selection()
            return
        except Exception as exc:
            self._polygon_mean_batch = None
            self._set_polygon_mean_status(
                tr(
                    "Falha inesperada: {kind}: {error}",
                    kind=type(exc).__name__,
                    error=exc,
                ),
                error=True,
            )
            self._update_area_control_states()
            return

        self._polygon_mean_batch = batch
        target_mode = (
            "polygon_means_separate"
            if self.polygon_mean_view_combo.currentData() == "separate"
            else "polygon_means_overlay"
        )
        mode_index = self.display_mode_combo.findData(target_mode)
        if mode_index >= 0 and mode_index != self.display_mode_combo.currentIndex():
            self.display_mode_combo.setCurrentIndex(mode_index)
        else:
            self._update_from_current_selection()

        status_parts = [
            tr("{count} média(s) calculada(s)", count=batch.group_count),
            tr(
                "{count} polígono(s) examinado(s)",
                count=batch.requested_polygon_count,
            ),
        ]
        if batch.polygons_without_points:
            status_parts.append(
                tr("{count} sem pontos", count=len(batch.polygons_without_points))
            )
        if batch.polygons_with_errors:
            status_parts.append(
                tr("{count} com erro", count=len(batch.polygons_with_errors))
            )
        self._set_polygon_mean_status(" · ".join(status_parts) + ".")
        self._update_area_control_states()

    def _clear_polygon_mean_results(self, *_args) -> None:
        self._polygon_mean_batch = None
        self._set_polygon_mean_status(
            "Médias poligonais removidas; exibindo a seleção de pontos."
        )
        if self.settings.display_mode in {
            "polygon_means_overlay",
            "polygon_means_separate",
        }:
            mode_index = self.display_mode_combo.findData("mean")
            if mode_index >= 0:
                self.display_mode_combo.setCurrentIndex(mode_index)
            else:
                self._update_from_current_selection()
        else:
            self._update_from_current_selection()
        self._update_area_control_states()

    def _start_polygon_capture(self, *_args) -> None:
        if self.current_layer is None or self.current_schema is None:
            self._set_area_status(
                "Selecione primeiro uma camada pontual InSAR compatível.",
                error=True,
            )
            return

        canvas = self.iface.mapCanvas()
        if self._polygon_capture_tool is None:
            self._polygon_capture_tool = PolygonCaptureTool(canvas)
            self._polygon_capture_tool.polygonCompleted.connect(
                self._on_polygon_capture_completed
            )
            self._polygon_capture_tool.canceled.connect(
                self._on_polygon_capture_canceled
            )
            self._polygon_capture_tool.deactivated.connect(
                self._on_polygon_tool_deactivated
            )

        active_tool = canvas.mapTool()
        if active_tool is not self._polygon_capture_tool:
            self._previous_map_tool = active_tool
        self.draw_area_button.setText(tr("Desenhando área..."))
        self._set_area_status(
            "Adicione ao menos três vértices. Botão direito conclui; Esc cancela."
        )
        canvas.setMapTool(self._polygon_capture_tool)
        self._update_area_control_states()

    def _on_polygon_capture_completed(self, geometry) -> None:
        canvas = self.iface.mapCanvas()
        source_crs = canvas.mapSettings().destinationCrs()
        self._restore_previous_map_tool()
        if self._apply_area_geometry(
            geometry,
            source_crs,
            description=tr("área desenhada"),
        ):
            self._show_area_geometry(geometry, source_layer=None)

    def _on_polygon_capture_canceled(self) -> None:
        self._restore_previous_map_tool()
        self._set_area_status("Desenho da área cancelado.")
        self._update_area_control_states()

    def _on_polygon_tool_deactivated(self) -> None:
        self.draw_area_button.setText(tr("Desenhar área no mapa"))
        self._update_area_control_states()

    def _restore_previous_map_tool(self) -> None:
        if self._polygon_capture_tool is None:
            self._previous_map_tool = None
            return
        canvas = self.iface.mapCanvas()
        if canvas.mapTool() is self._polygon_capture_tool:
            previous = self._previous_map_tool
            try:
                if previous is not None and previous is not self._polygon_capture_tool:
                    canvas.setMapTool(previous)
                else:
                    canvas.unsetMapTool(self._polygon_capture_tool)
            except RuntimeError:
                try:
                    canvas.unsetMapTool(self._polygon_capture_tool)
                except RuntimeError:
                    pass
        self._previous_map_tool = None
        self.draw_area_button.setText(tr("Desenhar área no mapa"))
        self._update_area_control_states()

    def _show_area_geometry(self, geometry, source_layer=None) -> None:
        canvas = self.iface.mapCanvas()
        if self._area_rubber_band is None:
            self._area_rubber_band = QgsRubberBand(
                canvas, QgsWkbTypes.PolygonGeometry
            )
            configure_persistent_rubber_band(self._area_rubber_band)
        self._area_rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self._area_rubber_band.setToGeometry(geometry, source_layer)
        self._area_rubber_band.show()
        self._has_displayed_area = True
        self._update_area_control_states()

    def _clear_drawn_area(self, *_args, update_status: bool = True) -> None:
        if self._area_rubber_band is not None:
            try:
                self._area_rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            except RuntimeError:
                self._area_rubber_band = None
        self._has_displayed_area = False
        if update_status and hasattr(self, "area_status_label"):
            self._set_area_status(
                "Área removida do mapa. A seleção de pontos foi mantida."
            )
        if hasattr(self, "clear_area_button"):
            self._update_area_control_states()

    def _use_selected_polygon_feature(self, *_args) -> None:
        layer_id = self.polygon_layer_combo.currentData()
        source_layer = self.project.mapLayer(layer_id) if layer_id else None
        if not self._is_polygon_vector_layer(source_layer):
            self._set_area_status(
                "Escolha uma camada poligonal válida.", error=True
            )
            return

        selected_ids = list(source_layer.selectedFeatureIds())
        if len(selected_ids) != 1:
            self._set_area_status(
                "Selecione exatamente uma feição na camada poligonal.",
                error=True,
            )
            return

        feature = source_layer.getFeature(selected_ids[0])
        if feature is None or not feature.isValid() or not feature.hasGeometry():
            self._set_area_status(
                "A feição poligonal selecionada não possui geometria válida.",
                error=True,
            )
            return

        geometry = feature.geometry()
        if self._apply_area_geometry(
            geometry,
            source_layer.crs(),
            description=tr("polígono de {layer}", layer=source_layer.name()),
        ):
            self._show_area_geometry(geometry, source_layer=source_layer)

    def _apply_area_geometry(
        self, geometry, source_crs, *, description: str
    ) -> bool:
        layer = self.current_layer
        if layer is None or self.current_schema is None:
            self._set_area_status(
                "Selecione primeiro uma camada pontual InSAR compatível.",
                error=True,
            )
            return False

        try:
            target_geometry = polygon_in_target_crs(
                geometry, source_crs, layer, self.project
            )
            if self._point_spatial_index is None:
                self._set_area_status(
                    "Construindo índice espacial da camada de pontos..."
                )
                self._point_spatial_index = build_point_spatial_index(layer)
            found_ids = point_ids_intersecting_polygon(
                layer, target_geometry, self._point_spatial_index
            )
            operation = self.area_operation_combo.currentData()
            final_ids = resulting_selection_ids(
                layer.selectedFeatureIds(), found_ids, operation
            )
            layer.selectByIds(final_ids)
        except SpatialSelectionError as exc:
            self._set_area_status(str(exc), error=True)
            return False
        except Exception as exc:
            self._set_area_status(
                tr(
                    "Falha inesperada na seleção espacial: {kind}: {error}",
                    kind=type(exc).__name__,
                    error=exc,
                ),
                error=True,
            )
            return False

        operation_label = self.area_operation_combo.currentText().lower()
        self._set_area_status(
            tr(
                "{description}: {found} ponto(s) encontrado(s); {operation}; {selected} ponto(s) selecionado(s) ao final.",
                description=tr(description).capitalize(),
                found=len(found_ids),
                operation=operation_label,
                selected=len(final_ids),
            )
        )
        return True

    def _invalidate_spatial_index(self, *_args) -> None:
        self._point_spatial_index = None
        self._polygon_mean_batch = None
        if hasattr(self, "polygon_mean_status_label"):
            self._set_polygon_mean_status(
                "Os pontos foram alterados; recalcule as médias por polígonos."
            )

    def _dispose_area_tools(self) -> None:
        self._restore_previous_map_tool()
        if self._polygon_capture_tool is not None:
            for signal, slot in (
                (self._polygon_capture_tool.polygonCompleted, self._on_polygon_capture_completed),
                (self._polygon_capture_tool.canceled, self._on_polygon_capture_canceled),
                (self._polygon_capture_tool.deactivated, self._on_polygon_tool_deactivated),
            ):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
            self._polygon_capture_tool.dispose()
            self._polygon_capture_tool = None

        if self._area_rubber_band is not None:
            try:
                self.iface.mapCanvas().scene().removeItem(self._area_rubber_band)
            except (AttributeError, RuntimeError):
                pass
            self._area_rubber_band = None
        self._has_displayed_area = False
        self._point_spatial_index = None

    # ------------------------------------------------------- point navigation
    def _update_selection_action_states(self) -> None:
        if not hasattr(self, "zoom_feature_button"):
            return

        has_layer = self.current_layer is not None
        has_current_feature = has_layer and self.current_feature_id is not None
        selected_count = 0
        if has_layer:
            try:
                selected_count = len(self.current_layer.selectedFeatureIds())
            except RuntimeError:
                selected_count = 0

        self.zoom_feature_button.setEnabled(has_current_feature)
        self.clear_selection_button.setEnabled(has_layer and selected_count > 0)

    def _current_feature(self):
        layer = self.current_layer
        if layer is None or self.current_feature_id is None:
            return None
        try:
            feature = layer.getFeature(int(self.current_feature_id))
        except (TypeError, RuntimeError):
            return None
        if feature is None or not feature.isValid():
            return None
        return feature

    def _clear_current_selection(self, *_args) -> None:
        if self.current_layer is not None:
            self.current_layer.removeSelection()
        self._clear_active_feature_marker()
        self._update_selection_action_states()

    def _active_feature_marker(self):
        if self._active_feature_rubber_band is None:
            band = QgsRubberBand(
                self.iface.mapCanvas(),
                QgsWkbTypes.PointGeometry,
            )
            band.setColor(QColor(255, 170, 0, 230))
            band.setWidth(3)
            if hasattr(band, "setIcon"):
                band.setIcon(QgsRubberBand.ICON_CIRCLE)
            if hasattr(band, "setIconSize"):
                band.setIconSize(14)
            self._active_feature_rubber_band = band
        return self._active_feature_rubber_band

    def _show_active_feature_marker(self, feature_id: int) -> None:
        layer = self.current_layer
        if layer is None:
            self._clear_active_feature_marker()
            return

        try:
            feature = layer.getFeature(int(feature_id))
        except (TypeError, RuntimeError):
            self._clear_active_feature_marker()
            return

        if feature is None or not feature.isValid() or not feature.hasGeometry():
            self._clear_active_feature_marker()
            return

        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            self._clear_active_feature_marker()
            return

        band = self._active_feature_marker()
        try:
            band.reset(QgsWkbTypes.PointGeometry)
            band.setToGeometry(geometry, layer)
            band.show()
        except RuntimeError:
            self._active_feature_rubber_band = None

    def _clear_active_feature_marker(self, *, remove: bool = False) -> None:
        band = self._active_feature_rubber_band
        if band is None:
            return

        try:
            band.reset(QgsWkbTypes.PointGeometry)
        except RuntimeError:
            self._active_feature_rubber_band = None
            return

        if not remove:
            return

        try:
            self.iface.mapCanvas().scene().removeItem(band)
        except (AttributeError, RuntimeError):
            pass
        self._active_feature_rubber_band = None

    def _feature_geometry_in_canvas_crs(self, feature):
        layer = self.current_layer
        if layer is None or feature is None or not feature.hasGeometry():
            return None

        geometry = QgsGeometry(feature.geometry())
        if geometry is None or geometry.isEmpty():
            return None

        canvas = self.iface.mapCanvas()
        source_crs = layer.crs()
        target_crs = canvas.mapSettings().destinationCrs()
        if source_crs.isValid() and target_crs.isValid() and source_crs != target_crs:
            try:
                transform = QgsCoordinateTransform(
                    source_crs,
                    target_crs,
                    self.project,
                )
                geometry.transform(transform)
            except (QgsCsException, RuntimeError, ValueError) as exc:
                self.status_label.setText(
                    tr(
                        "Não foi possível reprojetar o ponto para o mapa: {error}",
                        error=exc,
                    )
                )
                return None

        return geometry

    def _zoom_to_current_feature(self, *_args) -> None:
        feature = self._current_feature()
        geometry = self._feature_geometry_in_canvas_crs(feature)
        if geometry is None:
            self.status_label.setText(
                tr("Nenhum ponto válido está disponível para aproximar.")
            )
            self._update_selection_action_states()
            return

        canvas = self.iface.mapCanvas()
        bbox = geometry.boundingBox()
        center = bbox.center()
        current_extent = canvas.extent()
        fallback_width = max(current_extent.width() * 0.025, 1.0)
        fallback_height = max(current_extent.height() * 0.025, 1.0)
        half_width = max(bbox.width() * 4.0, fallback_width)
        half_height = max(bbox.height() * 4.0, fallback_height)

        canvas.setExtent(
            QgsRectangle(
                center.x() - half_width,
                center.y() - half_height,
                center.x() + half_width,
                center.y() + half_height,
            )
        )
        canvas.refresh()
        self._show_active_feature_marker(int(feature.id()))
        self.status_label.setText(
            tr("Mapa aproximado para FID {fid}.", fid=int(feature.id()))
        )
        self._update_selection_action_states()

    # ----------------------------------------------------------- selection
    def _on_selection_changed(self, selected, deselected, _clear_and_select) -> None:
        newly_selected = list(selected)
        if newly_selected:
            self.current_feature_id = newly_selected[-1]
        elif self.current_feature_id in set(deselected):
            self.current_feature_id = None
        self._update_from_current_selection()

    def _update_from_current_selection(self) -> None:
        layer = self.current_layer
        schema = self.current_schema
        if layer is None or schema is None:
            return

        if self.settings.display_mode in {
            "polygon_means_overlay",
            "polygon_means_separate",
        }:
            self._display_polygon_mean_batch()
            return

        selected_ids = sorted(layer.selectedFeatureIds())
        selected_count = len(selected_ids)
        self.selection_count_label.setText(
            tr("1 selecionada")
            if selected_count == 1
            else tr("{count} selecionadas", count=selected_count)
        )

        if not selected_ids:
            self.current_feature_id = None
            self._clear_feature_info()
            self._show_plot_message("Nenhuma feição selecionada.\nSelecione um ou mais pontos no mapa.")
            self.status_label.setText(
                "Use uma ferramenta normal de seleção do QGIS para escolher os pontos."
            )
            self._clear_active_feature_marker()
            self._update_selection_action_states()
            return

        self._update_selection_action_states()
        if self.settings.display_mode == "overlay":
            self._display_overlay_selection(selected_ids)
        elif self.settings.display_mode == "separate":
            self._display_separate_selection(selected_ids)
        elif self.settings.display_mode == "mean":
            self._display_mean_selection(selected_ids)
        else:
            self._display_single_selection(selected_ids)

    def _display_single_selection(self, selected_ids: Sequence[int]) -> None:
        if self.current_feature_id not in selected_ids:
            self.current_feature_id = selected_ids[-1]

        series, error = self._read_series(self.current_feature_id)
        if series is None:
            self._clear_feature_info()
            self._show_plot_message(tr("Não foi possível construir a série temporal."))
            self.status_label.setText(error or "Erro desconhecido na leitura da feição.")
            return

        plot_warnings = self._display_series_list([series])
        status_parts = [
            f"FID {series.feature_id}",
            tr("{count} valores válidos", count=series.valid_count),
            tr("{count} ausências/999", count=series.missing_count),
        ]
        if len(selected_ids) > 1:
            status_parts.append(
                tr(
                    "{count} feições selecionadas; o modo Série única exibe a feição escolhida mais recentemente",
                    count=len(selected_ids),
                )
            )
        status_parts.extend(plot_warnings)
        self.status_label.setText(" · ".join(status_parts) + ".")

    def _display_overlay_selection(self, selected_ids: Sequence[int]) -> None:
        selected_count = len(selected_ids)
        limited_ids = list(selected_ids[: self.settings.max_overlay_series])
        truncated = selected_count > len(limited_ids)

        series_list = []
        errors = []
        for feature_id in limited_ids:
            series, error = self._read_series(feature_id)
            if series is not None:
                series_list.append(series)
            else:
                errors.append(error or tr("FID {fid}: erro de leitura", fid=feature_id))

        if not series_list:
            self._clear_feature_info()
            self._show_plot_message(tr("Nenhuma das séries selecionadas pôde ser lida."))
            self.status_label.setText("; ".join(errors))
            return

        plot_warnings = self._display_series_list(series_list)
        status_parts = [
            tr("{count} feições selecionadas", count=selected_count),
            tr("{count} séries exibidas", count=len(series_list)),
        ]
        if truncated:
            status_parts.append(
                tr("limite atual de {count} séries aplicado", count=self.settings.max_overlay_series)
            )
        if errors:
            status_parts.append(tr("{count} séries ignoradas por erro de leitura", count=len(errors)))
        status_parts.extend(plot_warnings)
        self.status_label.setText(" · ".join(status_parts) + ".")

    def _display_separate_selection(self, selected_ids: Sequence[int]) -> None:
        selected_count = len(selected_ids)
        limited_ids = list(selected_ids[: self.settings.max_overlay_series])
        truncated = selected_count > len(limited_ids)

        series_list = []
        errors = []
        for feature_id in limited_ids:
            series, error = self._read_series(feature_id)
            if series is not None:
                series_list.append(series)
            else:
                errors.append(error or tr("FID {fid}: erro de leitura", fid=feature_id))

        if not series_list:
            self._clear_feature_info()
            self._show_plot_message(tr("Nenhuma das séries selecionadas pôde ser lida."))
            self.status_label.setText("; ".join(errors))
            return

        plot_warnings = self._display_series_list(series_list)
        status_parts = [
            tr("{count} feições selecionadas", count=selected_count),
            tr("{count} gráficos separados exibidos", count=len(series_list)),
        ]
        if truncated:
            status_parts.append(
                tr("limite atual de {count} séries aplicado", count=self.settings.max_overlay_series)
            )
        if errors:
            status_parts.append(tr("{count} séries ignoradas por erro de leitura", count=len(errors)))
        status_parts.extend(plot_warnings)
        self.status_label.setText(" · ".join(status_parts) + ".")

    def _display_mean_selection(self, selected_ids: Sequence[int]) -> None:
        selected_count = len(selected_ids)
        if selected_count < 2:
            self._clear_feature_info()
            self._show_plot_message(
                tr("A média requer pelo menos dois pontos selecionados.")
            )
            self.status_label.setText(
                "Selecione dois ou mais pontos na mesma camada para calcular a média."
            )
            return

        limited_ids = list(selected_ids[: self.settings.max_overlay_series])
        truncated = selected_count > len(limited_ids)
        series_list = []
        errors = []
        for feature_id in limited_ids:
            series, error = self._read_series(feature_id)
            if series is not None:
                series_list.append(series)
            else:
                errors.append(error or tr("FID {fid}: erro de leitura", fid=feature_id))

        if len(series_list) < 2:
            self._clear_feature_info()
            self._show_plot_message(
                "Não foi possível ler pelo menos duas séries válidas para a média."
            )
            self.status_label.setText("; ".join(errors))
            return

        try:
            result = calculate_mean_series(
                series_list,
                common_interval=self.settings.mean_common_interval,
                reference_zero=self.settings.mean_reference_zero,
            )
        except MeanSeriesError as exc:
            self._clear_feature_info()
            self._show_plot_message(tr("Não foi possível calcular a média das séries."))
            self.status_label.setText(str(exc))
            return

        plot_warnings = self._display_mean_result(result, series_list)
        status_parts = [
            tr("{count} feições selecionadas", count=selected_count),
            tr("média calculada com {count} pontos", count=result.series_count),
        ]
        if self.settings.mean_common_interval:
            status_parts.append(tr("somente aquisições comuns"))
        elif result.count_varies:
            status_parts.append(
                tr("N variável entre {minimum} e {maximum}", minimum=result.minimum_count, maximum=result.maximum_count)
            )
        else:
            status_parts.append(tr("N = {count} por aquisição", count=result.minimum_count))
        if self.settings.mean_reference_zero:
            status_parts.append(tr("séries referenciadas em zero"))
        if truncated:
            status_parts.append(
                tr("limite atual de {count} pontos aplicado", count=self.settings.max_overlay_series)
            )
        if errors:
            status_parts.append(tr("{count} séries ignoradas por erro de leitura", count=len(errors)))
        status_parts.extend(plot_warnings)
        self.status_label.setText(" · ".join(status_parts) + ".")

    def _display_polygon_mean_batch(self) -> None:
        batch = self._polygon_mean_batch
        if batch is None or not batch.groups:
            self.selection_count_label.setText("0 médias poligonais")
            self._clear_feature_info()
            self._show_plot_message(
                "Nenhuma média por polígono calculada.\n"
                "Escolha a camada poligonal e clique em Calcular médias por polígonos."
            )
            self.status_label.setText(
                "Os resultados poligonais são calculados sob demanda e não alteram "
                "a seleção dos pontos."
            )
            return

        groups = list(batch.groups)
        separate = self.settings.display_mode == "polygon_means_separate"
        self.selection_count_label.setText(
            tr("{count} médias poligonais", count=len(groups))
        )
        self._set_chart_height(len(groups) if separate else 1, separate=separate)
        component_label = self._effective_component_label()
        if separate:
            plot_warnings = render_separate_polygon_mean_series(
                self.figure,
                groups,
                self.settings,
                component_label,
            )
        else:
            plot_warnings = render_polygon_mean_series(
                self.figure,
                groups,
                self.settings,
                component_label,
            )
        self._displayed_mode = self.settings.display_mode
        self._displayed_series = []
        self._displayed_labels = []
        self._displayed_mean_result = None
        self._displayed_mean_source_series = []
        self._displayed_polygon_groups = list(groups)
        self._apply_preview_watermark()
        self.canvas.draw_idle()
        self._clear_active_feature_marker()
        self._update_selection_action_states()
        self._update_export_control_states()
        self._fill_polygon_mean_info(groups, component_label)
        self._update_additional_properties_info()
        QTimer.singleShot(
            0,
            lambda: self.chart_scroll_area.verticalScrollBar().setValue(0),
        )

        point_counts = [group.point_count for group in groups]
        status_parts = [
            tr("{count} média(s) poligonal(is) exibida(s)", count=len(groups)),
            tr("camada {name}", name=batch.source_layer_name),
            tr("{count} participação(ões) de pontos", count=sum(point_counts)),
        ]
        if min(point_counts) != max(point_counts):
            status_parts.append(
                tr("entre {minimum} e {maximum} pontos por polígono", minimum=min(point_counts), maximum=max(point_counts))
            )
        else:
            status_parts.append(tr("{count} pontos por polígono", count=point_counts[0]))
        if batch.polygons_without_points:
            status_parts.append(
                tr("{count} polígono(s) sem pontos ignorado(s)", count=len(batch.polygons_without_points))
            )
        if batch.polygons_with_errors:
            status_parts.append(
                tr("{count} polígono(s) com erro ignorado(s)", count=len(batch.polygons_with_errors))
            )
        status_parts.extend(plot_warnings)
        self.status_label.setText(" · ".join(status_parts) + ".")

    def _fill_polygon_mean_info(self, groups, component_label: str) -> None:
        velocities = [
            group.result.mean_velocity
            for group in groups
            if group.result.mean_velocity is not None
        ]
        velocity_stds = [
            group.result.mean_velocity_std
            for group in groups
            if group.result.mean_velocity_std is not None
        ]
        cumulative = [group.result.cumulative_displacement for group in groups]
        earliest = min(group.result.first_valid_date for group in groups)
        latest = max(group.result.last_valid_date for group in groups)

        self.value_identifier.setText(tr("{count} médias poligonais", count=len(groups)))
        self.value_component.setText(component_label)
        self.value_velocity.setText(
            self._format_numeric_range(velocities, " mm/ano")
        )
        self.value_velocity_std.setText(
            self._format_numeric_range(velocity_stds, " mm/ano")
        )
        self.value_cumulative.setText(
            self._format_numeric_range(cumulative, " mm")
        )
        self.value_coverage.setText(
            tr("{start} a {end}", start=f"{earliest:%d/%m/%Y}", end=f"{latest:%d/%m/%Y}")
        )

    def _read_series(self, feature_id: int):
        layer = self.current_layer
        schema = self.current_schema
        if layer is None or schema is None:
            return None, tr("Nenhuma camada ativa no visualizador.")

        feature = layer.getFeature(feature_id)
        if feature is None or not feature.isValid():
            return None, tr("FID {fid}: feição inválida ou removida.", fid=feature_id)

        try:
            return read_feature(layer, feature, schema=schema), None
        except (FeatureReadError, LayerValidationError) as exc:
            return None, f"FID {feature_id}: {exc}"

    # --------------------------------------------------------------- chart
    def _display_series_list(self, series_list: Sequence[TimeSeriesData]) -> list[str]:
        component_label = self._effective_component_label()
        labels = self._unique_legend_labels(series_list)
        separate = self.settings.display_mode == "separate"
        self._set_chart_height(len(series_list) if separate else 1, separate=separate)

        if separate:
            plot_warnings = render_separate_time_series(
                self.figure,
                series_list,
                labels,
                self.settings,
                component_label,
            )
        else:
            plot_warnings = render_time_series(
                self.figure,
                series_list,
                labels,
                self.settings,
                component_label,
            )
        self._displayed_mode = self.settings.display_mode
        self._displayed_series = list(series_list)
        self._displayed_labels = list(labels)
        self._displayed_mean_result = None
        self._displayed_mean_source_series = []
        self._displayed_polygon_groups = []
        self._apply_preview_watermark()
        self.canvas.draw_idle()
        self._update_export_control_states()

        if separate:
            QTimer.singleShot(
                0,
                lambda: self.chart_scroll_area.verticalScrollBar().setValue(0),
            )

        if len(series_list) == 1:
            self._show_active_feature_marker(series_list[0].feature_id)
            self._fill_single_info(series_list[0], component_label)
        else:
            self._clear_active_feature_marker()
            self._fill_multiple_info(series_list, component_label)
        self._update_selection_action_states()
        self._update_additional_properties_info()
        return plot_warnings

    def _display_mean_result(
        self,
        result: MeanSeriesResult,
        source_series: Sequence[TimeSeriesData],
    ) -> list[str]:
        component_label = self._effective_component_label()
        self._set_chart_height(1, separate=False)
        plot_warnings = render_mean_time_series(
            self.figure,
            result,
            self.settings,
            component_label,
        )
        self._displayed_mode = "mean"
        self._displayed_series = []
        self._displayed_labels = []
        self._displayed_mean_result = result
        self._displayed_mean_source_series = list(source_series)
        self._displayed_polygon_groups = []
        self._apply_preview_watermark()
        self.canvas.draw_idle()
        self._clear_active_feature_marker()
        self._update_selection_action_states()
        self._update_export_control_states()
        self._fill_mean_info(result, component_label)
        self._update_additional_properties_info()
        QTimer.singleShot(
            0,
            lambda: self.chart_scroll_area.verticalScrollBar().setValue(0),
        )
        return plot_warnings

    def _set_chart_height(self, series_count: int, *, separate: bool) -> None:
        if separate:
            # Altura suficiente para manter cada gráfico individual legível.
            target_height = max(340, int(series_count) * 250)
        else:
            target_height = 280
        self.canvas.setMinimumHeight(target_height)
        self.chart_container.setMinimumHeight(target_height)
        self.chart_container.updateGeometry()

    def _fill_single_info(
        self, series: TimeSeriesData, component_label: str
    ) -> None:
        self.value_identifier.setText(series.identifier)
        self.value_component.setText(component_label)
        self.value_velocity.setText(self._format_mm_per_year(series.velocity))
        self.value_velocity_std.setText(
            self._format_mm_per_year(series.velocity_std)
        )
        self.value_cumulative.setText(f"{series.cumulative_displacement:.1f} mm")
        self.value_coverage.setText(
            f"{series.first_valid_date:%d/%m/%Y} a "
            f"{series.last_valid_date:%d/%m/%Y} "
            f"({series.valid_count}/{series.acquisition_count})"
        )

    def _fill_mean_info(
        self, result: MeanSeriesResult, component_label: str
    ) -> None:
        self.value_identifier.setText(tr("Média de {count} pontos", count=result.series_count))
        self.value_component.setText(component_label)
        self.value_velocity.setText(self._format_mm_per_year(result.mean_velocity))
        self.value_velocity_std.setText(
            self._format_mm_per_year(result.mean_velocity_std)
        )
        self.value_cumulative.setText(
            f"{result.cumulative_displacement:.1f} mm"
        )
        self.value_coverage.setText(
            f"{result.first_valid_date:%d/%m/%Y} a "
            f"{result.last_valid_date:%d/%m/%Y} "
            f"({result.valid_count}/{result.acquisition_count})"
        )

    def _fill_multiple_info(
        self, series_list: Sequence[TimeSeriesData], component_label: str
    ) -> None:
        velocities = [item.velocity for item in series_list if item.velocity is not None]
        uncertainties = [
            item.velocity_std for item in series_list if item.velocity_std is not None
        ]
        cumulative = [item.cumulative_displacement for item in series_list]
        earliest = min(item.first_valid_date for item in series_list)
        latest = max(item.last_valid_date for item in series_list)

        self.value_identifier.setText(tr("{count} séries", count=len(series_list)))
        self.value_component.setText(component_label)
        self.value_velocity.setText(self._format_numeric_range(velocities, " mm/ano"))
        self.value_velocity_std.setText(
            self._format_numeric_range(uncertainties, " mm/ano")
        )
        self.value_cumulative.setText(self._format_numeric_range(cumulative, " mm"))
        self.value_coverage.setText(
            tr("{start} a {end}", start=f"{earliest:%d/%m/%Y}", end=f"{latest:%d/%m/%Y}")
        )

    @staticmethod
    def _unique_legend_labels(series_list: Sequence[TimeSeriesData]) -> list[str]:
        counts = Counter(item.identifier for item in series_list)
        return [
            (
                f"{item.identifier} [FID {item.feature_id}]"
                if counts[item.identifier] > 1
                else item.identifier
            )
            for item in series_list
        ]

    def _show_plot_message(self, message: str) -> None:
        self._clear_export_payload()
        self._clear_active_feature_marker()
        self._update_selection_action_states()
        self._set_chart_height(1, separate=False)
        render_message(self.figure, tr(message))
        self.canvas.draw_idle()
        self._update_export_control_states()
        QTimer.singleShot(
            0,
            lambda: self.chart_scroll_area.verticalScrollBar().setValue(0),
        )

    # ------------------------------------------------------------- export
    def _clear_export_payload(self) -> None:
        self._displayed_mode = None
        self._displayed_series = []
        self._displayed_labels = []
        self._displayed_mean_result = None
        self._displayed_mean_source_series = []
        self._displayed_polygon_groups = []

    def _apply_preview_watermark(self) -> None:
        apply_watermark(
            self.figure,
            enabled=self.settings.watermark_preview,
            opacity=self.settings.watermark_opacity,
            position=self.settings.watermark_position,
            scale=self.settings.watermark_scale,
        )

    def _update_export_control_states(self) -> None:
        if not hasattr(self, "export_current_button"):
            return
        has_current = bool(
            self._displayed_series or
            self._displayed_mean_result is not None or
            self._displayed_polygon_groups
        )
        batch_count = max(
            len(self._displayed_series),
            len(self._displayed_polygon_groups),
        )
        self.export_current_button.setEnabled(has_current)
        self.export_batch_button.setEnabled(batch_count >= 1)

    def _export_current_graph(self, *_args) -> None:
        if not (
            self._displayed_series or
            self._displayed_mean_result is not None or
            self._displayed_polygon_groups
        ):
            QMessageBox.information(
                self,
                tr("Exportação"),
                tr("Não há gráfico válido para exportar."),
            )
            return

        file_format = self.settings.export_format
        initial_dir = self._export_initial_directory()
        suggested = ensure_extension(
            initial_dir / sanitize_filename(self._current_export_basename()),
            file_format,
        )
        filter_text = {
            "png": tr("Imagem PNG (*.png)"),
            "svg": tr("Gráfico vetorial SVG (*.svg)"),
            "pdf": tr("Documento PDF (*.pdf)"),
        }[file_format]
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("Salvar gráfico"),
            str(suggested),
            filter_text,
        )
        if not filename:
            return

        target = ensure_extension(Path(filename), file_format)
        try:
            figure = self._render_current_export_figure()
            self._save_export_figure(figure, target)
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("Falha na exportação"),
                tr("Não foi possível salvar o gráfico.\n\n{kind}: {error}", kind=type(exc).__name__, error=exc),
            )
            return

        self._remember_export_directory(target.parent)
        self.status_label.setText(tr("Gráfico exportado para {path}.", path=target))
        QMessageBox.information(
            self,
            tr("Exportação concluída"),
            tr("Gráfico salvo em:\n{path}", path=target),
        )

    def _export_batch_graphs(self, *_args) -> None:
        if not self._displayed_series and not self._displayed_polygon_groups:
            QMessageBox.information(
                self,
                tr("Exportação em lote"),
                tr("O gráfico atual não contém séries individuais exportáveis."),
            )
            return

        folder = QFileDialog.getExistingDirectory(
            self,
            tr("Escolher pasta para os gráficos"),
            str(self._export_initial_directory()),
        )
        if not folder:
            return
        destination = Path(folder)
        file_format = self.settings.export_format
        saved_paths = []
        errors = []

        if self._displayed_series:
            labels = self._displayed_labels or self._unique_legend_labels(
                self._displayed_series
            )
            for series, label in zip(self._displayed_series, labels):
                base = sanitize_filename(
                    f"{label}_{self._component_token()}",
                    fallback=f"serie_FID_{series.feature_id}",
                )
                path = available_path(
                    ensure_extension(destination / base, file_format)
                )
                try:
                    figure = self._render_single_series_export_figure(
                        series,
                        label,
                    )
                    self._save_export_figure(figure, path)
                    saved_paths.append(path)
                except Exception as exc:
                    errors.append(f"{label}: {type(exc).__name__}: {exc}")

        if self._displayed_polygon_groups:
            for group in self._displayed_polygon_groups:
                base = sanitize_filename(
                    f"{group.label}_{self._component_token()}_mean",
                    fallback=f"polygon_FID_{group.polygon_fid}_mean",
                )
                path = available_path(
                    ensure_extension(destination / base, file_format)
                )
                try:
                    figure = self._render_polygon_group_export_figure(group)
                    self._save_export_figure(figure, path)
                    saved_paths.append(path)
                except Exception as exc:
                    errors.append(
                        f"{group.label}: {type(exc).__name__}: {exc}"
                    )

        self._remember_export_directory(destination)
        if saved_paths:
            message = tr("{count} arquivo(s) salvo(s) em:\n{destination}", count=len(saved_paths), destination=destination)
            if errors:
                message += tr("\n\n{count} item(ns) falharam.", count=len(errors))
            self.status_label.setText(
                tr(
                    "Exportação em lote: {saved} arquivo(s) salvo(s){failures}",
                    saved=len(saved_paths),
                    failures=(
                        tr("; {count} falha(s).", count=len(errors))
                        if errors
                        else "."
                    ),
                )
            )
            QMessageBox.information(self, tr("Exportação em lote"), tr(message))
        else:
            detail = "\n".join(errors[:5]) or tr("Erro desconhecido.")
            QMessageBox.critical(
                self,
                tr("Falha na exportação em lote"),
                tr("Nenhum arquivo foi salvo.\n\n{detail}", detail=detail),
            )

    def _render_current_export_figure(self):
        mode = self._displayed_mode or self.settings.display_mode
        separate_count = 1
        separate = mode in {"separate", "polygon_means_separate"}
        if mode == "separate":
            separate_count = len(self._displayed_series)
        elif mode == "polygon_means_separate":
            separate_count = len(self._displayed_polygon_groups)
        figure = self._new_export_figure(
            series_count=max(separate_count, 1),
            separate=separate,
        )
        component_label = self._effective_component_label()

        if mode == "mean" and self._displayed_mean_result is not None:
            render_mean_time_series(
                figure,
                self._displayed_mean_result,
                self.settings,
                component_label,
            )
        elif mode in {"polygon_means_overlay", "polygon_means_separate"}:
            groups = self._displayed_polygon_groups
            if mode == "polygon_means_separate":
                render_separate_polygon_mean_series(
                    figure,
                    groups,
                    self.settings,
                    component_label,
                )
            else:
                render_polygon_mean_series(
                    figure,
                    groups,
                    self.settings,
                    component_label,
                )
        elif self._displayed_series:
            if mode == "separate":
                render_separate_time_series(
                    figure,
                    self._displayed_series,
                    self._displayed_labels,
                    self.settings,
                    component_label,
                )
            else:
                render_time_series(
                    figure,
                    self._displayed_series,
                    self._displayed_labels,
                    self.settings,
                    component_label,
                )
        else:
            raise ValueError(tr("O estado atual do gráfico não contém dados exportáveis."))

        self._finish_export_figure(figure, self._current_export_header())
        return figure

    def _render_single_series_export_figure(
        self,
        series: TimeSeriesData,
        label: str,
    ):
        figure = self._new_export_figure(series_count=1, separate=False)
        render_time_series(
            figure,
            [series],
            [label],
            self.settings,
            self._effective_component_label(),
        )
        self._finish_export_figure(figure, self._series_export_header(series))
        return figure

    def _render_polygon_group_export_figure(self, group):
        figure = self._new_export_figure(series_count=1, separate=False)
        render_mean_time_series(
            figure,
            group.result,
            self.settings,
            self._effective_component_label(),
        )
        if figure.axes:
            figure.axes[0].set_title(
                f"{group.label} — {self._effective_component_label()}"
            )
        self._finish_export_figure(
            figure,
            self._polygon_group_export_header(group),
        )
        return figure

    def _new_export_figure(self, *, series_count: int, separate: bool):
        width = self.settings.export_width_cm / 2.54
        height_cm = self.settings.export_height_cm
        if separate:
            height_cm = max(height_cm, max(series_count, 1) * 7.0)
        height = height_cm / 2.54
        return Figure(
            figsize=(width, height),
            dpi=self.settings.export_dpi,
            constrained_layout=False,
        )

    def _finish_export_figure(self, figure, header: str) -> None:
        if self.settings.export_include_header and len(figure.axes) == 1:
            # Nos gráficos de referência o cabeçalho de dados ocupa o lugar do
            # título principal; evitar um segundo título elimina sobreposição.
            figure.axes[0].set_title("")
        apply_watermark(
            figure,
            enabled=self.settings.watermark_export,
            opacity=self.settings.watermark_opacity,
            position=self.settings.watermark_position,
            scale=self.settings.watermark_scale,
        )
        add_export_header(
            figure,
            header,
            enabled=self.settings.export_include_header,
        )
        if self.settings.export_include_header:
            top = 0.925 if "\n" in header else 0.955
            figure.tight_layout(rect=(0.0, 0.0, 1.0, top), h_pad=1.2)
        else:
            figure.tight_layout(h_pad=1.2)

    def _save_export_figure(self, figure, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        save_figure(
            figure,
            path,
            file_format=self.settings.export_format,
            dpi=self.settings.export_dpi,
            transparent=self.settings.export_transparent,
        )

    def _current_export_header(self) -> str:
        mode = self._displayed_mode or self.settings.display_mode
        if mode == "mean" and self._displayed_mean_result is not None:
            return self._mean_export_header(
                self._displayed_mean_result,
                [item.feature_id for item in self._displayed_mean_source_series],
            )
        if mode in {"polygon_means_overlay", "polygon_means_separate"}:
            groups = self._displayed_polygon_groups
            if len(groups) == 1:
                return self._polygon_group_export_header(groups[0])
            return self._polygon_batch_export_header(groups)
        if len(self._displayed_series) == 1:
            return self._series_export_header(self._displayed_series[0])
        return self._multiple_series_export_header(self._displayed_series)

    def _series_export_header(self, series: TimeSeriesData) -> str:
        schema = self.current_schema
        identifier_name = (schema.identifier_field or "FID") if schema else "ID"
        velocity_name = schema.velocity_field if schema else "VEL"
        velocity_std_name = schema.velocity_std_field if schema else "V_STDEV"
        header = (
            f"{identifier_name}: {series.identifier} | "
            f"{velocity_name}: {self._header_number(series.velocity)} | "
            f"Cumulative Displacement: "
            f"{self._header_number(series.cumulative_displacement)} | "
            f"{velocity_std_name}: {self._header_number(series.velocity_std)}"
        )
        suffix = self._additional_header_suffix_for_ids(
            [series.feature_id],
            mode="single",
        )
        return self._join_export_header(header, suffix)

    def _mean_export_header(
        self,
        result: MeanSeriesResult,
        point_ids: Sequence[int] = (),
    ) -> str:
        schema = self.current_schema
        velocity_name = schema.velocity_field if schema else "VEL"
        velocity_std_name = schema.velocity_std_field if schema else "V_STDEV"
        header = (
            f"Mean of {result.series_count} points | "
            f"{velocity_name}: {self._header_number(result.mean_velocity)} | "
            f"Cumulative Displacement: "
            f"{self._header_number(result.cumulative_displacement)} | "
            f"{velocity_std_name}: "
            f"{self._header_number(result.mean_velocity_std)}"
        )
        suffix = self._additional_header_suffix_for_ids(
            point_ids,
            mode="mean",
        )
        return self._join_export_header(header, suffix)

    def _multiple_series_export_header(self, series_list) -> str:
        schema = self.current_schema
        velocity_name = schema.velocity_field if schema else "VEL"
        velocity_std_name = schema.velocity_std_field if schema else "V_STDEV"
        velocities = [item.velocity for item in series_list if item.velocity is not None]
        velocity_stds = [
            item.velocity_std for item in series_list if item.velocity_std is not None
        ]
        cumulative = [item.cumulative_displacement for item in series_list]
        header = (
            f"{len(series_list)} series | "
            f"{velocity_name}: {self._header_range(velocities)} | "
            f"Cumulative Displacement: {self._header_range(cumulative)} | "
            f"{velocity_std_name}: {self._header_range(velocity_stds)}"
        )
        suffix = self._additional_header_suffix_for_ids(
            [item.feature_id for item in series_list],
            mode="range",
        )
        return self._join_export_header(header, suffix)

    def _polygon_group_export_header(self, group) -> str:
        return (
            f"{group.label} | "
            f"{self._mean_export_header(group.result, group.point_ids)}"
        )

    def _polygon_batch_export_header(self, groups) -> str:
        schema = self.current_schema
        velocity_name = schema.velocity_field if schema else "VEL"
        velocity_std_name = schema.velocity_std_field if schema else "V_STDEV"
        velocities = [
            group.result.mean_velocity
            for group in groups
            if group.result.mean_velocity is not None
        ]
        velocity_stds = [
            group.result.mean_velocity_std
            for group in groups
            if group.result.mean_velocity_std is not None
        ]
        cumulative = [group.result.cumulative_displacement for group in groups]
        header = (
            f"Means of {len(groups)} polygons | "
            f"{velocity_name}: {self._header_range(velocities)} | "
            f"Cumulative Displacement: {self._header_range(cumulative)} | "
            f"{velocity_std_name}: {self._header_range(velocity_stds)}"
        )
        suffix = self._additional_header_suffix_for_groups(groups)
        return self._join_export_header(header, suffix)

    def _current_export_basename(self) -> str:
        mode = self._displayed_mode or self.settings.display_mode
        component = self._component_token()
        if len(self._displayed_series) == 1:
            return f"{self._displayed_series[0].identifier}_{component}"
        if mode == "mean" and self._displayed_mean_result is not None:
            return f"mean_{self._displayed_mean_result.series_count}_points_{component}"
        if mode == "overlay":
            return f"{len(self._displayed_series)}_series_overlay_{component}"
        if mode == "separate":
            return f"{len(self._displayed_series)}_series_separate_{component}"
        if mode == "polygon_means_overlay":
            return f"{len(self._displayed_polygon_groups)}_polygon_means_overlay_{component}"
        if mode == "polygon_means_separate":
            return f"{len(self._displayed_polygon_groups)}_polygon_means_separate_{component}"
        return f"insar_timeseries_{component}"

    def _component_token(self) -> str:
        if self.current_schema is None:
            return "INSAR"
        if self.current_schema.component_key == "vertical":
            return "VERT"
        if self.current_schema.component_key == "east_west":
            return "EW"
        label = self._effective_component_label().casefold()
        if "ascendente" in label or "ascending" in label:
            return "LOS_ASC"
        if "descendente" in label or "descending" in label:
            return "LOS_DESC"
        return "LOS"

    def _export_initial_directory(self) -> Path:
        candidates = [
            self.settings.export_last_dir,
            self.project.homePath(),
            str(Path.home()),
        ]
        for candidate in candidates:
            if candidate:
                path = Path(candidate)
                if path.exists():
                    return path
        return Path.home()

    def _remember_export_directory(self, directory: Path) -> None:
        self.settings.export_last_dir = str(directory)
        self.settings.save(self.project)

    @staticmethod
    def _join_export_header(primary: str, suffix: str) -> str:
        suffix = str(suffix or "").strip()
        if not suffix:
            return primary
        if suffix.startswith("| "):
            suffix = suffix[2:].strip()
        return f"{primary}\n{suffix}"

    @staticmethod
    def _header_number(value) -> str:
        return "—" if value is None else f"{float(value):.1f}"

    @classmethod
    def _header_range(cls, values) -> str:
        numeric = [float(value) for value in values if value is not None]
        if not numeric:
            return "—"
        low = min(numeric)
        high = max(numeric)
        if abs(high - low) < 1e-12:
            return cls._header_number(low)
        return f"{low:.1f} to {high:.1f}"

    # --------------------------------------------------------------- hover
    def _on_canvas_hover(self, event) -> None:
        if (
            not self.settings.show_hover or
            event.inaxes is None or
            event.x is None or
            event.y is None
        ):
            self._hide_hover_annotations()
            return

        axes = event.inaxes
        best = None
        threshold_pixels = 9.0

        for line in axes.lines:
            if not line.get_visible():
                continue
            metadata = getattr(line, "_insar_hover_data", None)
            if not metadata:
                continue

            dates = metadata.get("dates", ())
            values = metadata.get("values", ())
            candidates = []
            source_indexes = []
            for index, (item_date, item_value) in enumerate(zip(dates, values)):
                if item_value is None:
                    continue
                try:
                    numeric_value = float(item_value)
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(numeric_value):
                    continue
                candidates.append((date2num(item_date), numeric_value))
                source_indexes.append(index)

            if not candidates:
                continue

            display_points = axes.transData.transform(np.asarray(candidates))
            distances = np.hypot(
                display_points[:, 0] - event.x,
                display_points[:, 1] - event.y,
            )
            local_index = int(np.argmin(distances))
            distance = float(distances[local_index])
            if distance > threshold_pixels:
                continue
            if best is None or distance < best[0]:
                original_index = source_indexes[local_index]
                best = (
                    distance,
                    line,
                    metadata,
                    original_index,
                    candidates[local_index],
                )

        if best is None:
            self._hide_hover_annotations()
            return

        _distance, line, metadata, index, xy = best
        annotation = getattr(axes, "_insar_hover_annotation", None)
        if annotation is None:
            annotation = axes.annotate(
                "",
                xy=xy,
                xytext=(12, 12),
                textcoords="offset points",
                ha="left",
                va="bottom",
                fontsize="small",
                bbox={
                    "boxstyle": "round,pad=0.35",
                    "facecolor": "white",
                    "edgecolor": "0.25",
                    "alpha": 0.94,
                },
                arrowprops={
                    "arrowstyle": "->",
                    "color": "0.25",
                    "linewidth": 0.7,
                },
                zorder=20,
            )
            self._configure_hover_annotation_layout(annotation)
            axes._insar_hover_annotation = annotation

        item_date = metadata["dates"][index]
        value = float(metadata["values"][index])
        text_parts = [
            str(metadata.get("label") or tr("Série")),
            tr("Data: {date}", date=f"{item_date:%d/%m/%Y}"),
            tr("Deslocamento acumulado: {value:.1f} mm", value=value),
        ]
        counts = metadata.get("counts")
        if counts is not None and index < len(counts):
            count = counts[index]
            if count is not None:
                noun = tr("ponto") if int(count) == 1 else tr("pontos")
                text_parts.append(f"N: {int(count)} {noun}")

        for other_axes in self.figure.axes:
            other = getattr(other_axes, "_insar_hover_annotation", None)
            if other is not None and other is not annotation:
                other.set_visible(False)

        placement = self._hover_annotation_placement(axes, event)
        xytext, horizontal_alignment, vertical_alignment = placement
        hover_key = (id(line), index, tuple(xytext), tuple(text_parts))

        if (
            getattr(axes, "_insar_hover_key", None) == hover_key and
            annotation.get_visible()
        ):
            return

        axes._insar_hover_key = hover_key
        annotation.xy = xy
        annotation.set_position(xytext)
        annotation.set_ha(horizontal_alignment)
        annotation.set_va(vertical_alignment)
        annotation.set_text("\n".join(text_parts))
        annotation.set_visible(True)
        self.canvas.draw_idle()

    def _hover_annotation_placement(self, axes, event):
        bbox = axes.bbox
        x_mid = bbox.x0 + bbox.width * 0.5
        y_mid = bbox.y0 + bbox.height * 0.5

        if event.x >= x_mid:
            x_offset = -12
            horizontal_alignment = "right"
        else:
            x_offset = 12
            horizontal_alignment = "left"

        if event.y >= y_mid:
            y_offset = -12
            vertical_alignment = "top"
        else:
            y_offset = 12
            vertical_alignment = "bottom"

        return (x_offset, y_offset), horizontal_alignment, vertical_alignment

    def _configure_hover_annotation_layout(self, annotation) -> None:
        annotation.set_clip_on(False)
        try:
            annotation.set_annotation_clip(False)
        except AttributeError:
            pass
        try:
            annotation.set_in_layout(False)
        except AttributeError:
            pass

    def _hide_hover_annotations(self) -> None:
        changed = False
        for axes in self.figure.axes:
            annotation = getattr(axes, "_insar_hover_annotation", None)
            if annotation is not None and annotation.get_visible():
                annotation.set_visible(False)
                axes._insar_hover_key = None
                changed = True
        if changed:
            self.canvas.draw_idle()

    # ------------------------------------------------------------ settings
    def _sync_controls_from_settings(self) -> None:
        self._updating_controls = True
        try:
            self.display_mode_combo.setCurrentIndex(
                max(0, self.display_mode_combo.findData(self.settings.display_mode))
            )
            self.show_lines_check.setChecked(self.settings.show_lines)
            self.show_markers_check.setChecked(self.settings.show_markers)
            self.show_zero_line_check.setChecked(self.settings.show_zero_line)
            self.show_legend_check.setChecked(self.settings.show_legend)
            self.show_hover_check.setChecked(self.settings.show_hover)
            self.line_width_spin.setValue(self.settings.line_width)
            self.marker_size_spin.setValue(self.settings.marker_size)
            self.max_series_spin.setValue(self.settings.max_overlay_series)
            self.show_trendline_check.setChecked(self.settings.show_trendline)
            self.trendline_scope_combo.setCurrentIndex(
                max(0, self.trendline_scope_combo.findData(self.settings.trendline_scope))
            )
            self.horizontal_grid_check.setChecked(self.settings.show_horizontal_grid)
            self.vertical_grid_check.setChecked(self.settings.show_vertical_grid)
            self.horizontal_grid_style_combo.setCurrentIndex(
                max(
                    0,
                    self.horizontal_grid_style_combo.findData(
                        self.settings.horizontal_grid_style
                    ),
                )
            )
            self.vertical_grid_style_combo.setCurrentIndex(
                max(
                    0,
                    self.vertical_grid_style_combo.findData(
                        self.settings.vertical_grid_style
                    ),
                )
            )
            self.show_shaded_period_check.setChecked(
                self.settings.show_shaded_period
            )
            self.shade_opacity_spin.setValue(
                round(self.settings.shade_opacity * 100)
            )
            self.y_manual_check.setChecked(self.settings.y_manual)
            self.y_min_spin.setValue(self.settings.y_min)
            self.y_max_spin.setValue(self.settings.y_max)
            self.y_tick_spin.setValue(self.settings.y_tick_interval)
            self.x_manual_check.setChecked(self.settings.x_manual)
            self.x_tick_days_spin.setValue(self.settings.x_tick_days)
            self.mean_common_interval_check.setChecked(
                self.settings.mean_common_interval
            )
            self.mean_reference_zero_check.setChecked(
                self.settings.mean_reference_zero
            )
            self.mean_show_dispersion_check.setChecked(
                self.settings.mean_show_dispersion
            )
            self.mean_show_individuals_check.setChecked(
                self.settings.mean_show_individuals
            )
            self.show_additional_panel_check.setChecked(
                self.settings.show_additional_properties_panel
            )
            self.export_additional_properties_check.setChecked(
                self.settings.export_additional_properties
            )
            self.export_format_combo.setCurrentIndex(
                max(0, self.export_format_combo.findData(self.settings.export_format))
            )
            self.export_width_spin.setValue(self.settings.export_width_cm)
            self.export_height_spin.setValue(self.settings.export_height_cm)
            self.export_dpi_spin.setValue(self.settings.export_dpi)
            self.export_transparent_check.setChecked(
                self.settings.export_transparent
            )
            self.export_header_check.setChecked(
                self.settings.export_include_header
            )
            self.watermark_export_check.setChecked(
                self.settings.watermark_export
            )
            self.watermark_preview_check.setChecked(
                self.settings.watermark_preview
            )
            self.watermark_opacity_spin.setValue(
                round(self.settings.watermark_opacity * 100)
            )
            self.watermark_position_combo.setCurrentIndex(
                max(
                    0,
                    self.watermark_position_combo.findData(
                        self.settings.watermark_position
                    ),
                )
            )
            self.watermark_scale_spin.setValue(
                round(self.settings.watermark_scale * 100)
            )
            self._set_date_edit_from_iso(self.x_start_edit, self.settings.x_start)
            self._set_date_edit_from_iso(self.x_end_edit, self.settings.x_end)
            self._set_date_edit_from_iso(
                self.shade_start_edit, self.settings.shade_start
            )
            self._set_date_edit_from_iso(self.shade_end_edit, self.settings.shade_end)
            self._update_axis_control_states()
        finally:
            self._updating_controls = False

    def _on_plot_settings_changed(self, *_args) -> None:
        if self._updating_controls:
            return

        sender = self.sender()
        self._updating_controls = True
        try:
            if sender is self.show_lines_check:
                if not self.show_lines_check.isChecked() and not self.show_markers_check.isChecked():
                    self.show_markers_check.setChecked(True)
            elif sender is self.show_markers_check:
                if not self.show_markers_check.isChecked() and not self.show_lines_check.isChecked():
                    self.show_lines_check.setChecked(True)
        finally:
            self._updating_controls = False

        self.settings.display_mode = self.display_mode_combo.currentData()
        self.settings.show_lines = self.show_lines_check.isChecked()
        self.settings.show_markers = self.show_markers_check.isChecked()
        self.settings.show_zero_line = self.show_zero_line_check.isChecked()
        self.settings.show_legend = self.show_legend_check.isChecked()
        self.settings.show_hover = self.show_hover_check.isChecked()
        self.settings.line_width = self.line_width_spin.value()
        self.settings.marker_size = self.marker_size_spin.value()
        self.settings.max_overlay_series = self.max_series_spin.value()
        self.settings.show_trendline = self.show_trendline_check.isChecked()
        self.settings.trendline_scope = self.trendline_scope_combo.currentData()
        self.settings.show_horizontal_grid = self.horizontal_grid_check.isChecked()
        self.settings.show_vertical_grid = self.vertical_grid_check.isChecked()
        self.settings.horizontal_grid_style = (
            self.horizontal_grid_style_combo.currentData()
        )
        self.settings.vertical_grid_style = (
            self.vertical_grid_style_combo.currentData()
        )
        self.settings.show_shaded_period = (
            self.show_shaded_period_check.isChecked()
        )
        self.settings.shade_start = (
            self.shade_start_edit.date().toString(Qt.ISODate)
        )
        self.settings.shade_end = self.shade_end_edit.date().toString(Qt.ISODate)
        self.settings.shade_opacity = self.shade_opacity_spin.value() / 100.0
        self.settings.y_manual = self.y_manual_check.isChecked()
        self.settings.y_min = self.y_min_spin.value()
        self.settings.y_max = self.y_max_spin.value()
        self.settings.y_tick_interval = self.y_tick_spin.value()
        self.settings.x_manual = self.x_manual_check.isChecked()
        self.settings.x_start = self.x_start_edit.date().toString(Qt.ISODate)
        self.settings.x_end = self.x_end_edit.date().toString(Qt.ISODate)
        self.settings.x_tick_days = self.x_tick_days_spin.value()
        self.settings.mean_common_interval = (
            self.mean_common_interval_check.isChecked()
        )
        self.settings.mean_reference_zero = (
            self.mean_reference_zero_check.isChecked()
        )
        self.settings.mean_show_dispersion = (
            self.mean_show_dispersion_check.isChecked()
        )
        self.settings.mean_show_individuals = (
            self.mean_show_individuals_check.isChecked()
        )
        self.settings.show_additional_properties_panel = (
            self.show_additional_panel_check.isChecked()
        )
        self.settings.export_additional_properties = (
            self.export_additional_properties_check.isChecked()
        )
        self.settings.export_format = self.export_format_combo.currentData()
        self.settings.export_width_cm = self.export_width_spin.value()
        self.settings.export_height_cm = self.export_height_spin.value()
        self.settings.export_dpi = self.export_dpi_spin.value()
        self.settings.export_transparent = self.export_transparent_check.isChecked()
        self.settings.export_include_header = self.export_header_check.isChecked()
        self.settings.watermark_export = self.watermark_export_check.isChecked()
        self.settings.watermark_preview = self.watermark_preview_check.isChecked()
        self.settings.watermark_opacity = self.watermark_opacity_spin.value() / 100.0
        self.settings.watermark_position = self.watermark_position_combo.currentData()
        self.settings.watermark_scale = self.watermark_scale_spin.value() / 100.0
        self.settings.normalized().save(self.project)
        self._update_axis_control_states()
        if (
            self.settings.display_mode
            in {"polygon_means_overlay", "polygon_means_separate"} and
            self._polygon_mean_batch is not None and
            sender
            in {self.mean_common_interval_check, self.mean_reference_zero_check}
        ):
            self._calculate_polygon_means()
            return
        self._update_from_current_selection()

    def _update_axis_control_states(self) -> None:
        y_enabled = self.y_manual_check.isChecked()
        self.y_min_spin.setEnabled(y_enabled)
        self.y_max_spin.setEnabled(y_enabled)
        x_enabled = self.x_manual_check.isChecked()
        self.x_start_edit.setEnabled(x_enabled)
        self.x_end_edit.setEnabled(x_enabled)
        self.trendline_scope_combo.setEnabled(
            self.show_trendline_check.isChecked()
        )
        self.horizontal_grid_style_combo.setEnabled(
            self.horizontal_grid_check.isChecked()
        )
        self.vertical_grid_style_combo.setEnabled(
            self.vertical_grid_check.isChecked()
        )
        shade_enabled = self.show_shaded_period_check.isChecked()
        self.shade_start_edit.setEnabled(shade_enabled)
        self.shade_end_edit.setEnabled(shade_enabled)
        self.shade_opacity_spin.setEnabled(shade_enabled)
        if not self.show_hover_check.isChecked():
            self._hide_hover_annotations()
        self.mean_group.setEnabled(
            self.display_mode_combo.currentData()
            in {"mean", "polygon_means_overlay", "polygon_means_separate"}
        )
        has_additional_fields = bool(self._additional_field_checks)
        self.show_additional_panel_check.setEnabled(has_additional_fields)
        self.export_additional_properties_check.setEnabled(has_additional_fields)
        watermark_enabled = (
            self.watermark_export_check.isChecked() or
            self.watermark_preview_check.isChecked()
        )
        self.watermark_opacity_spin.setEnabled(watermark_enabled)
        self.watermark_position_combo.setEnabled(watermark_enabled)
        self.watermark_scale_spin.setEnabled(watermark_enabled)
        self._update_export_control_states()

    def _reset_plot_settings(self, *_args) -> None:
        self.settings = PlotSettings()
        self.settings.save(self.project)
        self._sync_controls_from_settings()
        if self.current_schema is not None:
            self._sync_x_dates_for_schema(self.current_schema)
        self._update_from_current_selection()

    def _sync_x_dates_for_schema(self, schema: LayerSchema) -> None:
        self._updating_controls = True
        try:
            if not (
                self.settings.x_manual and
                self.settings.x_start and
                self.settings.x_end
            ):
                self.x_start_edit.setDate(self._qdate(schema.first_acquisition))
                self.x_end_edit.setDate(self._qdate(schema.last_acquisition))
                self.settings.x_start = schema.first_acquisition.isoformat()
                self.settings.x_end = schema.last_acquisition.isoformat()

            if not self.settings.shade_start:
                self.settings.shade_start = schema.first_acquisition.isoformat()
                self.shade_start_edit.setDate(self._qdate(schema.first_acquisition))
            if not self.settings.shade_end:
                self.settings.shade_end = schema.last_acquisition.isoformat()
                self.shade_end_edit.setDate(self._qdate(schema.last_acquisition))
        finally:
            self._updating_controls = False

    def _sync_orbit_control(self) -> None:
        is_los = self.current_schema is not None and self.current_schema.component_key == "los"
        self._updating_controls = True
        try:
            self.orbit_combo.setEnabled(is_los)
            index = self.orbit_combo.findData(
                self.current_orbit_override if is_los else ORBIT_AUTO
            )
            self.orbit_combo.setCurrentIndex(max(0, index))
        finally:
            self._updating_controls = False

    def _on_orbit_override_changed(self, _index: int) -> None:
        if self._updating_controls or self.current_layer is None or self.current_schema is None:
            return
        if self.current_schema.component_key != "los":
            return
        self.current_orbit_override = self.orbit_combo.currentData()
        save_layer_orbit_override(
            self.project, self.current_layer.id(), self.current_orbit_override
        )
        self._update_layer_info()
        self._refresh_current_layer_combo_label()
        self._update_from_current_selection()

    def _refresh_current_layer_combo_label(self) -> None:
        if self.current_layer is None or self.current_schema is None:
            return
        index = self.layer_combo.findData(self.current_layer.id())
        if index < 0:
            return
        self.layer_combo.setItemText(
            index,
            f"{self.current_layer.name()} [{self._effective_component_label()}]",
        )

    def _effective_component_label(self) -> str:
        if self.current_layer is None or self.current_schema is None:
            return "—"
        return component_display_label(
            self.current_schema,
            self.current_layer,
            self.current_orbit_override,
        )

    # -------------------------------------------------------------- helpers
    def _clear_feature_info(self) -> None:
        for label in (
            self.value_identifier,
            self.value_component,
            self.value_velocity,
            self.value_velocity_std,
            self.value_cumulative,
            self.value_coverage,
            self.value_additional_properties,
        ):
            label.setText("—")
        self.caption_additional_properties.setVisible(False)
        self.value_additional_properties.setVisible(False)

    def _show_layer_error(self, message: str) -> None:
        self._update_area_control_states()
        self.layer_info.setText("Camada incompatível.")
        self.selection_count_label.setText("0 selecionadas")
        self._clear_feature_info()
        self._show_plot_message(tr("A camada selecionada não é compatível."))
        self.status_label.setText(message)

    @staticmethod
    def _format_mm_per_year(value: Optional[float]) -> str:
        return "—" if value is None else tr("{value:.1f} mm/ano", value=value)

    @staticmethod
    def _format_numeric_range(values: Sequence[float], suffix: str) -> str:
        if not values:
            return "—"
        minimum = min(values)
        maximum = max(values)
        if abs(maximum - minimum) < 1e-12:
            return f"{minimum:.1f}{suffix}"
        return tr("{minimum:.1f} a {maximum:.1f}{suffix}", minimum=minimum, maximum=maximum, suffix=suffix)

    @staticmethod
    def _set_date_edit_from_iso(widget: QDateEdit, iso_value: str) -> None:
        parsed = QDate.fromString(iso_value, Qt.ISODate)
        widget.setDate(parsed if parsed.isValid() else QDate.currentDate())

    @staticmethod
    def _qdate(value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
