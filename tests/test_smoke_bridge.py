from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_smoke_module():
    spec = importlib.util.spec_from_file_location(
        "smoke_bridge_test",
        ROOT / "examples/smoke_bridge.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeOrigin:
    def origin_bridge_status(self):
        return {"ok": True, "data": {"bridge": "origin-mcp-bridge"}}

    def origin_ping(self, show=True):
        return {"ok": True, "data": {"show": show, "connected": True}}

    def origin_new_project(self, show=True):
        return {"ok": True, "data": {"show": show, "new_project": True}}

    def origin_import_table(self, **_kwargs):
        return {
            "ok": True,
            "data": {
                "worksheet": {
                    "book_name": "SmokeBridge",
                    "sheet_name": "Data",
                    "columns": ["time", "signal_a", "signal_b"],
                    "rows": 3,
                }
            },
        }

    def origin_get_worksheet_info(self, **_kwargs):
        return {"ok": True, "data": {"rows": 3, "columns": ["time", "signal_a", "signal_b"]}}

    def origin_read_worksheet(self, **_kwargs):
        return {"ok": True, "data": {"rows": [{"time": 0, "signal_a": 1, "signal_b": 2}]}}

    def origin_plot_line(self, **kwargs):
        return {"ok": True, "data": {"graph": {"graph_name": kwargs["graph_name"]}}}

    def origin_inspect_export(self, path):
        return {"ok": True, "data": {"path": path, "looks_nonempty": True}}

    def origin_save_project(self, path):
        return {"ok": True, "data": {"path": path}}

    def origin_detach(self):
        return {"ok": True, "data": {"detached": True}}

    def origin_quit(self):
        return {"ok": True, "data": {"quit": True}}

    def origin_doctor(self, ping_origin=False):
        return {"ok": True, "data": {"ping_origin": ping_origin}}


class FailingOrigin(FakeOrigin):
    def origin_plot_line(self, **_kwargs):
        return {"ok": False, "message": "plot failed", "error_code": "plot_failed"}


def test_smoke_report_records_success(tmp_path: Path) -> None:
    smoke = load_smoke_module()
    report_path = tmp_path / "report.json"

    report = smoke.run_smoke(
        FakeOrigin(),
        data_path=ROOT / "examples" / "sample_data.csv",
        output_dir=tmp_path,
        report_path=report_path,
        keep_origin_open=True,
        show_origin=False,
    )

    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert written["ok"] is True
    assert [step["name"] for step in report["steps"]][-1] == "origin_detach"
    assert report["artifacts"]["export_inspection"]["looks_nonempty"] is True


def test_smoke_report_records_failure_and_doctor(tmp_path: Path) -> None:
    smoke = load_smoke_module()

    report = smoke.run_smoke(
        FailingOrigin(),
        data_path=ROOT / "examples" / "sample_data.csv",
        output_dir=tmp_path,
    )

    assert report["ok"] is False
    assert report["error"]["message"].startswith("origin_plot_line failed")
    assert report["doctor"]["ok"] is True
    failed_steps = [step for step in report["steps"] if not step["ok"]]
    assert failed_steps[-1]["name"] == "origin_plot_line"


def test_release_smoke_wrapper_has_help() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "real_origin_smoke.py"), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "real-Origin release smoke gate" in result.stdout
