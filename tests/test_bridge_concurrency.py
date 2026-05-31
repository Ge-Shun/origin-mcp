"""The bridge serves synchronous requests and async tasks on different
threads, but originpro drives Origin's single UI thread. These tests verify
that the dispatch layer serializes Origin calls through the client lock.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from origin_mcp import _bridge_dispatch


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
