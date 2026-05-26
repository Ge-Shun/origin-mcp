# origin-mcp

`origin-mcp` is a local MCP server that lets AI clients control Origin/OriginPro on a
Windows machine through Origin's Python automation interface.

The first version focuses on a practical plotting loop:

- connect to a local Origin/OriginPro instance
- create or save projects
- import CSV, TSV, TXT, DAT, XLS, and XLSX data into worksheets
- import files through Origin's official Data Connector path
- append data into existing worksheets
- read worksheet data back as JSON rows and write structured rows into worksheets
- inspect worksheet metadata and add calculated columns
- create line, scatter, line+symbol, error bar, column, contour, and template plots
- set graph title, axis labels, legends, and templates
- set plot color, line width, symbol style, axis scale, and axis limits
- adjust graph page size, arrange layers, add graph labels, and add reference lines
- run common analysis X-Functions such as fitting, smoothing, integration, and peak finding
- run linear fitting through `originpro.LinearFit` when X/Y columns are provided
- export graphs to image/PDF files
- export preview images with file-size and image-dimension diagnostics
- export all graphs in a project
- run LabTalk commands directly when a higher-level tool is not enough

## Requirements

- Windows
- Origin or OriginPro installed and licensed
- Python 3.10 to 3.12 recommended
- Origin's `originpro` Python package and `pywin32`

Python 3.14 may run the MCP server itself, but Origin's automation packages may not
publish wheels for it yet. If package installation fails, install Python 3.11 or 3.12
and use that interpreter for this server.

## Install

From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[origin]"
```

If `originpro` is already provided by your Origin installation, this also works:

```powershell
python -m pip install -e .
```

## Run

```powershell
origin-mcp
```

The server speaks MCP over stdio. It is normally launched by an MCP client rather than
run by hand.

## MCP Client Configuration

Example configuration:

```json
{
  "mcpServers": {
    "origin": {
      "command": "D:\\origin-mcp\\.venv\\Scripts\\origin-mcp.exe",
      "args": []
    }
  }
}
```

See [docs/mcp-config.md](docs/mcp-config.md) for more examples.

## Available Tools

- `origin_ping`: connect to Origin and report basic status
- `origin_capabilities`: report Origin/originpro versions and feature availability
- `origin_new_project`: create a new project
- `origin_open_project`: open an OPJU/OPJ project
- `origin_save_project`: save the current project
- `origin_import_csv`: import a CSV file into a worksheet
- `origin_import_table`: import CSV, TSV, TXT, DAT, XLS, or XLSX into a worksheet
- `origin_import_excel`: import an Excel sheet into a worksheet
- `origin_import_file`: import through Origin's Data Connector / `WSheet.from_file`
- `origin_append_table`: append table data to an existing worksheet
- `origin_get_worksheet_info`: get row/column counts and worksheet label rows
- `origin_read_worksheet`: read worksheet data as structured JSON rows
- `origin_write_worksheet`: write structured rows to a new or existing worksheet
- `origin_add_calculated_column`: add a column filled by a LabTalk formula
- `origin_sort_worksheet`: sort worksheet rows by a column
- `origin_plot_line`: import table data and create a line plot
- `origin_plot_scatter`: import table data and create a scatter plot
- `origin_plot_line_symbol`: create a line+symbol plot
- `origin_plot_errorbar`: create a line+symbol plot with X/Y error bars
- `origin_plot_column`: create a column/bar-style plot
- `origin_plot_contour`: create a contour plot from XYZ columns
- `origin_plot_from_range`: plot an existing Origin range with any template
- `origin_batch_plot_from_template`: batch plot existing ranges with one template
- `origin_format_graph`: set graph title, axis labels, legend visibility, and rescale
- `origin_set_axis`: set axis scale, limits, tick step, and title
- `origin_set_plot_style`: set color, line width, line style, symbol, and transparency
- `origin_set_graph_page`: set graph page size and page placement properties
- `origin_arrange_layers`: arrange graph layers into a panel layout
- `origin_add_graph_label`: add text labels to a graph layer
- `origin_add_reference_line`: add horizontal or vertical reference lines
- `origin_set_column_labels`: set worksheet Long Name, Units, Comments, or custom labels
- `origin_set_column_designations`: set worksheet plotting designations such as `XYY`
- `origin_format_legend`: set legend text, font size, frame, and position
- `origin_export_graph`: export the active or named graph
- `origin_export_all_graphs`: export every graph in the project
- `origin_export_preview`: export a graph preview and return diagnostics
- `origin_inspect_export`: inspect an exported image/PDF file
- `origin_list_project`: list workbooks, worksheets, graphs, and images
- `origin_rename_object`: rename a graph, workbook, matrix book, or worksheet
- `origin_delete_object`: delete a graph, workbook, matrix book, or worksheet
- `origin_run_analysis`: run a named Origin X-Function analysis
- `origin_linear_fit`, `origin_polynomial_fit`, `origin_nonlinear_fit`
- `origin_smooth`, `origin_differentiate`, `origin_integrate`
- `origin_peak_find`, `origin_descriptive_stats`
- `origin_run_labtalk`: execute LabTalk script text
- `origin_quit`: close Origin
- `origin_detach`: release the automation connection without closing Origin
- `origin_release`: alias for `origin_detach`
- `origin_force_quit`: force OriginExt to close Origin

## Origin Lifecycle

If Origin says it is being controlled by another program, use `origin_detach` first.
This releases the external automation connection and leaves Origin open for manual
use. Use `origin_quit` to close Origin normally. Use `origin_force_quit` only after
confirming there is no unsaved work, because it asks OriginExt to close Origin.

## Example Prompt

> Import `D:\data\experiment.csv`, use column `time` as x, plot columns `force`
> and `displacement` as line curves, then export the graph as
> `D:\data\experiment_plot.png`.

With labels and a title:

```text
Import D:\origin-mcp\examples\sample_data.csv, plot signal_a and signal_b
against time as lines, set the title to "Sample Signals", set the X axis label
to "Time (s)", set the Y axis label to "Signal", and export the graph to
D:\origin-mcp\output\sample_labeled.png.
```

For Excel files, use `origin_import_excel` or pass an `.xlsx` path to
`origin_plot_line` / `origin_plot_scatter`. The `excel_sheet` argument accepts a
zero-based sheet index or a sheet name.

## Worksheet Editing

Use `origin_get_worksheet_info` before editing to inspect row counts, column counts,
Long Name (`L`), Units (`U`), and Comments (`C`) label rows. Use
`origin_read_worksheet` with `start_row` and `max_rows` to keep responses small.
Use `origin_write_worksheet` for structured rows and `origin_add_calculated_column`
for formulas such as `col(B)-col(A)` or `col(A)*1000`.

## Graph Refinement

Use `origin_set_graph_page` for page sizing, `origin_arrange_layers` for panel
layouts, `origin_add_graph_label` for annotations, and `origin_add_reference_line`
for threshold or baseline markers. For lower-level styling that is not yet wrapped,
use `origin_run_labtalk` after selecting the target graph.

## Preview Loop

Use `origin_export_preview` after plotting or formatting. It writes a temporary PNG
by default and returns path, file size, and PNG/JPEG dimensions when available.
Use `origin_inspect_export` to verify an existing export without re-exporting it.

## Safety

By default the server can read and write paths that the local user can access. To
restrict file operations, set `ORIGIN_MCP_ALLOWED_ROOTS` to one or more allowed
root directories separated by the platform path separator.

PowerShell example:

```powershell
$env:ORIGIN_MCP_ALLOWED_ROOTS = "D:\origin-mcp;D:\data"
```

## Analysis Tools

The named analysis tools are wrappers around Origin LabTalk/X-Function commands.
They return the generated script and whether Origin accepted execution. For
advanced analysis settings, pass an `options` object whose keys map to X-Function
option names.

The generic analysis path uses a centralized adapter table for X-Function names,
aliases, minimum versions, output option names, and common option aliases. It
returns the generated LabTalk script plus `executed`; if Origin rejects a command,
`executed` is `false` and the script is included for debugging.

Origin option-list values such as smoothing `method:=sg` or peak direction
`dir:=p` are emitted as LabTalk symbols rather than quoted strings, matching the
official X-Function examples.

`origin_linear_fit` is more structured when both `x_col` and `y_col` are provided:
it uses Origin's `originpro.LinearFit` API and returns either a result tree or a
report sheet reference. Use `options={"report": true, "band": 1}` to create a
report with confidence bands.

## Official Origin APIs Used

The implementation follows OriginLab's documented `originpro` patterns:

- `WSheet.from_file` / Data Connector for native Origin imports
- `WSheet.from_df`, `set_labels`, and `cols_axis` for worksheet data and metadata
- `new_graph`, `GLayer.add_plot`, `axis(...).title`, `label("Legend")`, and
  `GPage.save_fig` for graph creation, formatting, and export
- `originpro.LinearFit` for structured linear regression results

## Version Compatibility

Use `origin_capabilities` after configuring the MCP server. It reports:

- Origin version from LabTalk `@V`
- installed `originpro` and `OriginExt` package versions
- whether important APIs are available, including project listing, graph batch export,
  Data Connector import, and structured fitting APIs

The code prefers official `originpro` APIs and falls back to LabTalk commands where
reasonable. Some advanced analysis X-Functions differ by Origin version; when a
feature is unavailable, tools return a structured error instead of silently doing
the wrong thing.

Capability detection is cached after the first check so normal tool calls do not
pay repeated startup cost. Pass `refresh=true` to `origin_capabilities` after
upgrading Origin or changing the Python environment.

Version-gated tools currently check their required capabilities before running:

- Data Connector import checks `worksheet_from_file`
- project listing checks `pages`
- batch graph export checks `graph_list`
- structured linear fitting checks `linear_fit_api`

## Safety Notes

This server can read data files and write exported graphs/projects on the local
machine. Run it only for trusted MCP clients. Prefer absolute file paths and avoid
granting broad filesystem access to untrusted prompts.
