"""Bounded output processing for LLM and tool responses.

Ensures no unbounded string accumulation from:
- Model output
- Tool output
- File contents
- Subprocess output
- Logs / test output

TRUNCATED != SUCCESS — preserves enough structured failure information
for the repair loop.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger('getszy.bounded_output')


# ── Limits ────────────────────────────────────────────────────────────────────
MAX_LLM_OUTPUT_BYTES = 256_000       # 256 KB max LLM response
MAX_TOOL_OUTPUT_BYTES = 64_000       # 64 KB max tool response
MAX_HTML_OUTPUT_BYTES = 512_000      # 512 KB max HTML document
MAX_SUBPROCESS_OUTPUT_BYTES = 32_000 # 32 KB max subprocess output
MAX_FILE_READ_BYTES = 128_000        # 128 KB max file read
MAX_CONTEXT_BYTES = 500_000          # 500 KB max total context for LLM


@dataclass
class BoundedResult:
    """Result with truncation metadata."""
    content: str
    truncated: bool
    original_length: int
    returned_length: int
    limit: int

    @property
    def is_complete(self) -> bool:
        return not self.truncated

    def to_dict(self) -> dict:
        return {
            'content': self.content,
            'truncated': self.truncated,
            'original_length': self.original_length,
            'returned_length': self.returned_length,
            'limit': self.limit,
        }


def bounded_string(text: str, max_bytes: int = MAX_LLM_OUTPUT_BYTES) -> BoundedResult:
    """Truncate a string to max_bytes, preserving structure.

    Returns a BoundedResult with truncation metadata.
    TRUNCATED is explicitly marked so callers know the result is incomplete.
    """
    if not text:
        return BoundedResult(content='', truncated=False, original_length=0, returned_length=0, limit=max_bytes)

    text_bytes = len(text.encode('utf-8'))
    if text_bytes <= max_bytes:
        return BoundedResult(
            content=text,
            truncated=False,
            original_length=text_bytes,
            returned_length=text_bytes,
            limit=max_bytes,
        )

    # Truncate with clear marker
    # Keep 70% from head, 30% from tail to preserve both start and end context
    head_limit = int(max_bytes * 0.7)
    tail_limit = max_bytes - head_limit - 100  # leave room for marker

    head = text[:head_limit].encode('utf-8', errors='ignore').decode('utf-8', errors='replace')
    tail = text[-tail_limit:].encode('utf-8', errors='ignore').decode('utf-8', errors='replace')

    marker = '\n\n...[TRUNCATED: original was %d bytes, returned %d of %d bytes]...\n\n'
    truncated_text = head + marker % (text_bytes, head_limit + tail_limit + len(marker), max_bytes) + tail

    return BoundedResult(
        content=truncated_text,
        truncated=True,
        original_length=text_bytes,
        returned_length=len(truncated_text.encode('utf-8')),
        limit=max_bytes,
    )


def bounded_llm_output(text: str) -> BoundedResult:
    """Bound LLM response output."""
    return bounded_string(text, MAX_LLM_OUTPUT_BYTES)


def bounded_tool_output(text: str) -> BoundedResult:
    """Bound tool execution output."""
    return bounded_string(text, MAX_TOOL_OUTPUT_BYTES)


def bounded_html_output(text: str) -> BoundedResult:
    """Bound HTML document output."""
    return bounded_string(text, MAX_HTML_OUTPUT_BYTES)


def bounded_subprocess_output(text: str) -> BoundedResult:
    """Bound subprocess output."""
    return bounded_string(text, MAX_SUBPROCESS_OUTPUT_BYTES)


def bounded_file_read(text: str) -> BoundedResult:
    """Bound file read output."""
    return bounded_string(text, MAX_FILE_READ_BYTES)


def truncate_for_context(parts: list[dict], max_bytes: int = MAX_CONTEXT_BYTES) -> list[dict]:
    """Truncate a list of context parts (messages, files, etc.) to fit within max_bytes.

    Preserves as many complete parts as possible, dropping from the end.
    Each part should have a 'content' key.
    """
    total = 0
    result = []
    for part in parts:
        content = part.get('content', '')
        part_bytes = len(content.encode('utf-8')) if isinstance(content, str) else 256
        if total + part_bytes > max_bytes:
            # This part would exceed the budget — truncate it if it's the first part,
            # otherwise stop here
            if not result:
                truncated = bounded_string(content, max_bytes)
                result.append({**part, 'content': truncated.content, '_truncated': True})
            break
        total += part_bytes
        result.append(part)
    return result


def repair_evidence(original_error: str, truncated_output: str, attempt: int) -> dict:
    """Create structured evidence for the repair loop when output is truncated.

    TRUNCATED != SUCCESS — this preserves enough info for the next attempt.
    """
    return {
        'type': 'output_truncated',
        'original_error': original_error,
        'truncated_output_preview': truncated_output[:2000],
        'attempt': attempt,
        'note': 'Output was truncated and may be incomplete. Do not treat truncated output as success.',
    }
