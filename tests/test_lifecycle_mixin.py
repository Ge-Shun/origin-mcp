"""Behavioural tests for ``_LifecycleMixin`` against the fake Origin."""

from __future__ import annotations

from pathlib import Path

import pytest
from fake_origin import FakeOp

from origin_mcp.errors import OriginOperationError
from origin_mcp.origin_client import OriginClient


def test_connect_reports_version_and_show(fake_client: OriginClient) -> None:
    fake_client.op.lt_values["@V"] = 10.3

    result = fake_client.connect(show=True)

    assert result["connected"] is True
    assert result["visible"] is True
    assert result["origin_version"] == 10.3
    assert fake_client.op.show is True


def test_capabilities_are_cached(fake_client: OriginClient) -> None:
    first = fake_client.capabilities()
    second = fake_client.capabilities()

    assert first is second  # cached, no recomputation
    assert "features" in first
    # The fake exposes lt_exec and pages, so those features read as available.
    assert first["features"]["labtalk"]["available"] is True
    assert first["features"]["pages"]["available"] is True


def test_capabilities_refresh_recomputes(fake_client: OriginClient) -> None:
    first = fake_client.capabilities()
    second = fake_client.capabilities(refresh=True)

    assert first is not second


def test_ensure_feature_raises_for_missing(fake_client: OriginClient) -> None:
    # The fake op has no LinearFit, so linear_fit_api is unavailable.
    with pytest.raises(OriginOperationError) as excinfo:
        fake_client.ensure_feature("linear_fit_api", "Structured linear fitting")
    assert excinfo.value.error_code == "unsupported_origin_feature"


def test_new_project_invokes_new(fake_client: OriginClient) -> None:
    result = fake_client.new_project(show=False)

    assert result["created"] is True
    assert ("new", ()) in fake_client.op.calls


def test_save_project_uses_originpro_save(fake_client: OriginClient, tmp_path: Path) -> None:
    target = tmp_path / "proj.opju"

    result = fake_client.save_project(path=target)

    assert result["saved"] is True
    assert result["method"] == "originpro.save"
    assert any(name == "save" for name, _ in fake_client.op.calls)


def test_quit_clears_state(fake_client: OriginClient) -> None:
    result = fake_client.quit()

    assert result["closed"] is True
    assert fake_client._op is None
    assert fake_client._capabilities is None


def test_detach_releases_without_closing(fake_client: OriginClient) -> None:
    result = fake_client.detach()

    assert result == {"detached": True, "closed": False}
    assert fake_client._op is None


def test_run_labtalk_rejects_empty(fake_client: OriginClient) -> None:
    with pytest.raises(OriginOperationError):
        fake_client.run_labtalk("   ")


def test_run_labtalk_warns_on_false_result(fake_client: OriginClient) -> None:
    fake_client.op.lt_exec_result = False

    response = fake_client.run_labtalk("bad_command;")

    assert response["result"] is False
    assert "warning" in response


def test_run_labtalk_unavailable_without_lt_exec() -> None:
    op = FakeOp()
    # Remove lt_exec to simulate an environment without LabTalk execution.
    op.lt_exec = None  # type: ignore[assignment]
    client = OriginClient()
    client._op = op
    with pytest.raises(OriginOperationError) as excinfo:
        client.run_labtalk("foo;")
    assert excinfo.value.error_code == "labtalk_unavailable"


def test_run_labtalk_capture_log(fake_client: OriginClient) -> None:
    response = fake_client.run_labtalk("type test;", capture_log=True)

    assert "result" in response
    assert "message_log" in response


def test_open_project(fake_client: OriginClient, tmp_path: Path) -> None:
    project = tmp_path / "p.opju"
    project.write_bytes(b"opju")

    result = fake_client.open_project(path=project)

    assert result["opened"] is True
    assert any(name == "open" for name, _ in fake_client.op.calls)


def test_open_project_rejects_non_project_file(fake_client: OriginClient, tmp_path: Path) -> None:
    bad = tmp_path / "p.txt"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(OriginOperationError):
        fake_client.open_project(path=bad)


def test_save_project_falls_back_to_pe_save(fake_client: OriginClient, tmp_path: Path) -> None:
    fake_client.op.save_raises = True
    target = tmp_path / "p.opju"

    result = fake_client.save_project(path=target)

    assert result["saved"] is True
    assert result["method"] == "labtalk.pe_save"
    assert "fallback_error" in result
