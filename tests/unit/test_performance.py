from insar_timeseries_viewer.performance import log_performance


def test_log_performance_accepts_context(monkeypatch):
    messages = []

    class FakeMessageLog:
        @staticmethod
        def logMessage(message, channel, level):
            messages.append((message, channel, level))

    monkeypatch.setattr(
        "insar_timeseries_viewer.performance.QgsMessageLog",
        FakeMessageLog,
    )

    log_performance("event", 1.23456, series=10, ignored=None)

    assert messages
    assert messages[0][0] == "event: 1.235s | series=10"
    assert messages[0][1] == "InSAR Time Series Viewer"
