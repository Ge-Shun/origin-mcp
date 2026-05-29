# Tools and Compatibility

`origin-mcp` exposes MCP tools for Origin project management, worksheet editing,
plotting, graph formatting, analysis, export, and lifecycle control. By default
it uses a compact tool profile to reduce model tool-selection cost.

Tool failures return `ok=false`, a human-readable `message`, the Python
`error_type`, and a stable `error_code` such as `worksheet_not_found`,
`graph_not_found`, `file_not_found`, `path_not_allowed`,
`unsupported_origin_feature`, `unsupported_analysis_type`, or
`origin_dependency_unavailable`. Clients should branch on `error_code` instead
of parsing the message text.

## Tool Profiles

The default profile is `compact`, which registers a small set of high-level
tools (listed in `COMPACT_TOOL_NAMES` and reported by `origin_doctor`). It keeps
the common workflow surface small while preserving the specialized wrappers as
internal Python functions.

Set `ORIGIN_MCP_TOOL_PROFILE=full` before starting the MCP server to expose all
specialized worksheet, plotting, graph editing, analysis, and lifecycle tools.
The aliases `expert` and `all` behave the same as `full`.

## Default Compact Tools

The exact compact tool list is owned by `COMPACT_TOOL_NAMES` in
`src/origin_mcp/tools/_shared.py` and is reported by `origin_doctor`. The
searchable tool catalog is generated from tool module docstrings and is
available through the `mcp_tools` knowledge collection.

In compact mode, use `origin_query_knowledge` or `origin_browse_knowledge` to
discover the right high-level workflow instead of choosing from every
specialized wrapper.

## Knowledge Base Tools

`origin-mcp` includes a local, structured knowledge base modeled as searchable
and browsable collections. It is intentionally tool-addressable rather than only
README text, so an MCP client can discover the right workflow before calling
Origin.

General entry points are `origin_browse_knowledge` and
`origin_query_knowledge`. In full profile, collection-specific browse/query
helpers are also available, but the general tools are the stable default
surface.

Collections:

- `mcp_tools`: origin-mcp tools grouped by workflow, such as worksheet,
  plotting, graph editing, analysis, export, and lifecycle control. Tool entries
  are generated from `src/origin_mcp/tools/*.py` docstrings so the index tracks
  the current MCP surface.
- `reference`: Origin workflow notes, Plot Type ID entries, style modes,
  graph formatting behavior, chart routing, analysis adapters, and runtime
  compatibility notes.
- `python_api`: OriginPro Python API usage notes used by this project.
- `labtalk`: LabTalk and X-Function routes used by this project, including
  worksheet plotting, `plotxyz`, `plotm`, legend refresh, export fallbacks, and
  analysis X-Functions.
- `official_docs`: versioned official OriginLab documentation boundary map for
  Python, originpro API class pages, LabTalk command/function/object references,
  and X-Function category references.

The local knowledge base is a curated operational index. It does not copy the
entire OriginLab documentation set into this repository; entries that need exact
official syntax include `official_url`, `doc_family`, `doc_kind`, `versions`,
and `verified` metadata fields.

The official documentation boundary map has two layers: a hand-curated seed
index in `src/origin_mcp/knowledge.py` and an optional generated overlay at
`src/origin_mcp/official_docs.generated.json`. Refresh the overlay with:

```powershell
.\.venv\Scripts\python.exe scripts\update_official_docs_index.py
```

The crawler follows OriginLab documentation links, classifies LabTalk command
pages, X-Function pages, and originpro API class pages into stable browse paths,
then validates duplicate paths and required version metadata before writing the
JSON index.

Origin 2026 is the baseline index. Older supported versions use
`src/origin_mcp/official_docs.version_diffs.json`, which stores only `added`,
`removed`, and `changed` records for each version. At query time, origin-mcp
applies that delta in memory so `version="2024"` and `version="2025"` do not
require duplicate full indexes.

To compare two generated indexes for Origin version drift:

```powershell
.\.venv\Scripts\python.exe scripts\compare_official_docs_index.py old.json new.json --output diff.json
```

To build a compact version-diff overlay from separately generated version
indexes:

```powershell
.\.venv\Scripts\python.exe scripts\build_official_docs_version_diffs.py --base origin2026.json --version-index 2025 origin2025.json --version-index 2024 origin2024.json --output src\origin_mcp\official_docs.version_diffs.json
```

Browse calls use a path-like topic. Examples:

```json
{"collection": "reference", "topic": "plot-types/200"}
```

```json
{"api": "originpro.find_graph"}
```

Query calls return ranked entries with path, title, summary, keywords, metadata,
and score. Examples:

```json
{"query": "heatmap plot type id", "collection": "reference", "limit": 5}
```

```json
{"query": "legend font position", "limit": 3}
```

```json
{"collection": "official_docs", "topic": "labtalk/commands/display-control", "version": "2026"}
```

## Single Source of Truth

Avoid maintaining hand-written exhaustive tool lists in docs. Use these
knowledge queries instead:

```json
{"query": "worksheet tools", "collection": "mcp_tools", "limit": 10}
```

```json
{"query": "plotting recommended entry points", "collection": "reference", "limit": 5}
```

```json
{"query": "legend font position", "collection": "reference", "limit": 5}
```

```json
{"query": "analysis adapters include_output metrics", "collection": "reference", "limit": 5}
```

```json
{"query": "runtime compatibility embedded bridge", "collection": "reference", "limit": 5}
```

The implementation remains the source of truth for schemas and callable
functions. The knowledge base is the source of truth for searchable workflow
guidance, Plot Type ID entries, style modes, graph formatting behavior, analysis
adapter notes, runtime compatibility, and curated official documentation links.

See [origin-bridge.md](origin-bridge.md) for bridge startup and real-Origin
validation workflows. Use `origin_doctor` first for bridge issues.
