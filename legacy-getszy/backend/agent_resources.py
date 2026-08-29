"""Agent Factory — resource admission & reliability layer.

The Factory runs local Ollama on a memory-constrained VPS (~7.9 GB). This module
is the ONE place that answers: is it safe to run this now, and how do we keep a
single task from taking the whole process down. It is deterministic, dependency-
free (no psutil), and composes with the existing runtime — it does not replace
delegation bounds, the repair loop, or the guard.

Cost profile (as required for a constrained host):
  RAM        : a few KB (small dict cache + counters); the LRU is byte-bounded.
  CPU        : negligible; one /proc read or one ctypes call per probe.
  startup    : none — everything is lazy.
  steady     : O(1) per admission / cache op.

What it provides:
  * system_memory()      — real available/total RAM, dependency-free, honest when unknown
  * resident_models()    — what Ollama already has loaded (best-effort, fail-safe)
  * admit()              — NORMAL / CONSTRAINED / DEGRADED / REJECT; never a predicted OOM
  * ResourceLimits       — enforceable per-task caps, fail-closed validation
  * ResourceTracker      — counts tool calls / output bytes, detects breach
  * BoundedLRU           — one byte- and entry-bounded cache with stats
  * clip_output()        — bounded output with truncation metadata (truncated != done)
  * run_isolated()       — timeout + cancellation, turns a crash into evidence

Model boundary is unchanged: LOCAL OLLAMA ONLY. Nothing here reaches a cloud
provider or the customer provider chain.
"""
from __future__ import annotations

import json
import time
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass, field

# Admission decisions, weakest constraint to strongest.
NORMAL = "normal"          # run as-is
CONSTRAINED = "constrained"  # run, but reduce concurrency / be careful
DEGRADED = "degraded"      # run only a smaller/cheaper shape if the caller allows
REJECT = "reject"          # would risk OOM — do not run, fail honestly

# Default safety headroom kept free so the OS / other work does not get squeezed.
DEFAULT_HEADROOM_MB = 768


# ── system memory, without psutil ────────────────────────────────────────────

@dataclass
class MemInfo:
    total_mb: int | None
    available_mb: int | None
    source: str            # "proc" | "windows" | "unknown"

    @property
    def known(self) -> bool:
        return self.available_mb is not None


def system_memory() -> MemInfo:
    """Available/total RAM in MB. Dependency-free and honest: when it cannot be
    read, `available_mb` is None (source='unknown') rather than a fabricated
    number that could wave through a run that then OOMs."""
    # Linux / Docker: /proc/meminfo is authoritative and cheap.
    try:
        with open("/proc/meminfo", "r") as fh:
            info = {}
            for line in fh:
                k, _, rest = line.partition(":")
                info[k.strip()] = int(rest.strip().split()[0])  # kB
        total = info.get("MemTotal")
        avail = info.get("MemAvailable", info.get("MemFree"))
        if total and avail is not None:
            return MemInfo(total_mb=total // 1024, available_mb=avail // 1024, source="proc")
    except Exception:
        pass
    # Windows: GlobalMemoryStatusEx via ctypes, no dependency.
    try:
        import ctypes

        class _MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        ms = _MS()
        ms.dwLength = ctypes.sizeof(_MS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
            return MemInfo(total_mb=int(ms.ullTotalPhys // (1024 * 1024)),
                           available_mb=int(ms.ullAvailPhys // (1024 * 1024)), source="windows")
    except Exception:
        pass
    return MemInfo(total_mb=None, available_mb=None, source="unknown")


# ── model memory estimates (deterministic, from the name) ────────────────────

# Conservative resident footprints for common local models, MB. Used only to
# decide admission; the real number is whatever Ollama loads.
_MODEL_MB = {
    "qwen2.5-coder:7b": 6144,
    "qwen2.5:7b": 6144,
    "qwen2.5-coder:14b": 10240,
    "llama3.1:8b": 6656,
}


def estimate_model_mb(model: str | None) -> int:
    """Estimate a model's resident memory from its name. Falls back to parsing a
    '<n>b' size, then to a safe 6 GB default so an unknown model is not treated
    as free."""
    if not model:
        return 6144
    m = model.strip().lower()
    if m in _MODEL_MB:
        return _MODEL_MB[m]
    # parse e.g. "...:7b" / "13b" -> GB * ~0.85 for a quantised resident size
    import re
    match = re.search(r"(\d+(?:\.\d+)?)\s*b\b", m)
    if match:
        billions = float(match.group(1))
        return int(billions * 900)      # ~0.9 GB per B, quantised
    return 6144


def resident_models(base_url: str | None = None, timeout: float = 2.0) -> list[str]:
    """Models Ollama currently holds in memory (via /api/ps). Best-effort: any
    failure returns [] so admission simply assumes nothing is resident."""
    if base_url is None:
        try:
            import agent_llm
            base_url = agent_llm.ollama_base_url()
        except Exception:
            base_url = "http://127.0.0.1:11434"
    try:
        req = urllib.request.Request(base_url.rstrip("/") + "/api/ps")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [m.get("name", "") for m in (data.get("models") or []) if m.get("name")]
    except Exception:
        return []


# ── admission ────────────────────────────────────────────────────────────────

@dataclass
class Admission:
    decision: str
    reason: str
    need_mb: int
    available_mb: int | None
    resident: bool = False

    @property
    def ok(self) -> bool:
        """Whether execution may proceed at all (anything but REJECT)."""
        return self.decision != REJECT

    def to_dict(self) -> dict:
        return {"decision": self.decision, "reason": self.reason, "need_mb": self.need_mb,
                "available_mb": self.available_mb, "resident": self.resident}


def admit(model: str, *, available_mb: int | None = None, resident: list[str] | None = None,
          task_mb: int = 0, headroom_mb: int = DEFAULT_HEADROOM_MB) -> Admission:
    """Decide whether running `model` now is safe. Never returns NORMAL for a
    configuration that would predictably OOM.

    Inputs are injectable so this is deterministic and unit-testable without a
    live system."""
    mem = system_memory() if available_mb is None else MemInfo(None, available_mb, "injected")
    resident = resident_models() if resident is None else resident
    is_resident = any(model == r or model in r for r in resident) if model else False
    est = estimate_model_mb(model)
    # A resident model is already paid for; only the task's own working set is new.
    need = (task_mb if is_resident else est + task_mb)

    if mem.available_mb is None:
        # Unknown memory: proceed cautiously rather than block a viable 7B run or
        # wave through a risky one. Caller may still lower concurrency.
        return Admission(CONSTRAINED, "available memory unknown; proceeding cautiously",
                         need, None, is_resident)

    free = mem.available_mb
    if is_resident and free >= headroom_mb:
        return Admission(NORMAL, f"model already resident; {free} MB free", need, free, True)
    if free >= need + headroom_mb:
        return Admission(NORMAL, f"{free} MB free covers {need} MB need + {headroom_mb} MB headroom",
                         need, free, is_resident)
    if free >= need:
        return Admission(CONSTRAINED, f"{free} MB free covers {need} MB need but not full headroom",
                         need, free, is_resident)
    if free >= int(need * 0.6):
        return Admission(DEGRADED, f"only {free} MB free vs {need} MB need; run a smaller shape only",
                         need, free, is_resident)
    return Admission(REJECT, f"insufficient memory: {free} MB free, need ~{need} MB — refusing to risk OOM",
                     need, free, is_resident)


# ── enforceable limits ───────────────────────────────────────────────────────

@dataclass
class ResourceLimits:
    """Per-task caps. Existing runtime bounds (repair attempts, delegation depth)
    are NOT replaced by these — this adds output/tool/time/concurrency ceilings."""
    max_output_bytes: int = 262_144      # 256 KB of accumulated tool output
    max_tool_calls: int = 64
    timeout_sec: float = 900.0
    max_concurrency: int = 3
    max_subprocess: int = 8


def validate_limits(limits: ResourceLimits) -> list[str]:
    """Fail-closed validation. An invalid limit is an error, never a silent
    dangerous default (e.g. a 0 that means 'unlimited')."""
    problems = []
    for name in ("max_output_bytes", "max_tool_calls", "max_concurrency", "max_subprocess"):
        v = getattr(limits, name)
        if not isinstance(v, int) or v <= 0:
            problems.append(f"{name} must be a positive int, got {v!r}")
    if not (isinstance(limits.timeout_sec, (int, float)) and limits.timeout_sec > 0):
        problems.append(f"timeout_sec must be > 0, got {limits.timeout_sec!r}")
    return problems


class LimitExceeded(RuntimeError):
    """A resource ceiling was hit. Produces a controlled failure, never success."""


@dataclass
class ResourceTracker:
    """Counts what a task has consumed and refuses past the ceiling. A breach is
    a controlled failure with evidence — the runtime must never treat it as
    success."""
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    tool_calls: int = 0
    output_bytes: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def record_tool_call(self, output: str = "") -> None:
        self.tool_calls += 1
        self.output_bytes += len(output.encode("utf-8", "ignore")) if output else 0
        breach = self.breach()
        if breach:
            raise LimitExceeded(breach)

    def breach(self) -> str:
        if self.tool_calls > self.limits.max_tool_calls:
            return f"tool call limit exceeded ({self.tool_calls}/{self.limits.max_tool_calls})"
        if self.output_bytes > self.limits.max_output_bytes:
            return f"output byte limit exceeded ({self.output_bytes}/{self.limits.max_output_bytes})"
        if time.monotonic() - self.started_at > self.limits.timeout_sec:
            return f"time limit exceeded (> {self.limits.timeout_sec}s)"
        return ""

    def evidence(self) -> dict:
        return {"tool_calls": self.tool_calls, "output_bytes": self.output_bytes,
                "elapsed_sec": round(time.monotonic() - self.started_at, 2),
                "limits": {"max_tool_calls": self.limits.max_tool_calls,
                           "max_output_bytes": self.limits.max_output_bytes,
                           "timeout_sec": self.limits.timeout_sec}}


# ── bounded output ───────────────────────────────────────────────────────────

def clip_output(text: str, max_bytes: int = 4096, *, keep: str = "tail") -> tuple[str, dict]:
    """Bound a string to max_bytes, returning (clipped, meta). `meta.truncated`
    is True when content was dropped — a truncated result is explicitly NOT a
    complete one, so a caller can never read truncation as success."""
    raw = (text or "").encode("utf-8", "ignore")
    if len(raw) <= max_bytes:
        return text or "", {"truncated": False, "original_bytes": len(raw), "kept_bytes": len(raw)}
    piece = raw[-max_bytes:] if keep == "tail" else raw[:max_bytes]
    clipped = piece.decode("utf-8", "ignore")
    return clipped, {"truncated": True, "original_bytes": len(raw), "kept_bytes": len(piece), "keep": keep}


# ── one bounded LRU cache ────────────────────────────────────────────────────

class BoundedLRU:
    """A single byte- and entry-bounded LRU with TTL and stats. Safe to cache
    deterministic, non-sensitive resources only (repo-map answers, tool/model
    metadata). Never store secrets, tokens, or cross-user private data."""

    def __init__(self, max_entries: int = 256, max_bytes: int = 4_000_000, ttl_sec: float | None = None):
        if max_entries <= 0 or max_bytes <= 0:
            raise ValueError("max_entries and max_bytes must be positive")
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.ttl_sec = ttl_sec
        self._data: OrderedDict[str, tuple] = OrderedDict()  # key -> (value, size, expires_at)
        self._bytes = 0
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    @staticmethod
    def _sizeof(value) -> int:
        try:
            return len(value) if isinstance(value, (bytes, bytearray)) else len(json.dumps(value, default=str).encode("utf-8"))
        except Exception:
            return len(str(value).encode("utf-8", "ignore"))

    def get(self, key: str):
        item = self._data.get(key)
        if item is None:
            self.misses += 1
            return None
        value, size, expires_at = item
        if expires_at is not None and time.monotonic() > expires_at:
            self._drop(key)
            self.misses += 1
            return None
        self._data.move_to_end(key)
        self.hits += 1
        return value

    def set(self, key: str, value) -> bool:
        size = self._sizeof(value)
        if size > self.max_bytes:
            return False  # a single oversized value is never cached
        if key in self._data:
            self._drop(key)
        expires_at = (time.monotonic() + self.ttl_sec) if self.ttl_sec else None
        self._data[key] = (value, size, expires_at)
        self._bytes += size
        self._data.move_to_end(key)
        while len(self._data) > self.max_entries or self._bytes > self.max_bytes:
            old_key, (_, old_size, _) = self._data.popitem(last=False)
            self._bytes -= old_size
            self.evictions += 1
        return True

    def _drop(self, key: str) -> None:
        item = self._data.pop(key, None)
        if item is not None:
            self._bytes -= item[1]

    def clear(self) -> None:
        self._data.clear()
        self._bytes = 0

    def stats(self) -> dict:
        return {"entries": len(self._data), "bytes": self._bytes, "max_entries": self.max_entries,
                "max_bytes": self.max_bytes, "hits": self.hits, "misses": self.misses,
                "evictions": self.evictions}


# ── failure isolation ────────────────────────────────────────────────────────

async def run_isolated(coro, *, timeout_sec: float, on_cleanup=None, label: str = "task") -> dict:
    """Await a coroutine under a timeout, converting any failure into structured
    evidence instead of letting it crash the Factory. A tool/child/model blowing
    up becomes {ok: False, error, evidence}, never an unhandled exception."""
    import asyncio
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_sec)
        return {"ok": True, "result": result, "elapsed_sec": round(time.monotonic() - started, 2)}
    except asyncio.TimeoutError:
        outcome = {"ok": False, "error": "timeout", "label": label,
                   "evidence": {"timeout_sec": timeout_sec, "elapsed_sec": round(time.monotonic() - started, 2)}}
    except asyncio.CancelledError:
        # Cooperative cancellation is not a crash; surface it, still run cleanup.
        outcome = {"ok": False, "error": "cancelled", "label": label}
    except Exception as e:
        outcome = {"ok": False, "error": f"{type(e).__name__}: {e}", "label": label,
                   "evidence": {"elapsed_sec": round(time.monotonic() - started, 2)}}
    if on_cleanup is not None:
        try:
            maybe = on_cleanup()
            if hasattr(maybe, "__await__"):
                await maybe
        except Exception:
            pass
    return outcome


__all__ = [
    "NORMAL", "CONSTRAINED", "DEGRADED", "REJECT", "DEFAULT_HEADROOM_MB",
    "MemInfo", "system_memory", "estimate_model_mb", "resident_models",
    "Admission", "admit", "ResourceLimits", "validate_limits", "ResourceTracker",
    "LimitExceeded", "clip_output", "BoundedLRU", "run_isolated",
]
