"""Shared pytest fixtures for origin-mcp tests."""

from __future__ import annotations

import pandas as pd
import pytest
from fake_origin import FakeOp

from origin_mcp.origin_client import OriginClient


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
