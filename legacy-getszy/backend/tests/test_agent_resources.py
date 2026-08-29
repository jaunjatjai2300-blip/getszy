"""Resource & reliability layer: admission never risks OOM, limits are enforced,
output is bounded, and a crash becomes evidence rather than taking down the
Factory. Deterministic — memory and resident models are injected, no live host.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import agent_resources as R  # noqa: E402


# ── memory probe is honest ───────────────────────────────────────────────────

def test_system_memory_is_honest():
    mem = R.system_memory()
    # Either a real reading or an explicit unknown — never a fabricated number.
    assert mem.source in {"proc", "windows", "unknown"}
    if mem.source == "unknown":
        assert mem.available_mb is None and not mem.known
    else:
        assert mem.available_mb is not None and mem.total_mb >= mem.available_mb


def test_model_estimate_parses_size():
    assert R.estimate_model_mb("qwen2.5-coder:7b") == 6144
    assert R.estimate_model_mb("something:13b") == int(13 * 900)
    assert R.estimate_model_mb(None) == 6144           # unknown is not treated as free


# ── admission: never NORMAL when it would OOM ────────────────────────────────

def test_admit_normal_with_ample_memory():
    a = R.admit("qwen2.5-coder:7b", available_mb=8000, resident=[])
    assert a.decision == R.NORMAL and a.ok


def test_admit_resident_model_needs_no_extra_memory():
    a = R.admit("qwen2.5-coder:7b", available_mb=1000, resident=["qwen2.5-coder:7b"])
    assert a.decision == R.NORMAL and a.resident is True


def test_admit_rejects_predictable_oom():
    a = R.admit("qwen2.5-coder:7b", available_mb=1500, resident=[])   # need ~6144
    assert a.decision == R.REJECT and not a.ok


def test_admit_constrained_and_degraded_bands():
    # covers need but not full headroom -> constrained
    c = R.admit("qwen2.5-coder:7b", available_mb=6200, resident=[], headroom_mb=768)
    assert c.decision == R.CONSTRAINED
    # below need but above 60% -> degraded
    d = R.admit("qwen2.5-coder:7b", available_mb=4000, resident=[])
    assert d.decision == R.DEGRADED


def test_admit_unknown_memory_is_cautious_not_blind(monkeypatch):
    # Force the real probe to report "unknown" (both /proc and ctypes unavailable).
    monkeypatch.setattr(R, "system_memory", lambda: R.MemInfo(None, None, "unknown"))
    a = R.admit("qwen2.5-coder:7b", resident=[])   # no injected value -> real probe -> unknown
    assert a.decision == R.CONSTRAINED       # never a false NORMAL, never a hard REJECT


# ── limit validation is fail-closed ──────────────────────────────────────────

def test_valid_limits_pass_and_invalid_fail_closed():
    assert R.validate_limits(R.ResourceLimits()) == []
    bad = R.ResourceLimits(max_tool_calls=0, timeout_sec=-1, max_output_bytes=-5)
    problems = R.validate_limits(bad)
    assert any("max_tool_calls" in p for p in problems)
    assert any("timeout_sec" in p for p in problems)
    assert any("max_output_bytes" in p for p in problems)


def test_resource_tracker_breaches_are_controlled_failures():
    t = R.ResourceTracker(limits=R.ResourceLimits(max_tool_calls=2))
    t.record_tool_call("ok")
    t.record_tool_call("ok")
    with pytest.raises(R.LimitExceeded):
        t.record_tool_call("one too many")
    assert t.evidence()["tool_calls"] == 3

    t2 = R.ResourceTracker(limits=R.ResourceLimits(max_output_bytes=10))
    with pytest.raises(R.LimitExceeded):
        t2.record_tool_call("x" * 50)


# ── bounded output: truncated is not complete ────────────────────────────────

def test_clip_output_flags_truncation():
    kept, meta = R.clip_output("abc", 100)
    assert kept == "abc" and meta["truncated"] is False

    kept, meta = R.clip_output("x" * 500, 100)
    assert meta["truncated"] is True and meta["original_bytes"] == 500 and meta["kept_bytes"] <= 100


# ── the one bounded LRU ──────────────────────────────────────────────────────

def test_lru_hit_miss_and_stats():
    c = R.BoundedLRU(max_entries=8, max_bytes=10_000)
    assert c.get("k") is None
    c.set("k", {"v": 1})
    assert c.get("k") == {"v": 1}
    s = c.stats()
    assert s["hits"] == 1 and s["misses"] == 1 and s["entries"] == 1


def test_lru_evicts_by_entry_count():
    c = R.BoundedLRU(max_entries=3, max_bytes=10_000_000)
    for i in range(5):
        c.set(f"k{i}", i)
    assert c.stats()["entries"] == 3 and c.stats()["evictions"] == 2
    assert c.get("k0") is None and c.get("k4") == 4


def test_lru_evicts_by_bytes_and_refuses_oversized():
    c = R.BoundedLRU(max_entries=1000, max_bytes=200)
    assert c.set("big", "z" * 500) is False       # single oversized value never cached
    assert c.get("big") is None
    for i in range(20):
        c.set(f"k{i}", "y" * 40)
    assert c.stats()["bytes"] <= 200


def test_lru_ttl_expires():
    import time
    c = R.BoundedLRU(max_entries=8, max_bytes=10_000, ttl_sec=0.05)
    c.set("k", "v")
    assert c.get("k") == "v"
    time.sleep(0.08)
    assert c.get("k") is None


def test_lru_namespaced_keys_do_not_collide():
    c = R.BoundedLRU()
    c.set("projA|sym", 1)
    c.set("projB|sym", 2)
    assert c.get("projA|sym") == 1 and c.get("projB|sym") == 2


# ── failure isolation: a crash becomes evidence, never a Factory crash ───────

async def test_run_isolated_success_passthrough():
    async def ok():
        return 42
    out = await R.run_isolated(ok(), timeout_sec=5)
    assert out["ok"] is True and out["result"] == 42


async def test_run_isolated_turns_a_crash_into_evidence():
    async def boom():
        raise ValueError("kaboom")
    out = await R.run_isolated(boom(), timeout_sec=5, label="tool")
    assert out["ok"] is False and "ValueError" in out["error"] and out["label"] == "tool"


async def test_run_isolated_times_out_and_cleans_up():
    cleaned = {"v": False}

    async def slow():
        await asyncio.sleep(5)

    def cleanup():
        cleaned["v"] = True

    out = await R.run_isolated(slow(), timeout_sec=0.05, on_cleanup=cleanup, label="child")
    assert out["ok"] is False and out["error"] == "timeout"
    assert cleaned["v"] is True
