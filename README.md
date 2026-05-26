# origin-mcp

`origin-mcp` is a local MCP server that lets AI clients control Origin/OriginPro on a
Windows machine through Origin's Python automation interface.

The first version focuses on a practical plotting loop:

- connect to a local Origin/OriginPro instance
- create or save projects
- import CSV data into worksheets
- create line and scatter plots
- export graphs to image/PDF files
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
- `origin_save_project`: save the current project
- `origin_import_csv`: import a CSV file into a worksheet
- `origin_plot_line`: import CSV data and create a line plot
- `origin_plot_scatter`: import CSV data and create a scatter plot
- `origin_export_graph`: export the active or named graph
- `origin_run_labtalk`: execute LabTalk script text
- `origin_quit`: close Origin

## Example Prompt

> Import `D:\data\experiment.csv`, use column `time` as x, plot columns `force`
> and `displacement` as line curves, then export the graph as
> `D:\data\experiment_plot.png`.

## Safety Notes

This server can read data files and write exported graphs/projects on the local
machine. Run it only for trusted MCP clients. Prefer absolute file paths and avoid
granting broad filesystem access to untrusted prompts.
