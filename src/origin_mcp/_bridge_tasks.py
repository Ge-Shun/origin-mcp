from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ._bridge_dispatch import TASKABLE_METHODS, call_origin_method
from ._bridge_protocol import error_code, json_safe
from .errors import OriginOperationError
from .origin_client import OriginClient

DEFAULT_MAX_TASKS = 200
TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled"}


@dataclass
class BridgeTask:
    task_id: str
    method: str
    params: dict[str, Any]
    status: str = "queued"
    submitted_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    cancel_requested: bool = False

    def as_dict(self, include_result: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "task_id": self.task_id,
            "method": self.method,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cancel_requested": self.cancel_requested,
        }
        if include_result:
            if self.result is not None:
                data["result"] = self.result
            if self.error is not None:
                data["error"] = self.error
        return data


class BridgeTaskManager:
    def __init__(self, client: OriginClient, max_tasks: int = DEFAULT_MAX_TASKS) -> None:
        self._client = client
        self._max_tasks = max(1, max_tasks)
        self._tasks: dict[str, BridgeTask] = {}
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._work, daemon=True, name="origin-mcp-bridge")
        self._worker.start()

    def submit(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method not in TASKABLE_METHODS:
            raise OriginOperationError(
                f"Unsupported bridge task method: {method}",
                error_code="unsupported_bridge_task_method",
            )
        task = BridgeTask(task_id=str(uuid.uuid4()), method=method, params=params)
        with self._lock:
            self._tasks[task.task_id] = task
            self._prune_locked()
        self._queue.put(task.task_id)
        return {"task": task.as_dict(include_result=False)}

    def status(self, task_id: str) -> dict[str, Any]:
        return {"task": self._get_task(task_id).as_dict()}

    def cancel(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise OriginOperationError(
                    f"Bridge task not found: {task_id}",
                    error_code="bridge_task_not_found",
                )
            was_queued = task.status == "queued"
            if task.status == "queued":
                task.status = "cancelled"
                task.cancel_requested = True
                task.finished_at = time.time()
                changed = True
            elif task.status in TERMINAL_TASK_STATUSES:
                changed = False
            else:
                task.cancel_requested = True
                changed = True
            return {
                "cancel_requested": task.cancel_requested,
                "changed": changed,
                "interruptible": was_queued,
                "task": task.as_dict(),
            }

    def list_tasks(self, limit: int = 20) -> dict[str, Any]:
        if limit < 1:
            raise OriginOperationError("Task list limit must be at least 1.")
        with self._lock:
            tasks = sorted(
                self._tasks.values(),
                key=lambda task: task.submitted_at,
                reverse=True,
            )[: min(limit, 100)]
            return {"tasks": [task.as_dict(include_result=False) for task in tasks]}

    def _get_task(self, task_id: str) -> BridgeTask:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise OriginOperationError(
                    f"Bridge task not found: {task_id}",
                    error_code="bridge_task_not_found",
                )
            return task

    def _work(self) -> None:
        while True:
            task_id = self._queue.get()
            try:
                task = self._start_task(task_id)
                if task is None:
                    continue
                try:
                    result = call_origin_method(self._client, task.method, task.params)
                except Exception as exc:
                    self._finish_task(task_id, error=exc)
                else:
                    self._finish_task(task_id, result=result)
            finally:
                self._queue.task_done()

    def _start_task(self, task_id: str) -> BridgeTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != "queued":
                return None
            task.status = "running"
            task.started_at = time.time()
            return task

    def _finish_task(
        self,
        task_id: str,
        result: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task.finished_at = time.time()
            if error is not None:
                task.status = "failed"
                task.error = {
                    "message": str(error),
                    "error_code": error_code(error),
                    "error_type": type(error).__name__,
                }
            else:
                task.status = "completed"
                task.result = json_safe(result or {})
            self._prune_locked()

    def _prune_locked(self) -> None:
        overflow = len(self._tasks) - self._max_tasks
        if overflow <= 0:
            return
        removable = sorted(
            (
                task
                for task in self._tasks.values()
                if task.status in TERMINAL_TASK_STATUSES
            ),
            key=lambda task: task.submitted_at,
        )
        for task in removable[:overflow]:
            self._tasks.pop(task.task_id, None)

