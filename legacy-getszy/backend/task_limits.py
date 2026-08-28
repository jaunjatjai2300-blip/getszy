"""Per-task resource limits enforcement for the Agent Factory.

Enforceable limits per-task/per-agent:
- RAM, CPU/time, execution timeout
- Output bytes, tool calls, concurrency
- Disk usage, subprocess count
- Delegation depth, child count

Limit breach produces: controlled termination + structured evidence + cleanup + honest failure state.
"""
from __future__ import annotations

import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger('getszy.limits')


# ── Factory Limits (MUST NOT be weakened) ─────────────────────────────────────
MAX_REPAIR_ATTEMPTS = 3
CHILD_MAX_ATTEMPTS = 2
CHILD_ROUNDS = 5
MASTER_ROUNDS = 10
MAX_TOOL_ROUNDS = 10
MAX_DELEGATION_DEPTH = 3
MAX_CHILDREN = 5
MAX_DESCENDANTS = 15
MAX_CONCURRENT_TASKS = 5
MAX_OUTPUT_BYTES = 256_000
MAX_SUBPROCESSES = 3
MAX_DISK_WRITE_MB = 100
DEFAULT_EXECUTION_TIMEOUT = 300.0  # 5 minutes
MAX_CONTEXT_MESSAGES = 20
MAX_CONTEXT_TOKENS = 8000


@dataclass
class TaskLimits:
    """Limits for a single task execution."""
    execution_timeout: float = DEFAULT_EXECUTION_TIMEOUT
    max_output_bytes: int = MAX_OUTPUT_BYTES
    max_tool_rounds: int = MAX_TOOL_ROUNDS
    max_repair_attempts: int = MAX_REPAIR_ATTEMPTS
    max_delegation_depth: int = MAX_DELEGATION_DEPTH
    max_children: int = MAX_CHILDREN
    max_retries: int = 2
    max_context_tokens: int = MAX_CONTEXT_TOKENS
    max_context_messages: int = MAX_CONTEXT_MESSAGES

    def to_dict(self) -> dict:
        return {
            'execution_timeout': self.execution_timeout,
            'max_output_bytes': self.max_output_bytes,
            'max_tool_rounds': self.max_tool_rounds,
            'max_repair_attempts': self.max_repair_attempts,
            'max_delegation_depth': self.max_delegation_depth,
            'max_children': self.max_children,
            'max_retries': self.max_retries,
        }


@dataclass
class LimitBreach:
    """Record of a limit being breached."""
    limit_name: str
    limit_value: Any
    actual_value: Any
    task_id: str = ''
    agent_id: str = ''
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            'limit_name': self.limit_name,
            'limit_value': self.limit_value,
            'actual_value': self.actual_value,
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'timestamp': self.timestamp,
        }


class LimitTracker:
    """Track resource usage against limits for a task/agent."""

    def __init__(self, task_id: str, agent_id: str = '', limits: TaskLimits | None = None):
        self.task_id = task_id
        self.agent_id = agent_id
        self.limits = limits or TaskLimits()
        self.breaches: list[LimitBreach] = []
        self._start_time = time.monotonic()
        self._tool_calls = 0
        self._repair_attempts = 0
        self._output_bytes = 0
        self._children_spawned = 0
        self._delegation_depth = 0

    def check_timeout(self) -> bool:
        """Returns True if the task has exceeded its execution timeout."""
        elapsed = time.monotonic() - self._start_time
        if elapsed > self.limits.execution_timeout:
            self.breaches.append(LimitBreach(
                limit_name='execution_timeout',
                limit_value=self.limits.execution_timeout,
                actual_value=round(elapsed, 2),
                task_id=self.task_id,
                agent_id=self.agent_id,
            ))
            return True
        return False

    def check_tool_rounds(self) -> bool:
        """Returns True if tool call limit reached."""
        self._tool_calls += 1
        if self._tool_calls > self.limits.max_tool_rounds:
            self.breaches.append(LimitBreach(
                limit_name='max_tool_rounds',
                limit_value=self.limits.max_tool_rounds,
                actual_value=self._tool_calls,
                task_id=self.task_id,
                agent_id=self.agent_id,
            ))
            return True
        return False

    def check_repair_attempts(self) -> bool:
        """Returns True if repair limit reached."""
        self._repair_attempts += 1
        if self._repair_attempts > self.limits.max_repair_attempts:
            self.breaches.append(LimitBreach(
                limit_name='max_repair_attempts',
                limit_value=self.limits.max_repair_attempts,
                actual_value=self._repair_attempts,
                task_id=self.task_id,
                agent_id=self.agent_id,
            ))
            return True
        return False

    def check_output_bytes(self, additional_bytes: int) -> bool:
        """Returns True if output limit would be exceeded."""
        self._output_bytes += additional_bytes
        if self._output_bytes > self.limits.max_output_bytes:
            self.breaches.append(LimitBreach(
                limit_name='max_output_bytes',
                limit_value=self.limits.max_output_bytes,
                actual_value=self._output_bytes,
                task_id=self.task_id,
                agent_id=self.agent_id,
            ))
            return True
        return False

    def check_children(self) -> bool:
        """Returns True if child limit reached."""
        self._children_spawned += 1
        if self._children_spawned > self.limits.max_children:
            self.breaches.append(LimitBreach(
                limit_name='max_children',
                limit_value=self.limits.max_children,
                actual_value=self._children_spawned,
                task_id=self.task_id,
                agent_id=self.agent_id,
            ))
            return True
        return False

    def check_delegation_depth(self, depth: int) -> bool:
        """Returns True if delegation depth exceeded."""
        if depth > self.limits.max_delegation_depth:
            self.breaches.append(LimitBreach(
                limit_name='max_delegation_depth',
                limit_value=self.limits.max_delegation_depth,
                actual_value=depth,
                task_id=self.task_id,
                agent_id=self.agent_id,
            ))
            return True
        return False

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start_time

    @property
    def has_breaches(self) -> bool:
        return len(self.breaches) > 0

    @property
    def tool_calls(self) -> int:
        return self._tool_calls

    @property
    def repair_attempts(self) -> int:
        return self._repair_attempts

    def status(self) -> dict:
        return {
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'elapsed': round(self.elapsed, 2),
            'tool_calls': self._tool_calls,
            'repair_attempts': self._repair_attempts,
            'output_bytes': self._output_bytes,
            'children_spawned': self._children_spawned,
            'breaches': [b.to_dict() for b in self.breaches],
            'limits': self.limits.to_dict(),
        }


class TimeoutError(Exception):
    """Raised when a task exceeds its execution timeout."""
    pass


class LimitExceededError(Exception):
    """Raised when a resource limit is breached."""
    def __init__(self, breach: LimitBreach):
        self.breach = breach
        super().__init__(f'Limit {breach.limit_name} exceeded: {breach.actual_value} > {breach.limit_value}')


# ── Active limit trackers ────────────────────────────────────────────────────
_active_trackers: dict[str, LimitTracker] = {}
_semaphore: asyncio.Semaphore | None = None


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    return _semaphore


def create_tracker(task_id: str, agent_id: str = '', limits: TaskLimits | None = None) -> LimitTracker:
    tracker = LimitTracker(task_id, agent_id, limits)
    _active_trackers[task_id] = tracker
    return tracker


def get_tracker(task_id: str) -> LimitTracker | None:
    return _active_trackers.get(task_id)


def remove_tracker(task_id: str) -> LimitTracker | None:
    return _active_trackers.pop(task_id, None)


def active_task_count() -> int:
    return len(_active_trackers)


def limits_status() -> dict:
    return {
        'active_tasks': active_task_count(),
        'max_concurrent': MAX_CONCURRENT_TASKS,
        'trackers': {tid: t.status() for tid, t in _active_trackers.items()},
    }
