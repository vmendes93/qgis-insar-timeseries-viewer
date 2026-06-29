from insar_timeseries_viewer.i18n import initialize_locale, tr

def test_english_source_messages_translate_to_pt_br():
    initialize_locale("pt_BR", log=False)
    try:
        assert tr("Show report") == "Mostrar relatório"
        assert tr("Hide report") == "Ocultar relatório"
        assert (
            tr("Show or hide the active layer structural report")
            == "Mostrar ou ocultar o relatório estrutural da camada"
        )
    finally:
        initialize_locale("en", log=False)


def test_english_source_messages_remain_english_in_fallback_locale():
    initialize_locale("en", log=False)
    assert tr("Show report") == "Show report"
    assert tr("Hide report") == "Hide report"
