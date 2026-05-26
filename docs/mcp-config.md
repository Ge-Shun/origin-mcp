# MCP Client Configuration

Install the project into a virtual environment first:

```powershell
cd D:\origin-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[origin]"
```

Then configure your MCP client to launch the server over stdio.

## Codex / Claude Desktop style

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

Replace `C:\\path\\to\\origin-mcp` with your local checkout path.

Using `python.exe` with `-m origin_mcp` avoids hard-coding the generated console
script path and works reliably for editable installs.

## First Test Prompt

Ask your MCP client:

```text
Use the origin MCP server to ping Origin. If it connects, import
D:\origin-mcp\examples\sample_data.csv, plot signal_a and signal_b against time
as lines, and export the graph to D:\origin-mcp\output\sample_plot.png.
```

## Troubleshooting

If `origin_ping` reports that `originpro` is missing:

1. Confirm Origin/OriginPro is installed and licensed.
2. Try installing the package into the same environment:

   ```powershell
   python -m pip install originpro pywin32
   ```

3. If installation fails on Python 3.14, use Python 3.11 or 3.12 for this MCP
   server.

If Origin starts but plotting fails, use `origin_run_labtalk` for a small command
such as:

```text
type -b "hello from mcp";
```

That confirms the MCP-to-Origin command path works before debugging worksheet or
graph APIs.
