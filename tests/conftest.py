"""Shared pytest fixtures for origin-mcp tests."""

from __future__ import annotations

from collections.abc import Iterator

import pandas as pd
import pytest
from fake_origin import FakeOp

from origin_mcp import bridge_client
from origin_mcp.origin_client import OriginClient
from origin_mcp.tools import _shared


@pytest.fixture(autouse=True)
def _reset_bridge_client_caches() -> Iterator[None]:
    """Isolate the process-wide bridge connection caches between tests.

    Bridge sockets are pooled by config (``bridge_client._shared_clients``) and
    fronted by the ``_shared.client`` proxy facade, both of which live for the
    whole process. Tests spin up many short-lived bridges that often reuse the
    same localhost port, so a socket pooled for one test would otherwise leak
    into the next and connect to a defunct server. Clearing both caches around
    each test keeps connections deterministic.
    """

    def _reset() -> None:
        bridge_client.close_shared_bridge_clients()
        _shared.client._proxy = None
        _shared.client._config = None

    _reset()
    yield
    _reset()


@pytest.fixture
def fake_op() -> FakeOp:
    """A fresh in-memory fake ``originpro`` module."""

    return FakeOp()


@pytest.fixture
def fake_client(fake_op: FakeOp) -> OriginClient:
    """An ``OriginClient`` wired to the in-memory fake originpro.

    Injecting ``_op`` short-circuits the lazy ``op`` property so no real
    ``originpro`` import is attempted. ``client.op`` is the same ``FakeOp``,
    so tests can seed books with ``client.op.add_book(...)``.
    """

    client = OriginClient()
    client._op = fake_op
    return client


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4],
            "y": [10.0, 20.0, 30.0, 40.0],
        }
    )
