from types import SimpleNamespace

from origin_mcp.compat import collect_capabilities, is_origin_version_at_least


def test_is_origin_version_at_least() -> None:
    assert is_origin_version_at_least(10.3, 10.25)
    assert not is_origin_version_at_least(10.1, 10.25)
    assert not is_origin_version_at_least(None, 10.25)


def test_collect_capabilities_marks_missing_features() -> None:
    op = SimpleNamespace(lt_exec=lambda _script: True, save=lambda _path: True)

    data = collect_capabilities(op, 10.3)

    assert data["features"]["labtalk"]["available"] is True
    assert data["features"]["project_save"]["available"] is True
    assert data["features"]["project_open"]["available"] is False
    assert data["features"]["origin_2024_or_newer"]["available"] is True
