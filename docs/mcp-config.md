# MCP Client Configuration

Install the project first using the commands in the README. Then configure your
MCP client to launch the server over stdio.

## Codex / Claude Desktop style

```json
{
  "mcpServers": {
    "origin": {
      "command": "python",
      "args": ["-m", "origin_mcp"]
    }
  }
}
```

Use an absolute `python.exe` path if `python` is not the Python 3.10+
interpreter where `origin-mcp` was installed.

Using `python` with `-m origin_mcp` avoids hard-coding the generated console
script path and works reliably for editable installs.

## After Configuration

Restart or reconnect your MCP client after changing the configuration. Do not
run `origin_doctor` automatically as part of normal setup.

Start the Origin GUI bridge with `addon.py` only when you are ready to use
Origin tools. The smoke script is an optional deeper validation tool for
development or troubleshooting because it creates an Origin project, imports
sample data, exports an image, and saves an OPJU file.

## Troubleshooting

Run `origin_doctor` first. For detailed startup and troubleshooting guidance,
search the knowledge base for `bridge startup` or `bridge diagnostics`.
