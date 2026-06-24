# Data Requirements

## Compatible point layers

The source must be a valid vector layer with point geometry and at least two
valid acquisition fields.

### Required acquisition fields

Time-series values must be stored in fields named exactly:

```text
DYYYYMMDD
```

Examples:

```text
D20231110
D20240115
D20260522
```

Rules:

- The prefix must be uppercase `D`.
- The remaining eight characters must form a valid calendar date.
- Acquisition dates must not be duplicated.
- Physical field order is irrelevant; the plugin parses and sorts the dates.
- Values should be numeric displacement observations, normally in millimetres.

### Component detection

The plugin recognizes a layer from one of these field pairs:

| Component | Velocity field | Velocity standard-deviation field |
|---|---|---|
| LOS | `VEL` | `V_STDEV` |
| VERT | `VEL_V` | `V_STDEV_V` |
| EW | `VEL_E` | `V_STDEV_E` |

Field matching for these component fields is case-insensitive, while the actual
field names are preserved for display and export.

### Missing values

The following values are treated as missing observations:

- numeric sentinel `999`;
- QGIS `NULL`;
- Python `None`;
- NaN or non-finite numeric values.

Unexpected non-numeric values in acquisition fields are ignored and reported
as invalid fields for that feature.

### Point label

`CODE` is preferred as the local display label. If it is unavailable, the QGIS
layer display field is used when possible; otherwise the feature ID is used.

`CODE` is never used to join or associate layers, components, products, or
polygon groups.

### Optional general fields

Any non-temporal attribute may be selected as an additional property, such as:

- `ACC`;
- `HEIGHT`;
- `H_STDEV`;
- `STD_DEF`;
- `COHERENCE`;
- `EFF_AREA`.

Numeric fields are summarized statistically in mean modes. Text fields are
shown directly when consistent or reported as multiple values when they differ.

## Polygon layers

Area selection and polygon means require a polygon or multipolygon vector
layer. The polygon and point layers may use different coordinate reference
systems; the plugin transforms the polygon geometry temporarily into the point
layer CRS.

For independent polygon means:

- each polygon feature defines its own point group;
- overlapping polygons may share points;
- polygons without points are skipped and reported;
- multipart geometry is treated as one polygon feature;
- a user-selected attribute can name each mean series;
- empty names fall back to `Mean of X points`.

## Recommended preparation

- Ensure the layer has a valid CRS.
- Confirm displacement and velocity units before interpretation.
- Keep field names stable throughout a project.
- Validate that `999` is used only as a missing-value sentinel.
- Avoid duplicate acquisition fields or malformed date names.
- Save edits before calculating large polygon groups.
