from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_health_module():
    spec = importlib.util.spec_from_file_location(
        "real_origin_health_test",
        ROOT / "scripts" / "real_origin_health.py",
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
                    "book_name": "HealthBridge",
                    "sheet_name": "Data",
                    "columns": ["time", "signal_a", "signal_b"],
                    "rows": 3,
                }
            },
        }

    def origin_get_worksheet_info(self, **_kwargs):
        return {"ok": True, "data": {"rows": 3, "columns": ["time", "signal_a", "signal_b"]}}

    def origin_doctor(self, ping_origin=False):
        return {"ok": True, "data": {"ping_origin": ping_origin}}


class FailingOrigin(FakeOrigin):
    def origin_new_project(self, show=True):
        return {"ok": False, "message": "new project failed", "data": {"show": show}}


def test_health_report_records_success(tmp_path: Path) -> None:
    health = load_health_module()
    report_path = tmp_path / "health-report.json"

    report = health.run_health(
        FakeOrigin(),
        data_path=ROOT / "examples" / "sample_data.csv",
        output_dir=tmp_path,
        report_path=report_path,
        show_origin=False,
    )

    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert written["ok"] is True
    assert [step["name"] for step in report["steps"]] == [
        "origin_bridge_status",
        "origin_ping",
        "origin_new_project",
        "origin_import_table",
        "origin_get_worksheet_info",
    ]
    assert report["artifacts"]["worksheet"]["book_name"] == "HealthBridge"


def test_health_report_records_failure_and_doctor(tmp_path: Path) -> None:
    health = load_health_module()

    report = health.run_health(
        FailingOrigin(),
        data_path=ROOT / "examples" / "sample_data.csv",
        output_dir=tmp_path,
    )

    assert report["ok"] is False
    assert report["error"]["message"].startswith("origin_new_project failed")
    assert report["doctor"]["ok"] is True
    failed_steps = [step for step in report["steps"] if not step["ok"]]
    assert failed_steps[-1]["name"] == "origin_new_project"


def test_real_origin_health_has_help() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "real_origin_health.py"), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "lightweight real-Origin bridge health gate" in result.stdout
