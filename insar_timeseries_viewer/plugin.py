# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""QGIS plugin lifecycle and user-interface integration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .i18n import initialize_locale, tr


class InsarTimeSeriesViewerPlugin:
    """Integra o painel do visualizador à interface principal do QGIS."""

    MENU_NAME = "&Visualizador de Séries Temporais"

    def __init__(self, iface):
        self.iface = iface
        initialize_locale(log=True)
        self.action: Optional[QAction] = None
        self.help_action: Optional[QAction] = None
        self.dock = None

    def initGui(self) -> None:
        icon_path = Path(__file__).with_name("icon.png")
        self.action = QAction(
            QIcon(str(icon_path)),
            tr("Visualizador de Séries Temporais InSAR"),
            self.iface.mainWindow(),
        )
        self.action.setObjectName("insarTimeSeriesViewerAction")
        self.action.setCheckable(True)
        self.action.setStatusTip(
            tr("Abre o painel de séries temporais para camadas pontuais InSAR")
        )
        self.action.toggled.connect(self._set_dock_visible)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu(tr(self.MENU_NAME), self.action)

        self.help_action = QAction(
            QIcon(str(icon_path)),
            tr("Ajuda do Visualizador de Séries Temporais InSAR"),
            self.iface.mainWindow(),
        )
        self.help_action.setObjectName("insarTimeSeriesViewerHelpAction")
        self.help_action.setStatusTip(tr("Abre a documentação do plugin"))
        self.help_action.triggered.connect(self._show_help)
        self.iface.addPluginToVectorMenu(tr(self.MENU_NAME), self.help_action)
        self.iface.pluginHelpMenu().addAction(self.help_action)

    def unload(self) -> None:
        if self.action is not None:
            try:
                self.action.toggled.disconnect(self._set_dock_visible)
            except (TypeError, RuntimeError):
                pass
            self.iface.removePluginVectorMenu(tr(self.MENU_NAME), self.action)
            self.iface.removeToolBarIcon(self.action)

        if self.help_action is not None:
            try:
                self.help_action.triggered.disconnect(self._show_help)
            except (TypeError, RuntimeError):
                pass
            self.iface.removePluginVectorMenu(tr(self.MENU_NAME), self.help_action)
            self.iface.pluginHelpMenu().removeAction(self.help_action)
            self.help_action.deleteLater()
            self.help_action = None

        if self.dock is not None:
            try:
                self.dock.visibilityChanged.disconnect(self._sync_action_state)
            except (TypeError, RuntimeError):
                pass
            self.dock.shutdown()
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None

        self.action = None

    def _set_dock_visible(self, visible: bool) -> None:
        if visible:
            if not self._ensure_dock():
                if self.action is not None:
                    self.action.blockSignals(True)
                    self.action.setChecked(False)
                    self.action.blockSignals(False)
                return
            self.dock.show()
            self.dock.raise_()
            self.dock.activateWindow()
        elif self.dock is not None:
            self.dock.hide()

    def _ensure_dock(self) -> bool:
        if self.dock is not None:
            return True

        try:
            from .dock_widget import TimeSeriesDockWidget

            self.dock = TimeSeriesDockWidget(self.iface, self.iface.mainWindow())
            self.dock.visibilityChanged.connect(self._sync_action_state)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            return True
        except Exception as exc:  # mensagem útil se Matplotlib/Qt falhar
            self.dock = None
            QMessageBox.critical(
                self.iface.mainWindow(),
                tr("Visualizador de Séries Temporais"),
                tr("Não foi possível criar o painel do plugin.") + "\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            return False

    @staticmethod
    def _show_help() -> None:
        """Open the localized help bundled with the plugin."""
        from qgis.utils import showPluginHelp

        showPluginHelp(packageName="insar_timeseries_viewer")

    def _sync_action_state(self, visible: bool) -> None:
        if self.action is None or self.action.isChecked() == visible:
            return
        self.action.blockSignals(True)
        self.action.setChecked(visible)
        self.action.blockSignals(False)
