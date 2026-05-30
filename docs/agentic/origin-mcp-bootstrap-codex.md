# origin-mcp Bootstrap Profile: Codex

Use this profile for Step 1 of `docs/agentic/origin-mcp-bootstrap.md` when the
MCP client is Codex.

## Target

Configure a user-level Codex MCP server named `origin` that launches the local
editable checkout:

```toml
[mcp_servers.origin]
command = "python"
args = ["-m", "origin_mcp"]
```

Use an absolute Python 3.10+ `python.exe` path if `python` is not the
interpreter where `origin-mcp` was installed.

## Agent Rules

- Prefer Codex's user/global MCP configuration or settings UI.
- If a Codex workspace-local MCP config already exists, use it only when
  user/global configuration is unavailable or write-blocked.
- Preserve all existing MCP server entries.
- If an `origin` entry already exists, update only the launch fields needed for
  this server: `command`, `args`, and any Codex-supported environment fields.

## After Configuration

After changing the MCP configuration, restart or reconnect Codex so the server
entry is reloaded. Do not call `origin_doctor` automatically.

If the tools are not visible, restart the Codex session fully and retry before
changing the Origin bridge setup.

