"""The bridge serves synchronous requests and async tasks on different
threads, but originpro drives Origin's single UI thread. These tests verify
that the dispatch layer serializes Origin calls through the client lock.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from origin_mcp import _bridge_dispatch
from origin_mcp._bridge_server import OriginBridgeHandler, OriginBridgeServer
from origin_mcp.errors import OriginOperationError


class _ConcurrencyTrackingClient:
    def __init__(
        self,
        lock: threading.RLock | None = None,
        barrier: threading.Barrier | None = None,
    ) -> None:
        if lock is not None:
            self._origin_call_lock = lock
        self._barrier = barrier
        self._guard = threading.Lock()
        self.active = 0
        self.max_active = 0

    def run_labtalk(self, script: str) -> dict[str, Any]:
        if self._barrier is not None:
            # Force every caller to arrive before any proceeds, so a missing
            # lock deterministically produces overlap instead of relying on
            # scheduling luck.
            self._barrier.wait(timeout=2.0)
        with self._guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.02)
        with self._guard:
            self.active -= 1
        return {"script": script}


def _hammer(client: _ConcurrencyTrackingClient, n: int) -> None:
    threads = [
        threading.Thread(
            target=lambda: _bridge_dispatch.call_origin_method(
                client, "run_labtalk", {"script": "x"}
            )
        )
        for _ in range(n)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5.0)


def test_origin_calls_are_serialized_when_client_has_lock() -> None:
    client = _ConcurrencyTrackingClient(lock=threading.RLock())

    _hammer(client, n=8)

    # The lock guarantees mutual exclusion regardless of scheduling.
    assert client.max_active == 1


def test_origin_calls_overlap_without_a_lock() -> None:
    # Control case: with no lock, concurrent dispatch genuinely overlaps,
    # confirming the serialization above comes from the lock and not the test.
    n = 4
    client = _ConcurrencyTrackingClient(lock=None, barrier=threading.Barrier(n))

    _hammer(client, n=n)

    assert client.max_active == n


@pytest.mark.parametrize(
    "release_origin,close_origin", [(True, False), (True, True), (False, False)]
)
@pytest.mark.parametrize("as_task", [False, True])
def test_shutdown_waits_for_origin_and_cancels_pending_tasks(
    release_origin: bool, close_origin: bool, as_task: bool
) -> None:
    class Client:
        def __init__(self) -> None:
            self._origin_call_lock = threading.RLock()
            self.started = threading.Event()
            self.finish = threading.Event()
            self.calls: list[str] = []

        def run_labtalk(self, script: str) -> dict[str, Any]:
            self.calls.append(script)
            self.started.set()
            assert self.finish.wait(5)
            self.calls.append("finished")
            return {"result": True}

        def detach(self) -> dict[str, Any]:
            self.calls.append("detach")
            return {"detached": True}

        def force_quit(self) -> dict[str, Any]:
            self.calls.append("force_quit")
            return {"closed": True}

    client = Client()
    server = OriginBridgeServer(("127.0.0.1", 0), client=client)
    handler = object.__new__(OriginBridgeHandler)
    handler.server = server
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            if as_task:
                first = server.tasks.submit("run_labtalk", {"script": "running"})["task"]["task_id"]
            else:
                running = pool.submit(
                    handler._call,
                    "call_client",
                    {"method": "run_labtalk", "kwargs": {"script": "running"}},
                )
            try:
                assert client.started.wait(2)
                queued = server.tasks.submit("run_labtalk", {"script": "queued"})["task"]["task_id"]
            except BaseException:
                client.finish.set()
                raise
            stopped = pool.submit(
                handler._shutdown_bridge,
                {"release_origin": release_origin, "close_origin": close_origin},
            )
            try:
                assert server.stopping_requested.wait(2)
                assert not server.shutdown_requested.is_set()
                assert not stopped.done()
                assert client.calls == ["running"]
                assert server.tasks.status(queued)["task"]["status"] == "cancelled"
                with pytest.raises(OriginOperationError) as excinfo:
                    server.tasks.submit("run_labtalk", {"script": "new"})
                assert excinfo.value.error_code == "origin_bridge_shutting_down"
            finally:
                client.finish.set()
            result = stopped.result(timeout=2)
            if as_task:
                assert server.tasks.status(first)["task"]["status"] == "completed"
            else:
                assert running.result(timeout=2)["value"] == {"result": True}
        assert result["shutdown_requested"] is True
        assert server.shutdown_requested.is_set()
        expected = ["running", "finished"]
        if release_origin:
            expected.append("force_quit" if close_origin else "detach")
        assert client.calls == expected
        for method, params in (
            ("call_client", {"method": "run_labtalk", "kwargs": {"script": "late"}}),
            ("run_labtalk", {"script": "late"}),
        ):
            with pytest.raises(OriginOperationError) as excinfo:
                handler._call(method, params)
            assert excinfo.value.error_code == "origin_bridge_shutting_down"
        assert handler._shutdown_bridge({"close_origin": True}) == result
        assert client.calls == expected
        server.tasks._worker.join(timeout=2)
        assert not server.tasks._worker.is_alive()
    finally:
        client.finish.set()
        server.shutdown()
        server.server_close()
