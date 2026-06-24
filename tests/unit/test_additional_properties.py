from types import SimpleNamespace

from insar_timeseries_viewer.additional_properties import (
    format_number,
    property_field_candidates,
    summarize_group_means,
    summarize_values,
)


def test_property_candidates_exclude_identifier_and_velocity_fields():
    schema = SimpleNamespace(
        identifier_field="CODE",
        velocity_field="VEL",
        velocity_std_field="V_STDEV",
        general_fields=("CODE", "VEL", "V_STDEV", "HEIGHT", "CLASS"),
    )
    assert property_field_candidates(schema) == ("HEIGHT", "CLASS")


def test_numeric_summaries():
    assert summarize_values([1, 2, 3], mode="mean") == "2"
    assert summarize_values([1, 3], mode="range") == "1–3"
    assert summarize_values([2, 2], mode="range") == "2"
    assert summarize_group_means([[1, 3], [5, 7]], mode="range") == "2–6"


def test_text_and_null_summaries():
    assert summarize_values([None, "null", ""]) == "—"
    assert summarize_values(["A", "A"]) == "A"
    assert summarize_values(["A", "B"]) == "Vários valores"


def test_number_formatting():
    assert format_number(2.0) == "2"
    assert format_number(1.23456) == "1.2346"
