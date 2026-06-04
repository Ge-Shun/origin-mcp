from __future__ import annotations

import queue
import threading
import time
import uuid
from collections.abc import Callable
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
    updated_at: float = field(default_factory=time.time)
    progress: float | None = None
    current_step: str | None = "Queued"
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    logs: list[dict[str, Any]] = field(default_factory=list)
    cancel_requested: bool = False

    def as_dict(
        self,
        include_result: bool = True,
        *,
        include_logs: bool = False,
        log_limit: int = 20,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "task_id": self.task_id,
            "method": self.method,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "updated_at": self.updated_at,
            "progress": self.progress,
            "current_step": self.current_step,
            "cancel_requested": self.cancel_requested,
        }
        if include_result:
            if self.result is not None:
                data["result"] = self.result
            if self.error is not None:
                data["error"] = self.error
        if include_logs:
            limit = max(1, min(int(log_limit), 100))
            data["logs"] = self.logs[-limit:]
        return data


class BridgeTaskManager:
    def __init__(
        self,
        client: OriginClient,
        max_tasks: int = DEFAULT_MAX_TASKS,
        *,
        use_worker_thread: bool = True,
    ) -> None:
        self._client = client
        self._max_tasks = max(1, max_tasks)
        self._tasks: dict[str, BridgeTask] = {}
        self._queue: queue.Queue[str] = queue.Queue()
        self._lock = threading.Lock()
        # The threaded bridge runs Origin calls off a dedicated worker thread.
        # The embedded cooperative bridge must keep originpro on Origin's UI
        # thread, so it owns no worker and drains the queue via ``pump_pending``
        # from its serving loop instead.
        self._use_worker_thread = use_worker_thread
        self._worker: threading.Thread | None = None
        if use_worker_thread:
            self._worker = threading.Thread(
                target=self._work, daemon=True, name="origin-mcp-bridge"
            )
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

    def status(
        self,
        task_id: str,
        *,
        include_logs: bool = False,
        log_limit: int = 20,
        include_result: bool = True,
    ) -> dict[str, Any]:
        return {
            "task": self._get_task(task_id).as_dict(
                include_result=include_result,
                include_logs=include_logs,
                log_limit=log_limit,
            )
        }

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
                task.updated_at = task.finished_at
                task.progress = task.progress if task.progress is not None else 0.0
                task.current_step = "Cancelled before start"
                task.logs.append(
                    {
                        "time": task.finished_at,
                        "level": "info",
                        "message": "Task cancelled before it started.",
                    }
                )
                changed = True
            elif task.status in TERMINAL_TASK_STATUSES:
                changed = False
            else:
                task.cancel_requested = True
                task.updated_at = time.time()
                task.logs.append(
                    {
                        "time": task.updated_at,
                        "level": "warning",
                        "message": (
                            "Cancellation requested; running Origin calls stop at the next "
                            "safe point."
                        ),
                    }
                )
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
                self._run_one(task_id)
            finally:
                self._queue.task_done()

    def pump_pending(self, max_items: int | None = None) -> int:
        """Run queued tasks on the calling thread; return the number executed.

        The embedded cooperative bridge has no worker thread because originpro
        must stay on Origin's UI thread. Its serving loop calls this between
        ``handle_request`` cycles to drain the queue on that thread. ``submit``
        only enqueues, so the async ``submit_task``/``task_status`` contract is
        unchanged -- execution simply moves onto the serving (UI) thread.
        """

        executed = 0
        while max_items is None or executed < max_items:
            try:
                task_id = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                self._run_one(task_id)
            finally:
                self._queue.task_done()
            executed += 1
        return executed

    def _run_one(self, task_id: str) -> None:
        task = self._start_task(task_id)
        if task is None:
            return
        try:
            result = call_origin_method(
                self._client,
                task.method,
                task.params,
                progress=self._progress_callback(task_id),
            )
        except Exception as exc:
            self._finish_task(task_id, error=exc)
        else:
            self._finish_task(task_id, result=result)

    def _start_task(self, task_id: str) -> BridgeTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != "queued":
                return None
            task.status = "running"
            now = time.time()
            task.started_at = now
            task.updated_at = now
            task.progress = 0.0
            task.current_step = "Starting"
            task.logs.append({"time": now, "level": "info", "message": "Task started."})
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
            task.updated_at = task.finished_at
            if error is not None:
                task.status = "failed"
                task.current_step = "Failed"
                task.error = {
                    "message": str(error),
                    "error_code": error_code(error),
                    "error_type": type(error).__name__,
                }
                task.logs.append(
                    {
                        "time": task.finished_at,
                        "level": "error",
                        "message": str(error),
                        "error_code": task.error["error_code"],
                    }
                )
            else:
                task.status = "completed"
                task.progress = 1.0
                task.current_step = "Completed"
                task.result = json_safe(result or {})
                task.logs.append(
                    {"time": task.finished_at, "level": "info", "message": "Task completed."}
                )
            self._prune_locked()

    def _progress_callback(self, task_id: str) -> Callable[[float | None, str, str | None], None]:
        def update(progress: float | None, step: str, message: str | None = None) -> None:
            self._update_progress(task_id, progress=progress, step=step, message=message)

        return update

    def _update_progress(
        self,
        task_id: str,
        *,
        progress: float | None,
        step: str,
        message: str | None,
    ) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status in TERMINAL_TASK_STATUSES:
                return
            now = time.time()
            task.updated_at = now
            if progress is not None:
                task.progress = max(0.0, min(float(progress), 1.0))
            if step:
                task.current_step = step
            if message:
                last = task.logs[-1]["message"] if task.logs else None
                if last != message:
                    task.logs.append({"time": now, "level": "info", "message": message})

    def _prune_locked(self) -> None:
        overflow = len(self._tasks) - self._max_tasks
        if overflow <= 0:
            return
        removable = sorted(
            (task for task in self._tasks.values() if task.status in TERMINAL_TASK_STATUSES),
            key=lambda task: task.submitted_at,
        )
        for task in removable[:overflow]:
            self._tasks.pop(task.task_id, None)
