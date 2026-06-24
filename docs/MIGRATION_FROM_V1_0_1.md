# Migration from the pre-public 1.0.1 package

The public package uses the installable directory `insar_timeseries_viewer` instead of `visualizador_series_temporais`.

## Avoid duplicate installations

Before installing the public package:

1. Disable the earlier plugin in QGIS.
2. Close QGIS.
3. Remove the old `visualizador_series_temporais` directory from the active profile's `python/plugins` directory.
4. Install the new ZIP through the Plugin Manager.

If both directories remain installed, QGIS may display duplicate actions with the same user-facing name.

## Project settings

The QGIS project settings scope remains `VisualizadorSeriesTemporais`. Existing chart settings and LOS orbit overrides should therefore remain readable after migration.

## Release ZIP name

The public package is distributed as:

```text
insar_timeseries_viewer-1.0.0.zip
```
