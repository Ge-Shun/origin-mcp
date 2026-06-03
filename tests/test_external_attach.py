"""Tests for external-mode attach-to-running-Origin behavior.

When originpro runs external (OriginExt) the bridge should attach to the running
Origin via the wrapper's ``Attach()`` instead of letting the first call spawn a
new instance. See ``_OriginClientBase._attach_external_origin_if_needed``.
"""

from __future__ import annotations

import types
from typing import Any

import pytest

from origin_mcp.origin_client import OriginClient


class _PoWrapper:
    def __init__(self) -> None:
        self.attached = 0

    def Attach(self) -> None:  # noqa: N802 - mirrors originpro APP.Attach
        self.attached += 1


def _fake_originpro(oext: bool, po: Any) -> types.ModuleType:
    mod = types.ModuleType("originpro")
    cfg = types.ModuleType("originpro.config")
    cfg.oext = oext
    cfg.po = po
    mod.config = cfg
    return mod


def test_attaches_when_external(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORIGIN_MCP_NO_ATTACH", raising=False)
    po = _PoWrapper()
    client = OriginClient()
    client._op = _fake_originpro(oext=True, po=po)

    client._attach_external_origin_if_needed()

    assert po.attached == 1


def test_noop_when_embedded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORIGIN_MCP_NO_ATTACH", raising=False)
    po = _PoWrapper()
    client = OriginClient()
    client._op = _fake_originpro(oext=False, po=po)

    client._attach_external_origin_if_needed()

    assert po.attached == 0


def test_opt_out_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORIGIN_MCP_NO_ATTACH", "1")
    po = _PoWrapper()
    client = OriginClient()
    client._op = _fake_originpro(oext=True, po=po)

    client._attach_external_origin_if_needed()

    assert po.attached == 0


def test_attach_failure_is_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORIGIN_MCP_NO_ATTACH", raising=False)

    class _Boom:
        def Attach(self) -> None:  # noqa: N802
            raise RuntimeError("COM not ready")

    client = OriginClient()
    client._op = _fake_originpro(oext=True, po=_Boom())

    # Must not raise.
    client._attach_external_origin_if_needed()
