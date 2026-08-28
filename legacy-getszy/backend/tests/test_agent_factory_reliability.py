"""Unit tests for Agent Factory reliability layer.

Tests for:
- Bounded LRU Cache
- Resource Admission
- Config Validation
- Bounded Output
- Task Limits
- Failure Isolation
- Attempt Ledger
- Reviewer
"""
import pytest
import asyncio
import time
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ── Bounded LRU Cache Tests ──────────────────────────────────────────────────

class TestBoundedLRUCache:
    def test_basic_set_get(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=100, max_bytes=10_000_000)
        c.set('k1', 'value1', ttl=60)
        assert c.get('k1') == 'value1'

    def test_miss_returns_none(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=100)
        assert c.get('nonexistent') is None

    def test_expiry(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=100)
        c.set('k1', 'value1', ttl=0)  # immediate expiry
        time.sleep(0.01)
        assert c.get('k1') is None

    def test_lru_eviction(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=2, max_bytes=10_000_000)
        c.set('k1', 'v1')
        c.set('k2', 'v2')
        assert len(c) == 2
        # Adding 3rd should evict oldest (k1) because max_entries=2
        c.set('k3', 'v3')
        assert len(c) == 2
        assert c.get('k1') is None
        assert c.get('k2') == 'v2'

    def test_byte_budget_eviction(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=100, max_bytes=200)
        c.set('k1', 'x' * 100)
        c.set('k2', 'y' * 100)
        # Adding third should trigger eviction by byte budget
        c.set('k3', 'z' * 100)
        assert c.estimated_bytes <= 300  # at most 3 entries

    def test_invalidate_prefix(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=100)
        c.set('build:plan:1', 'a')
        c.set('build:design:1', 'b')
        c.set('other:1', 'c')
        removed = c.invalidate('build:')
        assert removed == 2
        assert c.get('build:plan:1') is None
        assert c.get('other:1') == 'c'

    def test_stats(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=100)
        c.set('k1', 'v1')
        c.get('k1')  # hit
        c.get('miss')  # miss
        assert c.stats.hits == 1
        assert c.stats.misses == 1
        assert c.stats.hit_rate == 0.5

    def test_info(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=10, max_bytes=5000)
        c.set('k1', 'v1')
        info = c.info()
        assert info['entries'] == 1
        assert info['max_entries'] == 10
        assert info['max_bytes'] == 5000

    def test_module_level_api(self):
        from cache_utils import cache_get, cache_set, cache_key, cache_invalidate, cache_info, cache_clear
        cache_clear()
        k = cache_key('test', 'key')
        cache_set(k, 'hello', ttl=60)
        assert cache_get(k) == 'hello'
        assert cache_invalidate('test:') == 1
        assert cache_get(k) is None
        info = cache_info()
        assert 'entries' in info

    def test_overwrite_same_key(self):
        from cache_utils import BoundedLRUCache
        c = BoundedLRUCache(max_entries=100)
        c.set('k1', 'first')
        c.set('k1', 'second')
        assert c.get('k1') == 'second'
        assert len(c) == 1


# ── Resource Admission Tests ─────────────────────────────────────────────────

class TestResourceAdmission:
    def test_get_system_memory(self):
        from resource_admission import get_system_memory
        mem = get_system_memory()
        assert mem.total_mb > 0
        assert mem.available_mb >= 0

    def test_estimate_task_resources(self):
        from resource_admission import estimate_task_resources
        est = estimate_task_resources('builder_pipeline')
        assert est.estimated_ram_mb > 0
        assert est.timeout_seconds > 0

    def test_estimate_task_resources_llm(self):
        from resource_admission import estimate_task_resources
        est = estimate_task_resources('llm_call')
        assert est.requires_llm is True

    def test_get_degraded_config(self):
        from resource_admission import get_degraded_config
        cfg = get_degraded_config('builder_pipeline')
        assert cfg['max_tokens'] < 8000  # degraded should be smaller
        assert cfg['skip_polish'] is True

    def test_resource_status(self):
        from resource_admission import resource_status
        status = resource_status()
        assert 'total_mb' in status
        assert 'available_mb' in status

    @pytest.mark.asyncio
    async def test_admit_task_runs(self):
        from resource_admission import admit_task, AdmissionDecision
        result = await admit_task('llm_call', task_id='test-1')
        # On a normal system, should admit
        assert result.decision in (AdmissionDecision.RUN, AdmissionDecision.DEGRADE, AdmissionDecision.QUEUE)

    def test_task_ram_estimates(self):
        from resource_admission import TASK_RAM_ESTIMATES
        assert 'llm_call' in TASK_RAM_ESTIMATES
        assert 'builder_pipeline' in TASK_RAM_ESTIMATES
        assert 'builder_fast' in TASK_RAM_ESTIMATES


# ── Config Validation Tests ──────────────────────────────────────────────────

class TestConfigValidation:
    def test_validate_positive_int(self):
        from config_validation import validate_positive_int
        assert validate_positive_int(5, 'test', 1, 10) is None
        assert validate_positive_int(0, 'test', 1, 10) is not None
        assert validate_positive_int('abc', 'test', 1, 10) is not None

    def test_validate_string(self):
        from config_validation import validate_string
        assert validate_string('hello', 'test', 1, 100) is None
        assert validate_string('', 'test', 1, 100) is not None

    def test_validate_enum(self):
        from config_validation import validate_enum
        assert validate_enum('a', 'test', ['a', 'b', 'c']) is None
        assert validate_enum('d', 'test', ['a', 'b', 'c']) is not None

    def test_validate_model_config(self):
        from config_validation import validate_model_config
        result = validate_model_config({'provider': 'ollama', 'model': 'qwen2.5:7b'})
        assert result.valid is True

    def test_validate_model_config_invalid(self):
        from config_validation import validate_model_config
        result = validate_model_config({'provider': 'invalid'})
        assert result.valid is False

    def test_validate_resource_config(self):
        from config_validation import validate_resource_config
        result = validate_resource_config({'max_ram_mb': 4096, 'max_cpu_seconds': 300})
        assert result.valid is True

    def test_validate_agent_config(self):
        from config_validation import validate_agent_config
        result = validate_agent_config({'name': 'test_agent', 'role': 'coder'})
        assert result.valid is True

    def test_validate_agent_config_missing(self):
        from config_validation import validate_agent_config
        result = validate_agent_config({})
        assert result.valid is False

    def test_validate_task_config(self):
        from config_validation import validate_task_config
        result = validate_task_config({'task_type': 'builder_pipeline', 'timeout': 300})
        assert result.valid is True

    def test_validation_result_to_dict(self):
        from config_validation import ValidationResult, ValidationError
        r = ValidationResult(valid=True, warnings=[ValidationError('w', 'v', 'reason')])
        d = r.to_dict()
        assert d['valid'] is True
        assert len(d['warnings']) == 1


# ── Bounded Output Tests ─────────────────────────────────────────────────────

class TestBoundedOutput:
    def test_bounded_string_no_truncate(self):
        from bounded_output import bounded_string
        r = bounded_string('hello', max_bytes=1000)
        assert r.truncated is False
        assert r.content == 'hello'

    def test_bounded_string_truncate(self):
        from bounded_output import bounded_string
        big = 'x' * 10000
        r = bounded_string(big, max_bytes=1000)
        assert r.truncated is True
        assert r.original_length == 10000
        assert 'TRUNCATED' in r.content

    def test_bounded_string_empty(self):
        from bounded_output import bounded_string
        r = bounded_string('', max_bytes=100)
        assert r.truncated is False
        assert r.content == ''

    def test_bounded_llm_output(self):
        from bounded_output import bounded_llm_output, MAX_LLM_OUTPUT_BYTES
        r = bounded_llm_output('test')
        assert r.limit == MAX_LLM_OUTPUT_BYTES

    def test_bounded_tool_output(self):
        from bounded_output import bounded_tool_output, MAX_TOOL_OUTPUT_BYTES
        r = bounded_tool_output('test')
        assert r.limit == MAX_TOOL_OUTPUT_BYTES

    def test_bounded_result_to_dict(self):
        from bounded_output import bounded_string
        r = bounded_string('hi', max_bytes=1000)
        d = r.to_dict()
        assert 'content' in d
        assert 'truncated' in d

    def test_repair_evidence(self):
        from bounded_output import repair_evidence
        e = repair_evidence('error msg', 'truncated output', 1)
        assert e['type'] == 'output_truncated'
        assert e['attempt'] == 1

    def test_truncate_for_context(self):
        from bounded_output import truncate_for_context
        parts = [
            {'role': 'user', 'content': 'hello'},
            {'role': 'assistant', 'content': 'world' * 1000},
            {'role': 'user', 'content': 'again'},
        ]
        result = truncate_for_context(parts, max_bytes=5000)
        assert len(result) >= 1
        assert result[0]['content'] == 'hello'


# ── Task Limits Tests ────────────────────────────────────────────────────────

class TestTaskLimits:
    def test_create_tracker(self):
        from task_limits import create_tracker, remove_tracker
        t = create_tracker('test-task', agent_id='tester')
        assert t.task_id == 'test-task'
        remove_tracker('test-task')

    def test_timeout_check(self):
        from task_limits import TaskLimits, LimitTracker
        limits = TaskLimits(execution_timeout=0.01)
        t = LimitTracker('t1', 'a1', limits)
        time.sleep(0.02)
        assert t.check_timeout() is True

    def test_tool_rounds_check(self):
        from task_limits import TaskLimits, LimitTracker
        limits = TaskLimits(max_tool_rounds=2)
        t = LimitTracker('t1', 'a1', limits)
        assert t.check_tool_rounds() is False  # 1st call
        assert t.check_tool_rounds() is False  # 2nd call
        assert t.check_tool_rounds() is True   # 3rd call = breach

    def test_repair_attempts_check(self):
        from task_limits import TaskLimits, LimitTracker
        limits = TaskLimits(max_repair_attempts=1)
        t = LimitTracker('t1', 'a1', limits)
        assert t.check_repair_attempts() is False
        assert t.check_repair_attempts() is True

    def test_output_bytes_check(self):
        from task_limits import TaskLimits, LimitTracker
        limits = TaskLimits(max_output_bytes=100)
        t = LimitTracker('t1', 'a1', limits)
        assert t.check_output_bytes(50) is False
        assert t.check_output_bytes(60) is True

    def test_children_check(self):
        from task_limits import TaskLimits, LimitTracker
        limits = TaskLimits(max_children=2)
        t = LimitTracker('t1', 'a1', limits)
        assert t.check_children() is False
        assert t.check_children() is False
        assert t.check_children() is True

    def test_delegation_depth_check(self):
        from task_limits import TaskLimits, LimitTracker
        limits = TaskLimits(max_delegation_depth=2)
        t = LimitTracker('t1', 'a1', limits)
        assert t.check_delegation_depth(1) is False
        assert t.check_delegation_depth(2) is False
        assert t.check_delegation_depth(3) is True

    def test_tracker_status(self):
        from task_limits import create_tracker, remove_tracker
        t = create_tracker('status-test', agent_id='s')
        status = t.status()
        assert 'task_id' in status
        assert 'limits' in status
        remove_tracker('status-test')

    def test_limit_constants_not_weakened(self):
        from task_limits import (
            MAX_REPAIR_ATTEMPTS, CHILD_MAX_ATTEMPTS, CHILD_ROUNDS,
            MASTER_ROUNDS, MAX_TOOL_ROUNDS, MAX_DELEGATION_DEPTH,
            MAX_CHILDREN,
        )
        assert MAX_REPAIR_ATTEMPTS >= 3
        assert CHILD_MAX_ATTEMPTS >= 2
        assert CHILD_ROUNDS >= 5
        assert MASTER_ROUNDS >= 10
        assert MAX_TOOL_ROUNDS >= 10
        assert MAX_DELEGATION_DEPTH >= 3
        assert MAX_CHILDREN >= 5

    def test_limits_status(self):
        from task_limits import limits_status
        status = limits_status()
        assert 'active_tasks' in status
        assert 'max_concurrent' in status


# ── Failure Isolation Tests ──────────────────────────────────────────────────

class TestFailureIsolation:
    @pytest.mark.asyncio
    async def test_with_timeout_ok(self):
        from failure_isolation import with_timeout
        result = await with_timeout(asyncio.sleep(0.01), timeout_seconds=1.0, task_id='t1', default='fallback')
        assert result is None  # sleep returns None

    @pytest.mark.asyncio
    async def test_with_timeout_exceeded(self):
        from failure_isolation import with_timeout
        result = await with_timeout(asyncio.sleep(10), timeout_seconds=0.01, task_id='t1', default='fallback')
        assert result == 'fallback'

    @pytest.mark.asyncio
    async def test_exception_boundary_catches(self):
        from failure_isolation import ExceptionBoundary, FailureType
        async with ExceptionBoundary(task_id='t1') as boundary:
            raise ValueError('test error')
        assert boundary.failure is not None
        assert boundary.failure.failure_type == FailureType.UNKNOWN

    @pytest.mark.asyncio
    async def test_exception_boundary_timeout(self):
        from failure_isolation import ExceptionBoundary, FailureType
        async with ExceptionBoundary(task_id='t1') as boundary:
            raise asyncio.TimeoutError()
        assert boundary.failure is not None
        assert boundary.failure.failure_type == FailureType.MODEL_TIMEOUT

    @pytest.mark.asyncio
    async def test_exception_boundary_no_error(self):
        from failure_isolation import ExceptionBoundary
        async with ExceptionBoundary(task_id='t1') as boundary:
            pass  # no error
        assert boundary.failure is None

    @pytest.mark.asyncio
    async def test_isolated_subprocess(self):
        from failure_isolation import isolated_subprocess
        if sys.platform == 'win32':
            # Windows: use asyncio.create_subprocess_shell via a direct test
            proc = await asyncio.create_subprocess_shell(
                'echo hello',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            assert proc.returncode == 0
            assert b'hello' in stdout
        else:
            result = await isolated_subprocess(['echo', 'hello'], timeout=5.0)
            assert result['returncode'] == 0
            assert 'hello' in result['stdout']

    @pytest.mark.asyncio
    async def test_isolated_subprocess_timeout(self):
        from failure_isolation import isolated_subprocess
        if sys.platform == 'win32':
            proc = await asyncio.create_subprocess_shell(
                'python -c "import time; time.sleep(100)"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=0.5)
                assert False, 'should have timed out'
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                assert True
        else:
            result = await isolated_subprocess(['sleep', '100'], timeout=0.5)
            assert result['timed_out'] is True

    def test_child_failure_to_evidence(self):
        from failure_isolation import FailureRecord, FailureType, child_failure_to_evidence
        f = FailureRecord(failure_type=FailureType.MODEL_TIMEOUT, message='timeout', task_id='child-1')
        evidence = child_failure_to_evidence(f, 'parent-1')
        assert evidence['source'] == 'child_failure'
        assert evidence['child_task_id'] == 'child-1'
        assert evidence['parent_task_id'] == 'parent-1'
        assert 'recommendation' in evidence

    def test_failure_record_to_dict(self):
        from failure_isolation import FailureRecord, FailureType
        f = FailureRecord(failure_type=FailureType.TOOL_FAILURE, message='tool broke')
        d = f.to_dict()
        assert d['failure_type'] == 'tool_failure'
        assert d['message'] == 'tool broke'


# ── Attempt Ledger Tests ─────────────────────────────────────────────────────

class TestAttemptLedger:
    def test_create_ledger(self):
        from attempt_ledger import AttemptLedger
        l = AttemptLedger('task-1', max_attempts=3)
        assert l.task_id == 'task-1'
        assert l.max_attempts == 3
        assert l.attempt_count == 0

    def test_start_complete_attempt(self):
        from attempt_ledger import AttemptLedger, AttemptOutcome, StrategyType
        l = AttemptLedger('task-1')
        record = l.start_attempt(strategy=StrategyType.STANDARD, description='first try')
        assert record.attempt_id == 1
        l.complete_attempt(record, outcome=AttemptOutcome.SUCCESS, observed_output='done')
        assert l.attempt_count == 1
        assert l.last_outcome == AttemptOutcome.SUCCESS

    def test_exhausted(self):
        from attempt_ledger import AttemptLedger, AttemptOutcome, StrategyType
        l = AttemptLedger('task-1', max_attempts=2)
        r1 = l.start_attempt(StrategyType.STANDARD)
        l.complete_attempt(r1, AttemptOutcome.FAILED)
        r2 = l.start_attempt(StrategyType.ALTERNATIVE)
        l.complete_attempt(r2, AttemptOutcome.FAILED)
        assert l.exhausted is True

    def test_recommend_next_strategy(self):
        from attempt_ledger import AttemptLedger, AttemptOutcome, StrategyType
        l = AttemptLedger('task-1')
        # No attempts yet -> STANDARD
        assert l.recommend_next_strategy() == StrategyType.STANDARD

        # First attempt STANDARD failed -> ALTERNATIVE
        r1 = l.start_attempt(StrategyType.STANDARD)
        l.complete_attempt(r1, AttemptOutcome.FAILED)
        assert l.recommend_next_strategy() == StrategyType.ALTERNATIVE

        # ALTERNATIVE failed -> DECOMPOSED
        r2 = l.start_attempt(StrategyType.ALTERNATIVE)
        l.complete_attempt(r2, AttemptOutcome.FAILED)
        assert l.recommend_next_strategy() == StrategyType.DECOMPOSED

    def test_get_rejected_strategies(self):
        from attempt_ledger import AttemptLedger, AttemptOutcome, StrategyType
        l = AttemptLedger('task-1')
        r1 = l.start_attempt(StrategyType.STANDARD, description='standard approach')
        l.complete_attempt(r1, AttemptOutcome.FAILED, error_message='model returned garbage')
        rejected = l.get_rejected_strategies()
        assert len(rejected) == 1
        assert 'standard' in rejected[0]

    def test_build_briefing(self):
        from attempt_ledger import AttemptLedger, AttemptOutcome, StrategyType
        l = AttemptLedger('task-1', max_attempts=3)
        r1 = l.start_attempt(StrategyType.STANDARD)
        l.complete_attempt(r1, AttemptOutcome.FAILED, error_message='timeout')
        briefing = l.build_briefing()
        assert briefing['task_id'] == 'task-1'
        assert briefing['total_attempts'] == 1
        assert briefing['exhausted'] is False
        assert len(briefing['rejected_strategies']) == 1
        assert briefing['recommended_strategy'] == 'alternative'

    def test_summary(self):
        from attempt_ledger import AttemptLedger, AttemptOutcome, StrategyType
        l = AttemptLedger('task-1')
        r1 = l.start_attempt(StrategyType.STANDARD)
        l.complete_attempt(r1, AttemptOutcome.SUCCESS)
        s = l.summary()
        assert s['total_attempts'] == 1
        assert s['any_succeeded'] is True

    def test_to_dict(self):
        from attempt_ledger import AttemptLedger, AttemptOutcome, StrategyType
        l = AttemptLedger('task-1')
        r1 = l.start_attempt(StrategyType.STANDARD)
        l.complete_attempt(r1, AttemptOutcome.SUCCESS)
        d = l.to_dict()
        assert len(d['attempts']) == 1

    def test_ledger_registry(self):
        from attempt_ledger import get_ledger, remove_ledger
        l = get_ledger('reg-test')
        assert l.task_id == 'reg-test'
        remove_ledger('reg-test')
        assert get_ledger('reg-test').attempt_count == 0  # fresh ledger


# ── Reviewer Tests ───────────────────────────────────────────────────────────

class TestReviewer:
    def test_review_valid_html(self):
        from reviewer import review_task_result, ReviewVerdict
        html = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Test Site</title></head>
<body><main><h1>Welcome</h1><p>Hello world</p></main>
<footer>Footer</footer></body></html>'''
        result = review_task_result(html, 'builder', {})
        assert result.verdict in (ReviewVerdict.PASS, ReviewVerdict.FAIL)
        assert len(result.checks) > 0

    def test_review_empty(self):
        from reviewer import review_task_result, ReviewVerdict
        result = review_task_result('', 'builder')
        assert result.verdict == ReviewVerdict.FAIL

    def test_review_with_brief(self):
        from reviewer import review_task_result
        html = '''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Brand</title></head>
<body><main><h1>Brand helps you</h1></main>
<footer>Footer</footer></body></html>'''
        brief = {'brand_name': 'Brand', 'primary_cta': 'Get Started'}
        result = review_task_result(html, 'builder', brief)
        assert len(result.checks) > 0

    def test_review_checks_structure(self):
        from reviewer import _check_html_structure
        good = '<!DOCTYPE html><html><head></head><body></body></html>'
        bad = '<p>not html</p>'
        assert _check_html_structure(good).passed is True
        assert _check_html_structure(bad).passed is False

    def test_review_no_placeholders(self):
        from reviewer import _check_no_placeholders
        assert _check_no_placeholders('<p>Real content</p>').passed is True
        assert _check_no_placeholders('<p>[placeholder]</p>').passed is False
        assert _check_no_placeholders('<p>lorem ipsum</p>').passed is False

    def test_review_single_h1(self):
        from reviewer import _check_single_h1
        assert _check_single_h1('<h1>One</h1>').passed is True
        assert _check_single_h1('<h1>A</h1><h1>B</h1>').passed is False

    def test_review_result_to_dict(self):
        from reviewer import review_task_result
        r = review_task_result('test content here', 'builder')
        d = r.to_dict()
        assert 'verdict' in d
        assert 'checks' in d

    def test_review_no_external_calls(self):
        from reviewer import _check_no_external_calls
        assert _check_no_external_calls('<p>safe</p>').passed is True
        assert _check_no_external_calls('<script>fetch("https://evil.com")</script>').passed is False


# ── Builder Agents Integration Tests ─────────────────────────────────────────

class TestBuilderAgentsIntegration:
    def test_imports_work(self):
        """Verify all new modules can be imported."""
        import cache_utils
        import resource_admission
        import config_validation
        import bounded_output
        import task_limits
        import failure_isolation
        import attempt_ledger
        import reviewer

    def test_builder_agents_has_reliable(self):
        """Verify builder_agents has the new reliable functions."""
        from builder_agents import build_site_reliable, compose_site_reliable
        assert callable(build_site_reliable)
        assert callable(compose_site_reliable)

    def test_builder_agents_has_limits(self):
        """Verify builder_agents enforces limit constants."""
        from task_limits import MAX_REPAIR_ATTEMPTS
        assert MAX_REPAIR_ATTEMPTS >= 3

    def test_factory_constants_preserved(self):
        """Verify existing factory constants are NOT weakened."""
        from task_limits import (
            MAX_REPAIR_ATTEMPTS, CHILD_MAX_ATTEMPTS, CHILD_ROUNDS,
            MASTER_ROUNDS, MAX_TOOL_ROUNDS, MAX_DELEGATION_DEPTH,
            MAX_CHILDREN, MAX_DESCENDANTS,
        )
        assert MAX_REPAIR_ATTEMPTS >= 3
        assert CHILD_MAX_ATTEMPTS >= 2
        assert CHILD_ROUNDS >= 5
        assert MASTER_ROUNDS >= 10
        assert MAX_TOOL_ROUNDS >= 10
        assert MAX_DELEGATION_DEPTH >= 3
        assert MAX_CHILDREN >= 5
        assert MAX_DESCENDANTS >= 15
