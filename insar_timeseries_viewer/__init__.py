# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""QGIS entry point for InSAR Time Series Viewer."""


def classFactory(iface):
    """Cria a instância principal solicitada pelo QGIS."""
    from .plugin import InsarTimeSeriesViewerPlugin

    return InsarTimeSeriesViewerPlugin(iface)
