# Plot Visual Specification

This document defines the target visual behavior for exported figures in the InSAR Time Series Viewer.

The purpose is to make exported plots suitable for direct use in technical reports without mandatory post-processing in another application.

This specification applies to the public, generic plugin. Organization-specific branding, logos, colors, support contacts, or report templates belong in private downstream distributions.

## Scope

This specification covers:

- single-point time-series plots;
- multi-point overlay plots;
- separate multi-point plots;
- selected-point mean plots;
- polygon mean plots;
- PNG, SVG, and PDF chart export;
- preview/export consistency;
- default visual presets.

This specification does not cover:

- CSV data export;
- map canvas symbology;
- QGIS layer styling;
- private downstream branding;
- report layout outside the exported chart.

## Core principles

- The plot must remain readable before it becomes decorative.
- The default output must be conservative enough for technical reporting.
- Every acquisition must remain visible as a marker.
- Trendlines and fitted values must never obscure the original observations.
- Product type must be communicated clearly: LOS, vertical, or east-west.
- Sign convention must be visible or inferable without external context.
- Missing observations must not be connected as if they existed.
- Preview and exported output must be visually consistent.
- Public output must remain generic and provider-neutral.

## Figure anatomy

A report-ready figure should contain these regions, in this order:

1. Title area
2. Metadata subtitle area
3. Plot area
4. Legend area
5. Optional note/footer area

### Required elements

Every exported figure must show:

- displacement time series;
- acquisition markers for every valid observation;
- x-axis date context;
- y-axis displacement unit;
- plot title or clear series label;
- product/component when known;
- observation period when available;
- enough metadata to identify what was plotted.

### Optional elements

These elements may be enabled, but should not be visually dominant by default:

- fitted trendline;
- velocity label;
- velocity uncertainty;
- cumulative displacement;
- shaded periods;
- additional attributes;
- watermark;
- dense metadata notes.

## Product conventions

### LOS

Meaning:

- LOS displacement is measured along the satellite line of sight.
- Positive LOS values should be labeled as displacement toward the satellite when that convention is known.

Recommended default label:

```text
LOS displacement (mm)
```

Recommended sign note when space allows:

```text
Positive values: toward satellite
```

Default visual behavior:

- neutral/cyan-compatible style;
- avoid implying vertical motion;
- orbit direction should be shown when detected.

### Vertical

Meaning:

- negative vertical displacement indicates subsidence;
- positive vertical displacement indicates uplift.

Recommended default label:

```text
Vertical displacement (mm)
```

Recommended sign note when space allows:

```text
Negative: subsidence · Positive: uplift
```

Default visual behavior:

- use a style distinct from LOS;
- emphasize zero line when visible;
- avoid labels that imply LOS or east-west movement.

### East-west

Meaning:

- negative east-west displacement indicates westward motion;
- positive east-west displacement indicates eastward motion.

Recommended default label:

```text
East-west displacement (mm)
```

Recommended sign note when space allows:

```text
Negative: westward · Positive: eastward
```

Default visual behavior:

- use a style distinct from LOS and vertical;
- emphasize zero line when visible;
- avoid labels that imply vertical motion.

### Unknown component

When component cannot be inferred:

- use generic displacement labels;
- do not invent sign convention;
- include a clear unknown/unspecified component note in metadata.

Recommended default label:

```text
Displacement (mm)
```

## Title and metadata hierarchy

### Single series

Recommended hierarchy:

```text
<identifier>
<component/orbit if known> · <date range> · VEL: <value> mm/yr · Cum.: <value> mm
```

Rules:

- identifier is the primary title;
- component and orbit belong in subtitle metadata;
- VEL and cumulative displacement should be compact;
- velocity uncertainty may be shown when available and not cluttering the title.

### Overlay and separate plots

Recommended hierarchy:

```text
Selected point time series
<n> points · <component if common> · <date range>
```

Rules:

- avoid putting every point identifier in the title;
- point identifiers belong in the legend;
- for dense overlays, legend behavior must prevent unreadable output;
- when multiple components are mixed, clearly indicate that the component is mixed.

### Mean plots

Recommended hierarchy:

```text
Mean displacement time series
<n> points · <component if common> · <date range>
```

Rules:

- mean plots must clearly state the number of source points;
- standard deviation or spread indicators may be optional;
- source identifiers should not clutter the title.

### Polygon mean plots

Recommended hierarchy:

```text
Polygon mean displacement time series
<n> polygons · <component if common> · <date range>
```

Rules:

- polygon labels belong in the legend;
- source point count per polygon should be available in metadata or CSV;
- do not overload the graph with all source point identifiers.

## Axes and gridlines

### X-axis

The x-axis must show acquisition dates in a readable format.

Recommended behavior:

- short histories: show more date ticks;
- medium histories: show reduced date ticks;
- long histories: show quarterly/yearly context as needed;
- avoid overlapping date labels;
- exported output must not clip date labels.

Preferred date label style:

```text
YYYY-MM-DD
```

or, for dense histories:

```text
YYYY-MM
```

### Y-axis

The y-axis must show displacement in millimeters.

Recommended label:

```text
Displacement (mm)
```

or product-specific variants:

```text
LOS displacement (mm)
Vertical displacement (mm)
East-west displacement (mm)
```

Rules:

- zero line should be visible when within range;
- automatic limits should include padding;
- low-displacement stable series should not look artificially dramatic;
- high-displacement series should not clip markers or annotations;
- manual limits must be validated before plotting.

### Gridlines

Default behavior:

- horizontal gridlines enabled;
- vertical gridlines subtle or disabled depending on preset;
- zero line visually clearer than regular gridlines;
- gridlines must not overpower observations.

## Observations, markers, and missing values

Markers are required on every valid acquisition.

Rules:

- line segments must not connect across missing observations;
- nulls and sentinel missing values must be treated as missing observations;
- marker size must remain visible in exported PNG/PDF output;
- SVG output must preserve marker visibility;
- dense overlays may reduce marker size but must not remove markers by default.

## Trendline and velocity behavior

Trendlines are analytical aids, not replacements for the observations.

Rules:

- the original time series must remain visually dominant;
- trendline must be visually secondary;
- trendline label must not overlap data;
- trendline must be omitted or disabled when too few valid observations exist;
- fitted trendline velocity must be distinguishable from source-layer velocity when both are displayed.

Recommended terminology:

```text
Layer VEL
```

for velocity supplied by the source layer.

```text
Fitted trend
```

for velocity calculated by the plugin from the displayed observations.

If source velocity and fitted velocity differ, the plot must not silently imply they are the same value.

## Legends

### Single series

Legend may be omitted if the title fully identifies the series.

### Overlay plots

Legend should be shown when the number of series is small.

For dense overlays:

- use compact legend;
- allow legend suppression via preset;
- avoid covering data;
- prefer outside/right or bottom placement when space allows.

### Mean and polygon mean plots

Legend should identify mean series and polygon labels when needed.

Rules:

- legend must never overlap the title;
- legend must never cover critical annotations;
- exported output must not clip the legend.

## Presets

The plugin should provide reusable plot presets. Presets should control visual choices only. They must not overwrite layer field mappings.

### Report-ready

Purpose:

- default technical report figure;
- balanced metadata;
- conservative styling;
- export-safe margins.

Recommended behavior:

- title and metadata enabled;
- horizontal grid enabled;
- zero line emphasized when visible;
- trendline optional but clean;
- legend enabled when useful;
- watermark disabled;
- PNG export at report quality.

### Exploration

Purpose:

- interactive inspection inside QGIS.

Recommended behavior:

- more metadata can be visible;
- hover/interactive behavior prioritized;
- preview readability prioritized over export compactness;
- legends may be more permissive.

### Dense overlay

Purpose:

- many selected points in one plot.

Recommended behavior:

- smaller markers but still visible;
- compact or suppressed legend;
- reduced metadata;
- stronger emphasis on overall pattern;
- avoid label clutter.

### Presentation

Purpose:

- slides and screen sharing.

Recommended behavior:

- larger fonts;
- thicker lines;
- fewer metadata details;
- high visual contrast;
- generous margins.

### Minimal

Purpose:

- clean figure for use inside larger report layouts.

Recommended behavior:

- reduced header;
- minimal grid;
- compact legend or no legend;
- no watermark;
- no excessive annotations.

## Export behavior

### Formats

Supported chart export formats:

- PNG;
- SVG;
- PDF.

All formats should contain the same intended content.

### Default export quality

Recommended defaults:

- PNG: 300 DPI when saved for report use;
- PDF: vector where possible;
- SVG: vector elements preserved where possible.

### File naming

Suggested filename pattern:

```text
<layer_name>_<plot_mode>_<identifier_or_count>_<YYYYMMDD>.png
```

Rules:

- sanitize unsafe filename characters;
- do not silently overwrite existing files;
- keep chart export and CSV export naming consistent but distinct.

### Margins and clipping

Exported figures must not clip:

- title;
- subtitle;
- axis labels;
- tick labels;
- legend;
- watermark;
- annotations;
- acquisition markers.

## Watermark and branding

Public plugin behavior:

- watermark disabled by default;
- watermark text must be generic if enabled;
- no organization-specific logos or names;
- watermark must never overlap data, labels, legends, or title;
- private branding belongs only in private downstream builds.

## Documentation requirements

After visual behavior stabilizes, documentation should include:

- screenshot of single-point plot;
- screenshot of overlay plot;
- screenshot of mean plot;
- screenshot of polygon mean plot;
- one exported PNG example;
- explanation of presets;
- explanation of sign conventions;
- recommended settings for report-ready figures.

## Acceptance checklist

Before releasing Block 2, verify:

- [ ] Single LOS plot is readable and export-safe.
- [ ] Single vertical plot is readable and export-safe.
- [ ] Single east-west plot is readable and export-safe.
- [ ] Dense overlay plot remains readable.
- [ ] Selected-point mean plot clearly states source count.
- [ ] Polygon mean plot clearly identifies polygon series.
- [ ] Markers appear on every valid acquisition.
- [ ] Missing values are not connected across gaps.
- [ ] Date ticks do not overlap severely.
- [ ] Y-axis limits do not clip markers or annotations.
- [ ] Zero line is clear when visible.
- [ ] Trendline does not dominate observations.
- [ ] Source VEL and fitted trend are not conflated.
- [ ] Legend does not cover data or metadata.
- [ ] PNG export is not clipped.
- [ ] SVG export is not clipped.
- [ ] PDF export is not clipped.
- [ ] Public output contains no organization-specific branding.
- [ ] `bash scripts/run_all_checks.sh` passes.

## Implementation notes

Likely implementation areas:

- plot settings model;
- plot controller;
- dock widget controls;
- graph export helpers;
- tests for settings, presets, labels, and export smoke behavior;
- documentation screenshots after behavior stabilizes.

Do not add pixel-perfect tests unless the comparison is robust across platforms. Prefer structural tests for labels, settings, preset values, export file creation, and missing-value behavior.
