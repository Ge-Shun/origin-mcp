# origin-mcp Bootstrap Profile: Codex

Use this profile for Step 1 of `docs/agentic/origin-mcp-bootstrap.md` when the
MCP client is Codex.

## Target

Configure a user-level Codex MCP server named `origin` that launches the local
editable checkout:

```toml
[mcp_servers.origin]
command = "C:\\path\\to\\origin-mcp\\.venv\\Scripts\\python.exe"
args = ["-m", "origin_mcp"]
```

Replace `C:\\path\\to\\origin-mcp` with the actual checkout path.

## Agent Rules

- Prefer Codex's user/global MCP configuration or settings UI.
- If a Codex workspace-local MCP config already exists, use it only when
  user/global configuration is unavailable or write-blocked.
- Preserve all existing MCP server entries.
- If an `origin` entry already exists, update only the launch fields needed for
  this server: `command`, `args`, and any Codex-supported environment fields.

## Verification Prompt

After restarting or reconnecting Codex, ask it to call:

```text
Use the origin MCP server to run origin_doctor with ping_origin=true.
```

If the tools are not visible, restart the Codex session fully and retry before
changing the Origin bridge setup.

