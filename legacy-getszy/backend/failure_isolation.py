"""Failure isolation for the Agent Factory.

A failing model, tool, subprocess, child agent, browser task, or research
request must NOT crash the Factory. Implement:
- Timeout + cancellation
- Subprocess isolation + cleanup
- Exception boundaries
- Stale-process cleanup
- Child failure containment
- Model transport failure handling

A child failure becomes evidence for the parent, not a Factory-wide crash.
"""
from __future__ import annotations

import asyncio
import logging
import signal
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger('getszy.isolation')


class FailureType(Enum):
    MODEL_TIMEOUT = 'model_timeout'
    MODEL_TRANSPORT = 'model_transport'
    TOOL_FAILURE = 'tool_failure'
    TOOL_TIMEOUT = 'tool_timeout'
    SUBPROCESS_CRASH = 'subprocess_crash'
    CHILD_FAILURE = 'child_failure'
    OOM_RISK = 'oom_risk'
    CANCELLATION = 'cancellation'
    UNKNOWN = 'unknown'


@dataclass
class FailureRecord:
    failure_type: FailureType
    message: str
    task_id: str = ''
    agent_id: str = ''
    parent_id: str = ''
    timestamp: float = field(default_factory=time.time)
    attempt: int = 0
    recoverable: bool = True
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'failure_type': self.failure_type.value,
            'message': self.message,
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'parent_id': self.parent_id,
            'timestamp': self.timestamp,
            'attempt': self.attempt,
            'recoverable': self.recoverable,
            'evidence': self.evidence,
        }


# ── Timeout wrapper ───────────────────────────────────────────────────────────

async def with_timeout(
    coro: Coroutine,
    timeout_seconds: float,
    task_id: str = '',
    default: Any = None,
) -> Any:
    """Run a coroutine with a timeout. Returns default on timeout instead of crashing."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning('Task %s timed out after %.1fs', task_id, timeout_seconds)
        return default
    except asyncio.CancelledError:
        logger.warning('Task %s was cancelled', task_id)
        return default


# ── Exception boundary ────────────────────────────────────────────────────────

class ExceptionBoundary:
    """Context manager that catches exceptions and converts them to FailureRecords."""

    def __init__(self, task_id: str = '', agent_id: str = '', parent_id: str = ''):
        self.task_id = task_id
        self.agent_id = agent_id
        self.parent_id = parent_id
        self.failure: FailureRecord | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False
        ft = FailureType.UNKNOWN
        recoverable = True

        if exc_type is asyncio.TimeoutError:
            ft = FailureType.MODEL_TIMEOUT
        elif exc_type is asyncio.CancelledError:
            ft = FailureType.CANCELLATION
        elif exc_type is ConnectionError or exc_type is OSError:
            ft = FailureType.MODEL_TRANSPORT
        elif exc_type is MemoryError:
            ft = FailureType.OOM_RISK
            recoverable = False

        self.failure = FailureRecord(
            failure_type=ft,
            message=str(exc_val)[:500],
            task_id=self.task_id,
            agent_id=self.agent_id,
            parent_id=self.parent_id,
            recoverable=recoverable,
            evidence={'exception_type': exc_type.__name__ if exc_type else 'None'},
        )
        logger.error('FAILURE ISOLATED [%s] %s: %s (recoverable=%s)',
                      self.agent_id or self.task_id, ft.value, self.failure.message, recoverable)
        return True  # suppress the exception


# ── Subprocess isolation ──────────────────────────────────────────────────────

async def isolated_subprocess(
    cmd: list[str],
    timeout: float = 60.0,
    max_output_bytes: int = 32_000,
    task_id: str = '',
) -> dict:
    """Run a subprocess with timeout, output bounding, and cleanup.

    Returns {'returncode', 'stdout', 'stderr', 'timed_out', 'killed'}.
    """
    proc = None
    timed_out = False
    killed = False
    try:
        # On Windows, use shell=True for commands like 'echo' and 'sleep'
        import sys as _sys
        use_shell = _sys.platform == 'win32'
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=use_shell,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
            logger.warning('Subprocess timed out after %.1fs: %s', timeout, cmd[0] if cmd else '?')
            try:
                proc.kill()
                killed = True
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
            stdout = b''
            stderr = b'subprocess killed: timeout'

        stdout_text = (stdout or b'')[:max_output_bytes].decode('utf-8', errors='replace')
        stderr_text = (stderr or b'')[:max_output_bytes].decode('utf-8', errors='replace')

        return {
            'returncode': proc.returncode,
            'stdout': stdout_text,
            'stderr': stderr_text,
            'timed_out': timed_out,
            'killed': killed,
            'task_id': task_id,
        }
    except Exception as e:
        if proc and proc.returncode is None:
            try:
                proc.kill()
            except Exception:
                pass
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': str(e)[:max_output_bytes],
            'timed_out': False,
            'killed': False,
            'task_id': task_id,
        }


# ── Stale process cleanup ────────────────────────────────────────────────────

async def cleanup_stale_processes(max_age_seconds: float = 600.0) -> int:
    """Find and kill stale child processes older than max_age_seconds."""
    cleaned = 0
    try:
        import psutil
        current_pid = __import__('os').getpid()
        for proc in psutil.process_iter(['pid', 'create_time', 'cmdline']):
            try:
                info = proc.info
                age = time.time() - info.get('create_time', time.time())
                cmdline = ' '.join(info.get('cmdline') or [])
                if (age > max_age_seconds and
                    current_pid != info['pid'] and
                    any(marker in cmdline for marker in ['ollama', 'node', 'python'])):
                    logger.warning('Cleaning stale process pid=%d age=%.0fs cmd=%s',
                                   info['pid'], age, cmdline[:100])
                    proc.kill()
                    cleaned += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        pass
    return cleaned


# ── Child failure containment ─────────────────────────────────────────────────

def child_failure_to_evidence(failure: FailureRecord, parent_task_id: str) -> dict:
    """Convert a child failure into structured evidence for the parent.

    The parent's repair loop uses this to decide the next strategy.
    """
    return {
        'source': 'child_failure',
        'child_task_id': failure.task_id,
        'child_agent_id': failure.agent_id,
        'failure_type': failure.failure_type.value,
        'message': failure.message,
        'recoverable': failure.recoverable,
        'parent_task_id': parent_task_id,
        'evidence': failure.evidence,
        'recommendation': _recommend_strategy(failure),
    }


def _recommend_strategy(failure: FailureRecord) -> str:
    """Recommend a repair strategy based on failure type."""
    strategies = {
        FailureType.MODEL_TIMEOUT: 'increase_timeout_or_switch_provider',
        FailureType.MODEL_TRANSPORT: 'retry_with_different_provider',
        FailureType.TOOL_FAILURE: 'skip_tool_or_use_fallback',
        FailureType.TOOL_TIMEOUT: 'increase_tool_timeout',
        FailureType.SUBPROCESS_CRASH: 'retry_or_skip_subprocess',
        FailureType.OOM_RISK: 'degrade_task_or_reject',
        FailureType.CANCELLATION: 'do_not_retry',
        FailureType.UNKNOWN: 'retry_with_evidence',
    }
    return strategies.get(failure.failure_type, 'retry_with_evidence')
