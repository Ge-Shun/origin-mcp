from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Any

FEATURE_REQUIREMENTS = {
    "data_connector": 9.6,
    "worksheet_from_file": 9.6,
    "origin_2021b_or_newer": 10.1,
    "origin_2024_or_newer": 10.25,
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


def is_origin_version_at_least(version: float | int | None, minimum: float) -> bool:
    if version is None:
        return False
    try:
        return float(version) >= minimum
    except (TypeError, ValueError):
        return False


def collect_capabilities(op: Any, origin_version: float | int | None) -> dict[str, Any]:
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
            is_origin_version_at_least(origin_version, 10.25),
            10.25,
        ),
    ]
    return {
        "origin_version": origin_version,
        "originpro_version": package_version("originpro"),
        "originext_version": package_version("OriginExt"),
        "features": {feature.name: feature.as_dict() for feature in feature_checks},
    }


def feature_available(capabilities: dict[str, Any], feature: str) -> bool:
    info = capabilities.get("features", {}).get(feature, {})
    return bool(info.get("available"))
