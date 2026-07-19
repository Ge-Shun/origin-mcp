from __future__ import annotations

import threading
from pathlib import Path

import pytest

from origin_mcp import bridge_handshake
from origin_mcp.bridge import OriginBridgeServer
from origin_mcp.bridge_client import OriginBridgeClient, OriginBridgeConfig
from origin_mcp.errors import OriginBridgeError

_BRIDGE_ENV_VARS = (
    "ORIGIN_MCP_BRIDGE_HOST",
    "ORIGIN_MCP_BRIDGE_PORT",
    "ORIGIN_MCP_BRIDGE_TOKEN",
    "ORIGIN_MCP_BRIDGE_TIMEOUT",
    "ORIGIN_MCP_BRIDGE_HANDSHAKE",
)


class FakeOriginClient:
    pass


@pytest.fixture
def isolated_handshake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the handshake file at a temp path and clear all bridge env vars."""

    for name in _BRIDGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "bridge.json"
    monkeypatch.setenv("ORIGIN_MCP_BRIDGE_HANDSHAKE", str(path))
    return path


def test_default_handshake_path_honors_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORIGIN_MCP_BRIDGE_HANDSHAKE", "/tmp/custom/bridge.json")
    assert bridge_handshake.default_handshake_path() == Path("/tmp/custom/bridge.json")


def test_generate_token_is_random_and_nonempty() -> None:
    first = bridge_handshake.generate_token()
    second = bridge_handshake.generate_token()
    assert first and second
    assert first != second


def test_write_read_clear_roundtrip(isolated_handshake: Path) -> None:
    status_path = isolated_handshake.parent / "status.json"
    bridge_handshake.write_handshake(
        "127.0.0.1",
        47631,
        "tok-123",
        status_path=status_path,
    )

    data = bridge_handshake.read_handshake()
    assert data is not None
    assert data["host"] == "127.0.0.1"
    assert data["port"] == 47631
    assert data["token"] == "tok-123"
    assert data["handshake_version"] == 2
    assert data["generation"]
    assert data["lease_id"] == data["generation"]
    assert data["origin_pid"] == data["pid"]
    assert data["status_path"] == str(status_path.resolve())
    assert bridge_handshake.read_handshake_token() == "tok-123"

    bridge_handshake.clear_handshake()
    assert bridge_handshake.read_handshake() is None
    assert bridge_handshake.read_handshake_token() is None


def test_read_handshake_returns_none_for_missing_or_invalid(isolated_handshake: Path) -> None:
    assert bridge_handshake.read_handshake() is None  # missing
    isolated_handshake.write_text("{ not json", encoding="utf-8")
    assert bridge_handshake.read_handshake() is None  # invalid


def test_from_env_reads_token_from_handshake(isolated_handshake: Path) -> None:
    bridge_handshake.write_handshake("127.0.0.1", 50000, "handshake-token")

    config = OriginBridgeConfig.from_env()

    assert config.token == "handshake-token"
    assert config.host == "127.0.0.1"
    assert config.port == 50000


def test_from_env_env_token_overrides_handshake(
    isolated_handshake: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge_handshake.write_handshake("127.0.0.1", 50000, "handshake-token")
    monkeypatch.setenv("ORIGIN_MCP_BRIDGE_TOKEN", "env-token")

    config = OriginBridgeConfig.from_env()

    assert config.token == "env-token"
    # Host/port still come from the handshake when their env vars are unset.
    assert config.port == 50000


def test_from_env_explicit_arg_overrides_everything(
    isolated_handshake: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge_handshake.write_handshake("127.0.0.1", 50000, "handshake-token")
    monkeypatch.setenv("ORIGIN_MCP_BRIDGE_TOKEN", "env-token")

    config = OriginBridgeConfig.from_env(token="explicit-token", port=12345)

    assert config.token == "explicit-token"
    assert config.port == 12345
    assert config.generation is None
    assert config.lease_id is None
    assert config.origin_pid is None
    assert config.handshake_managed is False


def test_explicit_connection_ignores_unrelated_handshake_lifecycle(
    isolated_handshake: Path,
) -> None:
    bridge_handshake.write_handshake(
        "127.0.0.1",
        50000,
        "stale-token",
        generation="stale-generation",
        lease_id="stale-generation",
    )
    server = OriginBridgeServer(
        ("127.0.0.1", 0),
        token="live-token",
        generation="live-generation",
        lease_id="live-generation",
        client=FakeOriginClient(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        config = OriginBridgeConfig.from_env(
            host=host,
            port=port,
            token="live-token",
            timeout=2.0,
        )

        assert config.generation is None
        assert config.lease_id is None
        result = OriginBridgeClient(config).request("ping")
        assert result["generation"] == "live-generation"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_from_env_falls_back_to_defaults_without_handshake(isolated_handshake: Path) -> None:
    config = OriginBridgeConfig.from_env()

    assert config.host == "127.0.0.1"
    assert config.port == 47631
    assert config.token is None


def test_from_env_rejects_invalid_env_port(
    isolated_handshake: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORIGIN_MCP_BRIDGE_PORT", "not-a-port")

    with pytest.raises(OriginBridgeError) as excinfo:
        OriginBridgeConfig.from_env()

    assert excinfo.value.error_code == "invalid_bridge_config"
    assert "ORIGIN_MCP_BRIDGE_PORT" in str(excinfo.value)


def test_from_env_rejects_invalid_handshake_port(isolated_handshake: Path) -> None:
    isolated_handshake.write_text(
        '{"host": "127.0.0.1", "port": "not-a-port", "token": "tok"}',
        encoding="utf-8",
    )

    with pytest.raises(OriginBridgeError) as excinfo:
        OriginBridgeConfig.from_env()

    assert excinfo.value.error_code == "invalid_bridge_config"
    assert "bridge handshake port" in str(excinfo.value)


def test_from_env_rejects_invalid_env_timeout(
    isolated_handshake: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORIGIN_MCP_BRIDGE_TIMEOUT", "not-a-timeout")

    with pytest.raises(OriginBridgeError) as excinfo:
        OriginBridgeConfig.from_env()

    assert excinfo.value.error_code == "invalid_bridge_config"
    assert "ORIGIN_MCP_BRIDGE_TIMEOUT" in str(excinfo.value)


@pytest.mark.parametrize("port", [0, -1, 65536])
def test_bridge_config_rejects_out_of_range_port(port: int) -> None:
    with pytest.raises(OriginBridgeError) as excinfo:
        OriginBridgeConfig(port=port)

    assert excinfo.value.error_code == "invalid_bridge_config"


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_bridge_config_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(OriginBridgeError) as excinfo:
        OriginBridgeConfig(timeout=timeout)

    assert excinfo.value.error_code == "invalid_bridge_config"


def test_handshake_token_authenticates_against_running_bridge(isolated_handshake: Path) -> None:
    """End-to-end: a token-protected bridge accepts a client configured purely
    from the handshake file, and rejects one that ignores it."""

    token = bridge_handshake.generate_token()
    server = OriginBridgeServer(("127.0.0.1", 0), token=token, client=FakeOriginClient())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        bridge_handshake.write_handshake(host, port, token)

        # Client built from env/handshake only -> picks up host/port/token.
        config = OriginBridgeConfig.from_env(timeout=2.0)
        assert config.token == token
        ok = OriginBridgeClient(config).request("ping")
        assert ok["bridge"] == "origin-mcp-bridge"

        # A client that explicitly sends no token is rejected.
        no_token = OriginBridgeConfig(host=host, port=port, token=None, timeout=2.0)
        with pytest.raises(OriginBridgeError) as excinfo:
            OriginBridgeClient(no_token).request("ping")
        assert excinfo.value.error_code == "origin_bridge_unauthorized"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_handshake_managed_client_refreshes_rotated_token(
    isolated_handshake: Path,
) -> None:
    server = OriginBridgeServer(
        ("127.0.0.1", 0),
        token="token-one",
        generation="generation-one",
        lease_id="generation-one",
        client=FakeOriginClient(),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        bridge_handshake.write_handshake(
            host,
            port,
            "token-one",
            generation="generation-one",
            lease_id="generation-one",
        )
        client = OriginBridgeClient(OriginBridgeConfig.from_env(timeout=2.0))

        server.token = "token-two"
        server.generation = "generation-two"
        server.lease_id = "generation-two"
        bridge_handshake.write_handshake(
            host,
            port,
            "token-two",
            generation="generation-two",
            lease_id="generation-two",
        )

        result = client.request("ping")
        assert result["generation"] == "generation-two"
        assert client.config.token == "token-two"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_handshake_managed_client_refreshes_moved_endpoint(
    isolated_handshake: Path,
) -> None:
    first = OriginBridgeServer(
        ("127.0.0.1", 0),
        token="token-one",
        generation="generation-one",
        lease_id="generation-one",
        client=FakeOriginClient(),
    )
    first_thread = threading.Thread(target=first.serve_forever, daemon=True)
    first_thread.start()
    second = OriginBridgeServer(
        ("127.0.0.1", 0),
        token="token-two",
        generation="generation-two",
        lease_id="generation-two",
        client=FakeOriginClient(),
    )
    second_thread = threading.Thread(target=second.serve_forever, daemon=True)
    second_thread.start()
    try:
        first_host, first_port = first.server_address
        second_host, second_port = second.server_address
        assert first_port != second_port
        bridge_handshake.write_handshake(
            first_host,
            first_port,
            "token-one",
            generation="generation-one",
            lease_id="generation-one",
        )
        client = OriginBridgeClient(OriginBridgeConfig.from_env(timeout=0.25))

        bridge_handshake.write_handshake(
            second_host,
            second_port,
            "token-two",
            generation="generation-two",
            lease_id="generation-two",
        )
        first.shutdown()
        first.server_close()
        first_thread.join(timeout=2)

        result = client.request("ping")
        assert result["generation"] == "generation-two"
        assert client.config.port == second_port
        assert client.config.token == "token-two"
    finally:
        first.shutdown()
        first.server_close()
        first_thread.join(timeout=2)
        second.shutdown()
        second.server_close()
        second_thread.join(timeout=2)


def test_bridge_clients_have_distinct_client_ids() -> None:
    config = OriginBridgeConfig()
    assert OriginBridgeClient(config).client_id != OriginBridgeClient(config).client_id
