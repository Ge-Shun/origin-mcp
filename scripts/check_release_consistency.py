"""Check release metadata that should not drift across package artifacts."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT_PATH = ROOT / "src" / "origin_mcp" / "__init__.py"
PYPROJECT_PATH = ROOT / "pyproject.toml"
APP_BUILDER_PATH = ROOT / "scripts" / "build_origin_app.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    problems = check_release_consistency()
    if problems:
        print("Release consistency check failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("Release consistency check passed.")
    return 0


def check_release_consistency() -> list[str]:
    problems: list[str] = []
    package_version = read_package_version()
    app_version = read_app_builder_version()

    if app_version != package_version:
        problems.append(
            f"Origin App version {app_version!r} does not match package version "
            f"{package_version!r}."
        )

    pyproject_text = PYPROJECT_PATH.read_text(encoding="utf-8")
    if 'dynamic = ["version"]' not in pyproject_text:
        problems.append("pyproject.toml should keep project.version dynamic.")
    expected_path = 'path = "src/origin_mcp/__init__.py"'
    if expected_path not in pyproject_text:
        problems.append(f"pyproject.toml hatch version path should be {expected_path!r}.")

    builder_text = APP_BUILDER_PATH.read_text(encoding="utf-8")
    if not re.search(r"APP_VERSION\s*=\s*package_version\(\)", builder_text):
        problems.append(
            "scripts/build_origin_app.py should derive APP_VERSION from package_version()."
        )

    return problems


def read_package_version() -> str:
    tree = ast.parse(INIT_PATH.read_text(encoding="utf-8"), filename=str(INIT_PATH))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in node.targets
            ):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    return node.value.value
    raise RuntimeError(f"Could not read __version__ from {INIT_PATH}")


def read_app_builder_version() -> str:
    spec = importlib.util.spec_from_file_location("origin_mcp_app_builder_check", APP_BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {APP_BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return str(module.APP_VERSION)


if __name__ == "__main__":
    raise SystemExit(main())
