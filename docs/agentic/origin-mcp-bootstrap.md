# origin-mcp Agent Bootstrap Guide

Use this guide when an agent needs to set up `origin-mcp` execution end to end
on a Windows machine.

## Target Outcome

1. The MCP client is configured to run the local `origin-mcp` server.
2. The server runtime can import `origin_mcp`.
3. The Origin GUI bridge is started from Origin with `addon.py`, either through
   installed UI buttons or the Python console.
4. The MCP client is restarted or reconnected so the server is available.

## Agent Execution Rules

- Use bounded, fast path detection for Origin. Do not run full-drive recursive
  scans by default.
- Prefer user/global MCP client configuration. Fall back to workspace-level
  configuration only if the user-level target is unavailable or write-blocked.
- When editing MCP configuration, merge only the `origin` server entry. Do not
  overwrite unrelated MCP servers.
- Do not run the smoke file-to-figure workflow by default. It creates an Origin
  project, imports sample data, exports an image, and saves an OPJU file. Run it
  only when the user explicitly asks for end-to-end validation or when
  troubleshooting a plotting/export problem after `origin_doctor` passes.
- Do not call `origin_doctor` automatically after configuring MCP. Reserve it
  for troubleshooting or for an explicit user request.
- If a command fails, report the exact command and important output, then apply
  the next fallback.
- Respect step ownership labels:
  - `[AGENT]` means the agent should execute the action.
  - `[USER ACTION REQUIRED]` means the user must execute it manually.

## Step 1 - Configure MCP Client

[AGENT]

Use the client-specific Step 1 profile when available:

- Codex: `docs/agentic/origin-mcp-bootstrap-codex.md`
- Claude Desktop / Claude Code: `docs/agentic/origin-mcp-bootstrap-claude.md`

Apply this MCP launch contract in the client's native config format:

- server id/name: `origin`
- command: `python` or the absolute path to a Python 3.10+ `python.exe`
- args: `["-m", "origin_mcp"]`
- working directory: the `origin-mcp` checkout, if the client supports it
- environment: include `ORIGIN_MCP_TOOL_PROFILE=compact` only when an explicit
  profile is required; compact is already the default

Example stdio server object:

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

Rationale: `origin-mcp` controls a machine-local Origin GUI session over
localhost, so the capability is machine-scoped. User/global MCP configuration
usually avoids a "change directory, lose Origin tools" failure mode.

## Step 2 - Prepare the Server Runtime

[AGENT]

From the `origin-mcp` checkout:

```powershell
python -m pip install -e .
```

If installation fails with an old `pip`, editable install, or build backend
error, upgrade `pip` and retry:

```powershell
python -m pip install -U pip
python -m pip install -e .
```

The MCP server process does not need to import `originpro`; Origin automation
runs inside the Origin GUI process after `addon.py` starts the bridge.

Verify the server import:

```powershell
python -c "import origin_mcp; print(origin_mcp.__version__)"
```

## Step 3 - Resolve Origin and Addon Paths

[AGENT]

The addon path is normally:

```text
C:\path\to\origin-mcp\addon.py
```

Use bounded common-path probes to find the Origin executable when the user has
not already opened Origin:

```powershell
$roots = @(
  'C:\Program Files\OriginLab',
  'C:\Program Files (x86)\OriginLab',
  'D:\Program Files\OriginLab',
  'D:\OriginLab'
)
$hits = @()
foreach ($root in $roots) {
  if (Test-Path $root) {
    Get-ChildItem -Path $root -Recurse -Depth 3 -Filter 'Origin*.exe' -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match '^Origin.*\.exe$' } |
      ForEach-Object {
        $hits += [PSCustomObject]@{ origin_exe = $_.FullName; install_dir = $_.Directory.FullName }
      }
  }
}
$hits | Sort-Object origin_exe -Unique | Select-Object -First 10
```

If this does not find Origin, ask the user for the Origin executable path or ask
them to open Origin manually.

## Step 4 - Start Origin and the Bridge

[AGENT]

If Origin is not open and an executable was found, launch it:

```powershell
Start-Process "C:\path\to\Origin.exe"
```

Confirm a likely Origin process is running:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match '^Origin.*\.exe$' } |
  Select-Object Name, ProcessId, ExecutablePath
```

[USER ACTION REQUIRED]

For daily use, build and install the Origin OPX from `docs/origin-ui-buttons.md`,
then click the **Origin MCP Bridge** App icon inside Origin as a single bridge
toggle.
If the OPX background bridge does not process requests on that installation,
fall back to the manual foreground startup below.

For manual startup or troubleshooting, in Origin/OriginPro:

1. Open the Python console.
2. Run the checkout addon by path:

```python
import runpy; runpy.run_path(r"C:\path\to\origin-mcp\addon.py", run_name="__main__")
```

Replace `C:\path\to\origin-mcp\addon.py` with the real checkout path.

On a fresh Origin embedded Python, `pandas`, `openpyxl`, or `xlrd` may be
missing even after the MCP server runtime has been installed.
`addon.py` attempts to install missing Origin-side runtime dependencies
automatically. If the user does not want the addon to run `pip install`, set
`ORIGIN_MCP_INSTALL_MISSING=0` before `runpy.run_path`:

```python
import os; os.environ["ORIGIN_MCP_INSTALL_MISSING"] = "0"
import runpy; runpy.run_path(r"C:\path\to\origin-mcp\addon.py", run_name="__main__")
```

Expected result:

- A Windows message box says the bridge is running inside Origin.
- `origin-bridge.status.txt` is written next to `addon.py`, unless
  `ORIGIN_MCP_BRIDGE_STATUS` is set.
- The Origin Python console should remain running while MCP clients use the
  bridge.

Optional environment variables before starting the addon can be set in the
Origin Python console immediately before `runpy.run_path`:

```python
import os
os.environ["ORIGIN_MCP_BRIDGE_HOST"] = "127.0.0.1"
os.environ["ORIGIN_MCP_BRIDGE_PORT"] = "47631"
os.environ["ORIGIN_MCP_BRIDGE_TOKEN"] = "replace-with-a-local-secret"
os.environ["ORIGIN_MCP_BRIDGE_STATUS"] = r"C:\path\to\origin-mcp\origin-bridge.status.txt"
```

Only set a token when the same token is also configured for the MCP server
environment.

## Step 5 - Reconnect the MCP Client

[AGENT]

Restart or reconnect the MCP client after changing its server configuration.
Do not call `origin_doctor` as a normal post-configuration step. If the MCP
client exposes a passive tool list or server status UI, use that to confirm the
server is visible without executing Origin diagnostics.

## Optional Smoke Test

[AGENT - ONLY WHEN REQUESTED OR TROUBLESHOOTING]

Validate a real file-to-figure workflow from a separate terminal only when the
user asks for deeper end-to-end validation, or when `origin_doctor` passes but
plotting/export still fails:

```powershell
python examples\smoke_bridge.py --keep-origin-open
```

The smoke workflow creates a new Origin project, imports
`examples\sample_data.csv`, reads worksheet rows, creates a plot, exports a PNG,
inspects the export, and saves an OPJU project. Report those side effects before
running it.

## Troubleshooting

- `origin_* tools missing`: fully restart or reconnect the MCP client after
  Step 1.
- `origin_bridge_unavailable`: start `addon.py` inside Origin, then compare
  `ORIGIN_MCP_BRIDGE_HOST` and `ORIGIN_MCP_BRIDGE_PORT` with the status file.
- `origin_bridge_unauthorized`: set the same `ORIGIN_MCP_BRIDGE_TOKEN` for the
  MCP server and the addon process, or clear both tokens.
- No status file: run `addon.py` from the checkout root or set
  `ORIGIN_MCP_BRIDGE_STATUS` to a writable path.
- `origin_mcp is not importable in Origin's embedded Python`: run `addon.py`
  from the checkout root so it can detect the adjacent `src` directory, install
  `origin-mcp` into Origin's Python environment, or set `ORIGIN_MCP_SRC` to the
  checkout `src` directory before running the addon.
- `originpro` or table dependencies missing inside Origin Python: `addon.py`
  attempts to install them automatically by default. When Origin's global
  site-packages is not writable (for example under `C:\Program Files`), the
  addon adds `--user` so the install does not require administrator rights. If
  automatic installation still fails, check network/proxy access or install the
  missing packages into Origin's Python manually. Set
  `ORIGIN_MCP_INSTALL_MISSING=0` only when the user wants to disable automatic
  installation.
