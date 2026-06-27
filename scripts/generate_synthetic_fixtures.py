#!/usr/bin/env python3
"""Generate deterministic synthetic InSAR shapefile fixtures.

The generated fixtures implement docs/SYNTHETIC_DATA_SPEC.md and are used as a
provider-independent test contract for the QGIS InSAR Time Series Viewer.

This script deliberately does not import QGIS. It requires only numpy and pyshp.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import shapefile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "tests" / "fixtures" / "synthetic_insar"
SCHEMA_VERSION = "1.0"
GENERATOR_NAME = "scripts/generate_synthetic_fixtures.py"
RANDOM_SEED = 20260626
RANDOM_ALGORITHM = "numpy.random.PCG64"
INCIDENCE_DEG = 35.0
REFERENCE_DATE = date(2024, 1, 12)
JUMP_DATE = date(2024, 10, 2)

DATE_FIELDS = [
    "D20240112",
    "D20240205",
    "D20240229",
    "D20240324",
    "D20240417",
    "D20240511",
    "D20240604",
    "D20240628",
    "D20240722",
    "D20240815",
    "D20240908",
    "D20241002",
    "D20241026",
    "D20241119",
    "D20241213",
    "D20250106",
    "D20250130",
    "D20250223",
    "D20250319",
    "D20250412",
]
DATE_VALUES = [date(int(name[1:5]), int(name[5:7]), int(name[7:9])) for name in DATE_FIELDS]
TIME_YEARS = np.array([(d - REFERENCE_DATE).days / 365.25 for d in DATE_VALUES], dtype=float)

PRJ_EPSG_31983 = (
    'PROJCS["SIRGAS_2000_UTM_Zone_23S",'
    'GEOGCS["GCS_SIRGAS_2000",'
    'DATUM["D_SIRGAS_2000",SPHEROID["GRS_1980",6378137.0,298.257222101]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],'
    'PARAMETER["False_Easting",500000.0],'
    'PARAMETER["False_Northing",10000000.0],'
    'PARAMETER["Central_Meridian",-45.0],'
    'PARAMETER["Scale_Factor",0.9996],'
    'PARAMETER["Latitude_Of_Origin",0.0],'
    'UNIT["Meter",1.0]]'
)


@dataclass(frozen=True)
class FieldDef:
    name: str
    field_type: str
    width: int
    decimal: int = 0


@dataclass(frozen=True)
class PointModel:
    point_id: str
    scenario: str
    vu: float = 0.0
    au: float = 0.0
    seasonal_u_amplitude: float = 0.0
    seasonal_u_phase_deg: float = 0.0
    jump_u: float = 0.0
    ve: float = 0.0
    ae: float = 0.0
    seasonal_e_amplitude: float = 0.0
    seasonal_e_phase_deg: float = 0.0
    jump_e: float = 0.0
    sigma_u: float = 0.0
    sigma_e: float = 0.0


POINT_MODELS = [
    PointModel("P00", "stable, noise-free"),
    PointModel("P01", "stable with controlled noise", sigma_u=0.8, sigma_e=0.8),
    PointModel("P02", "linear subsidence", vu=-20),
    PointModel("P03", "linear uplift", vu=15),
    PointModel("P04", "linear eastward motion", ve=18),
    PointModel("P05", "linear westward motion", ve=-18),
    PointModel("P06", "subsidence plus eastward motion", vu=-25, ve=12),
    PointModel("P07", "uplift plus westward motion", vu=10, ve=-14),
    PointModel("P08", "vertical seasonal signal", vu=-3, seasonal_u_amplitude=8, seasonal_u_phase_deg=30),
    PointModel("P09", "east-west seasonal signal", ve=2, seasonal_e_amplitude=10, seasonal_e_phase_deg=-45),
    PointModel("P10", "vertical negative jump", vu=-5, jump_u=-15),
    PointModel("P11", "east-west positive jump", ve=4, jump_e=20),
    PointModel("P12", "accelerating subsidence", vu=-5, au=-18),
    PointModel("P13", "accelerating westward motion", ve=-4, ae=-16),
    PointModel(
        "P14",
        "mixed trend, seasonality, and noise",
        vu=-12,
        seasonal_u_amplitude=4,
        seasonal_u_phase_deg=45,
        ve=9,
        seasonal_e_amplitude=3,
        seasonal_e_phase_deg=-30,
        sigma_u=0.3,
        sigma_e=0.3,
    ),
    PointModel("P15", "sentinel-coded gaps", vu=-8, sigma_u=0.3, sigma_e=0.2),
    PointModel("P16", "DBF-null gaps", ve=-10, sigma_u=0.2, sigma_e=0.3),
    PointModel("P17", "positive vertical outlier", vu=-10, ve=5, sigma_u=0.35, sigma_e=0.35),
    PointModel("P18", "negative east-west outlier", vu=5, ve=-6, sigma_u=0.35, sigma_e=0.35),
    PointModel("P19", "sparse observations", vu=-30, ve=20, sigma_u=0.2, sigma_e=0.2),
]

REFERENCE_CELLS = [
    ("P00", "D20240112"),
    ("P00", "D20250412"),
    ("P02", "D20250412"),
    ("P04", "D20250412"),
    ("P06", "D20250412"),
    ("P08", "D20240417"),
    ("P08", "D20250412"),
    ("P10", "D20240908"),
    ("P10", "D20241002"),
    ("P11", "D20240908"),
    ("P11", "D20241002"),
    ("P12", "D20250412"),
    ("P14", "D20250412"),
    ("P17", "D20241119"),
    ("P18", "D20250130"),
    ("P19", "D20250412"),
]
REFERENCE_VELOCITY_POINTS = ["P00", "P02", "P04", "P06", "P10", "P11", "P12", "P14", "P19"]


def _date_indices(indices: Iterable[int]) -> list[str]:
    return [DATE_FIELDS[i] for i in indices]


DATASETS: dict[str, dict[str, Any]] = {
    "synthetic_los_ascending": {
        "component": "LOS",
        "orbit": "ASC",
        "displacement_unit": "mm",
        "velocity_unit": "mm/year",
        "sentinel": 999.0,
        "date_order": DATE_FIELDS,
        "fields": [
            FieldDef("CODE", "C", 8),
            FieldDef("COMPONENT", "C", 9),
            FieldDef("ORBIT", "C", 4),
            FieldDef("UNIT", "C", 8),
            FieldDef("NODATA", "N", 12, 3),
            FieldDef("VEL", "N", 12, 3),
            FieldDef("V_STDEV", "N", 12, 3),
            FieldDef("HEIGHT", "N", 10, 2),
            FieldDef("COHERENCE", "N", 5, 3),
            *[FieldDef(name, "N", 14, 3) for name in DATE_FIELDS],
        ],
        "auto_mappings": {
            "identifier": "CODE",
            "velocity": "VEL",
            "velocity_uncertainty": "V_STDEV",
            "component": "COMPONENT",
            "orbit": "ORBIT",
            "displacement_unit": "UNIT",
            "sentinel": "NODATA",
        },
        "manual_mappings": {},
        "sentinel_masks": {"P15": _date_indices([4, 5, 6, 7]), "P19": _date_indices(range(1, 19))},
        "null_masks": {"P16": _date_indices([8, 9])},
        "invalid_masks": {},
        "expected_counts": {"features": 20, "observations": 400, "valid": 376, "missing": 24, "invalid": 0},
    },
    "synthetic_los_descending": {
        "component": "LOS",
        "orbit": "DESC",
        "displacement_unit": "mm",
        "velocity_unit": "mm/year",
        "sentinel": -9999.0,
        "date_order": list(reversed(DATE_FIELDS)),
        "fields": [
            *[FieldDef(name, "N", 14, 3) for name in reversed(DATE_FIELDS)],
            FieldDef("POINT_ID", "C", 8),
            FieldDef("PASS", "C", 4),
            FieldDef("COMP", "C", 8),
            FieldDef("UOM", "C", 8),
            FieldDef("NODATA", "N", 12, 3),
            FieldDef("RATE_MM_Y", "N", 12, 3),
            FieldDef("RATE_ERR", "N", 12, 3),
            FieldDef("QUALITY", "N", 5, 3),
        ],
        "auto_mappings": {
            "identifier": "POINT_ID",
            "velocity": "RATE_MM_Y",
            "velocity_uncertainty": "RATE_ERR",
            "component": "COMP",
            "orbit": "PASS",
            "displacement_unit": "UOM",
            "sentinel": "NODATA",
        },
        "manual_mappings": {},
        "sentinel_masks": {"P15": _date_indices([0, 1, 8]), "P19": _date_indices([i for i in range(20) if i not in (0, 10, 19)])},
        "null_masks": {"P16": _date_indices([6, 7, 8, 9])},
        "invalid_masks": {},
        "expected_counts": {"features": 20, "observations": 400, "valid": 376, "missing": 24, "invalid": 0},
    },
    "synthetic_vertical": {
        "component": "vertical",
        "orbit": None,
        "displacement_unit": "mm",
        "velocity_unit": None,
        "sentinel": None,
        "date_order": [*DATE_FIELDS[0::2], *DATE_FIELDS[1::2]],
        "fields": [
            FieldDef("QUALITY", "N", 5, 3),
            *[FieldDef(name, "N", 14, 3) for name in DATE_FIELDS[0::2]],
            FieldDef("ELEV_M", "N", 10, 2),
            *[FieldDef(name, "N", 14, 3) for name in DATE_FIELDS[1::2]],
        ],
        "auto_mappings": {},
        "manual_mappings": {"component_constant": "vertical", "displacement_unit_constant": "mm"},
        "sentinel_masks": {},
        "null_masks": {
            "P15": _date_indices([2, 3, 4]),
            "P16": _date_indices([0, 9, 10, 11]),
            "P19": _date_indices([i for i in range(20) if i not in (0, 19)]),
        },
        "invalid_masks": {},
        "expected_counts": {"features": 20, "observations": 400, "valid": 375, "missing": 25, "invalid": 0},
    },
    "synthetic_east_west": {
        "component": "east_west",
        "orbit": None,
        "displacement_unit": "cm",
        "velocity_unit": "cm/year",
        "sentinel": -32768.0,
        "date_order": [*DATE_FIELDS[1::2], *DATE_FIELDS[0::2]],
        "fields": [
            FieldDef("STATION", "C", 8),
            FieldDef("AXIS", "C", 8),
            FieldDef("UOM", "C", 8),
            FieldDef("NODATA", "N", 12, 1),
            FieldDef("MOTION", "N", 12, 4),
            FieldDef("UNCERT", "N", 12, 4),
            FieldDef("CLASS", "C", 16),
            *[
                FieldDef(name, "C", 16) if name in {"D20240628", "D20250130"} else FieldDef(name, "N", 14, 4)
                for name in [*DATE_FIELDS[1::2], *DATE_FIELDS[0::2]]
            ],
        ],
        "auto_mappings": {
            "identifier": "STATION",
            "component": "AXIS",
            "displacement_unit": "UOM",
            "sentinel": "NODATA",
        },
        "manual_mappings": {"velocity": "MOTION", "velocity_uncertainty": "UNCERT"},
        "sentinel_masks": {"P15": _date_indices([5, 6, 7, 8]), "P19": _date_indices([i for i in range(20) if i not in (0, 1, 2, 18, 19)])},
        "null_masks": {"P16": _date_indices([12, 13, 14])},
        "invalid_masks": {"P14": ["D20240628"]},
        "expected_counts": {"features": 20, "observations": 400, "valid": 377, "missing": 22, "invalid": 1},
    },
}


class FixtureError(RuntimeError):
    """Raised when generation or validation violates the fixture contract."""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Fixture output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate an existing fixture directory without regenerating it.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if args.validate_only:
        validate_fixture_dir(output_dir)
        print(f"Validated existing synthetic fixtures: {output_dir}")
        return

    generate_fixtures(output_dir)
    validate_fixture_dir(output_dir)
    print(f"Generated and validated synthetic fixtures: {output_dir}")


def generate_fixtures(output_dir: Path) -> None:
    truth = build_truth_arrays()
    parent = output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}.", dir=parent) as tmp_name:
        tmp_dir = Path(tmp_name)
        for stem in DATASETS:
            write_dataset(tmp_dir, stem, truth)
        write_fixture_readme(tmp_dir)

        manifest = build_manifest(tmp_dir, truth)
        (tmp_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if output_dir.exists():
            shutil.rmtree(output_dir)
        tmp_dir.rename(output_dir)


def build_truth_arrays() -> dict[str, Any]:
    rng = np.random.Generator(np.random.PCG64(RANDOM_SEED))
    z_u = rng.normal(size=(20, 20))
    z_e = rng.normal(size=(20, 20))

    u = np.zeros((20, 20), dtype=float)
    e = np.zeros((20, 20), dtype=float)
    jump_mask = np.array([d >= JUMP_DATE for d in DATE_VALUES], dtype=float)

    for i, model in enumerate(POINT_MODELS):
        u[i, :] = model.vu * TIME_YEARS + 0.5 * model.au * TIME_YEARS**2
        e[i, :] = model.ve * TIME_YEARS + 0.5 * model.ae * TIME_YEARS**2

        if model.seasonal_u_amplitude:
            phase = math.radians(model.seasonal_u_phase_deg)
            u[i, :] += model.seasonal_u_amplitude * (
                np.sin(2 * math.pi * TIME_YEARS + phase) - math.sin(phase)
            )
        if model.seasonal_e_amplitude:
            phase = math.radians(model.seasonal_e_phase_deg)
            e[i, :] += model.seasonal_e_amplitude * (
                np.sin(2 * math.pi * TIME_YEARS + phase) - math.sin(phase)
            )

        u[i, :] += model.jump_u * jump_mask
        e[i, :] += model.jump_e * jump_mask
        u[i, :] += model.sigma_u * (z_u[i, :] - z_u[i, 0])
        e[i, :] += model.sigma_e * (z_e[i, :] - z_e[i, 0])

    u[17, DATE_FIELDS.index("D20241119")] += 35.0
    e[18, DATE_FIELDS.index("D20250130")] += -40.0

    incidence_rad = math.radians(INCIDENCE_DEG)
    cos_i = math.cos(incidence_rad)
    sin_i = math.sin(incidence_rad)
    los_ascending = u * cos_i - e * sin_i
    los_descending = u * cos_i + e * sin_i

    return {
        "u_mm": u,
        "e_mm": e,
        "los_ascending_mm": los_ascending,
        "los_descending_mm": los_descending,
        "cos_incidence": cos_i,
        "sin_incidence": sin_i,
    }


def write_dataset(output_dir: Path, stem: str, truth: dict[str, Any]) -> None:
    config = DATASETS[stem]
    fields: list[FieldDef] = config["fields"]
    validate_field_defs(fields)

    writer = shapefile.Writer(str(output_dir / stem), shapeType=shapefile.POINT)
    writer.autoBalance = 1
    for field in fields:
        writer.field(field.name, field.field_type, size=field.width, decimal=field.decimal)

    for index, model in enumerate(POINT_MODELS):
        x, y = point_coordinates(index)
        writer.point(x, y)
        writer.record(*build_record(stem, index, model, truth, fields))
    writer.close()

    (output_dir / f"{stem}.prj").write_text(PRJ_EPSG_31983 + "\n", encoding="utf-8")
    (output_dir / f"{stem}.cpg").write_text("UTF-8\n", encoding="ascii")


def validate_field_defs(fields: list[FieldDef]) -> None:
    names = [field.name for field in fields]
    if len(names) != len(set(names)):
        raise FixtureError(f"Duplicated DBF field names: {names}")
    for field in fields:
        if len(field.name) > 10:
            raise FixtureError(f"DBF field name exceeds 10 characters: {field.name}")
        if field.field_type not in {"C", "N"}:
            raise FixtureError(f"Unsupported DBF field type for {field.name}: {field.field_type}")


def build_record(
    stem: str,
    index: int,
    model: PointModel,
    truth: dict[str, Any],
    fields: list[FieldDef],
) -> list[Any]:
    temporal_values = serialized_temporal_values(stem, index, truth)
    general_values = general_field_values(stem, index, model, truth)
    row: list[Any] = []
    for field in fields:
        if field.name in temporal_values:
            row.append(temporal_values[field.name])
        elif field.name in general_values:
            row.append(general_values[field.name])
        else:
            raise FixtureError(f"No value supplied for field {field.name} in {stem}")
    return row


def general_field_values(stem: str, index: int, model: PointModel, truth: dict[str, Any]) -> dict[str, Any]:
    row = index // 5
    column = index % 5
    point_id = model.point_id
    height = round(100.0 + 2.5 * row + 0.5 * column, 2)
    quality = round(0.95 - 0.01 * index, 3)
    los_velocity_uncertainty = round(source_los_uncertainty(model, truth), 3)

    if stem == "synthetic_los_ascending":
        velocity = None if point_id == "P19" else round(source_los_velocity(model, truth, orbit="ASC"), 3)
        uncertainty = None if point_id == "P19" else los_velocity_uncertainty
        return {
            "CODE": point_id,
            "COMPONENT": "LOS",
            "ORBIT": "ASC",
            "UNIT": "mm",
            "NODATA": 999.0,
            "VEL": velocity,
            "V_STDEV": uncertainty,
            "HEIGHT": height,
            "COHERENCE": quality,
        }

    if stem == "synthetic_los_descending":
        velocity = None if point_id == "P19" else round(source_los_velocity(model, truth, orbit="DESC"), 3)
        uncertainty = None if point_id == "P19" else los_velocity_uncertainty
        return {
            "POINT_ID": point_id,
            "PASS": "D",
            "COMP": "LOS",
            "UOM": "mm",
            "NODATA": -9999.0,
            "RATE_MM_Y": velocity,
            "RATE_ERR": uncertainty,
            "QUALITY": quality,
        }

    if stem == "synthetic_vertical":
        return {"QUALITY": quality, "ELEV_M": height}

    if stem == "synthetic_east_west":
        velocity = None if point_id == "P19" else round(model.ve / 10.0, 4)
        uncertainty = None if point_id == "P19" else round((0.25 + 0.5 * model.sigma_e) / 10.0, 4)
        return {
            "STATION": point_id,
            "AXIS": "E-W",
            "UOM": "cm",
            "NODATA": -32768.0,
            "MOTION": velocity,
            "UNCERT": uncertainty,
            "CLASS": scenario_class(index),
        }

    raise FixtureError(f"Unknown dataset stem: {stem}")


def serialized_temporal_values(stem: str, index: int, truth: dict[str, Any]) -> dict[str, Any]:
    point_id = POINT_MODELS[index].point_id
    config = DATASETS[stem]
    sentinel = config["sentinel"]

    if stem == "synthetic_los_ascending":
        raw_values = truth["los_ascending_mm"][index, :]
        precision = 3
    elif stem == "synthetic_los_descending":
        raw_values = truth["los_descending_mm"][index, :]
        precision = 3
    elif stem == "synthetic_vertical":
        raw_values = truth["u_mm"][index, :]
        precision = 3
    elif stem == "synthetic_east_west":
        raw_values = truth["e_mm"][index, :] / 10.0
        precision = 4
    else:
        raise FixtureError(f"Unknown dataset stem: {stem}")

    values: dict[str, Any] = {}
    for date_index, field_name in enumerate(DATE_FIELDS):
        if point_id in config["invalid_masks"] and field_name in config["invalid_masks"][point_id]:
            values[field_name] = "NA"
            continue
        if point_id in config["null_masks"] and field_name in config["null_masks"][point_id]:
            values[field_name] = None
            continue
        if point_id in config["sentinel_masks"] and field_name in config["sentinel_masks"][point_id]:
            if stem == "synthetic_east_west" and field_name in {"D20240628", "D20250130"}:
                values[field_name] = f"{sentinel:.1f}"
            else:
                values[field_name] = sentinel
            continue

        rounded = round_float(raw_values[date_index], precision)
        if stem == "synthetic_east_west" and field_name in {"D20240628", "D20250130"}:
            values[field_name] = f"{rounded:.4f}"
        else:
            values[field_name] = rounded
    return values


def source_los_velocity(model: PointModel, truth: dict[str, Any], orbit: str) -> float:
    if orbit == "ASC":
        return model.vu * truth["cos_incidence"] - model.ve * truth["sin_incidence"]
    if orbit == "DESC":
        return model.vu * truth["cos_incidence"] + model.ve * truth["sin_incidence"]
    raise FixtureError(f"Unsupported orbit: {orbit}")


def source_los_uncertainty(model: PointModel, truth: dict[str, Any]) -> float:
    sigma_velocity_u = 0.25 + 0.5 * model.sigma_u
    sigma_velocity_e = 0.25 + 0.5 * model.sigma_e
    return math.sqrt(
        (truth["cos_incidence"] * sigma_velocity_u) ** 2
        + (truth["sin_incidence"] * sigma_velocity_e) ** 2
    )


def scenario_class(index: int) -> str:
    if index <= 1:
        return "stable"
    if index <= 3:
        return "vertical_linear"
    if index <= 5:
        return "eastwest_linear"
    if index <= 7:
        return "combined_linear"
    if index <= 9:
        return "seasonal"
    if index <= 11:
        return "jump"
    if index <= 13:
        return "acceleration"
    if index == 14:
        return "mixed"
    if index == 15:
        return "missing_sentinel"
    if index == 16:
        return "missing_null"
    if index <= 18:
        return "outlier"
    return "sparse"


def point_coordinates(index: int) -> tuple[float, float]:
    column = index % 5
    row = index // 5
    return 300000.0 + 100.0 * column, 7400000.0 + 100.0 * row


def round_float(value: float, decimals: int) -> float:
    # Use numpy's deterministic decimal rounding to match the specification's
    # reference values and the arrays used by tests.
    return float(np.round(value, decimals))


def build_manifest(output_dir: Path, truth: dict[str, Any]) -> dict[str, Any]:
    datasets = {}
    for stem, config in DATASETS.items():
        fields = config["fields"]
        datasets[stem] = {
            "filename_stem": stem,
            "logical_component": config["component"],
            "orbit": config["orbit"],
            "displacement_unit": config["displacement_unit"],
            "velocity_unit": config["velocity_unit"],
            "field_order": [field.name for field in fields],
            "temporal_field_order_physical": config["date_order"],
            "temporal_field_order_chronological": DATE_FIELDS,
            "dbf_fields": [field_to_manifest(field) for field in fields],
            "auto_mappings": config["auto_mappings"],
            "manual_mappings": config["manual_mappings"],
            "missing_value_sentinels": [] if config["sentinel"] is None else [config["sentinel"]],
            "sentinel_masks": config["sentinel_masks"],
            "null_masks": config["null_masks"],
            "invalid_cell_masks": config["invalid_masks"],
            "expected_counts": config["expected_counts"],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR_NAME,
        "random_seed": RANDOM_SEED,
        "random_algorithm": RANDOM_ALGORITHM,
        "crs": {
            "auth_name": "EPSG",
            "auth_code": 31983,
            "name": "SIRGAS 2000 / UTM zone 23S",
            "prj_wkt": PRJ_EPSG_31983,
        },
        "geometry": {
            "type": "Point",
            "origin": {"easting": 300000.0, "northing": 7400000.0},
            "grid": {"columns": 5, "rows": 4, "spacing_m": 100.0, "record_order": "row-major west-east south-north"},
            "points": [
                {"record_index": i, "point_id": model.point_id, "x": point_coordinates(i)[0], "y": point_coordinates(i)[1]}
                for i, model in enumerate(POINT_MODELS)
            ],
        },
        "dates": {
            "field_names": DATE_FIELDS,
            "iso_dates": [d.isoformat() for d in DATE_VALUES],
            "reference_epoch": REFERENCE_DATE.isoformat(),
            "decimal_years_since_reference": [round_float(t, 10) for t in TIME_YEARS],
        },
        "conventions": {
            "canonical_displacement_unit": "mm",
            "vertical_positive": "upward",
            "east_west_positive": "eastward",
            "los_positive": "toward_satellite",
        },
        "los_geometry": {
            "incidence_angle_degrees": INCIDENCE_DEG,
            "north_south_displacement_mm": 0.0,
            "ascending_formula": "U * cos(35 deg) - E * sin(35 deg)",
            "descending_formula": "U * cos(35 deg) + E * sin(35 deg)",
            "inverse_u_formula": "(LOS_ASC + LOS_DESC) / (2 * cos(35 deg))",
            "inverse_e_formula": "(LOS_DESC - LOS_ASC) / (2 * sin(35 deg))",
        },
        "point_models": [point_model_to_manifest(model) for model in POINT_MODELS],
        "datasets": datasets,
        "reference_values": build_reference_values(truth),
        "checksums": sha256_checksums(output_dir),
    }


def field_to_manifest(field: FieldDef) -> dict[str, Any]:
    return {"name": field.name, "type": field.field_type, "width": field.width, "decimal": field.decimal}


def point_model_to_manifest(model: PointModel) -> dict[str, Any]:
    return {
        "point_id": model.point_id,
        "scenario": model.scenario,
        "velocity_u_mm_year": model.vu,
        "acceleration_u_mm_year2": model.au,
        "seasonal_u": {"amplitude_mm": model.seasonal_u_amplitude, "phase_degrees": model.seasonal_u_phase_deg},
        "jump_u_mm": model.jump_u,
        "velocity_e_mm_year": model.ve,
        "acceleration_e_mm_year2": model.ae,
        "seasonal_e": {"amplitude_mm": model.seasonal_e_amplitude, "phase_degrees": model.seasonal_e_phase_deg},
        "jump_e_mm": model.jump_e,
        "sigma_u_mm": model.sigma_u,
        "sigma_e_mm": model.sigma_e,
    }


def build_reference_values(truth: dict[str, Any]) -> dict[str, Any]:
    cells = []
    for point_id, field_name in REFERENCE_CELLS:
        i = int(point_id[1:])
        j = DATE_FIELDS.index(field_name)
        cells.append(
            {
                "point_id": point_id,
                "date_field": field_name,
                "iso_date": DATE_VALUES[j].isoformat(),
                "u_mm": round_float(truth["u_mm"][i, j], 3),
                "e_mm": round_float(truth["e_mm"][i, j], 3),
                "los_ascending_mm": round_float(truth["los_ascending_mm"][i, j], 3),
                "los_descending_mm": round_float(truth["los_descending_mm"][i, j], 3),
                "east_west_stored_cm": round_float(truth["e_mm"][i, j] / 10.0, 4),
            }
        )

    source_velocity_attributes = []
    for point_id in REFERENCE_VELOCITY_POINTS:
        model = POINT_MODELS[int(point_id[1:])]
        source_velocity_attributes.append(
            {
                "point_id": point_id,
                "velocity_u_mm_year": model.vu,
                "velocity_e_mm_year": model.ve,
                "velocity_los_ascending_mm_year": round_float(source_los_velocity(model, truth, "ASC"), 3),
                "velocity_los_descending_mm_year": round_float(source_los_velocity(model, truth, "DESC"), 3),
                "velocity_east_west_cm_year": round_float(model.ve / 10.0, 4),
                "uncertainty_los_mm_year": round_float(source_los_uncertainty(model, truth), 3),
                "uncertainty_east_west_cm_year": round_float((0.25 + 0.5 * model.sigma_e) / 10.0, 4),
            }
        )

    return {"cells": cells, "source_velocity_attributes": source_velocity_attributes}


def sha256_checksums(output_dir: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for path in sorted(output_dir.iterdir()):
        if path.name == "manifest.json" or not path.is_file():
            continue
        checksums[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return checksums


def write_fixture_readme(output_dir: Path) -> None:
    content = """# Synthetic InSAR fixtures

These shapefiles are deterministic reference fixtures for the QGIS InSAR Time Series Viewer.

They are generated by `scripts/generate_synthetic_fixtures.py` from the formal contract in `docs/SYNTHETIC_DATA_SPEC.md`.

Do not edit the generated shapefile components by hand. Update the specification and generator instead, then regenerate the complete directory.

Generated datasets:

- `synthetic_los_ascending.*`
- `synthetic_los_descending.*`
- `synthetic_vertical.*`
- `synthetic_east_west.*`
- `manifest.json`

All coordinates use EPSG:31983. Canonical displacement truth is in millimetres, except the east-west shapefile, which intentionally stores displacement and velocity in centimetres.
"""
    (output_dir / "README.md").write_text(content, encoding="utf-8")


def validate_fixture_dir(output_dir: Path) -> None:
    if not output_dir.exists():
        raise FixtureError(f"Fixture directory does not exist: {output_dir}")

    truth = build_truth_arrays()
    for stem in DATASETS:
        validate_dataset_files(output_dir, stem)
        validate_dataset_content(output_dir, stem, truth)
    validate_reference_values(output_dir, truth)
    validate_los_inverse(output_dir)


def validate_dataset_files(output_dir: Path, stem: str) -> None:
    for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
        path = output_dir / f"{stem}{suffix}"
        if not path.exists():
            raise FixtureError(f"Missing generated file: {path}")
    if (output_dir / f"{stem}.cpg").read_text(encoding="ascii").strip().upper() != "UTF-8":
        raise FixtureError(f"Unexpected CPG encoding for {stem}")
    if "SIRGAS" not in (output_dir / f"{stem}.prj").read_text(encoding="utf-8"):
        raise FixtureError(f"PRJ does not look like EPSG:31983 for {stem}")


def validate_dataset_content(output_dir: Path, stem: str, truth: dict[str, Any]) -> None:
    reader = shapefile.Reader(str(output_dir / f"{stem}.shp"))
    if len(reader) != 20:
        raise FixtureError(f"{stem} feature count mismatch: {len(reader)}")

    actual_fields = [field[0] for field in reader.fields[1:]]
    expected_fields = [field.name for field in DATASETS[stem]["fields"]]
    if actual_fields != expected_fields:
        raise FixtureError(f"{stem} field order mismatch:\nexpected={expected_fields}\nactual={actual_fields}")

    for index, shape_record in enumerate(reader.iterShapeRecords()):
        expected_x, expected_y = point_coordinates(index)
        actual_x, actual_y = shape_record.shape.points[0]
        if abs(actual_x - expected_x) > 1e-9 or abs(actual_y - expected_y) > 1e-9:
            raise FixtureError(f"{stem} coordinate mismatch at record {index}: {(actual_x, actual_y)}")

    counts = count_observations(reader, stem)
    expected_counts = DATASETS[stem]["expected_counts"]
    if counts != {key: expected_counts[key] for key in ("observations", "valid", "missing", "invalid")}:
        raise FixtureError(f"{stem} observation counts mismatch: expected {expected_counts}, actual {counts}")

    validate_selected_serialized_values(reader, stem, truth)


def count_observations(reader: shapefile.Reader, stem: str) -> dict[str, int]:
    sentinel_values = DATASETS[stem]["missing_value_sentinels"] if "missing_value_sentinels" in DATASETS[stem] else None
    sentinel_values = [] if DATASETS[stem]["sentinel"] is None else [float(DATASETS[stem]["sentinel"])]
    observations = valid = missing = invalid = 0
    for record in reader.iterRecords():
        record_dict = record.as_dict()
        for field_name in DATE_FIELDS:
            observations += 1
            value = record_dict[field_name]
            state = classify_temporal_value(value, sentinel_values)
            if state == "valid":
                valid += 1
            elif state == "missing":
                missing += 1
            else:
                invalid += 1
    return {"observations": observations, "valid": valid, "missing": missing, "invalid": invalid}


def classify_temporal_value(value: Any, sentinel_values: list[float]) -> str:
    if value is None:
        return "missing"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "invalid"
    for sentinel in sentinel_values:
        if math.isclose(numeric, sentinel, rel_tol=0.0, abs_tol=1e-9):
            return "missing"
    return "valid"


def validate_selected_serialized_values(reader: shapefile.Reader, stem: str, truth: dict[str, Any]) -> None:
    records = list(reader.iterRecords())
    selected = [("P00", "D20240112"), ("P02", "D20250412"), ("P14", "D20250412"), ("P19", "D20250412")]
    for point_id, field_name in selected:
        index = int(point_id[1:])
        record = records[index].as_dict()
        value = record[field_name]
        if value is None:
            # P19 may be intentionally missing in some layers at some dates, but
            # the selected final date is valid in all four datasets.
            raise FixtureError(f"{stem} unexpected NULL at {point_id}/{field_name}")
        expected = expected_serialized_value(stem, index, field_name, truth)
        actual = float(value)
        tolerance = 0.0001 if stem == "synthetic_east_west" else 0.001
        if abs(actual - expected) > tolerance:
            raise FixtureError(f"{stem} value mismatch at {point_id}/{field_name}: expected {expected}, actual {actual}")


def expected_serialized_value(stem: str, point_index: int, field_name: str, truth: dict[str, Any]) -> float:
    date_index = DATE_FIELDS.index(field_name)
    if stem == "synthetic_los_ascending":
        return round_float(truth["los_ascending_mm"][point_index, date_index], 3)
    if stem == "synthetic_los_descending":
        return round_float(truth["los_descending_mm"][point_index, date_index], 3)
    if stem == "synthetic_vertical":
        return round_float(truth["u_mm"][point_index, date_index], 3)
    if stem == "synthetic_east_west":
        return round_float(truth["e_mm"][point_index, date_index] / 10.0, 4)
    raise FixtureError(f"Unknown dataset stem: {stem}")


def validate_reference_values(output_dir: Path, truth: dict[str, Any]) -> None:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        raise FixtureError("Missing manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_reference_values = build_reference_values(truth)
    if manifest["reference_values"] != expected_reference_values:
        raise FixtureError("Manifest reference_values do not match deterministic truth arrays")

    expected_checksum_names = {
        "README.md",
        *{f"{stem}{suffix}" for stem in DATASETS for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg")},
    }
    actual_checksum_names = set(manifest["checksums"])
    if actual_checksum_names != expected_checksum_names:
        raise FixtureError(f"Checksum file set mismatch: expected {expected_checksum_names}, actual {actual_checksum_names}")


def validate_los_inverse(output_dir: Path) -> None:
    asc_reader = shapefile.Reader(str(output_dir / "synthetic_los_ascending.shp"))
    desc_reader = shapefile.Reader(str(output_dir / "synthetic_los_descending.shp"))
    vert_reader = shapefile.Reader(str(output_dir / "synthetic_vertical.shp"))
    ew_reader = shapefile.Reader(str(output_dir / "synthetic_east_west.shp"))

    cos_i = math.cos(math.radians(INCIDENCE_DEG))
    sin_i = math.sin(math.radians(INCIDENCE_DEG))
    max_u_error = 0.0
    max_e_error_mm = 0.0

    for asc_record, desc_record, vert_record, ew_record in zip(
        asc_reader.iterRecords(), desc_reader.iterRecords(), vert_reader.iterRecords(), ew_reader.iterRecords(), strict=True
    ):
        asc = asc_record.as_dict()
        desc = desc_record.as_dict()
        vert = vert_record.as_dict()
        ew = ew_record.as_dict()
        for field_name in DATE_FIELDS:
            asc_state = classify_temporal_value(asc[field_name], [999.0])
            desc_state = classify_temporal_value(desc[field_name], [-9999.0])
            vert_state = classify_temporal_value(vert[field_name], [])
            ew_state = classify_temporal_value(ew[field_name], [-32768.0])
            if {asc_state, desc_state, vert_state, ew_state} != {"valid"}:
                continue
            asc_value = float(asc[field_name])
            desc_value = float(desc[field_name])
            reconstructed_u = (asc_value + desc_value) / (2 * cos_i)
            reconstructed_e_mm = (desc_value - asc_value) / (2 * sin_i)
            expected_u = float(vert[field_name])
            expected_e_mm = float(ew[field_name]) * 10.0
            max_u_error = max(max_u_error, abs(reconstructed_u - expected_u))
            max_e_error_mm = max(max_e_error_mm, abs(reconstructed_e_mm - expected_e_mm))

    if max_u_error > 0.002 or max_e_error_mm > 0.002:
        raise FixtureError(
            f"LOS inverse reconstruction exceeded tolerance: U={max_u_error:.6f} mm, E={max_e_error_mm:.6f} mm"
        )


if __name__ == "__main__":
    main()
