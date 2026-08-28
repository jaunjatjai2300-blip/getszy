"""AttemptLedger — structured evidence tracking for repair loops.

Records every attempt's strategy, outcome, changed files, failing tests,
and observed output. The next attempt receives this structured information
so it does NOT blindly repeat a rejected strategy.

New attempt must receive:
- previous attempt
- changed files
- previous failing tests
- previous observed output
- previous strategy
- why that strategy failed
- current failing tests
"""
from __future__ import annotations

import time
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger('getszy.ledger')


class AttemptOutcome(Enum):
    SUCCESS = 'success'
    FAILED = 'failed'
    PARTIAL = 'partial'
    TIMED_OUT = 'timed_out'
    REJECTED = 'rejected'  # admission rejected


class StrategyType(Enum):
    STANDARD = 'standard'
    ALTERNATIVE = 'alternative'
    DECOMPOSED = 'decomposed'
    SIMPLIFIED = 'simplified'
    DIFFERENT_PROVIDER = 'different_provider'
    WITH_EVIDENCE = 'with_evidence'


@dataclass
class AttemptRecord:
    attempt_id: int
    strategy: StrategyType
    strategy_description: str
    task_id: str = ''
    agent_id: str = ''
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    outcome: AttemptOutcome = AttemptOutcome.FAILED
    changed_files: list[str] = field(default_factory=list)
    failing_tests: list[str] = field(default_factory=list)
    previous_failing_tests: list[str] = field(default_factory=list)
    observed_output: str = ''
    error_message: str = ''
    tool_calls_made: int = 0
    output_bytes: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        if self.completed_at > 0:
            return self.completed_at - self.started_at
        return time.time() - self.started_at

    def to_dict(self) -> dict:
        return {
            'attempt_id': self.attempt_id,
            'strategy': self.strategy.value,
            'strategy_description': self.strategy_description,
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'duration': round(self.duration, 2),
            'outcome': self.outcome.value,
            'changed_files': self.changed_files,
            'failing_tests': self.failing_tests,
            'previous_failing_tests': self.previous_failing_tests,
            'observed_output_preview': self.observed_output[:500],
            'error_message': self.error_message[:500],
            'tool_calls_made': self.tool_calls_made,
            'output_bytes': self.output_bytes,
            'metadata': self.metadata,
        }


class AttemptLedger:
    """Tracks all attempts for a task, providing structured history for repair loops."""

    def __init__(self, task_id: str, max_attempts: int = 3):
        self.task_id = task_id
        self.max_attempts = max_attempts
        self.attempts: list[AttemptRecord] = []
        self._next_id = 1

    def start_attempt(
        self,
        strategy: StrategyType = StrategyType.STANDARD,
        description: str = '',
        agent_id: str = '',
    ) -> AttemptRecord:
        """Start a new attempt. Returns the record for population."""
        # Capture previous failing tests for the new attempt's context
        prev_failing = []
        if self.attempts:
            prev_failing = self.attempts[-1].failing_tests

        record = AttemptRecord(
            attempt_id=self._next_id,
            strategy=strategy,
            strategy_description=description,
            task_id=self.task_id,
            agent_id=agent_id,
            previous_failing_tests=prev_failing,
        )
        self._next_id += 1
        self.attempts.append(record)
        logger.info('Ledger: attempt #%d started for task %s (strategy=%s)',
                     record.attempt_id, self.task_id, strategy.value)
        return record

    def complete_attempt(
        self,
        record: AttemptRecord,
        outcome: AttemptOutcome,
        changed_files: list[str] | None = None,
        failing_tests: list[str] | None = None,
        observed_output: str = '',
        error_message: str = '',
        metadata: dict | None = None,
    ):
        """Complete an attempt with its outcome."""
        record.completed_at = time.time()
        record.outcome = outcome
        record.changed_files = changed_files or []
        record.failing_tests = failing_tests or []
        record.observed_output = observed_output[:10_000]  # bound
        record.error_message = error_message[:2_000]
        record.metadata = metadata or {}
        logger.info('Ledger: attempt #%d completed for task %s (outcome=%s, duration=%.1fs)',
                     record.attempt_id, self.task_id, outcome.value, record.duration)

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def all_succeeded(self) -> bool:
        return all(a.outcome == AttemptOutcome.SUCCESS for a in self.attempts) if self.attempts else False

    @property
    def any_succeeded(self) -> bool:
        return any(a.outcome == AttemptOutcome.SUCCESS for a in self.attempts)

    @property
    def last_attempt(self) -> AttemptRecord | None:
        return self.attempts[-1] if self.attempts else None

    @property
    def last_outcome(self) -> AttemptOutcome | None:
        return self.attempts[-1].outcome if self.attempts else None

    @property
    def exhausted(self) -> bool:
        return self.attempt_count >= self.max_attempts

    def get_rejected_strategies(self) -> list[str]:
        """Return descriptions of strategies that failed, so the next attempt avoids them."""
        return [
            f'Attempt #{a.attempt_id}: {a.strategy.value} — {a.strategy_description} — FAILED: {a.error_message[:200]}'
            for a in self.attempts
            if a.outcome in (AttemptOutcome.FAILED, AttemptOutcome.TIMED_OUT)
        ]

    def recommend_next_strategy(self) -> StrategyType:
        """Recommend the next strategy based on what has failed."""
        if not self.attempts:
            return StrategyType.STANDARD

        last = self.attempts[-1]
        if last.outcome == AttemptOutcome.TIMED_OUT:
            return StrategyType.DIFFERENT_PROVIDER
        if last.outcome == AttemptOutcome.FAILED:
            if last.strategy == StrategyType.STANDARD:
                return StrategyType.ALTERNATIVE
            if last.strategy == StrategyType.ALTERNATIVE:
                return StrategyType.DECOMPOSED
            if last.strategy == StrategyType.DECOMPOSED:
                return StrategyType.SIMPLIFIED
            return StrategyType.WITH_EVIDENCE
        return StrategyType.STANDARD

    def build_briefing(self) -> dict:
        """Build a structured briefing for the next attempt.

        This is what the child/next attempt receives so it does NOT
        blindly repeat a rejected strategy.
        """
        rejected = self.get_rejected_strategies()
        last = self.last_attempt
        return {
            'task_id': self.task_id,
            'total_attempts': self.attempt_count,
            'max_attempts': self.max_attempts,
            'exhausted': self.exhausted,
            'all_succeeded': self.all_succeeded,
            'any_succeeded': self.any_succeeded,
            'last_outcome': last.outcome.value if last else None,
            'last_strategy': last.strategy.value if last else None,
            'last_error': last.error_message[:500] if last else None,
            'rejected_strategies': rejected,
            'recommended_strategy': self.recommend_next_strategy().value,
            'last_failing_tests': last.failing_tests if last else [],
            'last_changed_files': last.changed_files if last else [],
        }

    def summary(self) -> dict:
        return {
            'task_id': self.task_id,
            'total_attempts': self.attempt_count,
            'max_attempts': self.max_attempts,
            'outcomes': [a.outcome.value for a in self.attempts],
            'any_succeeded': self.any_succeeded,
            'briefing': self.build_briefing(),
        }

    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'max_attempts': self.max_attempts,
            'attempts': [a.to_dict() for a in self.attempts],
        }


# ── Global ledger registry ───────────────────────────────────────────────────
_ledgers: dict[str, AttemptLedger] = {}


def get_ledger(task_id: str, max_attempts: int = 3) -> AttemptLedger:
    if task_id not in _ledgers:
        _ledgers[task_id] = AttemptLedger(task_id, max_attempts)
    return _ledgers[task_id]


def remove_ledger(task_id: str) -> AttemptLedger | None:
    return _ledgers.pop(task_id, None)


def ledger_status() -> dict:
    return {
        'active_ledgers': len(_ledgers),
        'tasks': {tid: l.summary() for tid, l in _ledgers.items()},
    }


MAX_REPAIR_ATTEMPTS_DEFAULT = 3
