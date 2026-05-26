# Origin Plot Matrix

Run the real-Origin plot regression matrix after `origin-mcp` is installed in an
Origin-compatible Python environment:

```powershell
origin-mcp-plot-matrix
```

or from the source checkout:

```powershell
python -m origin_mcp.plot_matrix
```

The command writes:

- `output/plot_matrix/plot_matrix_data.csv`
- `output/plot_matrix/exports/*.png`
- `output/plot_matrix/origin_mcp_plot_matrix.opju`
- `output/plot_matrix/report.json`
- `output/plot_matrix/report.md`

Each case is checked for more than file existence. The runner decodes PNG
exports when possible and flags near-blank images, tiny previews, missing graph
plots, and exact duplicate exports.

Use `--limit N` while developing, or `--only 200 201 243` to test selected
Origin Plot Type IDs. If no matrix range is provided, the runner creates a
sample Origin matrix sheet automatically for matrix-only plot types.

Example:

```powershell
python -m origin_mcp.plot_matrix --limit 10
```

Inside a running MCP server, use `origin_run_plot_matrix`. That tool runs the
same matrix inside the server process, which is useful when direct external
`OriginExt` automation from a CLI Python environment is unavailable.
