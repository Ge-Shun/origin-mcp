from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Any

from .runtime import python_runtime_profile

PLOT_TYPE_CATALOG: list[dict[str, Any]] = [
    {
        "id": 101,
        "name": "3D Scatter",
        "input": "Matrix Object",
        "templates": ["gl3DScatterMat"],
        "category": "3D",
    },
    {
        "id": 103,
        "name": "3D Surface",
        "input": "XYZ Range/Matrix Object",
        "templates": ["glmesh", "glcmap", "glwirefrm", "glwireface"],
        "category": "3D",
    },
    {
        "id": 105,
        "name": "Heatmap",
        "input": "Matrix Object",
        "templates": ["heatmap"],
        "category": "Contour",
    },
    {
        "id": 108,
        "name": "Dendrogram",
        "input": "XYY Range",
        "templates": ["Cluster"],
        "category": "Statistical",
    },
    {
        "id": 183,
        "name": "3D Vector",
        "input": "XYZXYZ Range/XYZdXdYdZ Range",
        "templates": ["gl3DVector"],
        "category": "3D",
    },
    {
        "id": 184,
        "name": "3D Scatter + Error Bar",
        "input": "XYZZ Range",
        "templates": ["gl3DError"],
        "category": "3D",
    },
    {
        "id": 185,
        "name": "Ternary Contour",
        "input": "XYZZ Range",
        "templates": ["TernaryContour"],
        "category": "Contour",
    },
    {
        "id": 186,
        "name": "Polar X(R) Y(Theta)",
        "input": "XY Range",
        "templates": ["PolarXrYTheta"],
        "category": "Specialized",
    },
    {
        "id": 191,
        "name": "Smith Chart",
        "input": "XY Range",
        "templates": ["SmithCht"],
        "category": "Specialized",
    },
    {
        "id": 192,
        "name": "Polar",
        "input": "XY Range",
        "templates": ["polar"],
        "category": "Specialized",
        "direct_tool": "origin_plot_polar",
    },
    {
        "id": 193,
        "name": "Bubble (indexed size)",
        "input": "XYY Range",
        "templates": ["scatter"],
        "category": "Basic 2D",
    },
    {
        "id": 194,
        "name": "Bubble + color mapped",
        "input": "XYY Range",
        "templates": ["scatter"],
        "category": "Basic 2D",
    },
    {
        "id": 200,
        "name": "Line",
        "input": "XY Range",
        "templates": ["line"],
        "category": "Basic 2D",
        "direct_tool": "origin_plot_line",
    },
    {
        "id": 201,
        "name": "Scatter",
        "input": "XY Range",
        "templates": ["scatter"],
        "category": "Basic 2D",
        "direct_tool": "origin_plot_scatter",
    },
    {
        "id": 202,
        "name": "Line+symbol",
        "input": "XY Range",
        "templates": ["linesymb"],
        "category": "Basic 2D",
        "direct_tool": "origin_plot_line_symbol",
    },
    {
        "id": 203,
        "name": "Column",
        "input": "XY Range",
        "templates": ["column"],
        "category": "Bar, Pie, Area",
        "direct_tool": "origin_plot_column",
    },
    {
        "id": 204,
        "name": "Area",
        "input": "XY Range",
        "templates": ["area"],
        "category": "Bar, Pie, Area",
    },
    {
        "id": 205,
        "name": "High-Low-Close",
        "input": "XYYY Range",
        "templates": ["hclose"],
        "category": "Specialized",
    },
    {
        "id": 206,
        "name": "Box",
        "input": "Y Range",
        "templates": ["box"],
        "category": "Statistical",
        "direct_tool": "origin_plot_box",
    },
    {
        "id": 207,
        "name": "Floating Bar",
        "input": "XYY Range",
        "templates": ["floatbar"],
        "category": "Bar, Pie, Area",
    },
    {
        "id": 208,
        "name": "XYAM Vector",
        "input": "XYYY Range",
        "templates": ["vector"],
        "category": "Specialized",
    },
    {
        "id": 210,
        "name": "3D Walls/Waterfall",
        "input": "XYY Range",
        "templates": ["walls", "glWater3D"],
        "category": "3D",
    },
    {
        "id": 211,
        "name": "3D Ribbons",
        "input": "XYY Range",
        "templates": ["ribbon"],
        "category": "3D",
    },
    {
        "id": 212,
        "name": "3D Bars",
        "input": "XYY Range",
        "templates": ["bar3d"],
        "category": "3D",
    },
    {
        "id": 213,
        "name": "Column Stack/Windrose",
        "input": "XYY Range",
        "templates": ["column", "windrose"],
        "category": "Bar, Pie, Area",
    },
    {
        "id": 214,
        "name": "Stack Area",
        "input": "XYY Range",
        "templates": ["stackarea"],
        "category": "Bar, Pie, Area",
    },
    {
        "id": 215,
        "name": "Bar",
        "input": "XY Range",
        "templates": ["bar"],
        "category": "Bar, Pie, Area",
    },
    {
        "id": 216,
        "name": "Stack Bar",
        "input": "XYY Range",
        "templates": ["bar"],
        "category": "Bar, Pie, Area",
    },
    {
        "id": 218,
        "name": "XYXY Vector",
        "input": "XYXY Range",
        "templates": ["vectxyxy"],
        "category": "Specialized",
    },
    {
        "id": 219,
        "name": "Histogram",
        "input": "Y Range",
        "templates": ["hist"],
        "category": "Statistical",
        "direct_tool": "origin_plot_histogram",
    },
    {
        "id": 220,
        "name": "Image Plot",
        "input": "Matrix Object",
        "templates": ["image"],
        "category": "Specialized",
    },
    {
        "id": 221,
        "name": "OHLC Chart",
        "input": "OHLC Range",
        "templates": ["Candlestick", "OHLCBarChart"],
        "category": "Specialized",
    },
    {
        "id": 225,
        "name": "Pie Chart",
        "input": "XY Range",
        "templates": ["pie"],
        "category": "Bar, Pie, Area",
    },
    {
        "id": 226,
        "name": "Contours",
        "input": "Matrix Object",
        "templates": ["contour", "contline", "contgray"],
        "category": "Contour",
    },
    {
        "id": 231,
        "name": "Error Bar",
        "input": "XYyErr Range",
        "templates": ["Errbar"],
        "category": "Basic 2D",
        "direct_tool": "origin_plot_errorbar",
    },
    {
        "id": 233,
        "name": "X Error Bar",
        "input": "XYxErr Range",
        "templates": ["Errbar"],
        "category": "Basic 2D",
        "direct_tool": "origin_plot_errorbar",
    },
    {
        "id": 240,
        "name": "3D Scatter/Trajectory",
        "input": "XYZ Range",
        "templates": ["3d", "traject", "gl3d", "glTraject"],
        "category": "3D",
        "direct_tool": "origin_plot_3d_scatter",
    },
    {
        "id": 242,
        "name": "3D Surface/3D Bars",
        "input": "Matrix Object/XYZ Range",
        "templates": ["mesh", "xconst", "yconst", "cmap", "wirefrm", "wireface", "gl3dbars"],
        "category": "3D",
        "direct_tool": "origin_plot_3d_surface",
    },
    {
        "id": 243,
        "name": "Contours",
        "input": "XYZ Range",
        "templates": ["Contour", "PolarContour", "TriContour", "TriContline", "TriContgray"],
        "category": "Contour",
        "direct_tool": "origin_plot_contour",
    },
    {
        "id": 245,
        "name": "Ternary",
        "input": "XYZ Range",
        "templates": ["ternary"],
        "category": "Specialized",
    },
    {
        "id": 247,
        "name": "Color Mapped",
        "input": "XYY Range",
        "templates": ["scatter"],
        "category": "Basic 2D",
    },
    {
        "id": 248,
        "name": "Bubble + Color Mapped",
        "input": "XYYY Range",
        "templates": ["scatter"],
        "category": "Basic 2D",
    },
    {
        "id": 249,
        "name": "Fill Area",
        "input": "XYY Range",
        "templates": ["fillarea"],
        "category": "Bar, Pie, Area",
    },
]

PLOT_TYPE_DIRECT_TOOLS = {
    101: "origin_plot_matrix_3d_scatter",
    103: "origin_plot_matrix_3d_surface",
    105: "origin_plot_matrix_heatmap",
    108: "origin_plot_dendrogram",
    183: "origin_plot_3d_vector",
    184: "origin_plot_3d_errorbar",
    185: "origin_plot_ternary_contour",
    186: "origin_plot_polar_xr_ytheta",
    191: "origin_plot_smith",
    192: "origin_plot_polar",
    193: "origin_plot_bubble",
    194: "origin_plot_bubble_color_mapped",
    200: "origin_plot_line",
    201: "origin_plot_scatter",
    202: "origin_plot_line_symbol",
    203: "origin_plot_column",
    204: "origin_plot_area",
    205: "origin_plot_high_low_close",
    206: "origin_plot_box",
    207: "origin_plot_floating_bar",
    208: "origin_plot_vector_xyam",
    210: "origin_plot_waterfall",
    211: "origin_plot_3d_ribbon",
    212: "origin_plot_3d_bars",
    213: "origin_plot_column_stack",
    214: "origin_plot_stack_area",
    215: "origin_plot_bar",
    216: "origin_plot_stack_bar",
    218: "origin_plot_vector_xyxy",
    219: "origin_plot_histogram",
    220: "origin_plot_image",
    221: "origin_plot_candlestick",
    225: "origin_plot_pie",
    226: "origin_plot_matrix_contour",
    231: "origin_plot_errorbar",
    233: "origin_plot_errorbar",
    240: "origin_plot_3d_scatter",
    242: "origin_plot_3d_surface",
    243: "origin_plot_contour",
    245: "origin_plot_ternary",
    247: "origin_plot_color_mapped",
    248: "origin_plot_bubble_color_mapped",
    249: "origin_plot_fill_area",
}

FEATURE_REQUIREMENTS = {
    "data_connector": 9.6,
    "worksheet_from_file": 9.6,
    "origin_2021b_or_newer": 10.1,
    "origin_2024_or_newer": 10.15,
    "origin_2024b_or_newer": 10.15,
    "origin_2026_or_newer": 10.3,
}


@dataclass(frozen=True)
class FeatureCheck:
    name: str
    available: bool
    minimum_origin_version: float | None = None
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "minimum_origin_version": self.minimum_origin_version,
            "note": self.note,
        }


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def is_origin_version_at_least(version: float | int | str | None, minimum: float | str) -> bool:
    parsed = _origin_version_tuple(version)
    minimum_parsed = _origin_version_tuple(minimum)
    if parsed is None or minimum_parsed is None:
        return False
    return parsed >= minimum_parsed


def _origin_version_tuple(version: float | int | str | None) -> tuple[int, ...] | None:
    if version is None:
        return None
    text = str(version).strip()
    if not text:
        return None
    parts = text.split(".")
    parsed: list[int] = []
    for index, part in enumerate(parts):
        digits = ""
        for char in part:
            if char.isdigit():
                digits += char
            else:
                break
        if not digits:
            break
        value = int(digits)
        if index == 1 and len(digits) == 1:
            value *= 10
        parsed.append(value)
    if not parsed:
        return None
    return tuple(parsed)


def collect_capabilities(op: Any, origin_version: float | int | None) -> dict[str, Any]:
    runtime = python_runtime_profile()
    feature_checks = [
        FeatureCheck("labtalk", hasattr(op, "lt_exec"), note="Required for fallback commands."),
        FeatureCheck("project_open", hasattr(op, "open")),
        FeatureCheck("project_save", hasattr(op, "save")),
        FeatureCheck("pages", hasattr(op, "pages"), note="Required for project listing."),
        FeatureCheck(
            "graph_list",
            hasattr(op, "graph_list"),
            note="Required for export all graphs.",
        ),
        FeatureCheck("data_connector", hasattr(op, "Connector"), 9.6),
        FeatureCheck(
            "worksheet_from_file",
            True,
            9.6,
            "Checked on worksheet instances at runtime.",
        ),
        FeatureCheck("linear_fit_api", hasattr(op, "LinearFit")),
        FeatureCheck("nonlinear_fit_api", hasattr(op, "NLFit")),
        FeatureCheck("external_python", package_version("OriginExt") is not None),
        FeatureCheck(
            "origin_2021b_or_newer",
            is_origin_version_at_least(origin_version, 10.1),
            10.1,
        ),
        FeatureCheck(
            "origin_2024_or_newer",
            is_origin_version_at_least(origin_version, 10.15),
            10.15,
            "Compatibility alias for origin_2024b_or_newer.",
        ),
        FeatureCheck(
            "origin_2024b_or_newer",
            is_origin_version_at_least(origin_version, 10.15),
            10.15,
        ),
        FeatureCheck(
            "origin_2026_or_newer",
            is_origin_version_at_least(origin_version, 10.3),
            10.3,
        ),
    ]
    return {
        "origin_version": origin_version,
        "originpro_version": package_version("originpro"),
        "originext_version": package_version("OriginExt"),
        "python_version": runtime.version,
        "python_executable": runtime.executable,
        "python_runtime": runtime.as_dict(),
        "features": {feature.name: feature.as_dict() for feature in feature_checks},
        "plot_type_coverage": plot_type_coverage(origin_version),
    }


def feature_available(capabilities: dict[str, Any], feature: str) -> bool:
    info = capabilities.get("features", {}).get(feature, {})
    return bool(info.get("available"))


def plot_type_coverage(origin_version: float | int | None = None) -> dict[str, Any]:
    items = [_plot_type_item(item) for item in PLOT_TYPE_CATALOG]
    summary = {
        "catalog_count": len(items),
        "direct_tool_count": sum(item["coverage"] == "direct_tool" for item in items),
        "generic_template_count": sum(item["coverage"] == "generic_template" for item in items),
        "not_wrapped_count": sum(item["coverage"] == "not_wrapped" for item in items),
    }
    return {
        "origin_version": origin_version,
        "version_profile": _plot_version_profile(origin_version),
        "summary": summary,
        "items": items,
        "notes": [
            (
                "Origin has 100+ built-in graph types; this catalog tracks the "
                "documented Plot Type ID table."
            ),
            "direct_tool means origin-mcp exposes a named high-level MCP plotting tool.",
            (
                "generic_template means origin_plot_from_range can usually reach it "
                "by plot_type ID/template."
            ),
            (
                "not_wrapped means a dedicated wrapper is still missing or "
                "matrix/specialized input is required."
            ),
        ],
    }


def _plot_type_item(item: dict[str, Any]) -> dict[str, Any]:
    direct_tool = item.get("direct_tool") or PLOT_TYPE_DIRECT_TOOLS.get(item["id"])
    if direct_tool:
        coverage = "direct_tool"
    elif _can_use_generic_plotxy(item):
        coverage = "generic_template"
    else:
        coverage = "not_wrapped"
    return {
        **item,
        "coverage": coverage,
        "direct_tool": direct_tool,
        "generic_tool": "origin_plot_from_range" if coverage == "generic_template" else None,
    }


def _can_use_generic_plotxy(item: dict[str, Any]) -> bool:
    input_range = str(item.get("input", ""))
    if "Matrix Object" in input_range and "XYZ Range" not in input_range:
        return False
    if item["name"] in {"Dendrogram"}:
        return False
    return True


def _plot_version_profile(origin_version: float | int | None) -> dict[str, Any]:
    if origin_version is None:
        return {
            "name": "unknown",
            "recommended": False,
            "note": (
                "Origin version could not be detected; run origin_capabilities "
                "with Origin available."
            ),
        }
    if is_origin_version_at_least(origin_version, 10.3):
        return {
            "name": "Origin 2026 or newer",
            "recommended": True,
            "note": (
                "Primary tested target for origin-mcp. Other Origin versions are "
                "not currently guaranteed."
            ),
        }
    if is_origin_version_at_least(origin_version, 10.15):
        return {
            "name": "Origin 2024b to 2025",
            "recommended": False,
            "note": (
                "Detected as a modern Origin version, but origin-mcp currently "
                "targets Origin/OriginPro 2026 for active testing."
            ),
        }
    if is_origin_version_at_least(origin_version, 10.1):
        return {
            "name": "Origin 2021b to 2023",
            "recommended": False,
            "note": "Recognized, but not currently guaranteed by origin-mcp.",
        }
    return {
        "name": "Legacy Origin before 2021b",
        "recommended": False,
        "note": (
            "This MCP is built around originpro; older versions may require "
            "PyOrigin/LabTalk-only paths."
        ),
    }
