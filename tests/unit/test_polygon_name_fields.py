from insar_timeseries_viewer.polygon_name_fields import suggest_name_field


def test_suggest_name_field_prefers_canonical_name_fields():
    assert suggest_name_field(["FID", "NAME", "CODE"]) == "NAME"
    assert suggest_name_field(["fid", "nome", "codigo"]) == "nome"


def test_suggest_name_field_accepts_code_and_id_fields():
    assert suggest_name_field(["FID", "CODE", "OTHER"]) == "CODE"
    assert suggest_name_field(["VALUE", "ID"]) == "ID"


def test_suggest_name_field_uses_partial_matches_after_exact_matches():
    assert suggest_name_field(["polygon_name", "polygon_code"]) == "polygon_name"
    assert suggest_name_field(["sector_label", "value"]) == "sector_label"


def test_suggest_name_field_returns_none_when_no_candidate_exists():
    assert suggest_name_field(["value", "height", "class"]) is None
    assert suggest_name_field([]) is None
