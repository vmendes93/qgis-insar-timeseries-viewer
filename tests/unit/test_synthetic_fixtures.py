"""Validate the deterministic synthetic InSAR shapefile fixtures.

These tests deliberately avoid QGIS so they can run in the normal unit-test
suite and in generic CI environments.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import pytest
import shapefile

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_insar"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"
TEMPORAL_FIELD_RE = re.compile(r"^D\d{8}$")
SHAPEFILE_EXTENSIONS = (".shp", ".shx", ".dbf", ".prj", ".cpg")


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def datasets(manifest: dict[str, Any]) -> dict[str, Any]:
    return manifest["datasets"]


def _reader(stem: str) -> shapefile.Reader:
    return shapefile.Reader(str(FIXTURE_DIR / f"{stem}.shp"))


def _field_definitions(reader: shapefile.Reader) -> list[list[Any]]:
    return [list(field) for field in reader.fields[1:]]


def _field_names(reader: shapefile.Reader) -> list[str]:
    return [field[0] for field in reader.fields[1:]]


def _temporal_field_names(reader: shapefile.Reader) -> list[str]:
    return [name for name in _field_names(reader) if TEMPORAL_FIELD_RE.fullmatch(name)]


def _records_as_dicts(reader: shapefile.Reader) -> list[dict[str, Any]]:
    fields = _field_names(reader)
    return [dict(zip(fields, record)) for record in reader.records()]


def _to_number(value: Any) -> float:
    if isinstance(value, str):
        value = value.strip()
    return float(value)


def _is_sentinel(value: Any, sentinels: list[float]) -> bool:
    try:
        numeric = _to_number(value)
    except (TypeError, ValueError):
        return False
    return any(math.isclose(numeric, sentinel, abs_tol=1e-9) for sentinel in sentinels)


def _is_missing(value: Any, sentinels: list[float]) -> bool:
    return value is None or _is_sentinel(value, sentinels)


def _is_invalid(value: Any, sentinels: list[float]) -> bool:
    if _is_missing(value, sentinels):
        return False
    try:
        _to_number(value)
    except (TypeError, ValueError):
        return True
    return False


def _classify_observations(
    reader: shapefile.Reader,
    temporal_fields: list[str],
    sentinels: list[float],
) -> dict[str, int]:
    counts = {"observations": 0, "valid": 0, "missing": 0, "invalid": 0}
    for record in _records_as_dicts(reader):
        for field_name in temporal_fields:
            counts["observations"] += 1
            value = record[field_name]
            if _is_missing(value, sentinels):
                counts["missing"] += 1
            elif _is_invalid(value, sentinels):
                counts["invalid"] += 1
            else:
                counts["valid"] += 1
    return counts


def _point_record_lookup(
    manifest: dict[str, Any],
    dataset: dict[str, Any],
    reader: shapefile.Reader,
) -> dict[str, dict[str, Any]]:
    records = _records_as_dicts(reader)
    identifier_field = dataset.get("auto_mappings", {}).get("identifier")

    if identifier_field:
        return {str(record[identifier_field]): record for record in records}

    points = manifest["geometry"]["points"]
    return {point["point_id"]: records[point["record_index"]] for point in points}


def test_manifest_exists_and_declares_expected_global_contract(manifest: dict[str, Any]) -> None:
    assert manifest["schema_version"] == "1.0"
    assert manifest["random_seed"] == 20260626
    assert manifest["random_algorithm"] == "numpy.random.PCG64"
    assert manifest["crs"]["auth_name"] == "EPSG"
    assert manifest["crs"]["auth_code"] == 31983
    assert manifest["conventions"]["canonical_displacement_unit"] == "mm"
    assert manifest["conventions"]["vertical_positive"] == "upward"
    assert manifest["conventions"]["east_west_positive"] == "eastward"
    assert manifest["conventions"]["los_positive"] == "toward_satellite"

    dates = manifest["dates"]["field_names"]
    assert len(dates) == 20
    assert all(TEMPORAL_FIELD_RE.fullmatch(field_name) for field_name in dates)
    assert "D20240229" in dates

    los_geometry = manifest["los_geometry"]
    assert los_geometry["incidence_angle_degrees"] == 35.0
    assert "U * cos(35 deg) - E * sin(35 deg)" in los_geometry["ascending_formula"]
    assert "U * cos(35 deg) + E * sin(35 deg)" in los_geometry["descending_formula"]


def test_generated_file_set_matches_manifest_checksums(manifest: dict[str, Any]) -> None:
    expected_checksums = manifest["checksums"]
    actual_paths = sorted(path for path in FIXTURE_DIR.iterdir() if path.name != "manifest.json")

    assert {path.name for path in actual_paths} == set(expected_checksums)

    for path in actual_paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected_checksums[path.name], path.name


@pytest.mark.parametrize("dataset_name", [
    "synthetic_los_ascending",
    "synthetic_los_descending",
    "synthetic_vertical",
    "synthetic_east_west",
])
def test_shapefile_sidecars_exist(dataset_name: str, datasets: dict[str, Any]) -> None:
    stem = datasets[dataset_name]["filename_stem"]
    for extension in SHAPEFILE_EXTENSIONS:
        assert (FIXTURE_DIR / f"{stem}{extension}").is_file()


def test_manifest_defines_the_four_reference_datasets(datasets: dict[str, Any]) -> None:
    assert set(datasets) == {
        "synthetic_los_ascending",
        "synthetic_los_descending",
        "synthetic_vertical",
        "synthetic_east_west",
    }


def test_geometry_grid_is_deterministic(manifest: dict[str, Any]) -> None:
    geometry = manifest["geometry"]
    assert geometry["grid"]["columns"] == 5
    assert geometry["grid"]["rows"] == 4
    assert geometry["grid"]["spacing_m"] == 100.0

    points = geometry["points"]
    assert len(points) == 20
    assert points[0] == {"point_id": "P00", "record_index": 0, "x": 300000.0, "y": 7400000.0}
    assert points[-1] == {
        "point_id": "P19",
        "record_index": 19,
        "x": 300400.0,
        "y": 7400300.0,
    }


@pytest.mark.parametrize("dataset_name", [
    "synthetic_los_ascending",
    "synthetic_los_descending",
    "synthetic_vertical",
    "synthetic_east_west",
])
def test_shapefile_content_matches_dataset_manifest(
    dataset_name: str,
    manifest: dict[str, Any],
    datasets: dict[str, Any],
) -> None:
    dataset = datasets[dataset_name]
    reader = _reader(dataset["filename_stem"])

    assert reader.shapeType == shapefile.POINT
    assert len(reader) == dataset["expected_counts"]["features"]

    fields = _field_definitions(reader)
    expected_fields = [
        [field["name"], field["type"], field["width"], field["decimal"]]
        for field in dataset["dbf_fields"]
    ]
    assert fields == expected_fields

    temporal_fields = _temporal_field_names(reader)
    assert len(temporal_fields) == 20
    assert temporal_fields == dataset["temporal_field_order_physical"]
    assert sorted(temporal_fields) == sorted(manifest["dates"]["field_names"])
    assert dataset["temporal_field_order_chronological"] == manifest["dates"]["field_names"]

    counts = _classify_observations(
        reader,
        temporal_fields,
        dataset["missing_value_sentinels"],
    )
    assert counts == {
        "observations": dataset["expected_counts"]["observations"],
        "valid": dataset["expected_counts"]["valid"],
        "missing": dataset["expected_counts"]["missing"],
        "invalid": dataset["expected_counts"]["invalid"],
    }

    expected_points = manifest["geometry"]["points"]
    for shape_record, expected_point in zip(reader.iterShapeRecords(), expected_points):
        assert len(shape_record.shape.points) == 1
        x, y = shape_record.shape.points[0]
        assert x == pytest.approx(expected_point["x"])
        assert y == pytest.approx(expected_point["y"])


def test_layouts_exercise_auto_and_manual_mapping_cases(datasets: dict[str, Any]) -> None:
    assert datasets["synthetic_los_ascending"]["auto_mappings"] == {
        "component": "COMPONENT",
        "displacement_unit": "UNIT",
        "identifier": "CODE",
        "orbit": "ORBIT",
        "sentinel": "NODATA",
        "velocity": "VEL",
        "velocity_uncertainty": "V_STDEV",
    }

    assert datasets["synthetic_los_descending"]["auto_mappings"]["identifier"] == "POINT_ID"
    assert datasets["synthetic_los_descending"]["auto_mappings"]["velocity"] == "RATE_MM_Y"

    vertical = datasets["synthetic_vertical"]
    assert vertical["auto_mappings"] == {}
    assert vertical["manual_mappings"] == {
        "component_constant": "vertical",
        "displacement_unit_constant": "mm",
    }

    east_west = datasets["synthetic_east_west"]
    assert east_west["displacement_unit"] == "cm"
    assert east_west["manual_mappings"] == {
        "velocity": "MOTION",
        "velocity_uncertainty": "UNCERT",
    }


def test_reference_cell_values_are_serialized_as_declared(manifest: dict[str, Any]) -> None:
    readers = {
        name: _reader(dataset["filename_stem"])
        for name, dataset in manifest["datasets"].items()
    }
    lookups = {
        name: _point_record_lookup(manifest, dataset, readers[name])
        for name, dataset in manifest["datasets"].items()
    }

    for reference in manifest["reference_values"]["cells"]:
        point_id = reference["point_id"]
        field_name = reference["date_field"]

        assert _to_number(lookups["synthetic_los_ascending"][point_id][field_name]) == pytest.approx(
            reference["los_ascending_mm"],
            abs=0.001,
        )
        assert _to_number(lookups["synthetic_los_descending"][point_id][field_name]) == pytest.approx(
            reference["los_descending_mm"],
            abs=0.001,
        )
        assert _to_number(lookups["synthetic_vertical"][point_id][field_name]) == pytest.approx(
            reference["u_mm"],
            abs=0.001,
        )
        assert _to_number(lookups["synthetic_east_west"][point_id][field_name]) == pytest.approx(
            reference["east_west_stored_cm"],
            abs=0.0001,
        )


def test_los_pairs_can_reconstruct_vertical_and_east_west_reference_values(
    manifest: dict[str, Any],
) -> None:
    ascending = _point_record_lookup(
        manifest,
        manifest["datasets"]["synthetic_los_ascending"],
        _reader("synthetic_los_ascending"),
    )
    descending = _point_record_lookup(
        manifest,
        manifest["datasets"]["synthetic_los_descending"],
        _reader("synthetic_los_descending"),
    )

    incidence_rad = math.radians(manifest["los_geometry"]["incidence_angle_degrees"])
    sin_i = math.sin(incidence_rad)
    cos_i = math.cos(incidence_rad)

    for reference in manifest["reference_values"]["cells"]:
        point_id = reference["point_id"]
        field_name = reference["date_field"]
        los_ascending = _to_number(ascending[point_id][field_name])
        los_descending = _to_number(descending[point_id][field_name])

        reconstructed_u = (los_ascending + los_descending) / (2 * cos_i)
        reconstructed_e = (los_descending - los_ascending) / (2 * sin_i)

        assert reconstructed_u == pytest.approx(reference["u_mm"], abs=0.002)
        assert reconstructed_e == pytest.approx(reference["e_mm"], abs=0.002)
