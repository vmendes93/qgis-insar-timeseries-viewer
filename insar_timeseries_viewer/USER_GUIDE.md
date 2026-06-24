# User Guide

## 1. Open the viewer

Load a compatible InSAR point layer, then open the plugin from the Vector menu
or toolbar. The dock panel lists compatible point layers in the current QGIS
project.

The settings panel remains beside the chart so changes can be evaluated
immediately. Its divider can be resized, and the settings area can be hidden
when more chart space is required.

## 2. Select the point layer

Choose the target layer in the layer selector. The plugin reports:

- detected component (`LOS`, `VERT`, or `EW`);
- LOS orbit direction when inferred or manually assigned;
- acquisition count and overall date range;
- selected-point count.

LOS direction can be automatic, ascending, descending, or unspecified. The
automatic mode inspects separated `A`, `D`, `ASC`, and `DESC` tokens in the layer
name and source path.

## 3. Display modes

### Single series

Displays one selected feature. When several features remain selected, the
viewer uses the most recently selected feature for this mode.

### Overlaid series

Displays multiple selected point series on one axis. The first series is black;
additional series use the Matplotlib color cycle. The configured maximum number
of series limits the rendered selection for responsiveness.

### Separate series

Displays one vertically stacked chart per selected point. Each main series is
black because it is the only primary series in its subplot. The chart area is
vertically scrollable.

### Series mean

Calculates an acquisition-by-acquisition mean from the selected points.

Options:

- **Common acquisitions only:** uses dates valid for every included point.
- **Reference each series to zero:** subtracts a baseline before averaging.
- **Mean ± 1 standard deviation:** shows a population standard-deviation band.
- **Individual series in background:** displays the source series behind the mean.

When common acquisitions are disabled, the mean uses available values and
requires at least two valid points at each date. The hover and status text show
the effective sample count.

## 4. Area selection

### Draw an area

1. Choose the point-selection operation: replace, add, or remove.
2. Click **Draw area on map**.
3. Left-click to add vertices.
4. Right-click or double-click to finish.
5. Press `Esc` to cancel.

Points inside or touching the polygon boundary are applied to the QGIS
selection. Clearing the temporary area removes only the drawn outline; it does
not clear the point selection.

### Use a polygon feature

1. Choose a polygon layer.
2. Select exactly one polygon feature in that layer.
3. Choose the point-selection operation.
4. Click **Use selected polygon**.

## 5. Independent means by polygon

This workflow preserves each polygon as a separate group.

1. Choose a polygon layer under Area selection.
2. Choose whether to process all polygons or only selected polygons.
3. Optionally choose a field used to name the mean series.
4. Choose overlaid or separate polygon means.
5. Click **Calculate polygon means**.

Each polygon produces its own mean from the points it contains. If the naming
field is blank, the label becomes `Mean of X points`. Duplicate labels are
qualified with the polygon feature ID.

Use **Return to selected points** to leave polygon-mean mode.

## 6. Appearance and interaction

Available controls include:

- line and marker visibility;
- line width and marker size;
- zero-reference line;
- legend visibility;
- hover inspection;
- linear trendline for the primary or all series;
- independent horizontal and vertical gridlines;
- solid or dashed black gridline styles;
- shaded time period with adjustable opacity;
- automatic or manual X and Y ranges;
- manual tick intervals.

The trendline is a locally calculated least-squares linear regression drawn as
a solid red line. It is not the product `VEL` value and does not replace product
processing.

Hovering near a point displays its label, exact date, cumulative displacement,
and sample count for mean curves.

## 7. Additional properties

The Additional properties list contains non-temporal attributes from the active
point layer. Selected fields can be shown in the panel and/or added to exported
chart headers.

Interpretation by mode:

- single series: feature value;
- overlaid series: range or common text value;
- selected-point mean: mean of numeric fields;
- polygon mean: mean of numeric values inside that polygon;
- separate batch export: values specific to each exported item.

## 8. Export

The current chart can be saved as PNG, SVG, or PDF. Separate point charts and
separate polygon means can be batch-exported to a folder.

Options include:

- physical width and height;
- PNG DPI;
- white or transparent background;
- data header;
- selected additional properties;
- generic plugin watermark;
- watermark opacity, position, and scale.

The exported header uses the literal product field names, such as `VEL_V` and
`V_STDEV_V`. Existing files are not silently overwritten during batch export;
a numeric suffix is added.

## 9. Project persistence

Most chart, mean, axis, export, watermark, and panel-layout settings are saved
inside the QGIS project. Additional-property selections and LOS direction
overrides are stored per layer.

Save the `.qgz` project after configuring the viewer.

## 10. Language

The plugin follows the QGIS interface locale when QGIS starts:

- Portuguese locale → Brazilian Portuguese;
- English locale → English;
- unsupported locale → English fallback.

Restart QGIS after changing the interface language.
