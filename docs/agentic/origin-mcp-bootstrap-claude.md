# origin-mcp Bootstrap Profile: Claude

Use this profile for Step 1 of `docs/agentic/origin-mcp-bootstrap.md` when the
MCP client is Claude Desktop or Claude Code.

## Claude Desktop

Configure `%APPDATA%\Claude\claude_desktop_config.json` with an `origin` MCP
server entry:

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

Use an absolute Python 3.10+ `python.exe` path if `python` is not the
interpreter where `origin-mcp` was installed. If the file already contains other
MCP servers, merge this entry without removing them.

## Claude Code

Use Claude Code's native MCP configuration mechanism when available, but keep
the same launch contract:

- server name: `origin`
- command: `python` or the absolute path to a Python 3.10+ `python.exe`
- args: `-m origin_mcp`

Prefer user/global configuration for the same reason as the main bootstrap
guide: the Origin GUI bridge is machine-local, not project-local.

## After Configuration

After changing the MCP configuration, restart or reconnect Claude so the server
entry is reloaded. Do not call `origin_doctor` automatically.

If the tools are not visible, restart Claude fully and retry before changing the
Origin bridge setup.

