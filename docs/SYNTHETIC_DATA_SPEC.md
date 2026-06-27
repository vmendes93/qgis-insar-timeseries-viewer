# Synthetic InSAR Reference Datasets Specification

## 1. Status and scope

This document defines the four deterministic shapefile fixtures required by Block 1 of the development roadmap:

1. line-of-sight ascending;
2. line-of-sight descending;
3. vertical displacement;
4. east-west displacement.

The fixtures are designed to validate a provider-independent reader. They are not intended to imitate one vendor's schema or to represent a real site.

This specification is normative for the fixture generator, the machine-readable manifest, and the reader tests. Reader implementation changes must follow this specification rather than changing the fixtures to match existing assumptions.

## 2. Design goals

The fixtures must jointly verify that the plugin can:

- read a point layer from temporal structure alone;
- parse and sort uppercase `DYYYYMMDD` fields independently of physical field order;
- preserve missing observations as gaps;
- tolerate optional semantic metadata being absent;
- detect common field aliases when they are present;
- accept manual field and constant mappings when automatic detection is incomplete;
- distinguish source-supplied attributes from plugin-calculated values;
- handle different displacement units and missing-value sentinels;
- reproduce known vertical, east-west, and LOS values from documented formulas;
- expose stable, linear, seasonal, discontinuous, accelerated, noisy, sparse, null, sentinel, and outlier cases.

## 3. Output layout

Generated files must be written to:

```text
tests/fixtures/synthetic_insar/
```

Required contents:

```text
synthetic_los_ascending.shp
synthetic_los_ascending.shx
synthetic_los_ascending.dbf
synthetic_los_ascending.prj
synthetic_los_ascending.cpg

synthetic_los_descending.shp
synthetic_los_descending.shx
synthetic_los_descending.dbf
synthetic_los_descending.prj
synthetic_los_descending.cpg

synthetic_vertical.shp
synthetic_vertical.shx
synthetic_vertical.dbf
synthetic_vertical.prj
synthetic_vertical.cpg

synthetic_east_west.shp
synthetic_east_west.shx
synthetic_east_west.dbf
synthetic_east_west.prj
synthetic_east_west.cpg

manifest.json
README.md
```

The generator entry point must be:

```text
scripts/generate_synthetic_fixtures.py
```

## 4. Common spatial definition

All four datasets must contain the same 20 logical points in the same record order.

- Geometry type: Point
- CRS: EPSG:31983 — SIRGAS 2000 / UTM zone 23S
- Encoding: UTF-8, declared by `.cpg`
- Origin: easting `300000.0`, northing `7400000.0`
- Grid: 5 columns by 4 rows
- Spacing: 100 metres
- Record order: row-major, west to east, then south to north
- Logical point IDs: `P00` through `P19`

For logical point index `i`:

```text
column = i % 5
row    = i // 5
x      = 300000.0 + 100.0 * column
y      = 7400000.0 + 100.0 * row
```

The coordinates and record order are part of the public test contract. The vertical dataset intentionally omits an identifier field; tests must locate its reference points by coordinates or record index.

## 5. Common acquisition dates

All datasets must contain the same 20 acquisitions:

```text
D20240112
D20240205
D20240229
D20240324
D20240417
D20240511
D20240604
D20240628
D20240722
D20240815
D20240908
D20241002
D20241026
D20241119
D20241213
D20250106
D20250130
D20250223
D20250319
D20250412
```

The leap-day field `D20240229` is intentional.

For acquisition date `d`, time in decimal years is:

```text
t = (d - 2024-01-12).days / 365.25
```

The first acquisition is the reference epoch and must evaluate to zero before missing-value masking.

## 6. Sign and unit conventions

Canonical internal truth is expressed in millimetres.

- `U > 0`: upward movement
- `U < 0`: subsidence
- `E > 0`: eastward movement
- `E < 0`: westward movement
- `LOS > 0`: movement toward the satellite
- `LOS < 0`: movement away from the satellite

Canonical velocity coefficients are expressed in millimetres per year. Acceleration coefficients are expressed in millimetres per year squared.

The east-west shapefile stores displacement in centimetres and velocity in centimetres per year. Conversion from canonical truth is performed only when serializing that dataset:

```text
E_cm = E_mm / 10
```

## 7. Deterministic displacement model

For point `i`, component `C` (`U` or `E`), and acquisition time `t`:

```text
signal_C(t) =
    velocity_C * t
  + 0.5 * acceleration_C * t^2
  + amplitude_C * (sin(2*pi*t + phase_C) - sin(phase_C))
  + jump_C * I(date >= 2024-10-02)
  + noise_C(t)
```

The noise term is generated with:

```python
rng = numpy.random.Generator(numpy.random.PCG64(20260626))
z_u = rng.normal(size=(20, 20))
z_e = rng.normal(size=(20, 20))
noise_u[i, j] = sigma_u[i] * (z_u[i, j] - z_u[i, 0])
noise_e[i, j] = sigma_e[i] * (z_e[i, j] - z_e[i, 0])
```

The subtraction of the first random value guarantees zero displacement at the reference epoch.

After the model and noise are evaluated, the following deterministic outlier impulses are applied:

- `P17`, vertical component, `2024-11-19`: add `+35.0 mm`;
- `P18`, east-west component, `2025-01-30`: add `-40.0 mm`.

The outliers are part of the canonical synthetic observations and therefore propagate into both LOS products.

## 8. Point model catalogue

Angles are expressed in degrees. Empty model terms are zero.

| ID | Scenario | VU | AU | Seasonal U | Jump U | VE | AE | Seasonal E | Jump E | sigma U | sigma E |
|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|---:|
| P00 | stable, noise-free | 0 | 0 | — | 0 | 0 | 0 | — | 0 | 0.0 | 0.0 |
| P01 | stable with controlled noise | 0 | 0 | — | 0 | 0 | 0 | — | 0 | 0.8 | 0.8 |
| P02 | linear subsidence | -20 | 0 | — | 0 | 0 | 0 | — | 0 | 0.0 | 0.0 |
| P03 | linear uplift | 15 | 0 | — | 0 | 0 | 0 | — | 0 | 0.0 | 0.0 |
| P04 | linear eastward motion | 0 | 0 | — | 0 | 18 | 0 | — | 0 | 0.0 | 0.0 |
| P05 | linear westward motion | 0 | 0 | — | 0 | -18 | 0 | — | 0 | 0.0 | 0.0 |
| P06 | subsidence plus eastward motion | -25 | 0 | — | 0 | 12 | 0 | — | 0 | 0.0 | 0.0 |
| P07 | uplift plus westward motion | 10 | 0 | — | 0 | -14 | 0 | — | 0 | 0.0 | 0.0 |
| P08 | vertical seasonal signal | -3 | 0 | amplitude 8, phase 30 | 0 | 0 | 0 | — | 0 | 0.0 | 0.0 |
| P09 | east-west seasonal signal | 0 | 0 | — | 0 | 2 | 0 | amplitude 10, phase -45 | 0 | 0.0 | 0.0 |
| P10 | vertical negative jump | -5 | 0 | — | -15 | 0 | 0 | — | 0 | 0.0 | 0.0 |
| P11 | east-west positive jump | 0 | 0 | — | 0 | 4 | 0 | — | 20 | 0.0 | 0.0 |
| P12 | accelerating subsidence | -5 | -18 | — | 0 | 0 | 0 | — | 0 | 0.0 | 0.0 |
| P13 | accelerating westward motion | 0 | 0 | — | 0 | -4 | -16 | — | 0 | 0.0 | 0.0 |
| P14 | mixed trend, seasonality, and noise | -12 | 0 | amplitude 4, phase 45 | 0 | 9 | 0 | amplitude 3, phase -30 | 0 | 0.3 | 0.3 |
| P15 | sentinel-coded gaps | -8 | 0 | — | 0 | 0 | 0 | — | 0 | 0.3 | 0.2 |
| P16 | DBF-null gaps | 0 | 0 | — | 0 | -10 | 0 | — | 0 | 0.2 | 0.3 |
| P17 | positive vertical outlier | -10 | 0 | — | 0 | 5 | 0 | — | 0 | 0.35 | 0.35 |
| P18 | negative east-west outlier | 5 | 0 | — | 0 | -6 | 0 | — | 0 | 0.35 | 0.35 |
| P19 | sparse observations | -30 | 0 | — | 0 | 20 | 0 | — | 0 | 0.2 | 0.2 |

`VU` and `VE` are the source secular coefficients. They are not regressions of the serialized series. This distinction is intentional for seasonal, jump, acceleration, noise, missing-value, and outlier cases.

### 8.1 Auxiliary metadata values

Unrelated metadata must also be deterministic:

```text
HEIGHT = ELEV_M = 100.0 + 2.5 * row + 0.5 * column
COHERENCE = QUALITY = 0.95 - 0.01 * logical_point_index
```

`COHERENCE` and `QUALITY` are rounded to three decimal places.

The east-west `CLASS` field uses:

| Points | CLASS |
|---|---|
| P00-P01 | `stable` |
| P02-P03 | `vertical_linear` |
| P04-P05 | `eastwest_linear` |
| P06-P07 | `combined_linear` |
| P08-P09 | `seasonal` |
| P10-P11 | `jump` |
| P12-P13 | `acceleration` |
| P14 | `mixed` |
| P15 | `missing_sentinel` |
| P16 | `missing_null` |
| P17-P18 | `outlier` |
| P19 | `sparse` |

## 9. LOS derivation

Both LOS datasets must be calculated from the complete canonical `U` and `E` arrays before dataset-specific missing-value masks are applied.

Assumptions:

- incidence angle: `35 degrees`;
- north-south displacement: `0 mm`;
- ascending and descending observations are right-looking;
- LOS is positive toward the satellite.

Formulas:

```text
LOS_ASC  = U * cos(35 deg) - E * sin(35 deg)
LOS_DESC = U * cos(35 deg) + E * sin(35 deg)
```

Inverse check for cells available in both LOS layers:

```text
U = (LOS_ASC + LOS_DESC) / (2 * cos(35 deg))
E = (LOS_DESC - LOS_ASC) / (2 * sin(35 deg))
```

LOS values must not receive independent random noise after projection.

## 10. Source velocity and uncertainty attributes

Source velocity fields contain the model's secular coefficients, not a fitted trend:

```text
VEL_ASC  = VU * cos(35 deg) - VE * sin(35 deg)
VEL_DESC = VU * cos(35 deg) + VE * sin(35 deg)
VEL_EW   = VE / 10
```

Synthetic source uncertainty values are metadata used to test field reading. For each component:

```text
sigma_velocity_U = 0.25 + 0.5 * sigma_U
sigma_velocity_E = 0.25 + 0.5 * sigma_E

sigma_velocity_LOS = sqrt(
    (cos(35 deg) * sigma_velocity_U)^2
  + (sin(35 deg) * sigma_velocity_E)^2
)
```

The east-west uncertainty is serialized in centimetres per year:

```text
sigma_velocity_EW_cm = sigma_velocity_E / 10
```

No source velocity or uncertainty fields are included in the vertical dataset.

## 11. Dataset-specific schemas

All DBF field names must be 10 characters or fewer.

### 11.1 `synthetic_los_ascending`

Purpose: canonical backward-compatible layout and complete automatic detection.

General fields, in physical order:

| Field | Type | Meaning |
|---|---|---|
| `CODE` | Character(8) | identifier, values `P00` to `P19` |
| `COMPONENT` | Character(9) | constant `LOS` |
| `ORBIT` | Character(4) | constant `ASC` |
| `UNIT` | Character(8) | constant `mm` |
| `NODATA` | Numeric(12,3) | constant `999.0` |
| `VEL` | Numeric(12,3) | source LOS secular velocity, mm/year |
| `V_STDEV` | Numeric(12,3) | source LOS velocity uncertainty, mm/year |
| `HEIGHT` | Numeric(10,2) | unrelated metadata |
| `COHERENCE` | Numeric(5,3) | unrelated metadata |

Temporal fields follow the general fields in chronological order and use `Numeric(14,3)`.

Expected semantic result:

- identifier: automatic, `CODE`;
- velocity: automatic, `VEL`;
- uncertainty: automatic, `V_STDEV`;
- component: automatic, `LOS`;
- orbit: automatic, ascending;
- displacement unit: automatic or configured from `UNIT`;
- sentinel: default `999.0` or configured from the manifest.

### 11.2 `synthetic_los_descending`

Purpose: alias detection and date sorting independent of field position.

Temporal fields appear first, in reverse chronological order, using `Numeric(14,3)`. General fields follow them:

| Field | Type | Meaning |
|---|---|---|
| `POINT_ID` | Character(8) | identifier, values `P00` to `P19` |
| `PASS` | Character(4) | constant `D` |
| `COMP` | Character(8) | constant `LOS` |
| `UOM` | Character(8) | constant `mm` |
| `NODATA` | Numeric(12,3) | constant `-9999.0` |
| `RATE_MM_Y` | Numeric(12,3) | source LOS secular velocity, mm/year |
| `RATE_ERR` | Numeric(12,3) | source LOS velocity uncertainty, mm/year |
| `QUALITY` | Numeric(5,3) | unrelated metadata |

Expected semantic result:

- identifier: automatic alias, `POINT_ID`;
- velocity: automatic alias, `RATE_MM_Y`;
- uncertainty: automatic alias, `RATE_ERR`;
- component: automatic from `COMP=LOS`;
- orbit: automatic from `PASS=D`;
- displacement unit: automatic or configured from `UOM`;
- sentinel: configured as `-9999.0`.

### 11.3 `synthetic_vertical`

Purpose: minimum valid structure with optional semantic metadata absent.

No identifier, velocity, uncertainty, component, orbit, unit, or sentinel field is present.

Physical field order:

1. `QUALITY` — Numeric(5,3), unrelated metadata;
2. even-indexed acquisition fields in chronological order;
3. `ELEV_M` — Numeric(10,2), unrelated metadata;
4. odd-indexed acquisition fields in chronological order.

All temporal fields use `Numeric(14,3)`.

Expected semantic result:

- the layer is valid and its time series can be read without semantic metadata;
- label falls back to the provider feature ID or another explicit reader fallback;
- velocity and uncertainty are unavailable, not zero;
- component and unit remain unknown unless the user supplies constant mappings;
- recommended manual constants: component `vertical`, displacement unit `mm`.

### 11.4 `synthetic_east_west`

Purpose: manual mapping, centimetre units, alternate sentinel, mixed temporal field types, and one invalid cell.

General fields, in physical order:

| Field | Type | Meaning |
|---|---|---|
| `STATION` | Character(8) | identifier, values `P00` to `P19` |
| `AXIS` | Character(8) | constant `E-W` |
| `UOM` | Character(8) | constant `cm` |
| `NODATA` | Numeric(12,1) | constant `-32768.0` |
| `MOTION` | Numeric(12,4) | source east-west secular velocity, cm/year |
| `UNCERT` | Numeric(12,4) | source east-west velocity uncertainty, cm/year |
| `CLASS` | Character(16) | unrelated scenario class |

Temporal fields follow the general fields in this order:

```text
all odd-indexed acquisitions in chronological order,
then all even-indexed acquisitions in chronological order
```

Most temporal fields use `Numeric(14,4)`. The following two fields use `Character(16)` and normally contain decimal numeric strings:

```text
D20240628
D20250130
```

For logical point `P14`, `D20240628` contains `NA` and must be treated as one invalid observation rather than invalidating the layer.

Expected semantic result:

- identifier: automatic alias, `STATION`;
- component: automatic from `AXIS=E-W` or manually set to east-west;
- displacement unit: automatic or configured from `UOM=cm`;
- velocity and uncertainty: intentionally require manual mapping from `MOTION` and `UNCERT`;
- sentinel: configured as `-32768.0`;
- unresolved optional velocity metadata must not prevent plotting the temporal series.

## 12. Missing-data masks

Missing masks are applied only after all canonical components and LOS values have been calculated. Sentinel comparison occurs after numeric coercion, so a textual value such as `-32768.0` is also treated as the configured numeric sentinel.

### LOS ascending

- `P15`: `999.0` at acquisition indexes 4, 5, 6, and 7;
- `P16`: DBF NULL at indexes 8 and 9;
- `P19`: `999.0` at indexes 1 through 18;
- `P19`: `VEL` and `V_STDEV` are DBF NULL.

Expected layer scan:

- total observations: 400;
- valid observations: 376;
- missing observations: 24;
- invalid observations: 0.

### LOS descending

- `P15`: `-9999.0` at indexes 0, 1, and 8;
- `P16`: DBF NULL at indexes 6, 7, 8, and 9;
- `P19`: `-9999.0` at every index except 0, 10, and 19;
- `P19`: `RATE_MM_Y` and `RATE_ERR` are DBF NULL.

Expected layer scan:

- total observations: 400;
- valid observations: 376;
- missing observations: 24;
- invalid observations: 0.

### Vertical

- `P15`: DBF NULL at indexes 2, 3, and 4;
- `P16`: DBF NULL at indexes 0, 9, 10, and 11;
- `P19`: DBF NULL at every index except 0 and 19.

Expected layer scan:

- total observations: 400;
- valid observations: 375;
- missing observations: 25;
- invalid observations: 0.

### East-west

- `P15`: `-32768.0` at indexes 5, 6, 7, and 8;
- `P16`: DBF NULL at indexes 12, 13, and 14;
- `P19`: `-32768.0` at every index except 0, 1, 2, 18, and 19;
- `P14`: text value `NA` at index 7 (`D20240628`);
- `P19`: `MOTION` and `UNCERT` are DBF NULL.

Expected layer scan:

- total observations: 400;
- valid observations: 377;
- missing observations: 22;
- invalid observations: 1.

## 13. Serialization and numerical precision

Processing order is normative:

1. evaluate complete double-precision `U` and `E` arrays;
2. apply deterministic outlier impulses;
3. derive complete double-precision ascending and descending LOS arrays;
4. convert east-west values from millimetres to centimetres;
5. round values for DBF serialization;
6. apply dataset-specific missing and invalid masks.

Rounding:

- LOS and vertical temporal fields: 3 decimal places;
- east-west numeric temporal fields: 4 decimal places;
- source velocity and uncertainty fields: precision declared in each schema;
- coordinates: full double precision supported by the shapefile writer.

Tests comparing serialized values must use absolute tolerances:

- `0.001 mm` for LOS and vertical values;
- `0.0001 cm` for east-west values;
- `0.002 mm` for inverse LOS reconstruction, allowing for independent DBF rounding of the two LOS files.

## 14. Selected reference values

The following values are calculated before missing masks and shown at serialization precision.

| Point | Date | U (mm) | E (mm) | LOS ASC (mm) | LOS DESC (mm) | E stored (cm) |
|---|---|---:|---:|---:|---:|---:|
| P00 | 2024-01-12 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0000 |
| P00 | 2025-04-12 | 0.000 | 0.000 | 0.000 | 0.000 | 0.0000 |
| P02 | 2025-04-12 | -24.969 | 0.000 | -20.454 | -20.454 | 0.0000 |
| P04 | 2025-04-12 | 0.000 | 22.472 | -12.890 | 12.890 | 2.2472 |
| P06 | 2025-04-12 | -31.211 | 14.982 | -34.160 | -16.974 | 1.4982 |
| P08 | 2024-04-17 | 1.795 | 0.000 | 1.470 | 1.470 | 0.0000 |
| P08 | 2025-04-12 | -0.779 | 0.000 | -0.638 | -0.638 | 0.0000 |
| P10 | 2024-09-08 | -3.285 | 0.000 | -2.691 | -2.691 | 0.0000 |
| P10 | 2024-10-02 | -18.614 | 0.000 | -15.248 | -15.248 | 0.0000 |
| P11 | 2024-09-08 | 0.000 | 2.628 | -1.508 | 1.508 | 0.2628 |
| P11 | 2024-10-02 | 0.000 | 22.891 | -13.130 | 13.130 | 2.2891 |
| P12 | 2025-04-12 | -20.270 | 0.000 | -16.604 | -16.604 | 0.0000 |
| P14 | 2025-04-12 | -15.536 | 16.391 | -22.128 | -3.325 | 1.6391 |
| P17 | 2024-11-19 | 27.015 | 4.009 | 19.830 | 24.429 | 0.4009 |
| P18 | 2025-01-30 | 5.450 | -47.291 | 31.590 | -22.660 | -4.7291 |
| P19 | 2025-04-12 | -37.364 | 24.796 | -44.829 | -16.384 | 2.4796 |

The manifest must contain machine-readable expected values for at least these cells and the source velocity attributes of `P00`, `P02`, `P04`, `P06`, `P10`, `P11`, `P12`, `P14`, and `P19`.

## 15. Manifest contract

`manifest.json` must contain at least:

```text
schema_version
generator
random_seed
random_algorithm
crs
geometry
dates
conventions
los_geometry
point_models
datasets
reference_values
checksums
```

Each dataset entry must declare:

- filename stem;
- logical component;
- orbit where applicable;
- displacement and velocity units;
- exact physical field order;
- DBF field types, widths, and precisions;
- semantic field mappings expected from automatic detection;
- semantic mappings intentionally requiring manual configuration;
- missing-value sentinels;
- null, sentinel, and invalid-cell masks;
- expected feature, observation, valid, missing, and invalid counts.

The `checksums` object must contain SHA-256 hashes for every generated file except `manifest.json` itself.

## 16. Generator requirements

The generator must:

- produce all files from scratch without QGIS;
- use a fixed `PCG64` seed of `20260626`;
- fail if a DBF field name exceeds 10 characters;
- preserve the exact field and record order defined here;
- write a valid `.prj` for EPSG:31983 and a UTF-8 `.cpg`;
- replace the complete fixture directory atomically or cleanly;
- write the machine-readable manifest and fixture README;
- calculate and record SHA-256 checksums;
- be idempotent: two clean runs with the same supported dependency versions must produce semantically identical shapefiles and identical manifest reference values;
- expose a validation mode that reopens the generated shapefiles and verifies schema, counts, coordinates, selected values, and LOS inverse reconstruction.

Binary byte-for-byte identity is desirable but not required across different shapefile-library versions because DBF headers may contain implementation-dependent metadata. Tests must validate semantic content and recorded reference values rather than whole-file binary equality.

## 17. Reader acceptance cases driven by the fixtures

The four datasets define the following minimum reader behaviors:

1. `synthetic_los_ascending` is recognized without manual mapping.
2. `synthetic_los_descending` is recognized through aliases and its reverse physical date order is sorted chronologically.
3. `synthetic_vertical` remains readable despite having no identifier, velocity, uncertainty, component, orbit, unit, or sentinel metadata.
4. `synthetic_east_west` remains readable before velocity mapping and accepts manual mappings for `MOTION` and `UNCERT`.
5. Configured sentinels `999`, `-9999`, and `-32768` become missing values, not plotted numbers.
6. DBF NULL values become gaps.
7. Numeric strings in temporal fields are accepted.
8. The single `NA` cell is reported as an invalid observation without invalidating its feature or layer.
9. A feature with only two valid temporal observations is readable.
10. Source velocities remain identifiable as source attributes and are not silently replaced by plugin regressions.
11. For cells available in both LOS files, inverse decomposition reconstructs the serialized vertical and east-west truth within the declared tolerance.

## 18. Non-goals

This fixture version does not test:

- line or polygon source geometries;
- north-south displacement;
- multiple incidence angles;
- multiple tracks within one shapefile;
- alternate temporal field-name conventions beyond uppercase `DYYYYMMDD`;
- duplicate or invalid acquisition field names;
- provider-specific proprietary metadata;
- large-layer performance.

Those cases may be added as separate negative or performance fixtures without changing the four reference datasets defined here.
