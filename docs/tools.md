# Tools and Compatibility

`origin-mcp` exposes MCP tools for Origin project management, worksheet editing,
plotting, graph formatting, analysis, export, and lifecycle control.

Tool failures return `ok=false`, a human-readable `message`, the Python
`error_type`, and a stable `error_code` such as `worksheet_not_found`,
`graph_not_found`, `file_not_found`, `path_not_allowed`,
`unsupported_origin_feature`, `unsupported_analysis_type`, or
`origin_dependency_unavailable`. Clients should branch on `error_code` instead
of parsing the message text.

## Core Tools

- `origin_ping`
- `origin_capabilities`
- `origin_get_default_plot_config`
- `origin_plot_type_coverage`
- `origin_new_project`
- `origin_open_project`
- `origin_save_project`
- `origin_list_project`
- `origin_rename_object`
- `origin_delete_object`

## Worksheet Tools

- `origin_import_csv`
- `origin_import_table`
- `origin_import_excel`
- `origin_import_file`
- `origin_append_table`
- `origin_get_worksheet_info`
- `origin_read_worksheet`
- `origin_write_worksheet`
- `origin_add_calculated_column`
- `origin_sort_worksheet`
- `origin_get_cell_value`
- `origin_set_cell_value`
- `origin_delete_columns`
- `origin_clear_worksheet`
- `origin_export_worksheet_csv`
- `origin_set_column_labels`
- `origin_set_column_designations`

## Plotting Tools

Common plot wrappers:

- `origin_plot_line`
- `origin_plot_scatter`
- `origin_plot_line_symbol`
- `origin_plot_errorbar`
- `origin_plot_column`
- `origin_plot_contour`
- `origin_plot_histogram`
- `origin_plot_box`
- `origin_plot_heatmap`
- `origin_plot_3d_scatter`
- `origin_plot_3d_surface`
- `origin_plot_polar`

Common plot wrappers accept `style_mode`. The default is `origin_default`, which
lets Origin resolve the graph template from the user's Origin/system template
folders and avoids origin-mcp style overrides. `publication` applies the compact
origin-mcp publication style after Origin creates the graph. `nature` applies a
Nature-style scientific figure preset with small typography, thin lines, short
ticks, compact symbols, a colorblind-safe palette, and a frameless legend while
preserving the resolved Origin template page size. The Nature preset also applies
conservative chart-specific tweaks for line, scatter, bar/column, heatmap,
surface/3D, polar, and box-style plots, then returns an automatic diagnostic
summary. `origin_apply_nature_style` accepts `palette_role` as a semantic color
sequence such as `hero,baseline,positive,negative`; supported roles are `hero`,
`baseline`, `positive`, `negative`, `neutral`, `accent`, `secondary`, and
`warning`. `template`, `theme`, and `none` are accepted aliases for preserving
Origin defaults; pass `template` when you want a specific custom template.

`origin_recommend_chart` and `origin_plot_auto` inspect the table before choosing
a graph route. The recommender profiles column types, date/time columns,
categorical groups, error/interval columns, OHLC financial columns, ternary
composition triplets, source/target network-like columns, and XYZ grid structure.
It returns ranked candidates with a rationale before plotting.

`origin_chart_atlas_route` and `origin_plot_chart_atlas` choose an expression
from a semantic intent before plotting. Supported intents include `correlation`
(scatter plus linear-fit summary), `effect_size` (interval/error-bar estimate),
`composition` (stacked/grouped bar), `matrix` (heatmap route), `image_plate`
(image/heatmap panel route), `time_series` (line), and `distribution` (box).
Chart atlas plotting also defaults to `origin_default`; pass `style_mode="nature"`
explicitly to apply Nature styling.

Origin Plot Type ID wrappers:

- `origin_plot_table_id`
- `origin_plot_matrix_id`
- `origin_plot_area`
- `origin_plot_stack_area`
- `origin_plot_fill_area`
- `origin_plot_bar`
- `origin_plot_stack_bar`
- `origin_plot_floating_bar`
- `origin_plot_column_stack`
- `origin_plot_pie`
- `origin_plot_ternary`
- `origin_plot_ternary_contour`
- `origin_plot_bubble`
- `origin_plot_bubble_color_mapped`
- `origin_plot_color_mapped`
- `origin_plot_vector_xyam`
- `origin_plot_vector_xyxy`
- `origin_plot_3d_vector`
- `origin_plot_high_low_close`
- `origin_plot_candlestick`
- `origin_plot_waterfall`
- `origin_plot_3d_ribbon`
- `origin_plot_3d_bars`
- `origin_plot_3d_errorbar`
- `origin_plot_polar_xr_ytheta`
- `origin_plot_smith`
- `origin_plot_dendrogram`
- `origin_plot_matrix_3d_scatter`
- `origin_plot_matrix_3d_surface`
- `origin_plot_matrix_heatmap`
- `origin_plot_matrix_contour`
- `origin_plot_image`

Template/range plotting:

- `origin_plot_from_range`
- `origin_batch_plot_from_template`
- `origin_list_graph_templates`

## Graph Editing Tools

- `origin_get_graph_info`
- `origin_get_layer_info`
- `origin_format_graph`
- `origin_set_axis`
- `origin_set_plot_style`
- `origin_apply_publication_style`
- `origin_apply_nature_style`
- `origin_diagnose_graph`
- `origin_recommend_chart`
- `origin_plot_auto`
- `origin_chart_atlas_route`
- `origin_plot_chart_atlas`
- `origin_apply_image_panel_style`
- `origin_add_plot_to_graph`
- `origin_remove_plot_from_graph`
- `origin_change_plot_type`
- `origin_change_plot_data`
- `origin_set_graph_page`
- `origin_arrange_layers`
- `origin_add_graph_label`
- `origin_add_reference_line`
- `origin_format_legend`

`origin_format_legend` formats legend text, font, and frame without moving the
legend by default. Pass `position` explicitly, such as
`position="inside_upper_left"`, to place the legend inside the active layer.
When `left` and `top` are provided together, values in the 0-100 range are
interpreted as layer percentages; use `coordinate_mode="page_pixel"` only when
raw Origin page-pixel coordinates are intended.

Text shown on graphs is normalized for Origin rich text automatically. Axis
titles, graph labels, reference-line labels, and column label rows
convert common notation such as `CO_2`, `x_{max}`, `m^2`, `E^{1/2}`, `H₂O`,
`m⁻²`, `<sub>2</sub>`, and `<sup>-1</sup>` to Origin escape sequences for
subscript and superscript rendering. Single-letter suffixes such as `signal_a`
also render as subscripts, while multi-letter identifiers such as `sample_id`
are left unchanged unless braces are used.

Plot `title` parameters are stored as graph page long names instead of visible
labels inside the exported image.

`origin_apply_image_panel_style` adds heatmap/image-plate metadata such as panel
labels, channel labels, scale bar labels, dynamic-range labels, and an optional
dark panel background. `origin_diagnose_graph` returns a QA checklist covering
layers, plots, axis titles, palette conformance, transparency, optional legend,
panel-label, scale-bar, channel-label, dynamic-range checks, and optional export
quality/dimension checks when `export_path` is provided.

## Analysis Tools

- `origin_run_analysis`
- `origin_linear_fit`
- `origin_polynomial_fit`
- `origin_nonlinear_fit`
- `origin_nonlinear_fit_structured`
- `origin_list_fit_functions`
- `origin_smooth`
- `origin_differentiate`
- `origin_integrate`
- `origin_peak_find`
- `origin_descriptive_stats`

Analysis tools accept `include_output=true` and `output_max_rows` when an
`output_sheet` is supplied. When enabled, the MCP response attempts to read the
output worksheet back as structured JSON rows. Generic analysis responses also
include stable machine-readable fields:

- `analysis`: resolved analysis adapter name
- `parameters`: extracted fit parameters or coefficients when recognized
- `metrics`: common fit/statistical metrics when recognized
- `sections`: reserved for summary/statistics sections
- `warnings`: non-fatal execution or output-read warnings

```json
{
  "output_sheet": "SmoothOut",
  "include_output": true,
  "output_max_rows": 50
}
```

`origin_polynomial_fit` can extract coefficient-like rows and common metrics
such as `RSquare` from the output worksheet when `output_sheet` and
`include_output=true` are supplied.

`origin_linear_fit` returns a normalized `result` object when it can use
`originpro.LinearFit`. The normalized result includes:

- `parameters`: extracted fit parameters such as slope, intercept, coefficients,
  or named nonlinear parameters when present
- `metrics`: common fit metrics such as `RSquare`
- `sections`: summary/statistics/ANOVA-like sections when they are present in the
  Origin result tree

For analysis tools that create output worksheets, prefer setting `output_sheet`
and `include_output=true` so the AI client can inspect the produced table without
issuing a separate worksheet read.

## Export and Lifecycle Tools

- `origin_export_graph`
- `origin_export_all_graphs`
- `origin_export_preview`
- `origin_inspect_export`
- `origin_run_labtalk`
- `origin_quit`
- `origin_detach`
- `origin_release`
- `origin_force_quit`

When a plotting tool receives `export_path`, it returns `export_inspection`
alongside the graph reference. `origin_export_graph`, `origin_export_preview`,
and `origin_inspect_export` also return the same diagnostics. PNG exports are
decoded when possible to report hash, dimensions, sampled pixel complexity,
near-blank detection, and content bounds. Plot creation without `export_path`
does not run image decoding.

## Plot Type Coverage

Origin has 100+ built-in graph types through system templates. The documented
Origin Plot Type ID table is covered by direct MCP tools in this project. Other
menu-only or custom template graph types remain reachable through
`origin_plot_from_range`, `origin_plot_table_id`, or `origin_plot_matrix_id` when
the data layout matches the template.

Use `origin_plot_type_coverage` after connecting to Origin to inspect:

- detected Origin version
- Origin/originpro runtime profile
- documented Plot Type ID entries
- the MCP tool mapped to each documented plot type

Coverage categories:

- `direct_tool`: a named MCP tool exists
- `generic_template`: reachable through template or Plot Type ID helpers
- `not_wrapped`: still missing a wrapper

The current catalog reports the documented Plot Type ID table as direct-tool
covered.

## Version Compatibility

Use `origin_capabilities` after configuring the MCP server. It reports:

- Origin version from LabTalk `@V`
- installed `originpro` and `OriginExt` package versions
- Python runtime profile and recommended Origin automation backend
- important API availability, including project listing, batch export,
  Data Connector import, and structured fitting APIs
- plot type coverage

The code prefers official `originpro` APIs and falls back to LabTalk commands
where reasonable. Advanced analysis X-Functions can differ by Origin version; in
those cases tools return structured errors instead of silently doing the wrong
thing.

Python runtime handling:

- Python 3.10-3.12: preferred external `OriginExt/originpro` automation range.
- Python 3.13: treated as experimental; prefer a 3.10-3.12 MCP server.
- Python 3.14+: treated as unsupported for direct external Origin automation in
  this project; route work through a compatible MCP server or Origin-embedded
  Python path.
