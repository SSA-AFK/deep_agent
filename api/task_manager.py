"""Single-process task lifecycle with bounded, replayable public events."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from collections.abc import Awaitable, Callable
from typing import Any


class TaskState(StrEnum):
    PLANNING = "planning"
    WAITING_CONFIRMATION = "waiting_confirmation"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL = {TaskState.SUCCEEDED, TaskState.FAILED, TaskState.CANCELLED}
_ALLOWED = {
    TaskState.PLANNING: {TaskState.WAITING_CONFIRMATION, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.WAITING_CONFIRMATION: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING: {TaskState.SUCCEEDED, TaskState.FAILED, TaskState.CANCELLED},
}


@dataclass
class ManagedTask:
    thread_id: str
    query: str
    state: TaskState = TaskState.PLANNING
    sequence: int = 0
    events: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))
    result: str | None = None
    error: dict[str, Any] | None = None
    background_task: asyncio.Task | None = None


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, ManagedTask] = {}
        self._lock = asyncio.Lock()
        self._listeners: list[Callable[[dict[str, Any]], Awaitable[None]]] = []

    def subscribe(self, listener: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    async def create(self, thread_id: str, query: str) -> ManagedTask:
        async with self._lock:
            if thread_id in self._tasks:
                raise ValueError("Task ID already exists.")
            task = ManagedTask(thread_id=thread_id, query=query)
            self._tasks[thread_id] = task
            self._emit(task, "task_status", {"state": task.state})
            return task

    async def transition(self, thread_id: str, state: TaskState, data: dict[str, Any] | None = None) -> ManagedTask:
        async with self._lock:
            task = self._require(thread_id)
            if task.state in _TERMINAL or state not in _ALLOWED.get(task.state, set()):
                raise ValueError(f"Invalid transition: {task.state} -> {state}")
            task.state = state
            self._emit(task, "task_status", {"state": state, **(data or {})})
            return task

    async def cancel(self, thread_id: str) -> ManagedTask:
        task = await self.transition(thread_id, TaskState.CANCELLED)
        if task.background_task:
            task.background_task.cancel()
        return task

    async def snapshot(self, thread_id: str) -> dict[str, Any]:
        async with self._lock:
            task = self._require(thread_id)
            return {"thread_id": task.thread_id, "state": task.state, "sequence": task.sequence, "result": task.result, "error": task.error, "events": list(task.events)}

    def _require(self, thread_id: str) -> ManagedTask:
        if thread_id not in self._tasks:
            raise KeyError(thread_id)
        return self._tasks[thread_id]

    def _emit(self, task: ManagedTask, event_type: str, data: dict[str, Any]) -> None:
        task.sequence += 1
        event = {"version": 1, "sequence": task.sequence, "type": event_type, "thread_id": task.thread_id, "timestamp": datetime.now(timezone.utc).isoformat(), "data": data}
        task.events.append(event)
        for listener in self._listeners:
            asyncio.create_task(listener(event))


task_manager = TaskManager()
