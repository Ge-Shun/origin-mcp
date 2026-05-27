from origin_mcp.runtime import PythonRuntimeProfile


def test_python_runtime_profile_serializes() -> None:
    profile = PythonRuntimeProfile(
        version="3.12.10",
        executable="python.exe",
        implementation="CPython",
        major=3,
        minor=12,
        origin_ext_tier="preferred",
        recommended_backend="origin_embedded_bridge",
        note="ok",
    )

    assert profile.as_dict()["origin_ext_tier"] == "preferred"
    assert profile.as_dict()["recommended_backend"] == "origin_embedded_bridge"
