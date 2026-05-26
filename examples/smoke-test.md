# Origin Smoke Test

`origin-mcp-smoke` runs a real end-to-end Origin workflow through the same
`OriginClient` code used by the MCP server. Use it after installation, after
upgrading Origin, or after changing graph/worksheet tools.

The smoke test:

- connects to Origin/OriginPro
- creates a new project
- imports `examples/sample_data.csv`
- creates a line graph
- applies publication-style formatting
- adds a baseline reference line and graph label
- exports a PNG preview
- saves an OPJU project
- releases the Origin automation connection with `detach`

## Run

From an installed editable checkout:

```powershell
.\.venv\Scripts\origin-mcp-smoke.exe
```

Or through Python:

```powershell
.\.venv\Scripts\python.exe -m origin_mcp.smoke_test
```

If `origin-mcp-smoke.exe` is missing after updating the repository, rerun:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

By default, outputs are written to:

```text
D:\origin-mcp\output\smoke_test\
```

The command prints a JSON report containing each step, the exported preview path,
the saved project path, and any error details.

## Options

```powershell
.\.venv\Scripts\origin-mcp-smoke.exe `
  --data D:\origin-mcp\examples\sample_data.csv `
  --output-dir D:\origin-mcp\output\smoke_test `
  --project-path D:\origin-mcp\output\smoke_test\origin_mcp_smoke.opju
```

Useful flags:

- `--hide`: run Origin hidden when supported
- `--no-detach`: leave the automation connection attached for debugging

## Expected Result

A successful run returns `"ok": true` and creates:

- a PNG preview image
- `origin_mcp_smoke.opju`

If the run fails, check the printed `error_type`, `error`, and `steps` fields.
Common causes are missing `originpro`, incompatible Python/OriginExt versions,
an unavailable Origin license, or a previous automation session still attached to
Origin.
