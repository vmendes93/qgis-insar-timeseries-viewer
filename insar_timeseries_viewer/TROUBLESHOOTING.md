# Troubleshooting

## The plugin does not appear

- Confirm that the ZIP contains one top-level directory named `insar_timeseries_viewer`.
- Confirm that `metadata.txt`, `__init__.py`, and `LICENSE` are present inside that directory.
- Restart QGIS and check **Plugins → Manage and Install Plugins → Installed**.

## The panel cannot be created

Open **View → Panels → Log Messages** and inspect the Python and plugin messages. The most common causes are an incomplete QGIS Python environment or an incompatible Matplotlib/Qt installation.

## A layer is rejected

Confirm that:

- the layer is a valid vector point layer;
- it has at least two valid `DYYYYMMDD` fields;
- it contains exactly one supported velocity pair;
- acquisition dates are valid and not duplicated.

## Values are missing from a chart

Null values, `NaN`, infinite values, and `999` are treated as missing observations. Other non-numeric values are excluded and reported as invalid fields.

## LOS direction is incorrect

Automatic detection uses separated tokens in the layer name and then the source filename. Set the per-layer orbit override in the panel when naming is ambiguous.

## Export fails

- Verify write permission in the destination directory.
- Use PNG, SVG, or PDF.
- Check whether the target file is open in another program.
- Try a shorter output path on Windows.

## Reporting a reproducible problem

Open an issue in the public tracker and include:

- QGIS version and operating system;
- plugin version;
- a minimal sanitized dataset or schema description;
- exact steps to reproduce;
- the complete traceback from the QGIS log.

Never attach confidential project data.
