# Technical Reference

## Module overview

| Module | Responsibility |
|---|---|
| `plugin.py` | QGIS lifecycle, menu actions, dock creation, and help integration |
| `dock_widget.py` | User interface and workflow coordination |
| `insar_timeseries_reader.py` | Layer schema validation and feature-series extraction |
| `timeseries_statistics.py` | Point-selection mean series and dispersion statistics |
| `spatial_selection.py` | Polygon-based point selection and CRS transformation |
| `polygon_means.py` | Independent means for polygon features |
| `plot_controller.py` | Matplotlib figure construction and styling |
| `plot_settings.py` | Persistent project-level chart and export settings |
| `graph_export.py` | Export, filenames, headers, and optional generic watermark |
| `orbit_direction.py` | LOS ascending/descending detection and per-layer override |
| `additional_properties.py` | Additional-attribute selection and summaries |
| `i18n.py` | English/Brazilian Portuguese runtime localization |

## Temporal schema

Acquisition fields must match `DYYYYMMDD` exactly. Valid fields are parsed as calendar dates and sorted chronologically. Duplicate dates and layers with fewer than two valid acquisition fields are rejected.

## Component detection

The reader requires one complete velocity pair:

- LOS: `VEL` and `V_STDEV`;
- vertical: `VEL_V` and `V_STDEV_V`;
- east-west: `VEL_E` and `V_STDEV_E`.

Matching is case-insensitive while the original field spelling is preserved.

## Missing observations

`NULL`, Python `None`, non-finite values, and configured sentinels are excluded. The default sentinel is `999`. Unexpected non-numeric temporal values are reported separately from missing values.

## Means

Point-selection means can use the union of acquisition dates or only acquisitions common to all valid series. Optional zero referencing subtracts each series value at its baseline date before aggregation. Population standard deviation is calculated for valid observations at each acquisition.

Polygon means are computed independently for each polygon. `CODE` is never used to link products or components.

## Trendline

The trendline is a first-degree least-squares fit of displacement against elapsed days. It is calculated locally for visualization and does not replace the product velocity attribute.

## Persistence

Chart settings and LOS orbit overrides are stored in the QGIS project. The stable settings scope is `VisualizadorSeriesTemporais` for compatibility with projects created by earlier builds.

## Help localization

QGIS resolves packaged help by locale. English files are `index-en.html` and `index.html`; Brazilian Portuguese is `index-pt_BR.html`.

## License

Source code is distributed under GPL-2.0-or-later. QGIS, Qt, Matplotlib, NumPy, and other dependencies remain under their respective licenses.
