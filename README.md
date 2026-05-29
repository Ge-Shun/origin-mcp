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

## Highlights

- Import CSV, TSV, TXT, DAT, XLS, and Excel data into Origin worksheets.
- Read, write, sort, clear, and export worksheet data.
- Create and refine common 2D, 3D, contour, statistical, and specialized plots.
- Run Origin analyses such as fitting, smoothing, integration, peak finding, and
  descriptive statistics.
- Export figures and projects through a local Origin GUI bridge.

## Requirements

- Windows
- Origin or OriginPro installed and licensed
- Origin/OriginPro 2026 is the primary tested target; other Origin versions are
  not currently guaranteed
- Python 3.10+ for the MCP server runtime
- Python 3.11 or 3.12 recommended when installing Origin automation packages
- Origin's `originpro` package and `pywin32`

The MCP server core targets Python 3.10+. Local checks currently pass on Python
3.12 and 3.14. Origin automation packages may lag newer Python releases, so use
Python 3.11 or 3.12 for environments that import `originpro` or `pywin32`.

## Agentic Setup

Copy this to your AI agent and let it self-configure:

```text
Fetch and follow this bootstrap guide end to end:
https://raw.githubusercontent.com/Ge-Shun/origin-mcp/main/docs/agentic/origin-mcp-bootstrap.md
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

## Start the Origin Bridge

The bridge runs inside Origin's own Python so `originpro` stays on Origin's UI
thread. There is nothing to configure — start it once per Origin session:

1. Open Origin, then open its **Python Console**.
2. Paste this single line (replace the path with your checkout):

```python
import runpy; runpy.run_path(r"C:\path\to\origin-mcp\addon.py", run_name="__main__")
```

A `Bridge is running inside Origin.` box confirms startup. Keep that console
running while you use the tools.

**To stop, just ask your MCP assistant to shut the Origin bridge down** — it
calls `origin_bridge_shutdown`, so no extra terminal or console input is needed.
If you are not using an assistant, double-click `scripts\stop-bridge.cmd` (or
run `python scripts\stop_bridge.py`) to send the same shutdown request. The
serving console returns to its prompt and Origin stays open.

If a package is missing or the bridge will not start, see
[docs/origin-bridge.md](docs/origin-bridge.md).

## License

MIT. See [LICENSE](LICENSE).
