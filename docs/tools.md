# Tools and Compatibility

`origin-mcp` exposes MCP tools for Origin project management, worksheet editing,
plotting, graph formatting, analysis, export, and lifecycle control. By default
it uses a compact tool profile to reduce model tool-selection cost.

Tool failures return `ok=false`, a human-readable `message`, the Python
`error_type`, and a stable `error_code` such as `worksheet_not_found`,
`graph_not_found`, `file_not_found`, `path_not_allowed`,
`unsupported_origin_feature`, `unsupported_analysis_type`, or
`origin_dependency_unavailable`. They also include a `recoverable` boolean and
an ordered `next_actions` list with concrete recovery steps. Clients should
branch on `error_code`, present or execute safe `next_actions`, and retry only
when `recoverable=true` and the failed operation is safe to repeat. Successful
responses omit both recovery fields.

```json
{
  "ok": false,
  "message": "Worksheet not found: [Book1]Data",
  "error_code": "worksheet_not_found",
  "recoverable": true,
  "next_actions": [
    "Inspect the current Origin project objects and correct the referenced name or ID.",
    "Create or import the missing object before retrying the operation."
  ],
  "data": {
    "error_type": "OriginOperationError",
    "error_code": "worksheet_not_found"
  }
}
```

## Tool Profiles

The default profile is `compact`, which registers 25 high-level tools (listed
in `COMPACT_TOOL_NAMES` and reported by `origin_doctor`). It keeps the common
workflow surface small while preserving specialized wrappers as internal
Python functions.

Set `ORIGIN_MCP_TOOL_PROFILE` before starting the MCP server to select a larger
surface: `data` adds worksheet transforms; `plot` adds specialized plot, graph,
template, and multi-panel composition tools; `analysis` adds typed fitting,
result inspection/recalculation, and advanced-statistics tools; and `standard`
restores the previous curated surface. `full` exposes every wrapper; `expert`
and `all` are aliases for it. Unknown values safely fall back to `compact`.

## Default Compact Tools

The exact compact tool list is owned by `COMPACT_TOOL_NAMES` in
`src/origin_mcp/tools/_shared.py` and is reported by `origin_doctor`. The
searchable tool catalog is generated from tool module docstrings and is
available through the `mcp_tools` knowledge collection.

In compact mode, use `origin_query_knowledge` or `origin_browse_knowledge` to
discover the right high-level workflow instead of choosing from every
specialized wrapper.

Named plotting calls are idempotent by default where Origin exposes an output
graph layer target. When a table plotting tool is called with `graph_name`,
origin-mcp first looks for that graph page, clears its existing plots, and draws
the new result into the same page instead of creating `Graph2`, `Graph3`, and so
on. If no `book_name` is supplied, the imported data is stored in a stable
workbook named from `graph_name` plus `_Data`; repeated calls overwrite that
worksheet. Calls without explicit names still create fresh Origin objects. A few
worksheet-command Plot Type ID routes that do not expose an output graph target
still use Origin's native creation route and do not clear an existing graph.

### Parameterized plotting with `origin_plot`

`origin_plot(path, kind, ...)` is a single compact-profile entry point for the
table plot kinds that each also have a dedicated `origin_plot_*` wrapper in the
full profile. It lets compact-mode clients reach every one of these kinds
without enabling `ORIGIN_MCP_TOOL_PROFILE=full`. `kind` must be one of:
`area`, `stack_area`, `fill_area`, `bar`, `stack_bar`, `floating_bar`,
`column_stack`, `pie`, `ternary`, `ternary_contour`, `bubble`,
`bubble_color_mapped`, `color_mapped`, `vector_xyam`, `vector_xyxy`,
`vector_3d`, `high_low_close`, `candlestick`, `waterfall`, `ribbon_3d`,
`bars_3d`, `errorbar_3d`, `polar_xr_ytheta`, `smith`, or `dendrogram`, plus the
common `line`, `scatter`, `line_symbol`, `column`, `histogram`, and `box` kinds.
For common XY plots, the first selected column is X and the remainder are Y; a
single selected column is treated as Y-only. An unknown `kind` returns
`ok=false` with `error_code=invalid_request` and lists the valid kinds. For
matrix-range plots use `origin_plot_matrix_id` from the `plot`/`full` profile.
The entry point accepts the shared `selected_cols`, `graph_name`, `title`,
`export_path`, and `style_mode` arguments and follows the same idempotent
`graph_name` behavior described above.

```json
{"path": "data/processed/sales.csv", "kind": "bar", "graph_name": "Sales"}
```

### Visual verification with `origin_view_graph`

`origin_view_graph(graph_name=None, max_width=1600)` renders a graph and returns
it as an image content block the model can actually see, so a vision-capable
client can visually verify a plot and iterate on it. Unlike
`origin_export_graph` and `origin_export_preview`, it leaves no file behind: the
graph is rendered to a temporary PNG, returned inline alongside a short text
summary (graph name, pixel dimensions, byte size), and the temp file is deleted.
`max_width` bounds the rendered pixel width to keep the image — and its token
cost — small. Pass a `graph_name` to target a specific page, or omit it to
render the active graph. Use `origin_export_graph` instead when you need a
persistent file on disk.

## User Template Library

`origin-mcp` can save a finished graph as a reusable Origin template and find a
matching one before plotting, so a user's preferred styling is captured once and
reapplied to same-type figures.

Templates live in a per-user library, by default `~/.origin-mcp/templates`
(override with `ORIGIN_MCP_TEMPLATE_DIR`). Each saved template is stored as three
files plus a shared index: `<slug>.otpu` (the Origin graph template),
`<slug>.json` (searchable metadata), and `<slug>.png` (a preview thumbnail),
aggregated into `index.json`.

The save tool stores the active or named graph and accepts optional `plot_types`
(e.g. `["scatter"]`), `roles` (e.g. `["x", "y"]`), `tags`, `description`, and
`n_columns` that make the template easier to match later; the layer and plot
counts are captured automatically. The search tool ranks the library against an
intended plot and returns each candidate with a `score` and human-readable
`match_reasons`. Ranking weights an exact plot-type match highest, then a same
plot-type family (e.g. a `line_symbol` template for a `scatter` request), close
column counts, matching tags, and keyword overlap with the name, description, and
tags, returning an empty list when nothing matches. A list tool reports every
saved template most recent first, a delete tool removes a template's files and
index entry, a rename tool moves a template to a new name (its `.otpu`/`.json`/
`.png` files and index entry) without redrawing, and a metadata-update tool edits
a template's description, tags, and matching hints in place without touching the
`.otpu` or needing a live graph. These management tools report `not_found` when
no template carries the given name.

Once saved, reuse a template by passing its name to any plotting tool's
`template` argument (for example a table plot tool's `template` or a FigureSpec
`style.template`). A bare name is resolved against the library first, then falls
back to Origin's built-in templates and explicit file paths.

Searching, listing, and deleting operate purely on the local library files and
do not require Origin to be running; only saving a template drives Origin. The
template management tools live in the `plot`, `standard`, and `full` profiles.
Their exact names are available in the generated `mcp_tools` knowledge
collection; discover them with `origin_query_knowledge`.

## FigureSpec Tools

`origin-mcp` includes a first-pass declarative FigureSpec workflow for
agent-friendly plotting plans. A FigureSpec describes the desired figure in
terms of data, page, layer, plot, annotation, style, export, and QA sections.
The MCP server then validates the structure and translates the supported subset
into existing Origin plotting and formatting calls.

Use `origin_plan_figure_spec(spec)` to validate a JSON FigureSpec and return
the planned Origin operations without touching Origin. Planning reads the data
file headers and verifies that mapped columns and column indexes exist before
any Origin calls are made. Use `origin_execute_figure_spec(spec, dry_run=false)`
to execute the current supported subset: worksheet-backed single-panel, grid,
custom grid/span, inset, and dual-Y figures; common plot types; X/Y/Z axis
settings and one X/Y break per axis; panel/legend/reference annotations;
exports, OPJU save, and graph diagnostics. Dual-Y specs use Origin's `doubleY`
template and require two layers, one shared data source and X mapping, and one
common line/scatter plot type without uncertainty mappings.
Unsupported features are reported in the plan instead of being guessed.

Minimal JSON shape:

```json
{
  "figure": {"id": "line_demo", "title": "Line Demo"},
  "data": [
    {
      "id": "ds_line",
      "source": "data/processed/line.csv",
      "object": "worksheet",
      "roles": {"x": "time", "y": "response"}
    }
  ],
  "page": {"layout": "grid"},
  "layers": [
    {
      "id": "panel_a",
      "data_ref": "ds_line",
      "grid_cell": [0, 0],
      "x": {"title": "Time (s)", "limits": "auto"},
      "y": {"title": "Response", "limits": "auto"},
      "panel_tag": "(a)"
    }
  ],
  "plots": [
    {
      "id": "plot_a",
      "layer": "panel_a",
      "type": "line",
      "map": {"x": "time", "y": "response"}
    }
  ],
  "style": {"theme": "nature", "palette_name": "nature"},
  "export": {
    "dir_figures": "output/figures",
    "dir_opju": "output/opju",
    "png": {"enabled": true},
    "pdf": {"enabled": true},
    "qa": {"require_opju": true, "require_axis_titles": true}
  }
}
```

For custom panel layouts, set `page.layout` to `custom`. Grid-style custom
layouts use `page.size_mm`, optional `page.margins_mm`, optional
`page.panel_spacing_mm`, and per-layer `grid_cell` / `grid_span`; the executor
converts those values into Origin page size plus per-layer geometry. Absolute
custom layouts use `position_mode="absolute"` plus `position.left`,
`position.top`, `position.width`, and `position.height` as page percentages.
For an inset, use `page.layout="inset"`; absolute positions are honored, while
unspecified positions get a deterministic upper-right inset. Use
`page.layout="dual_y"` with the first layer as the left axis and the second as
the right axis.

For Nature-style graph formatting, `origin_palette_catalog()` lists the built-in
palette registry, including semantic roles, source links, color counts, and
license notes. Each entry also includes `accessibility`: white-page contrast,
OKLab perceptual separation, and minimum separation under protanopia,
deuteranopia, and tritanopia simulations. `screening_status="pass"` means the
palette clears the automated preflight thresholds; `review` includes specific
warnings. This is a screening aid rather than a guarantee, so multi-series
figures should still combine color with markers, line styles, or direct labels.
By default the catalog returns a lightweight summary and omits full HEX color
arrays; pass `include_colors=true` when exact colors are needed.

Nature styling also applies non-color distinctions by default when a layer has
multiple series: line charts cycle line styles, scatter charts cycle marker
shapes, and line-symbol or polar charts use both. The response and diagnostics
include `series_distinction` with the exact per-plot assignments and warn when
the available patterns must repeat. Pass `differentiate_series=false` to
`origin_apply_nature_style` when an existing template already owns these
encodings.
`origin_apply_nature_style`, `origin_diagnose_graph`, `origin_plot_auto`,
`origin_plot_chart_atlas`, and FigureSpec `style.palette_name` can select a
palette such as `nature`, `lcpmgh_auto`, or a local `lcpmgh_006_001` style
palette. The default remains `nature`, now backed by the local lcpmgh/colors
Nature-style editorial palette. Use
`origin_palette_catalog(colors_count=6, family="lcpmgh/colors",
include_colors=true)` to list 6-color lcpmgh palettes, or
`origin_palette_catalog(min_colors=2, max_colors=16, family="lcpmgh/colors")`
to browse the local 2-16 color snapshot without returning every HEX value. Set
`ORIGIN_MCP_NATURE_PALETTE` or `ORIGIN_MCP_PALETTE` to change the process-wide
default.

Nature-style typography uses 20 pt as the minimum visual size across every
output profile: legends, axis titles, tick labels, and general graph/image
annotations are all at least 20 pt. FigureSpec annotations use the same 20 pt default unless
`style.annotation_font_size` or an individual annotation `style.font_size`
overrides it.

Nature styling resolves mark transparency before applying the preset. Dense
scatter and line-symbol plots retain their data-driven transparency, while
other Nature plots default to opaque marks. An explicit `transparency` passed
to `origin_apply_nature_style` takes precedence, and graph diagnostics compare
against the resolved value instead of assuming that every plot must be opaque.

`origin_apply_nature_style(output_profile=...)` also provides output-aware
geometry presets. `screen` preserves the existing 20/18 pt interactive style;
`journal_single_column` targets compact figures near 89 mm wide and
`journal_double_column` targets figures near 183 mm wide, while retaining the
project-wide 20 pt minimum and a 3 pt line width. `presentation` uses 24 pt axis
titles, 20 pt supporting text, and 3.5 pt lines for projected slides. Explicit
font sizes, line width, symbol size, and tick length override the selected profile.
Nature-style line and scatter markers use a 10 pt default, and automatically
generated numeric value labels use the same 20 pt minimum as other annotations.
Nature-style diagnostics verify the resolved symbol size and transparency
against the values Origin reports after applying the style, so a silently
ignored Origin property assignment is surfaced as a warning.

Table plotting also applies readability defaults when the caller does not
provide an explicit override. Machine-oriented headers such as
`measured_response`, `duration_s`, and `dose_uM` are written to worksheet Long
Name labels as `Measured response`, `Duration (s)`, and `Dose (µM)`. Common unit
symbols use Origin Unicode escape notation so they survive export. A shared
conservative rule resolver profiles chart family, series count, row count,
category-label length, and numeric range. It hides redundant single-series
legends, retains multi-series legends, moves line/scatter legends to the quieter
upper corner, rotates crowded category ticks, selects scientific notation only
for extreme magnitudes, keeps nonnegative bar-like charts on a zero baseline,
and reduces marker size while increasing transparency for dense scatter plots.
Continuous Cartesian axes request roughly five to seven major ticks according
to label width and chart footprint, with a single minor subdivision. Datetime
axes preserve Origin's date labels and use six temporal anchors; categorical
axes preserve their category positions. Dual-Y plots format the two numeric
scales independently, then use the smaller shared target tick count so the left
and right major ticks stay visually aligned. A light horizontal major grid aids
value comparison on line, scatter, bar, box, and generic Cartesian plots;
vertical and minor grids remain hidden, and specialized heatmap, surface, and
polar axes retain their own scale behavior. Standard Cartesian plots keep the
top frame line but suppress duplicate top-axis major and minor ticks. Long
numeric tick labels reserve additional left or right page margin automatically.
Plots with long categorical X labels remain vertically oriented; their page
height and bottom margin grow automatically so rotated labels are not clipped.
The height is set from a target page aspect ratio, so repeated formatting does
not keep increasing the page size.
Axis titles are inferred from field semantics instead of concatenating every
series name. Fields such as `temperature_C`, `temperature_mean_C`, and
`temperature_std_C` produce the shared axis title `Temperature (°C)`, while
`Mean` and `SD` remain available as legend labels. Wide fields such as
`glucose_control_mg_dL` and `glucose_treated_mg_dL` produce
`Glucose (mg/dL)` with compact `Control` and `Treated` legend entries. Tidy
`value`/`unit` data can also use a constant `metric`, `measure`, `measurement`,
`variable`, or `parameter` column to recover the metric name and unit.

Dual-Y plots infer the left and right titles independently from the columns
assigned to each axis. Explicit `x_label`, `y_label`, `y1_label`, and `y2_label`
values always take precedence. For line and scatter charts, legend placement
first estimates the legend footprint and checks all four inside corners against
the plotted data. Each Y-axis group is normalized independently so dual-axis
units do not distort the occupancy test. The quietest data-free corner is used
when it fits. Only when every candidate intersects data, or the legend footprint
is too large, does it move to a reserved column outside the plot; the page then
widens and the right margin grows so the legend does not cover data or clip
during export.
Each graph response includes `visual_defaults` with the selected values and the
reason for every choice. Explicit `show_legend` and `palette_name` arguments
take precedence.

When `style_mode="nature"` and no palette is specified, table plotting uses
`lcpmgh_auto` to choose an installed lcpmgh/colors palette whose color count
matches the number of plotted series. Exact-count candidates that pass the
accessibility preflight are preferred, then ranked by minimum and average OKLab
separation, simulated color-vision separation, white-page contrast, and hue
coverage. The selection notice exposes the same metrics. Dedicated table
plotting tools and the parameterized `origin_plot` entry point accept
`palette_name`; an explicit registered palette name always overrides automatic
selection. Origin or custom template palettes remain untouched in
`origin_default` mode.

Distribution and field-color tools use safer visual defaults: histograms choose
a bounded Freedman-Diaconis bin width unless `bin_width` or a custom template is
provided, and histogram/box/heatmap legends are hidden by default. Heatmaps use
the perceptually uniform `viridis` colormap unless `colormap` or a custom
template is supplied. Explicit arguments and FigureSpec plot styles always take
precedence over these defaults.

For existing plots, `origin_set_plot_style` controls color, line width/style,
symbols, transparency, column/bar width, colormaps, contour levels and color
scale limits, histogram bin width, error-bar cap width, and box-chart width on
a zero-based `layer_index`.
Pass `bar_gap` to set Origin's `-vg` gap value; larger `bar_gap` values make
columns or bars narrower. FigureSpec plot `style` entries can use the same
fields for supported plot primitives.

FigureSpec plot `group_style` can apply safe per-series style sequences for
multi-Y plots: `colors`, `line_widths`, `bar_gaps`, `line_styles`,
`symbol_kinds`, `symbol_sizes`, `transparencies`, `colormaps`, contour/color
scale sequences, and histogram/error-bar/box width sequences, or a `series` list of
per-series style objects. FigureSpec `uncertainty` supports error-bar mappings
that route to the existing safe plotting path, for example
`{"type": "errorbar", "y_error": "se"}` or `{"x_error": "xerr"}`. It also
supports worksheet-backed filled bands with lower/upper bound columns, for
example `{"type": "band", "lower": "lo", "upper": "hi", "transparency": 65}`.
Band support is intentionally narrow but covers multiple plot entries: each
banded plot must have one named y column plus named x/lower/upper columns. The
executor creates native Origin fill-area plots from contiguous x/lower/upper
columns, overlays the main line, and trims generated legend text to the main
series rather than the auxiliary band bounds.

For natural-language or registry-backed edits, `origin_set_plot_property`
resolves a semantic `property_name` such as `柱宽`, `折线粗细`, `点大小`, or
`误差棒帽宽` against the plot style capability registry. It only applies
properties that are marked `implemented` and map to a known safe route such as
`origin_set_plot_style`, `origin_apply_nature_style`, or
`origin_apply_image_panel_style`. Known-but-planned properties return
`applied=false` with the matching capability and safe alternatives instead of
guessing an Origin/LabTalk route.

Use `origin_plot_style_setter_coverage(chart_type, plot_type_id)` to audit
whether registry entries marked `implemented` are executable through safe MCP
routes. This is useful after adding a new style capability file or changing
capability status.

Use `origin_plot_style_capabilities(chart_type, plot_type_id, query)` before
changing an unfamiliar chart type. It is backed by the same registry as the
knowledge base: `core.json` holds the small common capability set, while
chart-specific JSON extensions such as `column_bar.json`, `field_color.json`,
`distribution.json`, `errorbar.json`, `image.json`, `three_d.json`,
`area_pie.json`, `financial.json`, and `specialized.json` are loaded only when
the requested chart type, Plot Type ID, or query needs them. Every Plot Type ID
in `PLOT_TYPE_CATALOG` has a style profile that maps it to one of these chart
style families. The registry maps user-facing terms such as `柱宽`, `折线粗细`,
`点大小`, `色带`, and `误差棒帽宽` to MCP setter parameters, Origin/LabTalk
routes, readable fields, and implementation status. Properties marked
`implemented` have stable MCP entry points; properties marked `planned` are
intentionally documented so the assistant can report that a semantic setter is
not yet available instead of guessing a LabTalk flag.

## Extended Origin Workflows

The `standard` and `full` profiles expose the broader workflows added from the
official originpro and X-Function surfaces:

- Data Connectors can be created from local or remote sources, inspected,
  updated, refreshed by sheet or project, expanded to another selection, and
  disconnected while keeping imported data. `keep_dc=false` removes the
  connector after the initial import.
- Matrix tools create/read/write matrix objects, set XY mapping and view
  controls, and transpose/rotate/flip them. Image tools import or create image
  pages, inspect/read/process them, and convert images to matrices.
- Analysis-template tools save/open OGW/OGWU templates. `origin_batch_process`
  covers file, folder, existing XY/XYZ, worksheet, and range inputs;
  `origin_clone_import` applies an existing connector/import structure to more
  files.
- Peak Analyzer tools expose theme/script/dialog execution, automatic baseline
  generation, and multi-Y batch analysis. The expert analysis surface includes
  typed FFT filtering, PCA, one-way ANOVA, and `origin_run_xfunction`, whose
  allow-listed catalog validates every argument before generating LabTalk.

### Analysis results and recalculation

The `analysis`, `standard`, and `full` profiles expose a complete workflow for
existing Origin analysis operations:

- Result reading through `origin_get_analysis_results` reads the report worksheet and uses Origin's
  official `getresults` X-Function to retrieve its result tree. The response
  provides stable `parameters`, `metrics`, `sections`, `worksheet`, and
  `result_tree` fields.
- Operation inspection through `origin_get_analysis_operation` reads a recalculating operation's settings
  tree through `op_change op:=get`.
- Recalculation through `origin_recalculate_analysis` runs the operation through `op_change op:=run`.
  Pass `settings` to replace the operation tree before recalculation, or omit it
  to use the current settings.

`operation_range` is the Origin range owned by the recalculating operation, for
example `[Book1]Result!col(2)`. Result-tree conversion uses the official
`originpro.utils` tree helpers and cleans up temporary LabTalk trees after each
call.

### Advanced statistics

`origin_multivariate_analysis` provides typed dispatch for K-means clustering,
hierarchical clustering, discriminant analysis, and partial least-squares
regression. `origin_nonparametric_test` covers Friedman, two-sample
Kolmogorov-Smirnov, Kruskal-Wallis, median, Mann-Whitney, paired sign, and
one-sample or paired Wilcoxon tests. `origin_survival_analysis` covers
Kaplan-Meier, Cox proportional-hazards, and censored Weibull workflows.

These tools accept worksheet columns or an explicit Origin range, validate all
method-specific options against an allow-listed X-Function schema, and can send
report output to `output_book`. They are available in the `analysis`,
`standard`, and `full` profiles and require OriginPro where the underlying
X-Function is OriginPro-only.

### Publication multi-panel graphs

The `plot`, `standard`, and `full` profiles expose official graph-composition
routes in addition to the existing FigureSpec and layer-arrangement tools:

- Graph merging through `origin_merge_graphs` combines graph pages into a new multi-panel graph with
  explicit rows, columns, gaps, margins, panel labels, and optional common
  scales. Common X-scale sizing works in Origin 2026; common Y-scale sizing uses
  `resizeheightbyscale` and requires Origin 2026b or newer.
- Layout creation through `origin_create_graph_layout` creates a Layout page containing selected graph
  pages while retaining them as separately editable graphs.
- Layer relationships through `origin_link_graph_layers` link X/Y scales and layer geometry;
  `origin_copy_layer_scale` copies axis-scale settings between layers.
- Layer extraction through `origin_extract_graph_layers` turns selected layers back into separate graph
  pages.

Use `origin_merge_graphs` for a single editable multi-layer figure and
`origin_create_graph_layout` when the final page should assemble independent
graph pages. Layer indexes in MCP calls are zero-based and are translated to
Origin's one-based selectors.

Notes tools create, read, replace/append, load, export as HTML, and delete Notes
windows. Syntax values are text, HTML, Markdown, or Origin rich text, with text
or rendered view modes. Project-folder tools list, activate, create, move, and
rename Project Explorer contents. Notes/folder deletion requires
`confirm=true`; recursive folder deletion is explicit, the root folder is
protected, and names/paths containing script delimiters are rejected.

## Knowledge Base Tools

`origin-mcp` includes a local, structured knowledge base modeled as searchable
and browsable collections. It is intentionally tool-addressable rather than only
README text, so an MCP client can discover the right workflow before calling
Origin.

General entry points are `origin_browse_knowledge` and
`origin_query_knowledge`. In full profile, collection-specific browse/query
helpers are also available, but the general tools are the stable default
surface.

Collections:

- `mcp_tools`: origin-mcp tools grouped by workflow, such as worksheet,
  plotting, graph editing, analysis, export, and lifecycle control. Tool entries
  are generated from `src/origin_mcp/tools/*.py` docstrings so the index tracks
  the current MCP surface.
- `reference`: Origin workflow notes, Plot Type ID entries, style modes,
  graph formatting behavior, chart routing, analysis adapters, and runtime
  compatibility notes.
- `python_api`: OriginPro Python API usage notes used by this project.
- `labtalk`: LabTalk and X-Function routes used by this project, including
  worksheet plotting, `plotxyz`, `plotm`, legend refresh, export fallbacks, and
  analysis X-Functions.
- `official_docs`: versioned official OriginLab documentation boundary map for
  Python, originpro API class pages, LabTalk command/function/object references,
  and X-Function category references.

The local knowledge base is a curated operational index. It does not copy the
entire OriginLab documentation set into this repository; entries that need exact
official syntax include `official_url`, `doc_family`, `doc_kind`, `versions`,
and `verified` metadata fields.

The official documentation boundary map has two layers: a hand-curated seed
index in `src/origin_mcp/knowledge.py` and an optional generated overlay at
`src/origin_mcp/official_docs.generated.json`. Refresh the overlay with:

```powershell
python scripts\update_official_docs_index.py
```

The crawler follows OriginLab documentation links, classifies LabTalk command
pages, X-Function pages, and originpro API class pages into stable browse paths,
then validates duplicate paths and required version metadata before writing the
JSON index.

Origin 2026b is the baseline index. Older supported versions use
`src/origin_mcp/official_docs.version_diffs.json`, which stores only `added`,
`removed`, and `changed` records for each version. At query time, origin-mcp
applies that delta in memory so `version="2024"`, `version="2025"`, and
`version="2026"` do not require duplicate full indexes.

To compare two generated indexes for Origin version drift:

```powershell
python scripts\compare_official_docs_index.py old.json new.json --output diff.json
```

To build a compact version-diff overlay from separately generated version
indexes:

```powershell
python scripts\build_official_docs_version_diffs.py --base origin2026b.json --base-version 2026b --version-index 2026 origin2026.json --version-index 2025 origin2025.json --version-index 2024 origin2024.json --output src\origin_mcp\official_docs.version_diffs.json
```

Browse calls use a path-like topic. Examples:

```json
{"collection": "reference", "topic": "plot-types/200"}
```

```json
{"api": "originpro.find_graph"}
```

Query calls return ranked entries with path, title, summary, keywords, metadata,
and score. Examples:

```json
{"query": "heatmap plot type id", "collection": "reference", "limit": 5}
```

```json
{"query": "legend font position", "limit": 3}
```

```json
{"collection": "official_docs", "topic": "labtalk/commands/display-control", "version": "2026b"}
```

## Single Source of Truth

Avoid maintaining hand-written exhaustive tool lists in docs. Use these
knowledge queries instead:

```json
{"query": "worksheet tools", "collection": "mcp_tools", "limit": 10}
```

```json
{"query": "plotting recommended entry points", "collection": "reference", "limit": 5}
```

```json
{"query": "legend font position", "collection": "reference", "limit": 5}
```

```json
{"query": "analysis adapters include_output metrics", "collection": "reference", "limit": 5}
```

```json
{"query": "runtime compatibility embedded bridge", "collection": "reference", "limit": 5}
```

The implementation remains the source of truth for schemas and callable
functions. The knowledge base is the source of truth for searchable workflow
guidance, Plot Type ID entries, style modes, graph formatting behavior, analysis
adapter notes, runtime compatibility, and curated official documentation links.

See [origin-bridge.md](origin-bridge.md) for bridge startup and real-Origin
validation workflows. Use `origin_doctor` first for bridge issues.
