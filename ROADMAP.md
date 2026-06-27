# Development Roadmap

This roadmap records the major development blocks planned after the first stable public release. It is intentionally organized around large outcomes rather than individual implementation tasks.

The roadmap is directional. Scope and version numbers may change as testing exposes new requirements.

## Guiding principles

- The reader must depend on the structure of the data, not on the identity of the data provider.
- Point-based InSAR time series should remain readable even when optional metadata is absent.
- Synthetic, redistributable datasets must provide an auditable reference for development and external contributions.
- Generic improvements belong in the public repository.
- Organization-specific branding, defaults, or workflows belong in a private downstream distribution.

## Block 1 — Generic reader and synthetic reference datasets

**Target:** 1.1.0

**Status:** Planned

**Goal:** Read point-based InSAR time series without requiring prior knowledge of the company or processing chain that produced the layer.

### Major deliverables

- [ ] Define the minimum valid input structure:
  - point geometry;
  - at least two valid temporal fields;
  - temporal values that can be interpreted as numeric displacement observations.
- [ ] Make identifier, velocity, velocity uncertainty, component, orbit, unit, and missing-value sentinels optional or configurable.
- [ ] Keep `DYYYYMMDD` as the initial temporal-field convention while designing the reader so other date mappings can be added later.
- [ ] Add automatic alias detection for common identifier, velocity, uncertainty, component, and orbit field names.
- [ ] Add manual field mapping when automatic detection is incomplete or ambiguous.
- [ ] Store layer-specific mappings in the QGIS project.
- [ ] Distinguish values supplied by the source layer from values calculated by the plugin.
- [ ] Create four deterministic synthetic point datasets:
  - LOS ascending;
  - LOS descending;
  - vertical;
  - east-west.
- [ ] Use different attribute layouts across the four datasets to exercise generic field detection.
- [ ] Include stable areas, subsidence, uplift, eastward and westward motion, seasonal behavior, jumps, controlled noise, missing values, nulls, and outliers.
- [ ] Generate LOS datasets mathematically from documented synthetic vertical and east-west components.
- [ ] Add a deterministic generator script with a fixed random seed.
- [ ] Add a machine-readable manifest describing CRS, fields, dates, units, sentinels, formulas, and expected behavior.
- [ ] Add expected values for selected reference points.
- [ ] Add unit and PyQGIS integration tests for schema detection, reading, missing values, manual mapping, and known synthetic results.
- [ ] Document the synthetic datasets for users and external contributors.

### Completion criteria

A point layer with valid temporal observations can generate a time series even when provider-specific metadata is missing. The four synthetic datasets can be regenerated, inspected, and used to verify known results.

## Block 2 — Plot appearance and exported products

**Target:** 1.2.0

**Status:** Planned

**Goal:** Produce clear, consistent figures that can be used directly in technical reports.

### Major deliverables

- [ ] Refine title, subtitle, and information hierarchy.
- [ ] Improve presentation of identifier, component, orbit, velocity, uncertainty, cumulative displacement, and observation period.
- [ ] Define coherent default styles for LOS, vertical, and east-west products.
- [ ] Improve legends, axes, date ticks, gridlines, annotations, and shaded periods.
- [ ] Refine trendline presentation and labeling.
- [ ] Add reusable plot presets.
- [ ] Improve watermark behavior and positioning.
- [ ] Ensure preview and exported output remain visually consistent.
- [ ] Standardize PNG, SVG, and PDF export behavior.
- [ ] Compare outputs against the project reference figures.

### Completion criteria

A default exported graph is suitable for direct inclusion in a technical report without mandatory editing in another application.

## Block 3 — User interface and user experience

**Target:** 1.3.0

**Status:** Planned

**Goal:** Make the complete workflow understandable, efficient, and resistant to configuration errors.

### Major deliverables

- [ ] Reorganize the dock to reduce simultaneous visual complexity.
- [ ] Separate basic and advanced controls.
- [ ] Establish a clear workflow:
  1. select layer;
  2. validate or map fields;
  3. select points or area;
  4. generate graph;
  5. export.
- [ ] Add a field-mapping interface for unrecognized or ambiguous layers.
- [ ] Add a layer diagnostic summary showing acquisitions, date range, detected fields, missing observations, inferred component, orbit, and confidence.
- [ ] Improve validation messages, warnings, and error recovery.
- [ ] Persist relevant settings per layer and QGIS project.
- [ ] Review enabled and disabled states for all controls.
- [ ] Add concise tooltips and contextual help.
- [ ] Review Brazilian Portuguese and English interface text.
- [ ] Validate behavior on supported Windows and Linux QGIS environments.
- [ ] Update screenshots, quick-start instructions, and user documentation.

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

- **1.1.0:** generic reader, synthetic datasets, field aliases, manual mapping, and integration tests.
- **1.2.0:** plot appearance, presets, and export refinement.
- **1.3.0:** broader interface and user-experience revision.
- **Private downstream build:** derived from a mature public tag when internal distribution is required.

## Immediate next step

Start Block 1 by writing the formal specification for the four synthetic datasets before modifying the reader. The specification will define the geometry, dates, fields, displacement models, missing-data cases, expected reference values, and regeneration requirements.
