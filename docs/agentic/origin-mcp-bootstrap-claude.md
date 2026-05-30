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
      "command": "C:\\path\\to\\origin-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "origin_mcp"]
    }
  }
}
```

Replace `C:\\path\\to\\origin-mcp` with the actual checkout path. If the file already
contains other MCP servers, merge this entry without removing them.

## Claude Code

Use Claude Code's native MCP configuration mechanism when available, but keep
the same launch contract:

- server name: `origin`
- command: `C:\path\to\origin-mcp\.venv\Scripts\python.exe`
- args: `-m origin_mcp`

Prefer user/global configuration for the same reason as the main bootstrap
guide: the Origin GUI bridge is machine-local, not project-local.

## Verification Prompt

After restarting or reconnecting Claude, ask it to call:

```text
Use the origin MCP server to run origin_doctor with ping_origin=true.
```

If the tools are not visible, restart Claude fully and retry before changing the
Origin bridge setup.

