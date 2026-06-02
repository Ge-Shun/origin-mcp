from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .official_docs import (
    BASE_OFFICIAL_DOC_VERSION,
    load_generated_records,
    merge_records,
    records_for_version,
    validate_records,
)
from .official_docs import (
    OfficialDocRecord as OfficialDocPage,
)


@dataclass(frozen=True)
class KnowledgeEntry:
    collection: str
    path: str
    title: str
    summary: str
    body: str
    keywords: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self, include_body: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "collection": self.collection,
            "path": self.path,
            "title": self.title,
            "summary": self.summary,
            "keywords": list(self.keywords),
            "metadata": self.metadata,
        }
        if include_body:
            data["body"] = self.body
        return data


COLLECTIONS: dict[str, str] = {
    "mcp_tools": "origin-mcp tool catalog grouped by user workflow.",
    "reference": "Origin workflow reference notes, plot IDs, styles, chart routing, and analysis.",
    "python_api": "OriginPro Python API usage notes used by origin-mcp.",
    "labtalk": "LabTalk and X-Function command notes used by origin-mcp.",
    "official_docs": "Official OriginLab documentation entry points indexed for follow-up lookup.",
}


OFFICIAL_DOC_VERIFIED = "2026-05-28"


OFFICIAL_URLS = {
    "python": "https://docs.originlab.com/python/",
    "originpro_api": "https://docs.originlab.com/originpro/annotated.html",
    "labtalk_reference": "https://docs.originlab.com/labtalk/ref",
    "labtalk_commands": "https://docs.originlab.com/labtalk/ref/command-reference-by-category",
    "xfunction_reference": "https://docs.originlab.com/x-function/ref/",
    "xfunction_plotting": "https://docs.originlab.com/x-function/ref/plotting/",
}


TOOL_GROUP_SUMMARIES: dict[str, str] = {
    "knowledge": "Local knowledge-base discovery, browsing, and search tools.",
    "core": "Project, capability, and runtime inspection tools.",
    "worksheet": "Import, inspect, edit, and export Origin worksheet data.",
    "plotting": "Common plotting tools, chart routing, and Plot Type ID wrappers.",
    "graph_editing": "Graph inspection, styling, layout, labels, axes, legends, and QA tools.",
    "analysis": "Origin analysis wrappers and structured fit output helpers.",
    "export_lifecycle": (
        "Figure export, preview, image inspection, LabTalk execution, and Origin lifecycle tools."
    ),
}


REFERENCE_ENTRIES: tuple[KnowledgeEntry, ...] = (
    KnowledgeEntry(
        collection="reference",
        path="official-docs",
        title="Official OriginLab documentation map",
        summary="Stable entry points to OriginLab Python, LabTalk, X-Function, and originpro docs.",
        body=(
            "Use official_docs entries when a workflow requires exact official wording, a complete "
            "parameter table, or a command/API page beyond this curated local index."
        ),
        keywords=("official", "documentation", "originlab", "python", "labtalk", "x-function"),
        metadata={"source_collection": "official_docs"},
    ),
    KnowledgeEntry(
        collection="reference",
        path="plotting/workflow",
        title="Plotting workflow",
        summary=(
            "Import table data, choose a plotting route, format the graph, then export/inspect."
        ),
        body=(
            "In the default compact MCP tool profile, start with origin_recommend_chart when "
            "the chart type is unclear and origin_plot_auto when the assistant should inspect "
            "columns and create the graph. Use origin_plot_chart_atlas for semantic intents "
            "such as correlation, distribution, composition, matrix, image_plate, and "
            "time_series. Use origin_plot_table_id for a specific Origin Plot Type ID. "
            "Core direct wrappers such as origin_plot_line and origin_plot_scatter are "
            "available in the compact profile; specialized matrix/3D wrappers remain in "
            "the full/expert profile. Named table plotting calls are idempotent where Origin "
            "exposes an output graph layer target: when graph_name points to an existing graph, "
            "origin-mcp clears that page's plots and draws into the same graph instead of "
            "creating another GraphN page. If book_name is omitted, graph_name also anchors a "
            "stable data workbook named <graph_name>_Data. Unnamed calls still create fresh "
            "Origin objects. Worksheet-command Plot Type ID routes that do not expose an output "
            "graph target keep using Origin's native creation route and do not clear an "
            "existing graph."
        ),
        keywords=(
            "plot",
            "workflow",
            "compact",
            "profile",
            "template",
            "plot type id",
            "reuse graph",
            "idempotent",
            "graph_name",
        ),
    ),
    KnowledgeEntry(
        collection="reference",
        path="plotting/recommended-entrypoints",
        title="Recommended plotting entry points",
        summary="Compact-profile plotting tools to prefer before direct origin_plot_* wrappers.",
        body=(
            "Prefer origin_plot_auto for file-backed table data because it profiles columns, "
            "routes to a suitable chart, and can export the result. Use origin_recommend_chart "
            "when you only need a recommendation. Use origin_plot_chart_atlas when the user "
            "states a semantic intent rather than a chart type. Use origin_plot_table_id when "
            "the user gives a concrete Origin Plot Type ID or template route. Core direct "
            "wrappers like origin_plot_line, origin_plot_scatter, and origin_plot_column are "
            "also available in compact mode. Specialized matrix/3D wrappers are expert/"
            "full-profile tools."
        ),
        keywords=(
            "plot",
            "entrypoint",
            "compact",
            "origin_plot_auto",
            "origin_recommend_chart",
            "origin_plot_chart_atlas",
            "origin_plot_table_id",
        ),
        metadata={
            "compact_tools": [
                "origin_recommend_chart",
                "origin_plot_auto",
                "origin_plot_chart_atlas",
                "origin_plot_table_id",
                "origin_plot_line",
                "origin_plot_scatter",
                "origin_plot_line_symbol",
                "origin_plot_column",
            ],
            "expert_profile": "ORIGIN_MCP_TOOL_PROFILE=full",
        },
    ),
    KnowledgeEntry(
        collection="reference",
        path="tool-profiles",
        title="MCP tool profiles",
        summary=(
            "Default compact profile exposes high-level tools; full profile exposes all wrappers."
        ),
        body=(
            "origin-mcp defaults to ORIGIN_MCP_TOOL_PROFILE=compact, which exposes a small "
            "high-level tool surface for diagnostics, knowledge search, worksheet import/read/"
            "write, plotting, export, analysis, LabTalk, and bridge tasks. Set "
            "ORIGIN_MCP_TOOL_PROFILE=full, expert, or all before starting the MCP server to "
            "register every specialized worksheet, graph editing, analysis, and origin_plot_* "
            "wrapper. Functions remain in the Python module even when they are not registered "
            "as MCP tools in compact mode."
        ),
        keywords=("tool profile", "compact", "full", "expert", "origin_plot", "mcp tools"),
        metadata={
            "default_profile": "compact",
            "full_profile_env": "ORIGIN_MCP_TOOL_PROFILE=full",
        },
    ),
    KnowledgeEntry(
        collection="reference",
        path="documentation/sources-of-truth",
        title="Documentation sources of truth",
        summary="Where to keep canonical details instead of duplicating them across docs.",
        body=(
            "Keep exhaustive tool catalogs in the generated mcp_tools knowledge collection, "
            "not in README or docs pages. Keep plotting workflow guidance, Plot Type ID "
            "entries, style modes, graph formatting behavior, analysis adapters, runtime "
            "compatibility, and official documentation links in the reference knowledge "
            "collection. Keep bridge startup, smoke testing, and user-facing installation "
            "steps in docs/origin-bridge.md and README. Keep callable schemas in "
            "src/origin_mcp/tools/*.py and exact tool registration behavior in "
            "src/origin_mcp/tools/_shared.py plus src/origin_mcp/server.py."
        ),
        keywords=(
            "documentation",
            "source of truth",
            "dedupe",
            "knowledge",
            "mcp_tools",
            "reference",
        ),
        metadata={
            "tool_catalog": "mcp_tools knowledge collection",
            "workflow_guidance": "reference knowledge collection",
            "tool_registration": "src/origin_mcp/tools/_shared.py and src/origin_mcp/server.py",
            "bridge_user_docs": "docs/origin-bridge.md",
        },
    ),
    KnowledgeEntry(
        collection="reference",
        path="plotting/style-modes",
        title="Plot style modes",
        summary="Controls whether origin-mcp preserves Origin defaults or applies MCP presets.",
        body=(
            "style_mode='origin_default' lets Origin resolve the graph template and keeps Origin "
            "styling. The aliases 'template', 'theme', and 'none' also preserve Origin defaults. "
            "style_mode='nature' applies a Nature-style scientific preset with colorblind-safe "
            "colors, Arial-compatible typography, Nature line weights, short ticks, and QA "
            "diagnostics."
        ),
        keywords=("style_mode", "origin_default", "nature", "template"),
    ),
    KnowledgeEntry(
        collection="reference",
        path="graph/legend",
        title="Legend formatting",
        summary="origin_format_legend edits legend text, font, frame, and optional placement.",
        body=(
            "origin_format_legend does not move the legend unless position or explicit left/top "
            "coordinates are supplied. Named positions such as inside_upper_left place the legend "
            "inside the active layer. left/top values in the 0-100 range are treated as layer "
            "percentages unless coordinate_mode='page_pixel' is requested."
        ),
        keywords=("legend", "font", "position", "left", "top", "frame"),
    ),
    KnowledgeEntry(
        collection="reference",
        path="graph/axis",
        title="Axis formatting",
        summary="origin_set_axis controls axis scale, start/end, major tick step, and title.",
        body=(
            "Use origin_set_axis for x, y, x2, y2, z, or z2 axes. Axis titles are passed through "
            "the text normalizer, so common forms like CO_2, x_{max}, m^2, and H₂O render as "
            "Origin rich text when possible."
        ),
        keywords=("axis", "scale", "tick", "title", "subscript", "superscript"),
    ),
    KnowledgeEntry(
        collection="reference",
        path="graph/plot-style",
        title="Plot style editing",
        summary=(
            "origin_set_plot_style changes color, line width/style, bar/column gap, "
            "symbols, and transparency."
        ),
        body=(
            "Use plot_index for one plot or omit it to apply a style to all plots in a layer. "
            "Use layer_index for non-first layers; layer indexes are zero-based. Colors can "
            "be RGB tuples or Origin-compatible strings. Use bar_gap to control bar/column "
            "width through Origin's -vg gap setting; larger values make bars narrower. "
            "FigureSpec plot style entries can apply these same fields to supported plots. "
            "Symbol and line styles use Origin integer codes because those are what the "
            "automation layer accepts."
        ),
        keywords=(
            "line color",
            "line width",
            "layer_index",
            "bar gap",
            "column width",
            "symbol",
            "transparency",
            "plot_index",
        ),
    ),
    KnowledgeEntry(
        collection="reference",
        path="graph/text-formatting",
        title="Origin rich text normalization",
        summary="Common subscript and superscript notation is converted for Origin graph text.",
        body=(
            "Axis titles, graph labels, reference-line labels, and worksheet column label rows "
            "normalize common scientific notation. Supported examples include CO_2, x_{max}, "
            "m^2, E^{1/2}, H₂O, m⁻², <sub>2</sub>, and <sup>-1</sup>. Multi-letter identifiers "
            "such as sample_id are preserved unless braces explicitly request formatting."
        ),
        keywords=("rich text", "subscript", "superscript", "label", "unicode"),
    ),
    KnowledgeEntry(
        collection="reference",
        path="graph/page-layout",
        title="Graph page and layer layout",
        summary="origin_set_graph_page and origin_arrange_layers control page size and panels.",
        body=(
            "origin_set_graph_page updates graph page width, height, and placement. "
            "origin_arrange_layers arranges existing layers into row/column panel layouts with "
            "optional x/y gaps. Use these after plot creation for multi-panel figures."
        ),
        keywords=("page", "layout", "panel", "layers", "arrange"),
    ),
    KnowledgeEntry(
        collection="reference",
        path="graph/export-inspection",
        title="Export inspection",
        summary="Export tools can inspect PNG dimensions, blankness, content bounds, and hash.",
        body=(
            "When a plotting or export tool receives export_path, origin-mcp can inspect the "
            "exported file. PNG inspection reports dimensions, sampled pixel complexity, "
            "near-blank status, content bounds, and a hash so clients can validate that a figure "
            "was produced."
        ),
        keywords=("export", "png", "inspection", "blank", "dimensions", "hash"),
    ),
    KnowledgeEntry(
        collection="reference",
        path="worksheet/labels",
        title="Worksheet labels and designations",
        summary="Column labels and plot designations help Origin route data correctly.",
        body=(
            "Use origin_set_column_labels for Origin label rows such as Long Name, Units, and "
            "Comments. Use origin_set_column_designations with specs such as XYY or XY so Origin "
            "can interpret selected worksheet columns as X, Y, error, or other plot roles."
        ),
        keywords=("worksheet", "labels", "long name", "units", "designation", "XYY"),
    ),
    KnowledgeEntry(
        collection="reference",
        path="worksheet/transforms",
        title="Worksheet data transforms",
        summary="Reshape and clean worksheet data without hand-written LabTalk.",
        body=(
            "Use origin_filter_rows for structured row filters (column/op/value, combined "
            "with and/or), origin_drop_duplicates to remove duplicate rows, and "
            "origin_fill_missing to drop or fill missing values (drop_rows, drop_columns, "
            "value, ffill, bfill, mean, median). Reshape with origin_transpose_worksheet, "
            "origin_pivot_worksheet (long to wide with an aggregate), and "
            "origin_melt_worksheet (wide to long). Combine sheets with "
            "origin_merge_worksheets (database-style join on key columns) or "
            "origin_concat_worksheets (stack rows as a UNION, or place sheets side by side). "
            "Compute several new columns at once with origin_add_calculated_columns; its "
            "LabTalk formulas can reference other sheets with the [Book]Sheet!index form (for "
            "example '[Book2]Sheet1!2 * 2'), which covers cross-sheet column references; note "
            "that col(...) resolves against the active sheet, so use the column-index form to "
            "reach another sheet. Every "
            "transform writes in place by default; pass output_book or output_sheet to send "
            "the result to a new worksheet instead. Prefer these over origin_run_labtalk for "
            "routine data preparation."
        ),
        keywords=(
            "worksheet",
            "filter",
            "duplicates",
            "missing",
            "transpose",
            "pivot",
            "melt",
            "merge",
            "join",
            "concat",
            "union",
            "reshape",
            "calculated column",
            "cross-sheet",
        ),
    ),
    KnowledgeEntry(
        collection="reference",
        path="analysis/workflow",
        title="Analysis workflow",
        summary="Run named Origin analyses through origin_run_analysis, with results read back.",
        body=(
            "origin_run_analysis(analysis=..., worksheet=, x_col=, y_col=, options=...) is the "
            "single entry point for every named analysis and is the compact-profile tool; the "
            "specialized wrappers below also exist in the full profile (origin_query_knowledge "
            "finds them) but are not needed. Supported analysis names and their key options: "
            "polynomial_fit (order); smooth (method, points); descriptive_stats; differentiate; "
            "integrate; peak_find (smooth_points, direction, threshold); interpolate (method "
            "0=line 1=spline, num_points); normalize (method 1=range[0,1] 2=z-score 3=max, value); "
            "ttest_one_sample (mean, tail two|upper|lower, alpha); ttest_two_sample (mdiff, tail, "
            "alpha, equal 1|0); ttest_paired (mdiff, tail, alpha); fft and ifft (win, interval); "
            "correlation (pearson|spearman|kendall as 1/0, OriginPro only). The t-tests return "
            "Statistic/PValue/DF/confidence limits in the response metrics with no output sheet; "
            "fft/ifft/correlation write a multi-column result worksheet, so pass output_sheet and "
            "include_output=true to read it back. Two structured fits keep dedicated compact tools "
            "because their typed arguments are awkward as options: origin_linear_fit and "
            "origin_nonlinear_fit_structured (function, initial_params, fixed_params; see "
            "origin_list_fit_functions). For any analysis that produces an output worksheet, set "
            "output_sheet and include_output=true to get rows, parameters, metrics, and warnings."
        ),
        keywords=(
            "analysis",
            "fit",
            "smooth",
            "peak",
            "output",
            "metrics",
            "ttest",
            "t-test",
            "interpolate",
            "normalize",
            "statistics",
            "fft",
            "ifft",
            "fourier",
            "correlation",
            "corrcoef",
        ),
    ),
    KnowledgeEntry(
        collection="reference",
        path="compatibility/runtime",
        title="Runtime compatibility",
        summary="Origin 2026 plus its embedded Python bridge is the primary automation target.",
        body=(
            "Use origin_capabilities after starting the Origin GUI bridge. The preferred route "
            "is to run addon.py from Origin's embedded Python console, "
            "then let the MCP server connect to that local bridge. External Python with "
            "OriginExt/originpro is more sensitive to Python version and Origin lifecycle "
            "mismatches. "
            "Origin/OriginPro 2026 is the primary tested Origin target in this project."
        ),
        keywords=("compatibility", "python", "origin 2026", "originpro", "OriginExt"),
    ),
    KnowledgeEntry(
        collection="reference",
        path="bridge/startup",
        title="Origin GUI bridge startup",
        summary="Run addon.py inside Origin's embedded Python and let MCP connect over localhost.",
        body=(
            "Start the bridge from Origin's Python console by running addon.py from the checkout "
            "root or an installed package location. The addon auto-detects an installed "
            "origin_mcp package or an adjacent src/origin_mcp directory. It writes JSON status "
            "to origin-bridge.status.txt next to addon.py unless ORIGIN_MCP_BRIDGE_STATUS is "
            "set. Common environment variables are ORIGIN_MCP_BRIDGE_HOST, "
            "ORIGIN_MCP_BRIDGE_PORT, ORIGIN_MCP_BRIDGE_TOKEN, ORIGIN_MCP_BRIDGE_TIMEOUT, "
            "ORIGIN_MCP_BRIDGE_MAX_TASKS, ORIGIN_MCP_INSTALL_MISSING, "
            "ORIGIN_MCP_BRIDGE_BACKGROUND, and ORIGIN_MCP_SRC."
        ),
        keywords=("bridge", "addon", "startup", "status file", "environment variables"),
        metadata={
            "addon": "addon.py",
            "status_file_default": "origin-bridge.status.txt",
            "env": [
                "ORIGIN_MCP_BRIDGE_HOST",
                "ORIGIN_MCP_BRIDGE_PORT",
                "ORIGIN_MCP_BRIDGE_TOKEN",
                "ORIGIN_MCP_BRIDGE_TIMEOUT",
                "ORIGIN_MCP_BRIDGE_MAX_TASKS",
                "ORIGIN_MCP_INSTALL_MISSING",
                "ORIGIN_MCP_BRIDGE_BACKGROUND",
                "ORIGIN_MCP_BRIDGE_STATUS",
                "ORIGIN_MCP_SRC",
            ],
        },
    ),
    KnowledgeEntry(
        collection="reference",
        path="bridge/tasks",
        title="Bridge background tasks",
        summary="Submit long Origin operations to the bridge queue and poll task status.",
        body=(
            "Use origin_bridge_submit_task for long-running bridge methods, then poll "
            "origin_bridge_task_status with the returned task_id. Task states are queued, "
            "running, completed, failed, and cancelled. Cancellation is cooperative: queued "
            "tasks can be cancelled, while running Origin calls can only be marked "
            "cancel_requested because Python cannot safely terminate the active Origin "
            "automation call. The bridge keeps bounded task history controlled by "
            "ORIGIN_MCP_BRIDGE_MAX_TASKS."
        ),
        keywords=("bridge", "task", "queue", "cancel", "task_id", "taskable_methods"),
        metadata={
            "states": ["queued", "running", "completed", "failed", "cancelled"],
            "submit_tool": "origin_bridge_submit_task",
            "status_tool": "origin_bridge_task_status",
            "cancel_tool": "origin_bridge_cancel_task",
            "history_limit_env": "ORIGIN_MCP_BRIDGE_MAX_TASKS",
        },
    ),
    KnowledgeEntry(
        collection="reference",
        path="bridge/diagnostics",
        title="Bridge diagnostics",
        summary="Use origin_doctor and the addon status file before retrying failed Origin calls.",
        body=(
            "When a tool cannot connect to Origin, run origin_doctor first. It reports MCP-side "
            "bridge configuration, status file contents, bridge ping results, optional Origin "
            "ping results, compact/full tool profile configuration, and recommendations. Common "
            "fixes are starting addon.py inside Origin, matching host and port with the status "
            "file, checking ORIGIN_MCP_BRIDGE_TOKEN, or inspecting last_error when dependency "
            "import or installation failed."
        ),
        keywords=("bridge", "doctor", "diagnostics", "status file", "last_error", "token"),
        metadata={"primary_tool": "origin_doctor"},
    ),
    KnowledgeEntry(
        collection="reference",
        path="bridge/file-to-figure",
        title="Bridge file-to-figure workflow",
        summary=(
            "Validate Origin automation by importing a table, plotting it, exporting PNG, "
            "and saving OPJU."
        ),
        body=(
            "Use examples/smoke_bridge.py for the canonical real-Origin validation workflow. "
            "It checks bridge status, pings Origin, creates a new project, imports "
            "examples/sample_data.csv, reads worksheet rows, creates a line plot, exports a "
            "PNG, inspects that the export is non-empty, saves an OPJU project, and prints "
            "origin_doctor output on failure. For ad hoc long-running file-to-figure work, "
            "submit a bridge task and poll task status."
        ),
        keywords=("bridge", "smoke", "file to figure", "import", "plot", "export", "opju"),
        metadata={
            "script": "examples/smoke_bridge.py",
            "sample_data": "examples/sample_data.csv",
            "failure_diagnostic": "origin_doctor",
        },
    ),
)


OFFICIAL_DOC_PAGES: tuple[OfficialDocPage, ...] = (
    OfficialDocPage(
        path="python",
        title="OriginLab Python documentation",
        summary="Official overview of Embedded Python and External Python in Origin.",
        url=OFFICIAL_URLS["python"],
        doc_family="python",
        doc_kind="chapter",
        keywords=("official", "python", "embedded python", "external python", "originpro"),
        body=(
            "OriginLab's Python chapter is the root for choosing between Embedded Python inside "
            "Origin and External Python that controls Origin as a server application."
        ),
    ),
    OfficialDocPage(
        path="python/embedded-python",
        title="Embedded Python",
        summary="Official documentation for Python running inside Origin.",
        url="https://docs.originlab.com/python/run-python-in-origin/",
        doc_family="python",
        doc_kind="guide",
        keywords=("embedded python", "origin", "originpro", "packages"),
    ),
    OfficialDocPage(
        path="python/external-python",
        title="External Python",
        summary="Official documentation for controlling Origin from an external Python runtime.",
        url="https://docs.originlab.com/externalpython",
        doc_family="python",
        doc_kind="guide",
        keywords=("external python", "originpro", "server application", "automation"),
    ),
    OfficialDocPage(
        path="python/running-python-code",
        title="Running Python Code",
        summary="Official entry point for running Python code in Origin workflows.",
        url="https://docs.originlab.com/python/running_python_code/",
        doc_family="python",
        doc_kind="guide",
        keywords=("run python", "embedded", "script", "origin"),
    ),
    OfficialDocPage(
        path="python/code-samples",
        title="Python Code Samples",
        summary="Official Python examples for Origin workflows.",
        url="https://docs.originlab.com/python/examples",
        doc_family="python",
        doc_kind="examples",
        keywords=("python", "samples", "examples", "originpro"),
    ),
    OfficialDocPage(
        path="python/originpro-api",
        title="originpro API class list",
        summary="Official Doxygen-style class list for the originpro Python package.",
        url=OFFICIAL_URLS["originpro_api"],
        doc_family="originpro_api",
        doc_kind="class_index",
        keywords=("originpro", "api", "class list", "LinearFit", "NLFit", "WBook", "WSheet"),
        body=(
            "The class list is the official map for originpro automation classes. Use the "
            "class-specific children under this path before relying on inferred method names."
        ),
    ),
    OfficialDocPage(
        path="python/originpro-api/analysis/LinearFit",
        title="originpro.analysis.LinearFit",
        summary="Official class page for linear fitting through Origin's fitting engine.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1analysis_1_1LinearFit.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "analysis", "LinearFit", "set_data", "result", "report"),
    ),
    OfficialDocPage(
        path="python/originpro-api/analysis/NLFit",
        title="originpro.analysis.NLFit",
        summary="Official class page for nonlinear fitting through Origin's fitting engine.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1analysis_1_1NLFit.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "analysis", "NLFit", "nonlinear", "fitting"),
    ),
    OfficialDocPage(
        path="python/originpro-api/graph/Axis",
        title="originpro.graph.Axis",
        summary="Official class page for graph axis scale, limits, step, and title APIs.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1graph_1_1Axis.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "graph", "Axis", "scale", "limits", "title"),
    ),
    OfficialDocPage(
        path="python/originpro-api/graph/GLayer",
        title="originpro.graph.GLayer",
        summary="Official class page for graph layer APIs.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1graph_1_1GLayer.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "graph", "GLayer", "layer", "plot"),
    ),
    OfficialDocPage(
        path="python/originpro-api/graph/GPage",
        title="originpro.graph.GPage",
        summary="Official class page for graph page APIs.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1graph_1_1GPage.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "graph", "GPage", "page", "export"),
    ),
    OfficialDocPage(
        path="python/originpro-api/graph/Plot",
        title="originpro.graph.Plot",
        summary="Official class page for data plot APIs.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1graph_1_1Plot.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "graph", "Plot", "data plot", "style"),
    ),
    OfficialDocPage(
        path="python/originpro-api/worksheet/WBook",
        title="originpro.worksheet.WBook",
        summary="Official class page for workbook APIs.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1worksheet_1_1WBook.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "worksheet", "WBook", "workbook", "add_sheet"),
    ),
    OfficialDocPage(
        path="python/originpro-api/worksheet/WSheet",
        title="originpro.worksheet.WSheet",
        summary="Official class page for worksheet APIs.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1worksheet_1_1WSheet.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "worksheet", "WSheet", "columns", "data"),
    ),
    OfficialDocPage(
        path="python/originpro-api/matrix/MBook",
        title="originpro.matrix.MBook",
        summary="Official class page for matrix book APIs.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1matrix_1_1MBook.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "matrix", "MBook", "matrix book"),
    ),
    OfficialDocPage(
        path="python/originpro-api/matrix/MSheet",
        title="originpro.matrix.MSheet",
        summary="Official class page for matrix sheet APIs.",
        url="https://docs.originlab.com/originpro/classoriginpro_1_1matrix_1_1MSheet.html",
        doc_family="originpro_api",
        doc_kind="class",
        keywords=("originpro", "matrix", "MSheet", "matrix sheet"),
    ),
    OfficialDocPage(
        path="labtalk",
        title="LabTalk language reference",
        summary=(
            "Official LabTalk reference for commands, functions, macros, objects, and variables."
        ),
        url=OFFICIAL_URLS["labtalk_reference"],
        doc_family="labtalk",
        doc_kind="chapter",
        keywords=("labtalk", "official", "commands", "functions", "objects", "variables"),
    ),
    OfficialDocPage(
        path="labtalk/commands",
        title="LabTalk command reference by category",
        summary="Official command categories for LabTalk scripts.",
        url=OFFICIAL_URLS["labtalk_commands"],
        doc_family="labtalk",
        doc_kind="category_index",
        keywords=("labtalk", "command reference", "category", "script"),
        body=(
            "The command category page is the boundary map for LabTalk command families. Browse "
            "children to select a category before issuing or composing LabTalk."
        ),
    ),
    OfficialDocPage(
        path="labtalk/command-reference",
        title="LabTalk command reference by category",
        summary="Compatibility path for the official LabTalk command category index.",
        url=OFFICIAL_URLS["labtalk_commands"],
        doc_family="labtalk",
        doc_kind="category_index",
        keywords=("labtalk", "command reference", "category", "script", "commands"),
        body=(
            "This path preserves the earlier origin-mcp official_docs topic name. Prefer "
            "labtalk/commands for category browsing."
        ),
    ),
    OfficialDocPage(
        path="labtalk/commands/data-manipulation-and-calculation",
        title="Data Manipulation and Calculation commands",
        summary="Official category for commands that change data or run calculations.",
        url="https://docs.originlab.com/labtalk/ref/data-manipulation-and-calculation",
        doc_family="labtalk",
        doc_kind="command_category",
        keywords=("labtalk", "data", "calculation", "average", "integrate", "sort", "plot"),
    ),
    OfficialDocPage(
        path="labtalk/commands/display-control",
        title="Display Control commands",
        summary="Official category for graph windows, axes, layers, labels, legends, and pages.",
        url="https://docs.originlab.com/labtalk/ref/display-control",
        doc_family="labtalk",
        doc_kind="command_category",
        keywords=("labtalk", "display", "axis", "legend", "layer", "page", "window"),
    ),
    OfficialDocPage(
        path="labtalk/commands/project-management",
        title="Project Management commands",
        summary="Official category for managing Origin projects and windows.",
        url="https://docs.originlab.com/labtalk/ref/project-management",
        doc_family="labtalk",
        doc_kind="command_category",
        keywords=("labtalk", "project", "window", "save", "rename", "delete"),
    ),
    OfficialDocPage(
        path="labtalk/commands/control-flow",
        title="Control Flow commands",
        summary="Official category for LabTalk script sequencing.",
        url="https://docs.originlab.com/labtalk/ref/control-flow",
        doc_family="labtalk",
        doc_kind="command_category",
        keywords=("labtalk", "control flow", "script", "loop", "condition"),
    ),
    OfficialDocPage(
        path="labtalk/commands/input-and-output",
        title="Input and Output commands",
        summary="Official category for file, system, and user I/O commands.",
        url="https://docs.originlab.com/labtalk/ref/input-and-output",
        doc_family="labtalk",
        doc_kind="command_category",
        keywords=("labtalk", "input", "output", "file", "system"),
    ),
    OfficialDocPage(
        path="labtalk/commands/script-management",
        title="Script Management commands",
        summary="Official category for scripts, macros, and menus.",
        url="https://docs.originlab.com/labtalk/ref/script-management",
        doc_family="labtalk",
        doc_kind="command_category",
        keywords=("labtalk", "script", "macro", "menu"),
    ),
    OfficialDocPage(
        path="labtalk/commands/external-access",
        title="External Access commands",
        summary="Official category for external DLL and DDE-style access.",
        url="https://docs.originlab.com/labtalk/ref/external-access",
        doc_family="labtalk",
        doc_kind="command_category",
        keywords=("labtalk", "external", "dll", "dde"),
    ),
    OfficialDocPage(
        path="labtalk/commands/time",
        title="Time commands",
        summary="Official category for timer operations and repeated scheduled scripts.",
        url="https://docs.originlab.com/labtalk/ref/time",
        doc_family="labtalk",
        doc_kind="command_category",
        keywords=("labtalk", "time", "timer", "schedule"),
    ),
    OfficialDocPage(
        path="labtalk/functions",
        title="LabTalk function reference",
        summary="Official function reference grouped by function category.",
        url="https://docs.originlab.com/labtalk/ref/function-reference",
        doc_family="labtalk",
        doc_kind="function_index",
        keywords=("labtalk", "functions", "statistics", "signal processing", "text"),
    ),
    OfficialDocPage(
        path="labtalk/objects",
        title="LabTalk object reference",
        summary="Official reference for LabTalk objects, properties, and methods.",
        url="https://docs.originlab.com/labtalk/ref/object-reference",
        doc_family="labtalk",
        doc_kind="object_index",
        keywords=("labtalk", "objects", "properties", "methods", "page", "wks", "layer"),
    ),
    OfficialDocPage(
        path="x-function",
        title="X-Function reference",
        summary="Official category index for Origin X-Functions.",
        url=OFFICIAL_URLS["xfunction_reference"],
        doc_family="x_function",
        doc_kind="category_index",
        keywords=("x-function", "official", "fitting", "plotting", "statistics"),
    ),
    OfficialDocPage(
        path="x-function/data-exploration",
        title="Data Exploration X-Functions",
        summary="Official X-Function category for data exploration tools.",
        url="https://docs.originlab.com/x-function/ref/data-exploration/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "data exploration", "explore"),
    ),
    OfficialDocPage(
        path="x-function/data-manipulation",
        title="Data Manipulation X-Functions",
        summary="Official X-Function category for data manipulation tools.",
        url="https://docs.originlab.com/x-function/ref/data-manipulation/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "data manipulation", "worksheet", "transform"),
    ),
    OfficialDocPage(
        path="x-function/database-access",
        title="Database Access X-Functions",
        summary="Official X-Function category for database access.",
        url="https://docs.originlab.com/x-function/ref/database-access/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "database", "access"),
    ),
    OfficialDocPage(
        path="x-function/fitting",
        title="Fitting X-Functions",
        summary="Official X-Function category for fitting tools.",
        url="https://docs.originlab.com/x-function/ref/fitting/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "fitting", "fitlr", "fitpoly", "nlfit"),
    ),
    OfficialDocPage(
        path="x-function/graph-manipulation",
        title="Graph Manipulation X-Functions",
        summary="Official X-Function category for graph manipulation.",
        url="https://docs.originlab.com/x-function/ref/graph-manipulation/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "graph", "manipulation", "legend", "layer"),
    ),
    OfficialDocPage(
        path="x-function/image",
        title="Image X-Functions",
        summary="Official X-Function category for image operations.",
        url="https://docs.originlab.com/x-function/ref/image/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "image", "import", "export"),
    ),
    OfficialDocPage(
        path="x-function/import-and-export",
        title="Import and Export X-Functions",
        summary="Official X-Function category for import and export workflows.",
        url="https://docs.originlab.com/x-function/ref/import-and-export/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "import", "export", "file", "data connector"),
    ),
    OfficialDocPage(
        path="x-function/mathematics",
        title="Mathematics X-Functions",
        summary="Official X-Function category for mathematical operations.",
        url="https://docs.originlab.com/x-function/ref/mathematics/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "mathematics", "math"),
    ),
    OfficialDocPage(
        path="x-function/miscellaneous",
        title="Miscellaneous X-Functions",
        summary="Official X-Function category for miscellaneous operations.",
        url="https://docs.originlab.com/x-function/ref/miscellaneous/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "miscellaneous"),
    ),
    OfficialDocPage(
        path="x-function/plotting",
        title="Plotting X-Functions",
        summary="Official Origin plotting X-Function category.",
        url=OFFICIAL_URLS["xfunction_plotting"],
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "plotting", "plotm", "plotxy", "plotxyz", "plotvm"),
        body=(
            "The plotting category is the official boundary for X-Functions such as plotm, "
            "plotmatrix, plotms, plotvm, plotxy, plotxyz, plot_prob, and plot_windrose."
        ),
    ),
    OfficialDocPage(
        path="x-function/signal-processing",
        title="Signal Processing X-Functions",
        summary="Official X-Function category for signal processing tools.",
        url="https://docs.originlab.com/x-function/ref/signal-processing/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "signal processing", "smooth", "filter", "peak"),
    ),
    OfficialDocPage(
        path="x-function/spectroscopy",
        title="Spectroscopy X-Functions",
        summary="Official X-Function category for spectroscopy tools.",
        url="https://docs.originlab.com/x-function/ref/spectroscopy/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "spectroscopy"),
    ),
    OfficialDocPage(
        path="x-function/statistics",
        title="Statistics X-Functions",
        summary="Official X-Function category for statistics tools.",
        url="https://docs.originlab.com/x-function/ref/statistics/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "statistics", "moments", "summary"),
    ),
    OfficialDocPage(
        path="x-function/utilities",
        title="Utilities X-Functions",
        summary="Official X-Function category for utility functions.",
        url="https://docs.originlab.com/x-function/ref/utilities/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "utilities"),
    ),
    OfficialDocPage(
        path="x-function/vision",
        title="Vision X-Functions",
        summary="Official X-Function category for vision tools.",
        url="https://docs.originlab.com/x-function/ref/vision/",
        doc_family="x_function",
        doc_kind="xfunction_category",
        keywords=("x-function", "vision"),
    ),
    OfficialDocPage(
        path="x-function/function-details",
        title="Function Details",
        summary="Official X-Function details index.",
        url="https://docs.originlab.com/x-function/ref/function-details/",
        doc_family="x_function",
        doc_kind="detail_index",
        keywords=("x-function", "function details", "parameters"),
    ),
    OfficialDocPage(
        path="x-function/alphabetic-list",
        title="Alphabetic List to X-Functions",
        summary="Official alphabetic X-Function lookup.",
        url="https://docs.originlab.com/x-function/ref/function-list",
        doc_family="x_function",
        doc_kind="alphabetic_index",
        keywords=("x-function", "alphabetic", "lookup"),
    ),
)


def _official_doc_pages(version: str | None = None) -> list[OfficialDocPage]:
    pages = merge_records(list(OFFICIAL_DOC_PAGES), load_generated_records())
    validate_records(pages)
    return records_for_version(pages, version)


def _official_doc_entries(version: str | None = None) -> list[KnowledgeEntry]:
    return [
        KnowledgeEntry(
            collection="official_docs",
            path=page.path,
            title=page.title,
            summary=page.summary,
            body=page.body
            or (
                f"{page.title} is an OriginLab official documentation page. Use this entry as "
                "the upstream boundary before generating LabTalk, X-Function, or originpro API "
                "syntax that is not already covered by a higher-level origin-mcp wrapper."
            ),
            keywords=("official", page.doc_family, page.doc_kind, *page.keywords),
            metadata={
                "source": "OriginLab official documentation",
                "doc_family": page.doc_family,
                "doc_kind": page.doc_kind,
                "url": page.url,
                "official_url": page.url,
                "versions": list(page.versions),
                "base_version": BASE_OFFICIAL_DOC_VERSION,
                "version_status": page.version_status or "baseline",
                "locale": page.locale,
                "verified": OFFICIAL_DOC_VERIFIED,
            },
        )
        for page in _official_doc_pages(version)
    ]


OFFICIAL_DOC_ENTRIES: tuple[KnowledgeEntry, ...] = tuple(_official_doc_entries())


PYTHON_API_ENTRIES: tuple[KnowledgeEntry, ...] = (
    KnowledgeEntry(
        collection="python_api",
        path="originpro",
        title="originpro package",
        summary="OriginLab's Python automation package used by origin-mcp.",
        body=(
            "origin-mcp prefers official originpro APIs when they are available and falls back "
            "to LabTalk commands for operations that are not exposed cleanly through originpro."
        ),
        keywords=("originpro", "automation", "python"),
    ),
    KnowledgeEntry(
        collection="python_api",
        path="originpro.new",
        title="originpro.new",
        summary="Create new Origin objects such as workbooks and graph pages.",
        body=(
            "origin-mcp uses object creation helpers to create workbooks, matrices, and graph "
            "pages before writing data or plotting. Actual support depends on the installed "
            "originpro and Origin versions."
        ),
        keywords=("new", "workbook", "graph", "matrix"),
    ),
    KnowledgeEntry(
        collection="python_api",
        path="originpro.find_sheet",
        title="originpro.find_sheet",
        summary="Resolve an Origin worksheet by book/sheet reference.",
        body=(
            "Worksheet lookup is used by read, write, append, plot, and analysis tools. "
            "origin-mcp also validates missing worksheet cases and returns stable "
            "worksheet_not_found errors."
        ),
        keywords=("worksheet", "sheet", "find", "lookup"),
    ),
    KnowledgeEntry(
        collection="python_api",
        path="originpro.find_graph",
        title="originpro.find_graph",
        summary="Resolve graph pages for formatting, export, and layer inspection.",
        body=(
            "Graph lookup accepts Origin page names and origin-mcp aliases. The project records "
            "requested graph names when Origin assigns a different short page name."
        ),
        keywords=("graph", "page", "find", "alias"),
    ),
    KnowledgeEntry(
        collection="python_api",
        path="originpro.oext",
        title="originpro.oext",
        summary="External Origin automation lifecycle.",
        body=(
            "origin-mcp now routes MCP tools through the Origin GUI bridge by default. The "
            "underlying client still uses originpro lifecycle APIs where available, so tools "
            "such as origin_detach, origin_quit, and origin_force_quit release or close the "
            "automation connection from inside the bridge."
        ),
        keywords=("OriginExt", "external", "detach", "quit", "bridge"),
    ),
    KnowledgeEntry(
        collection="python_api",
        path="originpro.LinearFit",
        title="originpro.LinearFit",
        summary="Structured linear fitting helper used when available.",
        body=(
            "origin_linear_fit uses originpro.LinearFit when x_col and y_col are supplied and the "
            "runtime supports it. The response normalizes result sections, parameters, and metrics "
            "where possible."
        ),
        keywords=("linear fit", "fit", "parameters", "RSquare"),
    ),
)


ORIGINPRO_CLASS_INDEX: tuple[tuple[str, str, str], ...] = (
    ("originpro.analysis.LinearFit", "Structured linear fitting helper.", "analysis fit linear"),
    ("originpro.analysis.NLFit", "Structured nonlinear fitting helper.", "analysis fit nonlinear"),
    ("originpro.base.BaseLayer", "Base class for layer-like Origin objects.", "base layer"),
    ("originpro.base.BaseObject", "Base class for wrapped Origin objects.", "base object"),
    ("originpro.base.BasePage", "Base class for page-like Origin objects.", "base page"),
    ("originpro.base.DBook", "Base data book abstraction.", "data book workbook matrix"),
    ("originpro.base.DSheet", "Base data sheet abstraction.", "data sheet worksheet matrix"),
    ("originpro.base.GObject", "Graph object wrapper.", "graph object label line"),
    ("originpro.base.Label", "Graph text label wrapper.", "label text graph"),
    ("originpro.base.Line", "Graph line object wrapper.", "line object graph"),
    ("originpro.config.APP", "Origin application configuration surface.", "config app"),
    ("originpro.dc.Connector", "Origin Data Connector helper.", "data connector import"),
    ("originpro.graph.Axis", "Graph axis wrapper.", "axis graph scale ticks"),
    ("originpro.graph.GLayer", "Graph layer wrapper.", "graph layer plots"),
    ("originpro.graph.GPage", "Graph page wrapper.", "graph page export"),
    ("originpro.graph.Plot", "Data plot wrapper.", "plot graph style data"),
    ("originpro.image.IPage", "Image page wrapper.", "image page"),
    ("originpro.matrix.MBook", "Matrix book wrapper.", "matrix book"),
    ("originpro.matrix.MSheet", "Matrix sheet wrapper.", "matrix sheet"),
    ("originpro.notes.Notes", "Origin notes window wrapper.", "notes"),
    ("originpro.pe.Folder", "Project Explorer folder wrapper.", "project folder"),
    ("originpro.worksheet.WBook", "Workbook wrapper.", "workbook worksheet"),
    ("originpro.worksheet.WSheet", "Worksheet wrapper.", "worksheet columns data"),
)


def _originpro_class_entries() -> list[KnowledgeEntry]:
    entries = [
        KnowledgeEntry(
            collection="python_api",
            path="originpro/classes",
            title="originpro class index",
            summary="Official originpro class names relevant to Origin automation.",
            body=(
                "This index mirrors the high-level class list from the official originpro API "
                "documentation and links those classes to origin-mcp workflows."
            ),
            keywords=("originpro", "classes", "api", "official"),
            metadata={"official_url": OFFICIAL_URLS["originpro_api"]},
        )
    ]
    for path, summary, keyword_text in ORIGINPRO_CLASS_INDEX:
        entries.append(
            KnowledgeEntry(
                collection="python_api",
                path=path,
                title=path.rsplit(".", 1)[-1],
                summary=summary,
                body=(
                    f"{path} is listed in the official originpro API class list. {summary} "
                    "Use the official API page for complete methods and parameters."
                ),
                keywords=(
                    "originpro",
                    *path.lower().replace(".", " ").split(),
                    *keyword_text.split(),
                ),
                metadata={"official_url": OFFICIAL_URLS["originpro_api"]},
            )
        )
    return entries


LABTALK_ENTRIES: tuple[KnowledgeEntry, ...] = (
    KnowledgeEntry(
        collection="labtalk",
        path="commands",
        title="LabTalk command categories",
        summary="Official LabTalk command categories indexed for origin-mcp workflows.",
        body=(
            "The official LabTalk command reference is organized by category. origin-mcp indexes "
            "the categories and the commands most relevant to data, display, project, and script "
            "automation."
        ),
        keywords=("labtalk", "commands", "categories", "official"),
        metadata={"official_url": OFFICIAL_URLS["labtalk_commands"]},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="commands/data-manipulation-and-calculation",
        title="Data Manipulation and Calculation commands",
        summary="Commands for changing datasets, calculations, sorting, fitting, and worksheets.",
        body=(
            "Official commands in this category include average, copy, create, delete, derivative, "
            "edit, integrate, limit, lr, mark, math, matrix, nlsf, plot, sort, and undo. "
            "origin-mcp uses modern X-Function routes for most analysis but keeps these commands "
            "indexed because legacy scripts and user examples often refer to them."
        ),
        keywords=(
            "average",
            "copy",
            "create",
            "delete",
            "derivative",
            "integrate",
            "lr",
            "math",
            "matrix",
            "nlsf",
            "sort",
        ),
        metadata={
            "official_url": (
                "https://docs.originlab.com/labtalk/ref/data-manipulation-and-calculation/"
            )
        },
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="commands/display-control",
        title="Display Control commands",
        summary="Commands for graph windows, axes, layers, labels, legends, pages, and plots.",
        body=(
            "Official commands in this category include axis, document -t, dotoolbox, draw, edit, "
            "get, label, layer, legend, page, plot, select, set, type, undo, window, and "
            "worksheet. These are the command families most relevant to origin-mcp graph editing "
            "and export fallbacks."
        ),
        keywords=(
            "axis",
            "draw",
            "label",
            "layer",
            "legend",
            "page",
            "plot",
            "set",
            "window",
            "worksheet",
        ),
        metadata={"official_url": "https://docs.originlab.com/labtalk/ref/display-control/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="commands/project-management",
        title="Project Management commands",
        summary="Commands for managing Origin projects, windows, and project contents.",
        body=(
            "Use the official Project Management category for exact syntax when automating Origin "
            "window/project state through LabTalk. origin-mcp exposes safer MCP wrappers for "
            "common project open/save/list/rename/delete operations."
        ),
        keywords=("project", "window", "list", "rename", "delete", "save"),
        metadata={"official_url": "https://docs.originlab.com/labtalk/ref/project-management/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="commands/control-flow",
        title="Control Flow commands",
        summary="Commands that affect LabTalk script sequencing.",
        body=(
            "Use the official Control Flow category for script-level sequencing syntax. "
            "origin-mcp usually exposes a single high-level tool call instead of multi-step "
            "LabTalk control flow."
        ),
        keywords=("control flow", "script", "sequencing", "loop", "condition"),
        metadata={"official_url": "https://docs.originlab.com/labtalk/ref/control-flow/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="commands/input-and-output",
        title="Input and Output commands",
        summary="Commands that interact with the user, system, and files.",
        body=(
            "Use the official Input and Output category for precise command syntax around file, "
            "system, and user interaction. origin-mcp uses Python-side path validation and "
            "structured tool responses before issuing Origin commands."
        ),
        keywords=("input", "output", "file", "system", "user"),
        metadata={"official_url": "https://docs.originlab.com/labtalk/ref/input-and-output/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="commands/script-management",
        title="Script Management commands",
        summary="Commands for scripts, macros, and menus.",
        body=(
            "Use the official Script Management category for exact syntax involving LabTalk script "
            "files, macros, and menu customization."
        ),
        keywords=("script", "macro", "menu", "labtalk"),
        metadata={"official_url": "https://docs.originlab.com/labtalk/ref/script-management/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="commands/external-access",
        title="External Access commands",
        summary="Commands for external DLLs and DDE-style integration.",
        body=(
            "External Access commands are primarily relevant to advanced legacy automation. "
            "origin-mcp normally uses Python originpro/OriginExt instead."
        ),
        keywords=("external", "dll", "dde", "automation"),
        metadata={"official_url": "https://docs.originlab.com/labtalk/ref/external-access/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="commands/time",
        title="Time commands",
        summary="Timer-related and repeated scheduled LabTalk scripts.",
        body=(
            "Time commands are used for timer operations and repeated scheduled scripts in "
            "LabTalk. origin-mcp does not currently expose timer scheduling wrappers."
        ),
        keywords=("time", "timer", "schedule", "repeated"),
        metadata={"official_url": "https://docs.originlab.com/labtalk/ref/time/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="plotting/worksheet-p",
        title="worksheet -p",
        summary="LabTalk route used for several worksheet Plot Type ID templates.",
        body=(
            "origin-mcp uses worksheet -p for worksheet plot types that require a contiguous "
            "selected range and a template. Prefer named MCP wrappers when available; use "
            "origin_plot_table_id for direct Plot Type ID routing."
        ),
        keywords=("worksheet -p", "plot type id", "template", "range"),
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="plotting/plotxyz",
        title="plotxyz",
        summary="LabTalk/X-Function route for XYZ and specialized worksheet plots.",
        body=(
            "origin-mcp uses plotxyz for XYZ-driven plot types such as 3D scatter, surface, "
            "contour, heatmap-style routes, ternary contour, and vector-like layouts when the "
            "data layout matches the selected Plot Type ID."
        ),
        keywords=("plotxyz", "xyz", "3d", "contour", "heatmap", "vector"),
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="plotting/plotm",
        title="plotm",
        summary="LabTalk route for matrix-based Plot Type ID templates.",
        body=(
            "origin_plot_matrix_id uses matrix ranges and plotm when creating matrix-based 3D "
            "surface, 3D scatter, heatmap, contour, and image routes."
        ),
        keywords=("plotm", "matrix", "heatmap", "surface", "image"),
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="graph/legend-r",
        title="legend -r",
        summary="Refresh graph legends after plotting or data changes.",
        body=(
            "origin-mcp refreshes or formats legends through LabTalk-compatible graph object "
            "operations where needed. Use origin_format_legend for the MCP-level interface."
        ),
        keywords=("legend", "refresh", "graph"),
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="graph/page-f",
        title="page -F",
        summary="Graph page export command used by export fallbacks.",
        body=(
            "origin-mcp prefers official export APIs when available and can fall back to LabTalk "
            "page export commands depending on runtime capability."
        ),
        keywords=("page -F", "export", "png", "pdf"),
    ),
)


XFUNCTION_ENTRIES: tuple[KnowledgeEntry, ...] = (
    KnowledgeEntry(
        collection="labtalk",
        path="x-functions",
        title="X-Function categories",
        summary="Official Origin X-Function categories indexed for tool routing.",
        body=(
            "Origin's official X-Function reference is organized into Data Exploration, Data "
            "Manipulation, Database Access, Fitting, Graph Manipulation, Image, Import and Export, "
            "Mathematics, Miscellaneous, Plotting, Signal Processing, Spectroscopy, Statistics, "
            "Utilities, Vision, Function Details, and an alphabetic list."
        ),
        keywords=("x-function", "categories", "fitting", "plotting", "statistics"),
        metadata={"official_url": OFFICIAL_URLS["xfunction_reference"]},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="x-functions/fitting",
        title="Fitting X-Functions",
        summary="Official fitting X-Function category used by fit adapters.",
        body=(
            "origin-mcp maps linear_fit to fitlr, polynomial_fit to fitpoly, nonlinear_fit to "
            "nlfit, and can use originpro.LinearFit for structured linear fits when available. "
            "Use official docs for exact option tables."
        ),
        keywords=("fitting", "fitlr", "fitpoly", "nlfit", "linear", "polynomial"),
        metadata={"official_url": "https://docs.originlab.com/x-function/ref/fitting/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="x-functions/plotting",
        title="Plotting X-Functions",
        summary="Official plotting X-Functions including plotm and plotxyz.",
        body=(
            "The official plotting category includes plotm, plotmatrix, plotms, plotvm, plotxy, "
            "plotxyz, plot_prob, plot_windrose, and other specialized plotting functions. "
            "origin-mcp uses plotxyz and plotm in Plot Type ID helpers."
        ),
        keywords=("plotting", "plotm", "plotxy", "plotxyz", "plotvm", "plotmatrix"),
        metadata={"official_url": OFFICIAL_URLS["xfunction_plotting"]},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="x-functions/statistics",
        title="Statistics X-Functions",
        summary="Official statistics X-Function category.",
        body=(
            "Statistics X-Functions cover statistical summaries and tests. origin-mcp currently "
            "uses the moments adapter for descriptive_stats and can read selected output rows back "
            "as structured JSON."
        ),
        keywords=("statistics", "moments", "descriptive", "summary"),
        metadata={"official_url": "https://docs.originlab.com/x-function/ref/statistics/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="x-functions/signal-processing",
        title="Signal Processing X-Functions",
        summary="Official signal processing category used by smoothing and peak tools.",
        body=(
            "origin-mcp indexes this category because smoothing, differentiation/integration "
            "workflows, and peak finding often overlap signal-processing style operations. "
            "Current adapters include smooth and pkFind."
        ),
        keywords=("signal processing", "smooth", "pkFind", "peak", "filter"),
        metadata={"official_url": "https://docs.originlab.com/x-function/ref/signal-processing/"},
    ),
    KnowledgeEntry(
        collection="labtalk",
        path="x-functions/import-and-export",
        title="Import and Export X-Functions",
        summary="Official X-Function category for import/export workflows.",
        body=(
            "Use this official category for exact import/export command syntax. origin-mcp also "
            "provides high-level import and export wrappers with file validation and diagnostics."
        ),
        keywords=("import", "export", "file", "data connector"),
        metadata={"official_url": "https://docs.originlab.com/x-function/ref/import-and-export/"},
    ),
)
