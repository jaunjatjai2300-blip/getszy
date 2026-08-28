"""Resource admission — memory-aware execution gate for the Agent Factory.

VPS constraint: ~7.9 GB RAM total. Running Ollama qwen2.5-coder:7b (~5 GB)
plus backend + MongoDB + Redis + frontend leaves tight margins.

This module provides deterministic resource admission:
  AVAILABLE MEMORY -> RESOURCE ESTIMATE -> ADMISSION DECISION
  -> RUN / DEGRADE / QUEUE / CONTROLLED REJECT

Never intentionally triggers OOM. If resources are insufficient, reject cleanly
with structured evidence. Factory model boundary: LOCAL OLLAMA ONLY.
"""
from __future__ import annotations

import os
import logging
import subprocess
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger('getszy.resources')


class AdmissionDecision(Enum):
    RUN = 'run'
    DEGRADE = 'degrade'
    QUEUE = 'queue'
    REJECT = 'reject'


@dataclass
class SystemMemory:
    total_mb: int = 0
    available_mb: int = 0
    used_mb: int = 0
    usage_pct: float = 0.0
    ollama_mb: int = 0  # estimated current Ollama process memory

    @property
    def free_mb(self) -> int:
        return self.available_mb


@dataclass
class ResourceEstimate:
    """Estimated resource cost for a task."""
    estimated_ram_mb: int = 0
    timeout_seconds: float = 300.0
    max_output_bytes: int = 100_000
    max_tool_rounds: int = 10
    requires_llm: bool = True
    task_type: str = 'unknown'


@dataclass
class AdmissionResult:
    decision: AdmissionDecision
    reason: str
    available_mb: int = 0
    required_mb: int = 0
    degraded: bool = False
    queue_position: int = 0

    def to_dict(self) -> dict:
        return {
            'decision': self.decision.value,
            'reason': self.reason,
            'available_mb': self.available_mb,
            'required_mb': self.required_mb,
            'degraded': self.degraded,
            'queue_position': self.queue_position,
        }


# ── Thresholds ────────────────────────────────────────────────────────────────
# Below this, we refuse to start new LLM-heavy tasks
REJECT_THRESHOLD_MB = 512

# Below this, we degrade (reduce max_tokens, skip polish, simpler prompts)
DEGRADE_THRESHOLD_MB = 1024

# Estimated RAM for various task types (conservative)
TASK_RAM_ESTIMATES = {
    'llm_call': 150,           # one LLM HTTP call
    'builder_pipeline': 400,   # full plan->design->code->review
    'builder_fast': 200,       # fast single-call composition
    'builder_polish': 150,     # background polish
    'tool_execution': 50,      # tool call
    'browser_task': 300,       # playwright/browser if added later
    'video_generation': 500,   # video factory chain step
    'research': 100,           # web search + analysis
    'default': 200,
}

# Ollama model RAM estimates (model loaded in VRAM/RAM)
OLLAMA_MODEL_RAM_MB = {
    'qwen2.5:7b': 4500,
    'qwen2.5-coder:7b': 4500,
    'qwen2.5:14b': 9000,
    'llama3.2:3b': 2000,
    'qwen3.6-27b': 14000,
}

# System overhead (backend process + MongoDB + Redis + OS)
SYSTEM_OVERHEAD_MB = 2048


def _read_system_memory() -> SystemMemory:
    """Read system memory via /proc/meminfo (Linux) or psutil fallback."""
    mem = SystemMemory()
    try:
        # Try /proc/meminfo first (Linux, zero deps)
        with open('/proc/meminfo', 'r') as f:
            info = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(':')
                    info[key] = int(parts[1])  # in kB
            mem.total_mb = info.get('MemTotal', 0) // 1024
            mem.available_mb = info.get('MemAvailable', 0) // 1024
            mem.used_mb = mem.total_mb - mem.available_mb
            mem.usage_pct = (mem.used_mb / mem.total_mb * 100) if mem.total_mb > 0 else 0
            return mem
    except (FileNotFoundError, PermissionError):
        pass

    # Fallback: try psutil
    try:
        import psutil
        vm = psutil.virtual_memory()
        mem.total_mb = vm.total // (1024 * 1024)
        mem.available_mb = vm.available // (1024 * 1024)
        mem.used_mb = mem.total_mb - mem.available_mb
        mem.usage_pct = vm.percent
        return mem
    except ImportError:
        pass

    # Last resort: assume constrained VPS
    logger.warning('Cannot read system memory; assuming 8GB VPS')
    mem.total_mb = 8192
    mem.available_mb = 4096
    mem.used_mb = 4096
    mem.usage_pct = 50.0
    return mem


def _estimate_ollama_memory() -> int:
    """Estimate current Ollama process RAM usage in MB."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'ollama'],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode != 0:
            return 0
        pids = result.stdout.strip().split('\n')
        total_kb = 0
        for pid in pids:
            pid = pid.strip()
            if not pid:
                continue
            try:
                with open(f'/proc/{pid}/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            total_kb += int(line.split()[1])
                            break
            except (FileNotFoundError, PermissionError, IndexError):
                pass
        return total_kb // 1024
    except Exception:
        return 0


def get_system_memory() -> SystemMemory:
    """Get current system memory state."""
    mem = _read_system_memory()
    mem.ollama_mb = _estimate_ollama_memory()
    return mem


def estimate_task_resources(task_type: str, **kwargs) -> ResourceEstimate:
    """Estimate resource requirements for a given task type."""
    base_ram = TASK_RAM_ESTIMATES.get(task_type, TASK_RAM_ESTIMATES['default'])

    # If model is specified, add its loading cost
    model = kwargs.get('model', '')
    if model and model in OLLAMA_MODEL_RAM_MB:
        base_ram += OLLAMA_MODEL_RAM_MB[model]

    max_tokens = kwargs.get('max_tokens', 4096)
    # Rough: 1K tokens ~ 4KB output buffer
    output_bytes = max_tokens * 4

    timeout = kwargs.get('timeout', 300.0)
    if task_type == 'builder_pipeline':
        timeout = max(timeout, 120.0)
    elif task_type == 'video_generation':
        timeout = max(timeout, 600.0)

    return ResourceEstimate(
        estimated_ram_mb=base_ram,
        timeout_seconds=timeout,
        max_output_bytes=output_bytes,
        max_tool_rounds=kwargs.get('max_tool_rounds', 10),
        requires_llm=kwargs.get('requires_llm', True),
        task_type=task_type,
    )


# ── Queue (simple in-memory) ─────────────────────────────────────────────────
_task_queue: asyncio.Queue | None = None


def _get_queue() -> asyncio.Queue:
    global _task_queue
    if _task_queue is None:
        _task_queue = asyncio.Queue(maxsize=20)
    return _task_queue


async def enqueue_task(task_id: str, task_type: str) -> int:
    """Add a task to the queue. Returns queue position."""
    q = _get_queue()
    await q.put({'task_id': task_id, 'task_type': task_type})
    return q.qsize()


def get_queue_depth() -> int:
    q = _get_queue()
    return q.qsize()


# ── Admission control ─────────────────────────────────────────────────────────
async def admit_task(
    task_type: str = 'default',
    task_id: str = '',
    **kwargs,
) -> AdmissionResult:
    """Determine whether a task should be admitted given current resources.

    Returns an AdmissionResult with decision, reason, and resource state.
    """
    mem = get_system_memory()
    estimate = estimate_task_resources(task_type, **kwargs)
    required_mb = estimate.estimated_ram_mb + SYSTEM_OVERHEAD_MB

    # Check Ollama model loaded overhead separately
    ollama_loaded = mem.ollama_mb > 100
    if ollama_loaded:
        required_mb += mem.ollama_mb

    # Decision logic
    if mem.available_mb < REJECT_THRESHOLD_MB:
        return AdmissionResult(
            decision=AdmissionDecision.REJECT,
            reason=f'System memory critically low: {mem.available_mb}MB available, {REJECT_THRESHOLD_MB}MB minimum',
            available_mb=mem.available_mb,
            required_mb=required_mb,
        )

    if mem.available_mb < DEGRADE_THRESHOLD_MB:
        return AdmissionResult(
            decision=AdmissionDecision.DEGRADE,
            reason=f'System memory constrained: {mem.available_mb}MB available, degrading task',
            available_mb=mem.available_mb,
            required_mb=required_mb,
            degraded=True,
        )

    # Check if estimated requirement exceeds available
    if required_mb > mem.available_mb - REJECT_THRESHOLD_MB:
        # Not enough for this task, but system is not critically low
        queue_depth = get_queue_depth()
        if queue_depth < 10:
            return AdmissionResult(
                decision=AdmissionDecision.QUEUE,
                reason=f'Insufficient memory for task ({required_mb}MB needed, {mem.available_mb}MB free)',
                available_mb=mem.available_mb,
                required_mb=required_mb,
                queue_position=queue_depth + 1,
            )
        else:
            return AdmissionResult(
                decision=AdmissionDecision.REJECT,
                reason=f'Queue full ({queue_depth}) and insufficient memory',
                available_mb=mem.available_mb,
                required_mb=required_mb,
            )

    return AdmissionResult(
        decision=AdmissionDecision.RUN,
        reason=f'Admitted: {mem.available_mb}MB available, {required_mb}MB estimated',
        available_mb=mem.available_mb,
        required_mb=required_mb,
    )


def get_degraded_config(task_type: str = 'default') -> dict:
    """Return reduced resource limits for degraded mode."""
    if task_type in ('builder_pipeline', 'builder_fast'):
        return {
            'max_tokens': 3000,
            'skip_polish': True,
            'skip_design_brief': True,
            'max_tool_rounds': 3,
            'timeout': 120.0,
        }
    return {
        'max_tokens': 2048,
        'skip_polish': True,
        'max_tool_rounds': 3,
        'timeout': 60.0,
    }


def resource_status() -> dict:
    """Return current resource state for health endpoints."""
    mem = get_system_memory()
    return {
        'total_mb': mem.total_mb,
        'available_mb': mem.available_mb,
        'used_mb': mem.used_mb,
        'usage_pct': round(mem.usage_pct, 1),
        'ollama_mb': mem.ollama_mb,
        'queue_depth': get_queue_depth(),
        'system_overhead_mb': SYSTEM_OVERHEAD_MB,
    }
