# SPDX-FileCopyrightText: 2026 Vinicius Mendes
# SPDX-License-Identifier: GPL-2.0-or-later

"""Coarse performance logging helpers."""

from __future__ import annotations

import logging

try:
    from qgis.core import Qgis, QgsMessageLog
except ImportError:  # unit tests may run with a minimal qgis.core stub
    Qgis = None
    QgsMessageLog = None


LOGGER = logging.getLogger(__name__)
PERFORMANCE_LOG_CHANNEL = "InSAR Time Series Viewer"


def log_performance(event: str, elapsed_seconds: float, **context) -> None:
    """Log performance timings to Python logging and the QGIS message log."""

    details = " | ".join(
        f"{key}={value}" for key, value in context.items() if value is not None
    )
    message = f"{event}: {elapsed_seconds:.3f}s"
    if details:
        message = f"{message} | {details}"

    LOGGER.info(message)
    if QgsMessageLog is None:
        return

    try:
        level = Qgis.Info if Qgis is not None else None
        QgsMessageLog.logMessage(message, PERFORMANCE_LOG_CHANNEL, level)
    except (RuntimeError, AttributeError):
        pass
