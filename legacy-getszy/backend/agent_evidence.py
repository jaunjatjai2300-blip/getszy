"""Agent Factory — structured failure evidence and the failed-attempt ledger.

A repair loop that is told only "the tests failed" cannot repair anything, and a
loop that is handed its whole transcript back re-reads its own dead ends and
proposes them again. Both were observed: a real specialist ran one failing
command fifteen times, and across attempts it kept re-proposing the same
conceptual fix in different code.

Three things live here:

1. PARSING. Raw pytest output becomes {test, assertion, expected, actual}. The
   parse is strictly an ADDITION -- the exit code remains the only thing that
   decides pass or fail, so a parser bug can never turn a failure into a success.

2. FAILURE SIGNATURES. A normalised identity for "the same conceptual failure".
   Two different implementations that both produce
   `parse_h_t_t_p_response != parse_http_response` share a signature, which is
   what makes stuck-detection semantic rather than syntactic.

3. THE LEDGER. Runtime-owned, per task. The model can neither read nor write it
   directly; it only ever receives a compact briefing derived from it. An agent
   that could edit its own record of what it already tried could erase the
   evidence that it is going in circles.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

MAX_RAW_EVIDENCE = 900
MAX_BRIEFING_CHARS = 3000
STUCK_THRESHOLD = 2          # the same signature twice is stuck, not unlucky

# pytest's assertion line, e.g.
#   E   AssertionError: assert 'parse_h_t_t_p_response' == 'parse_http_response'
_ASSERT = re.compile(
    r"^E\s+(?:AssertionError:\s*)?assert\s+(.+?)\s*(==|!=|<=|>=|<|>|is|in)\s*(.+?)\s*$",
    re.MULTILINE,
)
_FAILED_LINE = re.compile(r"^(?:FAILED\s+)?(\S+?\.py)::(\S+)", re.MULTILINE)
_ERROR_TYPE = re.compile(r"^E\s+(\w*(?:Error|Exception))\b", re.MULTILINE)
_SHORT_SUMMARY = re.compile(r"^FAILED\s+(\S+)", re.MULTILINE)


def parse_failure(output: str, exit_code: int) -> dict:
    """Turn real pytest output into a structured failure.

    Returns {} for a pass. Never claims a pass: the caller owns that decision and
    reads it from the exit code, not from anything in here.
    """
    if exit_code == 0 or not output:
        return {}

    text = output
    failure: dict = {"exit_code": exit_code}

    m = _FAILED_LINE.search(text)
    if m:
        failure["file"] = m.group(1)
        failure["test"] = m.group(2)
    else:
        s = _SHORT_SUMMARY.search(text)
        if s:
            failure["test"] = s.group(1)

    e = _ERROR_TYPE.search(text)
    if e:
        failure["error_type"] = e.group(1)

    a = _ASSERT.search(text)
    if a:
        failure["actual"] = _clip(a.group(1))
        failure["operator"] = a.group(2)
        failure["expected"] = _clip(a.group(3))

    if "error_type" not in failure and "collection" in text.lower():
        failure["error_type"] = "CollectionError"

    failure["raw"] = text.strip()[-MAX_RAW_EVIDENCE:]
    return failure


def _clip(s: str, limit: int = 120) -> str:
    s = s.strip()
    return s if len(s) <= limit else s[:limit] + "…"


def failure_signature(failure: dict) -> str:
    """Stable identity for a CONCEPTUAL failure.

    Deliberately excludes the implementation: what makes two attempts "the same
    failure" is that the test, the error and the observed values are unchanged,
    not that the code was.
    """
    if not failure:
        return ""
    parts = [
        str(failure.get("test") or failure.get("file") or "?"),
        str(failure.get("error_type") or "?"),
        _normalise_value(failure.get("expected")),
        _normalise_value(failure.get("actual")),
    ]
    if not any(p and p != "?" for p in parts[1:]):
        # Nothing distinguishing parsed out; fall back to the raw tail so two
        # genuinely different errors are not collapsed into one signature.
        parts.append(hashlib.sha256(
            (failure.get("raw") or "").encode("utf-8")).hexdigest()[:12])
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _normalise_value(v) -> str:
    """Ignore quoting and whitespace so cosmetic differences do not fork a signature."""
    if v is None:
        return "?"
    return re.sub(r"\s+", "", str(v)).strip("'\"")


@dataclass
class Attempt:
    """What one repair attempt did and what it produced."""
    number: int
    approach: str = ""
    files_inspected: list = field(default_factory=list)
    files_changed: list = field(default_factory=list)
    test_target: str = ""
    passed: bool | None = None
    failure: dict = field(default_factory=dict)
    signature: str = ""
    strategy: str = "default"

    def summary(self) -> str:
        bits = [f"ATTEMPT {self.number}"]
        if self.approach:
            bits.append(f"  approach: {self.approach}")
        if self.files_changed:
            bits.append(f"  changed: {', '.join(self.files_changed[:4])}")
        if self.passed:
            bits.append("  result: tests passed")
        elif self.failure:
            f = self.failure
            where = f.get("test") or f.get("file") or "the suite"
            if f.get("expected") is not None and f.get("actual") is not None:
                bits.append(f"  failed at {where}: expected {f['expected']}, "
                            f"got {f['actual']}")
            else:
                bits.append(f"  failed at {where}: "
                            f"{f.get('error_type') or 'exit ' + str(f.get('exit_code'))}")
        else:
            bits.append("  result: no test evidence produced")
        return "\n".join(bits)


class AttemptLedger:
    """Runtime-owned record of what has already been tried, and how it failed.

    Not exposed as a tool and not writable by a model. The agent only ever sees
    a bounded briefing derived from it, so it cannot quietly forget that it has
    already been down this road.
    """

    def __init__(self) -> None:
        self.attempts: list[Attempt] = []

    def open(self, number: int) -> Attempt:
        attempt = Attempt(number=number)
        self.attempts.append(attempt)
        return attempt

    def current(self) -> Attempt | None:
        return self.attempts[-1] if self.attempts else None

    def close(self, *, passed: bool | None, failure: dict | None) -> None:
        attempt = self.current()
        if attempt is None:
            return
        attempt.passed = passed
        attempt.failure = failure or {}
        attempt.signature = failure_signature(attempt.failure)

    def signatures(self) -> list[str]:
        return [a.signature for a in self.attempts if a.signature]

    def repeated_signature(self) -> str | None:
        """The signature that has now occurred STUCK_THRESHOLD times or more."""
        seen: dict[str, int] = {}
        for sig in self.signatures():
            seen[sig] = seen.get(sig, 0) + 1
            if seen[sig] >= STUCK_THRESHOLD:
                return sig
        return None

    def is_stuck(self) -> bool:
        return self.repeated_signature() is not None

    def stuck_detail(self) -> str:
        sig = self.repeated_signature()
        if not sig:
            return ""
        same = [a for a in self.attempts if a.signature == sig]
        f = same[-1].failure
        where = f.get("test") or f.get("file") or "the same test"
        if f.get("expected") is not None:
            return (f"{len(same)} attempts have produced the identical failure at "
                    f"{where}: expected {f['expected']}, got {f['actual']}")
        return f"{len(same)} attempts have produced the identical failure at {where}"

    def briefing(self) -> str:
        """Compact history for the next attempt. Facts only, no reasoning."""
        if not self.attempts:
            return ""
        lines = ["Previous attempts in this task:"]
        for a in self.attempts:
            lines.append(a.summary())
        if self.is_stuck():
            lines.append("")
            lines.append(f"STUCK: {self.stuck_detail()}.")
            lines.append("The approach you have been using does not work. Do not "
                         "adjust it again — use a structurally different approach.")
        text = "\n".join(lines)
        return text if len(text) <= MAX_BRIEFING_CHARS else text[-MAX_BRIEFING_CHARS:]

    def to_evidence(self) -> list[dict]:
        """Durable, redaction-safe form for the audit record."""
        return [{
            "attempt": a.number,
            "approach": a.approach,
            "files_changed": a.files_changed,
            "test_target": a.test_target,
            "passed": a.passed,
            "signature": a.signature,
            "strategy": a.strategy,
            "failure": {k: v for k, v in a.failure.items() if k != "raw"},
        } for a in self.attempts]


# Strategies offered in order. A repeat of the same signature moves to the next.
STRATEGIES = [
    "default",
    "reconsider_approach",
    "decompose",
]


def next_strategy(current: str) -> str:
    try:
        i = STRATEGIES.index(current)
    except ValueError:
        return STRATEGIES[0]
    return STRATEGIES[min(i + 1, len(STRATEGIES) - 1)]


STRATEGY_INSTRUCTIONS = {
    "default": "",
    "reconsider_approach": (
        "Your previous approach produced the same failure more than once. State in "
        "one sentence why that approach cannot work, then implement a different one. "
        "Do not make another small adjustment to it."
    ),
    "decompose": (
        "Solve only the single failing case named above. Ignore the cases that "
        "already pass — do not rewrite them. Change the smallest amount of code "
        "that makes that one case correct without breaking the others."
    ),
}


__all__ = [
    "Attempt", "AttemptLedger", "parse_failure", "failure_signature",
    "next_strategy", "STRATEGIES", "STRATEGY_INSTRUCTIONS", "STUCK_THRESHOLD",
    "MAX_RAW_EVIDENCE", "MAX_BRIEFING_CHARS",
]
