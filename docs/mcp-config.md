# MCP Client Configuration

Install the project first using the commands in the README. Then configure your
MCP client to launch the server over stdio.

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

## First Test

Start the Origin GUI bridge with `addon.py`, then run the smoke script from a
separate terminal:

```powershell
python examples\smoke_bridge.py --keep-origin-open
```

For an MCP-client prompt, use a compact workflow:

```text
Use the origin MCP server to run origin_doctor. If the bridge is healthy, import
<path-to-origin-mcp>\examples\sample_data.csv, create a suitable line plot for
signal_a and signal_b against time, and export the graph to
<path-to-origin-mcp>\output\sample_plot.png.
```

## Troubleshooting

Run `origin_doctor` first. For detailed startup and troubleshooting guidance,
search the knowledge base for `bridge startup` or `bridge diagnostics`.
