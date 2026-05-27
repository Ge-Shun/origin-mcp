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
3. Run:

```python
exec(open(r"D:\origin-mcp\examples\origin_bridge_addon.py", encoding="utf-8").read())
```

The addon shows a Windows message box when the bridge is ready:

```text
Bridge is running inside Origin on 127.0.0.1:47631.
```

By default the bridge serves requests in the Python console foreground with a
small Windows message pump so Origin can continue processing UI messages while
the bridge is active. Keep the Python console running while MCP clients use the
bridge. `background=True` is available, but Origin embedded Python may leave
background threads listening without processing requests on some installations.

The addon also writes the latest status to:

```text
D:\origin-mcp\origin-bridge.status.txt
```

On first run, the addon installs missing runtime packages such as `pandas`,
`openpyxl`, `xlrd`, and `originpro` into Origin's embedded Python. To disable
automatic installation, set `ORIGIN_MCP_INSTALL_MISSING=0` before running the
addon.

Then run the MCP server or smoke test from a separate terminal. The MCP server
connects to the same host and port through `OriginBridgeProxy`.

To stop the foreground bridge, press `Ctrl+C` in the Origin Python console. If
Origin does not return to the prompt, close Origin after saving any work.

If the checkout is not under `D:\origin-mcp`, set `ORIGIN_MCP_SRC` to the
checkout `src` directory before running the addon.

Use a token when multiple local tools may connect to the same machine:

```powershell
$env:ORIGIN_MCP_BRIDGE_TOKEN = "replace-with-a-local-secret"
```

The MCP server reads the same connection settings from environment variables:

- `ORIGIN_MCP_BRIDGE_HOST`, default `127.0.0.1`
- `ORIGIN_MCP_BRIDGE_PORT`, default `47631`
- `ORIGIN_MCP_BRIDGE_TOKEN`, optional
- `ORIGIN_MCP_BRIDGE_TIMEOUT`, default `10`
- `ORIGIN_MCP_BRIDGE_MAX_TASKS`, default `200`
- `ORIGIN_MCP_INSTALL_MISSING`, default `1`
- `ORIGIN_MCP_BRIDGE_BACKGROUND`, default `0`

Existing MCP tools such as `origin_ping`, `origin_import_table`, and
`origin_plot_line` keep their original names and route through an
`OriginClient`-style bridge proxy. The bridge allowlist is tested against
`server.py` so new public client calls must be added deliberately. The explicit
`origin_bridge_*` tools remain as diagnostics and bridge controls.

## MCP Tools

Bridge-specific tools provide a small diagnostic and execution surface for
validating and managing the split-process design:

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
exec(open(r"D:\origin-mcp\examples\origin_bridge_addon.py", encoding="utf-8").read())
```

Then in another terminal:

```powershell
python examples\smoke_bridge.py --keep-origin-open
```

The smoke run creates a new project, imports `examples/sample_data.csv`, reads
worksheet rows, creates a line plot, exports a PNG, checks that the export looks
non-empty, and saves an OPJU project under the output directory.

## Current Limits

The first bridge implementation intentionally uses the Python standard library
and a single-request JSON-lines TCP protocol. It now includes a small task queue,
but does not yet provide streaming logs, hard cancellation of running Origin
calls, or a WebSocket transport. Those can be added after the bridge lifecycle is
validated against a real Origin installation.
