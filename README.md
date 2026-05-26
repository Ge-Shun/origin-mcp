# origin-mcp

`origin-mcp` is a local MCP server that lets AI clients control Origin/OriginPro on a
Windows machine through Origin's Python automation interface.

The first version focuses on a practical plotting loop:

- connect to a local Origin/OriginPro instance
- create or save projects
- import CSV, TSV, TXT, DAT, XLS, and XLSX data into worksheets
- append data into existing worksheets
- create line, scatter, line+symbol, error bar, column, contour, and template plots
- set graph title, axis labels, legends, and templates
- set plot color, line width, symbol style, axis scale, and axis limits
- run common analysis X-Functions such as fitting, smoothing, integration, and peak finding
- export graphs to image/PDF files
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
- `origin_new_project`: create a new project
- `origin_open_project`: open an OPJU/OPJ project
- `origin_save_project`: save the current project
- `origin_import_csv`: import a CSV file into a worksheet
- `origin_import_table`: import CSV, TSV, TXT, DAT, XLS, or XLSX into a worksheet
- `origin_import_excel`: import an Excel sheet into a worksheet
- `origin_append_table`: append table data to an existing worksheet
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
- `origin_export_graph`: export the active or named graph
- `origin_export_all_graphs`: export every graph in the project
- `origin_list_project`: list workbooks, worksheets, graphs, and images
- `origin_rename_object`: rename a graph, workbook, matrix book, or worksheet
- `origin_delete_object`: delete a graph, workbook, matrix book, or worksheet
- `origin_run_analysis`: run a named Origin X-Function analysis
- `origin_linear_fit`, `origin_polynomial_fit`, `origin_nonlinear_fit`
- `origin_smooth`, `origin_differentiate`, `origin_integrate`
- `origin_peak_find`, `origin_descriptive_stats`
- `origin_run_labtalk`: execute LabTalk script text
- `origin_quit`: close Origin

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

## Safety Notes

This server can read data files and write exported graphs/projects on the local
machine. Run it only for trusted MCP clients. Prefer absolute file paths and avoid
granting broad filesystem access to untrusted prompts.
