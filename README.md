# origin-mcp

[简体中文](README.zh.md)

`origin-mcp` is a local Model Context Protocol (MCP) server that lets AI
assistants control Origin/OriginPro on Windows. It connects through OriginLab's
Python automation interface and exposes tools for importing data, editing
worksheets, creating and refining graphs, running Origin analyses, exporting
figures, and managing the Origin application lifecycle.

This project is still in a testing stage. Trying it on real Origin workflows,
reporting issues, suggesting improvements, and opening pull requests are all
welcome.

The goal is to let an AI model work with your installed Origin environment
directly instead of only generating standalone plotting code.

## Highlights

- Import CSV, TSV, TXT, DAT, XLS, and Excel data into Origin worksheets.
- Read, write, sort, clear, and export worksheet data.
- Create common 2D, 3D, contour, statistical, polar, ternary, vector, bubble,
  image, and matrix-based plots.
- Cover the documented Origin Plot Type ID table with direct MCP tools.
- Inspect and refine graph pages, layers, axes, legends, labels, reference lines,
  plot styles, and publication-style formatting.
- Run common Origin analysis commands, including fitting, smoothing, integration,
  differentiation, peak finding, and descriptive statistics.
- Read analysis output worksheets back as JSON and normalize fit parameters and
  metrics where possible.
- Search and browse a local Origin knowledge base covering MCP tools, Plot Type
  IDs, graph formatting, analysis adapters, OriginPro API notes, and
  LabTalk/X-Function routes.
- Export figures, preview exported images, save projects, and release or close
  Origin safely.
- Route Origin operations through a local Origin GUI bridge so the MCP server
  runtime can be separated from the Origin automation runtime.

## Requirements

- Windows
- Origin or OriginPro installed and licensed
- Origin/OriginPro 2026 is the primary tested target; other Origin versions are
  not currently guaranteed
- Python 3.11 or 3.12 recommended; Python 3.10 is supported but less tested
- Origin's `originpro` package and `pywin32`

Newer Python versions such as Python 3.14 may run the MCP server itself, but
Origin automation packages may not publish compatible wheels yet. If installation
fails on a newer Python version, use Python 3.11 or 3.12.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[origin]"
```

If `originpro` is already available from your Origin installation:

```powershell
python -m pip install -e .
```

## MCP Configuration

Example MCP client configuration:

```json
{
  "mcpServers": {
    "origin": {
      "command": "C:\\path\\to\\origin-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "origin_mcp"]
    }
  }
}
```

Replace `C:\\path\\to\\origin-mcp` with your local checkout path. More examples
are in [docs/mcp-config.md](docs/mcp-config.md).

## Documentation

- [Tool and compatibility reference](docs/tools.md)
- [MCP client configuration](docs/mcp-config.md)
- [Origin GUI bridge](docs/origin-bridge.md)

After starting the bridge inside Origin with
`exec(open(r"D:\origin-mcp\addon.py", encoding="utf-8").read())`,
run `python examples\smoke_bridge.py` to validate a real file-to-figure
workflow.

## Knowledge Base

The server exposes a structured local knowledge base through MCP tools. Use
`origin_query_knowledge` or the collection-specific query tools to search, and
use `origin_browse_knowledge` or the collection-specific browse tools to inspect
stable paths. The MCP tool index is generated from the current server tool
docstrings so it tracks the implemented tool surface.

Collections include `mcp_tools`, `reference`, `python_api`, `labtalk`, and
`official_docs`. The knowledge base is a curated operational index; official
OriginLab documentation entries include URLs for exact upstream syntax.

## Safety

This server can read local data files, write exported figures/projects, and
control a local Origin session. Run it only for trusted MCP clients. Use
`ORIGIN_MCP_ALLOWED_ROOTS` to restrict file access when needed.

If Origin says it is being controlled by another program, call `origin_detach`
first. Use `origin_force_quit` only after confirming there is no unsaved work.

## License

MIT. See [LICENSE](LICENSE).
