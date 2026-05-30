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

Start the Origin GUI bridge with `addon.py`, then verify MCP connectivity from
your MCP client with `origin_doctor`:

```json
{"ping_origin": true}
```

For an MCP-client prompt, use a compact workflow:

```text
Use the origin MCP server to run origin_doctor with ping_origin=true.
```

This is enough for normal installation checks. The smoke script is an optional
deeper validation tool for development or troubleshooting because it creates an
Origin project, imports sample data, exports an image, and saves an OPJU file.

## Troubleshooting

Run `origin_doctor` first. For detailed startup and troubleshooting guidance,
search the knowledge base for `bridge startup` or `bridge diagnostics`.
