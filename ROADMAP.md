# Development Roadmap

This roadmap records the major development blocks planned after the first stable public release. It is organized around large outcomes rather than individual implementation tasks.

The roadmap is directional. Scope and version numbers may change as testing exposes new requirements.

## Current status

- **1.1.0 is released.** The first public feature-complete workflow is available.
- **Block 1 is functionally complete for internal validation.** External field-alias hardening will be driven by real user feedback.
- **Block 2 is the next active block.** The focus is plot appearance, report-ready exports, presets, and visual consistency.
- **Block 3 is partially underway.** Field mapping, click-to-plot, CSV export, and the active-layer report already exist, but the dock still needs a broader UX pass.
- **Block 4 remains deferred.** The private downstream distribution should be created only from a stable public tag and kept as a small auditable delta.

## Guiding principles

- The reader must depend on the structure of the data, not on the identity of the data provider.
- Point-based InSAR time series should remain readable even when optional metadata is absent.
- Synthetic, redistributable datasets must provide an auditable reference for development and external contributions.
- Generic improvements belong in the public repository.
- Organization-specific branding, defaults, or workflows belong in a private downstream distribution.
- Public releases should remain installable, reproducible, and warning-free.
- Exported figures and data should be suitable for technical review without requiring manual cleanup.

## Block 1 — Generic reader and synthetic reference datasets

**Target:** 1.1.0

**Status:** Released / awaiting external feedback

**Goal:** Read point-based InSAR time series without requiring prior knowledge of the company or processing chain that produced the layer.

### Major deliverables

- [x] Define the minimum valid input structure:
  - point geometry;
  - at least two valid temporal fields;
  - temporal values that can be interpreted as numeric displacement observations.
- [x] Make identifier, velocity, velocity uncertainty, component, orbit, unit, and missing-value sentinels optional or configurable.
- [x] Keep `DYYYYMMDD` as the initial temporal-field convention while designing the reader so other date mappings can be added later.
- [x] Add automatic alias detection for common identifier, velocity, uncertainty, component, and orbit field names.
- [x] Add manual field mapping when automatic detection is incomplete or ambiguous.
- [x] Store layer-specific mappings in the QGIS project.
- [x] Distinguish values supplied by the source layer from values calculated by the plugin.
- [x] Create four deterministic synthetic point datasets:
  - LOS ascending;
  - LOS descending;
  - vertical;
  - east-west.
- [x] Use different attribute layouts across the four datasets to exercise generic field detection.
- [x] Include stable areas, subsidence, uplift, eastward and westward motion, seasonal behavior, jumps, controlled noise, missing values, nulls, and outliers.
- [x] Generate LOS datasets mathematically from documented synthetic vertical and east-west components.
- [x] Add a deterministic generator script with a fixed random seed.
- [x] Add a machine-readable manifest describing CRS, fields, dates, units, sentinels, formulas, and expected behavior.
- [x] Add expected values for selected reference points.
- [x] Add unit and PyQGIS integration tests for schema detection, reading, missing values, manual mapping, and known synthetic results.
- [x] Document the synthetic datasets for users and external contributors.

### Completion criteria

A point layer with valid temporal observations can generate a time series even when provider-specific metadata is missing. The four synthetic datasets can be regenerated, inspected, and used to verify known results.

### Remaining risk

The reader is structurally generic, but real-world provider aliases and malformed layer variants cannot be fully anticipated. Additional aliases and edge-case handling should be added only when real users provide reproducible examples.

## Block 2 — Plot appearance, presets, and exported products

**Target:** 1.2.0

**Status:** Active next block

**Goal:** Produce clear, consistent figures that can be used directly in technical reports.

### Main task groups

#### 1. Visual specification and reference outputs

- [ ] Define a formal visual specification for default plots.
- [ ] Choose reference examples for LOS, vertical, east-west, selected mean, and polygon mean plots.
- [ ] Document sign conventions and labels:
  - LOS positive toward satellite;
  - vertical negative as subsidence and positive as uplift;
  - east-west negative as westward and positive as eastward.
- [ ] Define required visible elements for a report-ready figure.
- [ ] Define optional elements that should stay hidden unless explicitly enabled.
- [ ] Add a small visual acceptance checklist for every exported figure.

#### 2. Product-specific default styles

- [ ] Define coherent default color and label behavior for LOS products.
- [ ] Define coherent default color and label behavior for vertical products.
- [ ] Define coherent default color and label behavior for east-west products.
- [ ] Review line width, marker size, marker frequency, and marker contrast.
- [ ] Preserve markers on every acquisition.
- [ ] Ensure single, overlaid, separate, mean, and polygon-mean plots remain visually distinct.

#### 3. Header and metric hierarchy

- [ ] Refine title, subtitle, and information hierarchy.
- [ ] Improve presentation of identifier, component, orbit, velocity, uncertainty, cumulative displacement, and observation period.
- [ ] Keep single-series headers compact.
- [ ] Keep multi-series and mean headers readable without excessive width.
- [ ] Define when metadata belongs in the figure header, legend, footer, or CSV instead of the graph area.
- [ ] Avoid duplicated information between title, legend, and annotations.

#### 4. Axes, date ticks, gridlines, and limits

- [ ] Improve date tick behavior for short, medium, and long acquisition histories.
- [ ] Review automatic y-axis limits for high-motion and low-motion series.
- [ ] Improve manual limit behavior and validation messages.
- [ ] Refine horizontal and vertical gridline defaults.
- [ ] Improve label rotation and spacing for dense temporal series.
- [ ] Ensure exported PNG/SVG/PDF outputs match the preview.

#### 5. Trendline, velocity, and cumulative displacement presentation

- [ ] Refine trendline presentation and labeling.
- [ ] Decide how analytical VEL and fitted trendline velocity should be shown when both exist.
- [ ] Define behavior when velocity fields are absent.
- [ ] Define behavior when too few valid observations exist for a trendline.
- [ ] Improve cumulative displacement display for individual and mean series.
- [ ] Keep uncertainty display clear but not visually dominant.

#### 6. Plot presets

- [ ] Add reusable plot presets.
- [ ] Suggested initial presets:
  - `Report-ready`;
  - `Exploration`;
  - `Dense overlay`;
  - `Presentation`;
  - `Minimal`.
- [ ] Define which settings each preset controls.
- [ ] Let users apply a preset without overwriting unrelated layer mappings.
- [ ] Persist the selected preset in plugin settings.
- [ ] Add tests for preset serialization and defaults.

#### 7. Export behavior

- [ ] Standardize PNG, SVG, and PDF export behavior.
- [ ] Define default export DPI and dimensions.
- [ ] Define safe margins for titles, legends, and headers.
- [ ] Improve export filename suggestions.
- [ ] Ensure existing files are never silently overwritten.
- [ ] Keep chart export and CSV export conceptually separate but consistent in naming.
- [ ] Review whether PDF metadata should include plugin version and layer name.
- [ ] Add export smoke tests where feasible without fragile pixel-perfect comparisons.

#### 8. Watermark and branding behavior

- [ ] Improve watermark behavior and positioning.
- [ ] Keep watermark disabled by default in the public plugin.
- [ ] Ensure watermark never overlaps plotted data, labels, legends, or headers.
- [ ] Keep all public watermark behavior generic and free of organization-specific branding.
- [ ] Reserve organization-specific branding for private downstream builds.

#### 9. Documentation and screenshots

- [ ] Update screenshots after visual changes stabilize.
- [ ] Add example outputs for LOS, vertical, east-west, mean, and polygon-mean workflows.
- [ ] Update quick-start instructions to show export choices.
- [ ] Document the presets and what each is intended for.
- [ ] Document recommended figure settings for technical reports.
- [ ] Add a short “How to cite/export figures responsibly” note if needed.

#### 10. Validation and release criteria

- [ ] Compare outputs against the project reference figures.
- [ ] Run `bash scripts/run_all_checks.sh`.
- [ ] Test exported PNG/SVG/PDF from a clean QGIS profile.
- [ ] Test at least one dense overlay case.
- [ ] Test at least one low-displacement stable case.
- [ ] Test at least one high-displacement case.
- [ ] Test one polygon-mean output.
- [ ] Test on Linux/QGIS 3.44 and Windows/QGIS LTR when available.

### Completion criteria

A default exported graph is suitable for direct inclusion in a technical report without mandatory editing in another application. Presets make common plotting workflows reproducible, and exported PNG/SVG/PDF files match the preview closely enough for technical use.

## Block 3 — User interface and user experience

**Target:** 1.3.0

**Status:** Partially underway

**Goal:** Make the complete workflow understandable, efficient, and resistant to configuration errors.

### Already delivered in 1.1.0

- [x] Add a field-mapping interface for unrecognized or ambiguous layers.
- [x] Add a layer diagnostic summary showing acquisitions, date range, detected fields, inferred component, and relevant fields.
- [x] Persist layer-specific field mappings in the QGIS project.
- [x] Add click-to-plot map interaction.
- [x] Add active point highlighting, zoom-to-point, and clear-selection controls.
- [x] Add CSV export for displayed time-series data.
- [x] Review enabled and disabled states for the new selection/export controls.
- [x] Review Brazilian Portuguese and English interface text for the new workflows.

### Remaining major deliverables

- [ ] Reorganize the dock to reduce simultaneous visual complexity.
- [ ] Separate basic and advanced controls.
- [ ] Establish a clear workflow:
  1. select layer;
  2. validate or map fields;
  3. select points or area;
  4. generate graph;
  5. export.
- [ ] Improve validation messages, warnings, and error recovery.
- [ ] Persist additional relevant settings per layer and QGIS project.
- [ ] Review enabled and disabled states for all controls, not only the new controls.
- [ ] Add concise tooltips and contextual help for all controls.
- [ ] Validate behavior on supported Windows and Linux QGIS environments.
- [ ] Update screenshots, quick-start instructions, and user documentation after the Block 2 visual pass.

### Completion criteria

A user familiar with QGIS and InSAR can load a compatible layer and create the first graph without inspecting source code or requiring external instructions.

## Block 4 — Optional private downstream distribution

**Target:** After a sufficiently mature public release

**Status:** Deferred / optional

**Goal:** Produce an internal-use package derived from a stable public tag while keeping the public plugin generic and free of organization-specific material.

### Recommended model

- [ ] Maintain organization-specific changes in a private downstream repository or private fork, not in a permanent public branch.
- [ ] Base each internal build on an explicit stable public tag.
- [ ] Keep the private delta as small as possible.
- [ ] Limit private changes to branding, support contacts, defaults, internal documentation, and genuinely organization-specific workflows.
- [ ] Return all generic fixes and improvements to the public repository.
- [ ] Run the same tests, security checks, and release validation for internal packages.
- [ ] Record the upstream tag used for every internal ZIP.

### Completion criteria

An internal ZIP can be reproduced from a documented public tag plus a small, auditable private customization layer, without creating a divergent public code line.

## Proposed release sequence

- **1.1.0:** generic reader, synthetic datasets, field aliases, manual mapping, integration tests, click-to-plot, CSV export, and active-layer report.
- **1.2.0:** plot appearance, product-specific styles, presets, export refinement, reference outputs, and screenshot refresh.
- **1.3.0:** broader interface and user-experience revision.
- **Private downstream build:** derived from a mature public tag when internal distribution is required.

## Immediate next step

Start Block 2 by writing the visual specification for report-ready default plots. The specification should define required figure elements, product-specific style conventions, preset names, export dimensions, and acceptance criteria before changing plotting code.
