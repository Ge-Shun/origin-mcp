# MCP Client Configuration

Install the project first using the commands in the README. Then configure your
MCP client to launch the server over stdio.

## Claude Code

For Claude Code, prefer the native `claude mcp` command instead of manually
copying a Claude Desktop JSON file. For `origin-mcp`, a user-scoped server is
usually the best fit because it controls a machine-local Origin GUI session:

```bash
claude mcp add --transport stdio --scope user origin -- python -m origin_mcp
```

Use an absolute `python.exe` path if `python` is not the Python 3.10+
interpreter where `origin-mcp` was installed:

```bash
claude mcp add --transport stdio --scope user origin -- "C:\Path\To\Python\python.exe" -m origin_mcp
```

Then verify the entry:

```bash
claude mcp get origin
claude mcp list
```

Restart or reconnect Claude Code after changing MCP configuration. Inside a
Claude Code session, use `/mcp` to check whether the server is connected.

If you explicitly want a repository-shared project configuration, use
`--scope project`; Claude Code will create or update `.mcp.json` in the project
root and may ask you to approve that project-scoped server before loading it.

## Codex / Claude Desktop style

Codex and Claude Desktop can use a JSON server entry like this:

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
