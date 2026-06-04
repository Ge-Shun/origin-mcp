# Tools and Compatibility

`origin-mcp` exposes MCP tools for Origin project management, worksheet editing,
plotting, graph formatting, analysis, export, and lifecycle control. By default
it uses a compact tool profile to reduce model tool-selection cost.

Tool failures return `ok=false`, a human-readable `message`, the Python
`error_type`, and a stable `error_code` such as `worksheet_not_found`,
`graph_not_found`, `file_not_found`, `path_not_allowed`,
`unsupported_origin_feature`, `unsupported_analysis_type`, or
`origin_dependency_unavailable`. Clients should branch on `error_code` instead
of parsing the message text.

## Tool Profiles

The default profile is `compact`, which registers a small set of high-level
tools (listed in `COMPACT_TOOL_NAMES` and reported by `origin_doctor`). It keeps
the common workflow surface small while preserving the specialized wrappers as
internal Python functions.

Set `ORIGIN_MCP_TOOL_PROFILE=full` before starting the MCP server to expose all
specialized worksheet, plotting, graph editing, analysis, and lifecycle tools.
The aliases `expert` and `all` behave the same as `full`.

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
`bars_3d`, `errorbar_3d`, `polar_xr_ytheta`, `smith`, or `dendrogram`. An
unknown `kind` returns `ok=false` with `error_code=invalid_request` and lists
the valid kinds. For `line`, `scatter`, `column`, `histogram`, and `box` use the
dedicated tools; for matrix-range plots use `origin_plot_matrix_id`. It accepts
the shared `selected_cols`, `graph_name`, `title`, `export_path`, and
`style_mode` arguments and follows the same idempotent `graph_name` behavior
described above.

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
exact tool names live in `COMPACT_TOOL_NAMES` and the generated `mcp_tools`
knowledge collection; discover them with `origin_query_knowledge`.

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
to execute the current supported subset: worksheet-backed single-panel or grid
multi-panel figures, common plot types, axis settings, panel/legend/reference
annotations, exports, OPJU save, and graph diagnostics. Unsupported features are
reported in the plan instead of being guessed.

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

For Nature-style graph formatting, `origin_palette_catalog()` lists the built-in
palette registry, including semantic roles, source links, color counts, and
license notes. By default the catalog returns a lightweight summary and omits
full HEX color arrays; pass `include_colors=true` when exact colors are needed.
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

Nature-style typography uses the legend size as the visual anchor. Defaults are
legend 20 pt, axis titles 20 pt, tick labels 18 pt, and general graph/image
annotations 18 pt. FigureSpec annotations use the same 18 pt default unless
`style.annotation_font_size` or an individual annotation `style.font_size`
overrides it.

For existing plots, `origin_set_plot_style` controls color, line width/style,
symbols, transparency, and column/bar width on a zero-based `layer_index`.
Pass `bar_gap` to set Origin's `-vg` gap value; larger `bar_gap` values make
columns or bars narrower. FigureSpec plot `style` entries can use the same
fields for supported plot primitives.

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

Origin 2026 is the baseline index. Older supported versions use
`src/origin_mcp/official_docs.version_diffs.json`, which stores only `added`,
`removed`, and `changed` records for each version. At query time, origin-mcp
applies that delta in memory so `version="2024"` and `version="2025"` do not
require duplicate full indexes.

To compare two generated indexes for Origin version drift:

```powershell
python scripts\compare_official_docs_index.py old.json new.json --output diff.json
```

To build a compact version-diff overlay from separately generated version
indexes:

```powershell
python scripts\build_official_docs_version_diffs.py --base origin2026.json --version-index 2025 origin2025.json --version-index 2024 origin2024.json --output src\origin_mcp\official_docs.version_diffs.json
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
{"collection": "official_docs", "topic": "labtalk/commands/display-control", "version": "2026"}
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
