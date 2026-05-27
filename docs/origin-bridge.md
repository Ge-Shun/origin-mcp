# Origin GUI Bridge

`origin-mcp` uses a small local bridge process to own the Origin automation
session. The MCP server sends JSON-lines requests to that process over
localhost, so the MCP runtime can be separated from the Python environment that
imports `originpro`.

This is useful when a user's default Python is newer than the Python versions
commonly validated by OriginExt, or when the Origin GUI lifecycle should be kept
outside the MCP server process.

## Start the Bridge Inside Origin

The preferred route is to start the bridge from Origin's own Python console.
This keeps `originpro` calls inside the Origin process and avoids external
Python version mismatches.

1. Open Origin/OriginPro.
2. Open the Python console.
3. Open or paste `addon.py`, or run it by path:

```python
import runpy
runpy.run_path(r"<path-to-origin-mcp>\addon.py", run_name="__main__")
```

Replace `<path-to-origin-mcp>` with the local checkout path.

`addon.py` does not hard-code the checkout directory. It first tries to import
an installed `origin_mcp` package from Origin's embedded Python. If that is not
available, it looks for a sibling `src\origin_mcp` directory next to `addon.py`.
`ORIGIN_MCP_SRC` is only a fallback for unusual launch setups.

The addon shows a Windows message box when the bridge is ready:

```text
Bridge is running inside Origin. See the status file for connection details.
```

By default the bridge serves requests in the Python console foreground with a
small Windows message pump so Origin can continue processing UI messages while
the bridge is active. Keep the Python console running while MCP clients use the
bridge. `background=True` is available, but Origin embedded Python may leave
background threads listening without processing requests on some installations.

The addon also writes JSON status to `origin-bridge.status.txt` next to
`addon.py` by default. Set `ORIGIN_MCP_BRIDGE_STATUS` to choose another status
file location. The status includes the latest message, host, port, package
source, Python executable/version, and `last_error` when startup fails.

On first run, the addon installs missing runtime packages such as `pandas`,
`openpyxl`, `xlrd`, and `originpro` into Origin's embedded Python. To disable
automatic installation, set `ORIGIN_MCP_INSTALL_MISSING=0` before running the
addon.

Then run the MCP server or smoke test from a separate terminal. The MCP server
connects to the same host and port through `OriginBridgeProxy`.

To stop the foreground bridge, press `Ctrl+C` in the Origin Python console. If
Origin does not return to the prompt, close Origin after saving any work.

No source directory needs to be edited in `addon.py`. If the file was copied
away from the checkout and `origin-mcp` is not installed in Origin's Python, set
`ORIGIN_MCP_SRC` to the checkout `src` directory before running the addon.

Use a token when multiple local tools may connect to the same machine:

```powershell
$env:ORIGIN_MCP_BRIDGE_TOKEN = "replace-with-a-local-secret"
```

The MCP server reads the same connection settings from environment variables:

- `ORIGIN_MCP_BRIDGE_HOST`
- `ORIGIN_MCP_BRIDGE_PORT`
- `ORIGIN_MCP_BRIDGE_TOKEN`
- `ORIGIN_MCP_BRIDGE_TIMEOUT`
- `ORIGIN_MCP_BRIDGE_MAX_TASKS`
- `ORIGIN_MCP_INSTALL_MISSING`
- `ORIGIN_MCP_BRIDGE_BACKGROUND`

Existing tool functions such as `origin_ping`, `origin_import_table`, and
`origin_plot_line` keep their original names and route through an
`OriginClient`-style bridge proxy. The bridge allowlist is tested against
`server.py` so new public client calls must be added deliberately. The explicit
`origin_bridge_*` functions remain as diagnostics and bridge controls.

The MCP server registers the compact 20-tool profile by default. Specialized
bridge and plotting wrappers remain available in Python and can be exposed to
MCP clients by starting the server with `ORIGIN_MCP_TOOL_PROFILE=full`.

## MCP Tools

Bridge-specific tools provide a small diagnostic and execution surface for
validating and managing the split-process design:

- `origin_doctor`: inspect bridge configuration, status file contents, bridge
  reachability, optional Origin ping, and recommended next steps.
- `origin_bridge_status`: check that the bridge process is reachable.
- `origin_bridge_ping_origin`: ask the bridge to connect to Origin.
- `origin_bridge_capabilities`: collect Origin/originpro capabilities through
  the bridge.
- `origin_bridge_new_project`: create a new Origin project through the bridge.
- `origin_bridge_open_project`: open an OPJU/OPJ project through the bridge.
- `origin_bridge_save_project`: save the current project through the bridge.
- `origin_bridge_list_project`: list project objects through the bridge.
- `origin_bridge_get_worksheet_info`: inspect row/column counts and labels
  through the bridge.
- `origin_bridge_read_worksheet`: read worksheet rows through the bridge.
- `origin_bridge_write_worksheet`: write worksheet rows through the bridge.
- `origin_bridge_run_labtalk`: execute LabTalk through the bridge process.
- `origin_bridge_import_table`: import CSV, TSV, TXT, DAT, XLS, or Excel data
  through the bridge process.
- `origin_bridge_plot_table`: create a table-backed Origin plot through the
  bridge process.
- `origin_bridge_export_graph`: export a graph through the bridge process and
  inspect the exported file.
- `origin_bridge_run_analysis`: run an Origin analysis through the bridge
  process.
- `origin_bridge_submit_task`: submit a supported bridge method to the bridge
  background queue.
- `origin_bridge_task_status`: read task status, result, or error.
- `origin_bridge_cancel_task`: cancel a queued task or mark a running task for
  cancellation.
- `origin_bridge_list_tasks`: list recent bridge tasks.

Example:

```json
{"script": "type -b \"hello from bridge\";"}
```

## Background Tasks

Use background tasks for operations that may take longer than a normal MCP tool
call. The bridge exposes the current task method allowlist in
`origin_bridge_status` as `taskable_methods`.

Submit a task:

```json
{
  "method": "run_labtalk",
  "params": {
    "script": "type -b \"long Origin operation\";"
  }
}
```

Then poll `origin_bridge_task_status` with the returned `task_id`.

Task states are:

- `queued`: waiting for the bridge worker.
- `running`: currently executing in the bridge process.
- `completed`: finished with a `result`.
- `failed`: finished with an `error`.
- `cancelled`: cancelled before the worker started it.

Cancellation is cooperative. A queued task can be cancelled. A running task is
marked with `cancel_requested=true`, but the bridge cannot safely terminate a
Python thread while Origin is executing an automation call.

The bridge keeps a bounded in-memory task history. Completed, failed, and
cancelled task records are pruned oldest-first when the configured `max_tasks`
limit is exceeded. Queued and running tasks are not pruned.

## Diagnostics

If a tool cannot connect to Origin, run `origin_doctor` before retrying the
workflow. It checks the MCP-side bridge settings, reads the addon status file,
tries a bridge ping, and can optionally ask the bridge to ping Origin:

```json
{"ping_origin": true}
```

Read the `recommendations` field first. Typical fixes are starting `addon.py`
inside Origin, matching `ORIGIN_MCP_BRIDGE_HOST` and `ORIGIN_MCP_BRIDGE_PORT`
with the status file, or inspecting `last_error` when the addon failed during
dependency import or installation.

## High-Level Bridge Workflows

The bridge has enough surface to run a simple file-to-figure workflow without
`originpro` calls in the MCP server process:

```json
{
  "path": "C:\\data\\run.csv",
  "kind": "scatter",
  "x_col": "time",
  "y_cols": ["force"],
  "graph_name": "RunForce",
  "style_mode": "origin_default",
  "export_path": "C:\\data\\run_force.png"
}
```

For longer plots or exports, submit the bridge method itself as a task:

```json
{
  "method": "plot_table",
  "params": {
    "path": "C:\\data\\run.csv",
    "kind": "line",
    "export_path": "C:\\data\\run_line.png"
  }
}
```

## Smoke Test

Use the smoke script to validate the real Origin installation after changing the
bridge. It exercises the MCP tool layer rather than calling `OriginClient`
directly.

In the Origin Python console:

```python
import runpy
runpy.run_path(r"<path-to-origin-mcp>\addon.py", run_name="__main__")
```

Then in another terminal:

```powershell
python examples\smoke_bridge.py --keep-origin-open
```

The smoke run creates a new project, imports `examples/sample_data.csv`, reads
worksheet rows, creates a line plot, exports a PNG, checks that the export looks
non-empty, and saves an OPJU project under the output directory. If the smoke
run fails, it prints `origin_doctor` output before exiting.

## Current Limits

The first bridge implementation intentionally uses the Python standard library
and a single-request JSON-lines TCP protocol. It now includes a small task queue,
but does not yet provide streaming logs, hard cancellation of running Origin
calls, or a WebSocket transport. Those can be added after the bridge lifecycle is
validated against a real Origin installation.
