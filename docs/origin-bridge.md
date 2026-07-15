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
import runpy; runpy.run_path(r"C:\path\to\origin-mcp\addon.py", run_name="__main__")
```

Replace `C:\path\to\origin-mcp` with the local checkout path.

### Windows path and LabTalk launch pitfalls

Prefer the Python Console snippet above for manual startup. It runs in pure
Python mode and uses a raw string for the Windows path, so `C:\Users\...` is
not parsed as a Python `\UXXXXXXXX` Unicode escape.

If you launch from Origin's LabTalk Command Window instead, keep the command
simple and use forward slashes for Windows paths that are passed into Python:

```labtalk
run -pyf "C:/path/to/origin-mcp/addon.py";
```

Avoid complex inline commands such as nested `Python -exec "exec(open(...))"`
strings at the LabTalk `>>` prompt. Origin's LabTalk parser can treat the text
as a worksheet formula before Python sees it, which may produce misleading
messages such as `Math cannot be performed on Text column`. When you need to
force Origin to read the current on-disk file during development, switch the
Command Window to Python mode first by entering `Python`, then run:

```python
exec(open(r"C:\path\to\origin-mcp\addon.py", encoding="utf-8").read())
```

Use this reload form only for development or troubleshooting. For normal use,
the Python Console launch snippet or the Origin MCP Bridge Start App is clearer
and less fragile.

`addon.py` does not hard-code the checkout directory. It first tries to import
an installed `origin_mcp` package from Origin's embedded Python. If that is not
available, it looks for a sibling `src\origin_mcp` directory next to `addon.py`.
`ORIGIN_MCP_SRC` is only a fallback for unusual launch setups.

The addon shows a Windows message box when the bridge is ready:

```text
Bridge is running inside Origin.
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

By default the addon attempts to install missing runtime packages into Origin's
embedded Python. If `originpro`, `pydantic`, `pandas`, `openpyxl`, or `xlrd` is
missing, the addon runs `pip install` for the missing requirements before starting the
bridge, adding `--user` automatically when Origin's global site-packages is not
writable. Set `ORIGIN_MCP_INSTALL_MISSING=0` immediately before the launch snippet
to disable automatic installation and fail fast instead. If automatic
installation fails, check network/proxy access or install the listed packages
into Origin's embedded Python manually. Search the knowledge base for
`bridge startup` to inspect the full environment variable list and startup
behavior.

Then run the MCP server from a separate terminal or MCP client. The MCP server
connects to the same host and port through `OriginBridgeProxy`.

The host is validated before binding and must be a loopback address such as
`127.0.0.1`, `::1`, or `localhost`. Broad bindings such as `0.0.0.0` are
rejected even when configured through `ORIGIN_MCP_BRIDGE_HOST`, because the
protocol is intended only for local-process control.

The easiest way to stop the foreground bridge is to ask your MCP assistant to
shut the Origin bridge down. That calls the `origin_bridge_shutdown` tool with:

```json
{"release_origin": true}
```

The request stops the Origin-side serve loop and, by default, asks the Origin
automation layer to close/release the embedded Origin automation session. No
extra terminal or console input is needed.

If you are not driving Origin through an assistant, double-click
`scripts\stop-bridge.cmd` (or run `python scripts\stop_bridge.py`) to send the
same shutdown request. Both honor the `ORIGIN_MCP_BRIDGE_HOST` / `PORT` /
`TOKEN` / `TIMEOUT` environment variables. The equivalent raw call is:

```powershell
python -c "from origin_mcp.bridge_client import request_bridge; print(request_bridge('shutdown', {'release_origin': True}))"
```

After the request succeeds, the Origin Python console should return to a prompt
and Origin can be closed normally. `Ctrl+C` is only a fallback because some
Origin embedded Python builds do not interrupt the cooperative serve loop
reliably.

### Embedded vs external Origin

`originpro` runs in *embedded* mode when it can import Origin's host API and
drives the Origin the bridge runs inside. When that API is unavailable (for
example Origin 2026 exposes it only as `_PyOrigin`, which the PyPI `originpro`
does not load), `originpro` falls back to *external* automation and **launches a
separate Origin process** for the actual data and plots. In that case the window
you started the bridge in only hosts the socket, and your worksheets/graphs
appear in the spawned Origin window instead.

To avoid leaking that spawned instance as an orphan (which can hit the Origin
license limit over repeated sessions), the bridge **closes the external Origin on
shutdown** even when `close_origin` is not requested. Embedded mode never
auto-closes the host Origin. Set `ORIGIN_MCP_KEEP_EXTERNAL=1` before launching
the bridge to keep the external instance running on shutdown instead.

No source directory needs to be edited in `addon.py`. If the file was copied
away from the checkout and `origin-mcp` is not installed in Origin's Python, set
`ORIGIN_MCP_SRC` to the checkout `src` directory before running the addon.

Use a token when multiple local tools may connect to the same machine:

```powershell
$env:ORIGIN_MCP_BRIDGE_TOKEN = "replace-with-a-local-secret"
```

## Bridge Log

The bridge writes one JSON-lines record per request (timestamp, request id,
method, duration, error code) to a rotating log file. The default location is
`%TEMP%\origin-mcp\bridge.log`. Override with `ORIGIN_MCP_LOG_FILE`, or set the
variable to `-` to disable file logging entirely. `origin_doctor` returns the
active log path and the last 20 entries in its `data.log` field, so MCP clients
can inspect recent failures without leaving the tool surface.

Existing tool functions keep their original names and route through an
`OriginClient`-style bridge proxy. The bridge allowlist is tested against
the tool modules so new public client calls must be added deliberately. Explicit
`origin_bridge_*` functions remain available as diagnostics and bridge controls,
with most of them exposed only in the full tool profile.

The MCP server registers a 25-tool compact profile by default. Select
`ORIGIN_MCP_TOOL_PROFILE=data`, `plot`, or `analysis` for a focused expanded
surface, `standard` for the previous curated surface, or `full` for every
specialized wrapper.

## MCP Tools

Bridge-specific tools provide diagnostics and a task surface for validating and
managing the split-process design. The exact callable catalog is generated from
`src/origin_mcp/tools/*.py` docstrings and can be searched through the knowledge
base instead of duplicated here:

```json
{"query": "bridge tools", "collection": "mcp_tools", "limit": 10}
```

```json
{"query": "bridge task status cancel list tasks", "collection": "mcp_tools", "limit": 10}
```

Use `origin_doctor` first for connection issues. Use compact task tools for
longer operations; expose the full bridge-specific wrapper set with
`ORIGIN_MCP_TOOL_PROFILE=full` only when an expert workflow needs it.

## Background Tasks

Use background tasks for operations that may take longer than a normal MCP tool
call. Search the knowledge base for `bridge tasks` to inspect task states,
cancellation behavior, and the current queue-management tools.

Submit a task:

```json
{
  "method": "run_labtalk",
  "params": {
    "script": "type -b \"long Origin operation\";"
  }
}
```

Then poll task status with the returned `task_id`.

Task status responses are lightweight by default: they include state,
timestamps, `progress`, `current_step`, and `cancel_requested`, plus the final
`result` or `error` when available. Recent task logs are omitted unless
requested:

```json
{
  "task_id": "returned-task-id",
  "include_logs": true,
  "log_limit": 20,
  "include_result": false
}
```

Use `include_result=false` while polling long-running tasks when the final
payload may be large. `list_tasks` always returns summaries without task logs or
results.

## Diagnostics

If a tool cannot connect to Origin, run `origin_doctor` before retrying the
workflow:

```json
{"ping_origin": true}
```

On Windows, `WinError 10061` usually means nothing is listening at the bridge
host and port yet: start `addon.py` inside Origin, then retry `origin_doctor`.

Search the knowledge base for `bridge diagnostics` when you need the canonical
troubleshooting checklist.

Before an MCP client is connected, the equivalent command-line checks are:

```powershell
origin-mcp status
origin-mcp doctor --ping-origin
```

Add `--json` for machine-readable output. The commands return `0` when healthy,
`1` when the bridge is not running, `2` when startup failed or the live Origin
check is degraded, and `3` when diagnostics could not be completed. The status
command only probes the local bridge; `doctor --ping-origin` may bring the
Origin window forward while checking automation.

## High-Level Bridge Workflows

The bridge can run file-to-figure workflows without `originpro` calls in the MCP
server process. Use `origin_doctor` for normal connectivity checks; reserve the
smoke script for optional end-to-end validation. Search the knowledge base for
`bridge file to figure` when an MCP client needs the workflow steps.

## Smoke Test

Use the smoke script only when you want deeper end-to-end validation after
changing the bridge, or when `origin_doctor` passes but plotting/export still
fails. It exercises the MCP tool layer rather than calling `OriginClient`
directly.

After starting the bridge as described above, run this in another terminal:

```powershell
python examples\smoke_bridge.py --keep-origin-open
```

The smoke run creates a new project, imports `examples/sample_data.csv`, reads
worksheet rows, creates a line plot, exports a PNG, checks that the export looks
non-empty, and saves an OPJU project under the output directory. It always writes
a structured JSON report, by default to `%TEMP%\origin-mcp-smoke\smoke-report.json`;
pass `--output-dir` or `--report` to choose deterministic paths. If the smoke
run fails, the report includes the failing step and `origin_doctor` output.

For a release-style manual gate, use the wrapper below after starting the bridge:

```powershell
python scripts\real_origin_smoke.py --keep-origin-open
```

The wrapper stores the PNG, OPJU, and report under `output\smoke\`. Treat the
gate as passed only when the command exits with status 0, `smoke-report.json`
has `"ok": true`, the export inspection has `"looks_nonempty": true`, and both
the PNG and OPJU paths in the report exist. The output directory is ignored by
git so release validation artifacts do not pollute the working tree.

To run all non-Origin release checks plus the real-Origin gate from one entry
point, use:

```powershell
python scripts\release_check.py --real-origin-smoke --keep-origin-open
```

The manual GitHub Actions workflow `.github/workflows/real-origin.yml` runs the
same checks on a Windows self-hosted runner labeled `origin`. The runner must
have Origin installed and its bridge running; an optional dispatch input adds
the file-to-figure smoke gate and uploads its report artifacts.

## Current Limits

The first bridge implementation intentionally uses the Python standard library
and a single-request JSON-lines TCP protocol. It now includes a small task queue,
lightweight task progress, bounded task retention, and optional recent task
logs. It does not yet provide live streaming logs, hard cancellation of running
Origin calls, or a WebSocket transport. Those can be added after the bridge
lifecycle is validated against a real Origin installation.
