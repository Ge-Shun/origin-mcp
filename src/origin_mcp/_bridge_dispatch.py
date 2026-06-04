from __future__ import annotations

import inspect
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Any

from ._bridge_protocol import public_result, restore_bridge_value
from .errors import OriginOperationError
from .origin_client import OriginClient


def _origin_call_guard(client: OriginClient) -> AbstractContextManager[Any]:
    """Return the client's call lock, or a no-op when one is not present.

    originpro is single-threaded; the bridge serves synchronous requests and
    background tasks on separate threads, so every Origin call is funneled
    through the client's reentrant lock. Test doubles without the lock fall
    back to a no-op context.
    """

    lock = getattr(client, "_origin_call_lock", None)
    return lock if lock is not None else nullcontext()


ALLOWED_CLIENT_METHODS = {
    "connect",
    "capabilities",
    "plot_type_coverage",
    "default_plot_config",
    "save_graph_template",
    "new_project",
    "open_project",
    "save_project",
    "quit",
    "detach",
    "force_quit",
    "run_labtalk",
    "import_csv",
    "import_table",
    "import_file_connector",
    "append_table",
    "worksheet_info",
    "read_worksheet",
    "write_worksheet",
    "add_calculated_column",
    "add_calculated_columns",
    "sort_worksheet",
    "get_cell_value",
    "set_cell_value",
    "delete_columns",
    "clear_worksheet",
    "diagnose_worksheet",
    "export_worksheet_csv",
    "filter_rows",
    "drop_duplicates",
    "fill_missing",
    "transpose_worksheet",
    "merge_worksheets",
    "concat_worksheets",
    "pivot_worksheet",
    "melt_worksheet",
    "plot_table",
    "plot_dual_y",
    "plot_table_by_id",
    "plot_matrix_by_id",
    "list_project",
    "rename_object",
    "delete_object",
    "set_axis",
    "set_axis_break",
    "set_plot_style",
    "apply_nature_style",
    "diagnose_graph",
    "recommend_chart",
    "plot_auto",
    "chart_atlas_route",
    "plot_chart_atlas",
    "apply_image_panel_style",
    "add_plot_to_graph",
    "add_inset_layer",
    "remove_plot_from_graph",
    "change_plot_type",
    "change_plot_data",
    "set_graph_page",
    "arrange_layers",
    "add_graph_label",
    "add_reference_line",
    "set_column_labels",
    "set_column_designations",
    "format_legend",
    "linear_fit_result",
    "export_all_graphs",
    "plot_range",
    "batch_plot_from_template",
    "list_graph_templates",
    "get_graph_info",
    "get_layer_info",
    "list_fit_functions",
    "nonlinear_fit_structured",
    "run_analysis",
    "format_graph",
    "export_graph",
    "export_preview",
    "render_graph_png",
    "inspect_export",
}
TASKABLE_METHODS = {
    "origin_ping",
    "origin_capabilities",
    *ALLOWED_CLIENT_METHODS,
}


def call_client_method(
    client: OriginClient,
    method: str,
    args: list[Any],
    kwargs: dict[str, Any],
) -> Any:
    if method not in ALLOWED_CLIENT_METHODS:
        raise OriginOperationError(
            f"Unsupported bridge client method: {method}",
            error_code="unsupported_bridge_client_method",
        )
    func = getattr(client, method, None)
    if not callable(func):
        raise OriginOperationError(
            f"Origin client method is not available: {method}",
            error_code="origin_client_method_unavailable",
        )
    restored_args = [restore_bridge_value(arg) for arg in args]
    restored_kwargs = {key: restore_bridge_value(value) for key, value in kwargs.items()}
    coerced_args, coerced_kwargs = coerce_path_args(func, restored_args, restored_kwargs)
    with _origin_call_guard(client):
        return func(*coerced_args, **coerced_kwargs)


def coerce_path_args(
    func: Any,
    args: list[Any],
    kwargs: dict[str, Any],
) -> tuple[list[Any], dict[str, Any]]:
    signature = inspect.signature(func)
    path_names = {"path", "output_dir", "template_dir", "export_path"}
    coerced_args = list(args)
    params = list(signature.parameters.values())
    for index, value in enumerate(coerced_args):
        if index >= len(params):
            break
        if params[index].name in path_names and isinstance(value, str):
            coerced_args[index] = Path(value)
    coerced_kwargs = dict(kwargs)
    for key, value in list(coerced_kwargs.items()):
        if key in path_names and isinstance(value, str):
            coerced_kwargs[key] = Path(value)
    return coerced_args, coerced_kwargs


def call_origin_method(
    client: OriginClient,
    method: str,
    params: dict[str, Any],
    progress: Callable[[float | None, str, str | None], None] | None = None,
) -> dict[str, Any]:
    def report(value: float | None, step: str, message: str | None = None) -> None:
        if progress is not None:
            progress(value, step, message)

    # Hold the per-client lock for the whole call so the inner client calls and
    # the inspect_export follow-ups below run as one atomic Origin interaction
    # (the lock is reentrant, so the nested call_client_method calls are fine).
    with _origin_call_guard(client):
        report(0.05, "Dispatching", f"Dispatching {method}.")
        # ``origin_ping``/``origin_capabilities`` are taskable aliases for client
        # methods that carry a different name, so they cannot be routed generically.
        if method == "origin_ping":
            report(0.35, "Connecting to Origin", "Connecting to Origin.")
            result = client.connect(show=bool(params.get("show", True)))
            report(0.95, "Origin responded", "Origin connection check completed.")
            return result
        if method == "origin_capabilities":
            report(0.35, "Collecting capabilities", "Collecting Origin capabilities.")
            result = client.capabilities(
                show=bool(params.get("show", False)),
                refresh=bool(params.get("refresh", False)),
            )
            report(0.95, "Capabilities collected", "Origin capabilities collected.")
            return result
        if method not in ALLOWED_CLIENT_METHODS:
            raise OriginOperationError(f"Unsupported bridge method: {method}")

        # ``plot_table`` returns a (worksheet, graph) pair and ``export_graph``
        # returns a path dict; both enrich the response with an export inspection.
        # Every other client method maps cleanly onto the generic call path, which
        # already coerces path arguments and wraps WorksheetRef/GraphRef results.
        if method == "plot_table":
            report(0.20, "Creating plot", "Creating table-backed plot.")
            worksheet, graph = call_client_method(client, "plot_table", [], params)
            graph_data = graph.as_dict()
            response = {"worksheet": worksheet.as_dict(), "graph": graph_data}
            if graph_data.get("export_path"):
                report(0.75, "Inspecting export", "Inspecting exported graph.")
                response["export_inspection"] = client.inspect_export(
                    Path(graph_data["export_path"])
                )
            report(0.95, "Plot created", "Table-backed plot completed.")
            return response
        if method == "export_graph":
            report(0.25, "Exporting graph", "Exporting graph.")
            exported = call_client_method(client, "export_graph", [], params)
            report(0.75, "Inspecting export", "Inspecting exported graph.")
            return {
                **exported,
                "inspection": client.inspect_export(Path(str(exported["path"]))),
            }

        report(0.30, "Running Origin method", f"Running {method}.")
        result = public_result(call_client_method(client, method, [], params))
        report(0.95, "Method completed", f"{method} completed.")
        return result
