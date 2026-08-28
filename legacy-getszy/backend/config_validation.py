"""Strict configuration validation for the Agent Factory.

All agent/role/tool/model/resource configs must pass validation before use.
Invalid security/resource/provider configuration fails closed.

Lifecycle: INPUT -> VALIDATE -> EXPLAIN ERROR -> REPAIR IF SAFE -> REVALIDATE -> EXECUTE
"""
from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger('getszy.config_validation')


class ConfigValidationError(ValueError):
    """Raised when a configuration value is invalid and cannot be safely repaired."""
    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f'Config validation failed for {field}: {reason}')


@dataclass
class ValidationError:
    field: str
    value: Any
    reason: str
    severity: str = 'error'  # error | warning
    repaired: bool = False
    repaired_value: Any = None

    def to_dict(self) -> dict:
        d = {
            'field': self.field,
            'reason': self.reason,
            'severity': self.severity,
            'repaired': self.repaired,
        }
        if self.repaired:
            d['repaired_value'] = self.repaired_value
        return d


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'valid': self.valid,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
        }


# ── Validators ────────────────────────────────────────────────────────────────

def validate_positive_int(value: Any, field_name: str, min_val: int = 1, max_val: int = 10**9) -> ValidationError | None:
    try:
        v = int(value)
        if v < min_val or v > max_val:
            return ValidationError(field_name, value, f'must be between {min_val} and {max_val}')
    except (TypeError, ValueError):
        return ValidationError(field_name, value, f'must be a positive integer')
    return None


def validate_string(value: Any, field_name: str, min_len: int = 1, max_len: int = 10000, pattern: str | None = None) -> ValidationError | None:
    if not isinstance(value, str):
        return ValidationError(field_name, value, 'must be a string')
    if len(value) < min_len or len(value) > max_len:
        return ValidationError(field_name, value, f'length must be between {min_len} and {max_len}')
    if pattern and not re.search(pattern, value):
        return ValidationError(field_name, value, f'does not match required pattern')
    return None


def validate_enum(value: Any, field_name: str, allowed: list) -> ValidationError | None:
    if value not in allowed:
        return ValidationError(field_name, value, f'must be one of: {allowed}')
    return None


def validate_url(value: Any, field_name: str) -> ValidationError | None:
    if not isinstance(value, str):
        return ValidationError(field_name, value, 'must be a string URL')
    if not re.match(r'^https?://', value):
        return ValidationError(field_name, value, 'must be an HTTP/HTTPS URL')
    return None


# ── Model Config Validation ──────────────────────────────────────────────────

VALID_MODEL_TYPES = ['ollama', 'groq', 'gemini', 'openrouter', 'lmstudio']

def validate_model_config(config: dict) -> ValidationResult:
    """Validate a model/provider configuration dict."""
    errors = []
    warnings = []

    # Validate provider type
    provider = config.get('provider', '')
    err = validate_enum(provider, 'provider', VALID_MODEL_TYPES)
    if err:
        errors.append(err)

    # Validate model name
    model = config.get('model', '')
    err = validate_string(model, 'model', min_len=1, max_len=200)
    if err:
        errors.append(err)

    # Provider-specific validation
    if provider == 'ollama':
        base_url = config.get('base_url', 'http://localhost:11434')
        err = validate_url(base_url, 'base_url')
        if err:
            errors.append(err)
    elif provider == 'groq':
        if not os.environ.get('GROQ_API_KEY'):
            warnings.append(ValidationError('GROQ_API_KEY', '(env)', 'not set; Groq will be unavailable', severity='warning'))
    elif provider == 'gemini':
        if not os.environ.get('GEMINI_API_KEY'):
            warnings.append(ValidationError('GEMINI_API_KEY', '(env)', 'not set; Gemini will be unavailable', severity='warning'))

    # Validate numeric limits
    for field_name, min_v, max_v in [
        ('max_tokens', 1, 100000),
        ('temperature', 0, 2),
        ('timeout', 1, 3600),
    ]:
        if field_name in config:
            err = validate_positive_int(config[field_name], field_name, min_v, max_v)
            if err:
                errors.append(err)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ── Resource Config Validation ───────────────────────────────────────────────

def validate_resource_config(config: dict) -> ValidationResult:
    """Validate resource limits configuration."""
    errors = []
    warnings = []

    limits = {
        'max_ram_mb': (64, 32768),
        'max_cpu_seconds': (1, 7200),
        'max_output_bytes': (1024, 50_000_000),
        'max_tool_rounds': (1, 50),
        'max_concurrency': (1, 100),
        'max_delegation_depth': (1, 10),
        'max_children': (1, 50),
        'max_repair_attempts': (1, 10),
        'execution_timeout': (10, 3600),
    }

    for field_name, (min_v, max_v) in limits.items():
        if field_name in config:
            err = validate_positive_int(config[field_name], field_name, min_v, max_v)
            if err:
                errors.append(err)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ── Agent Config Validation ──────────────────────────────────────────────────

def validate_agent_config(config: dict) -> ValidationResult:
    """Validate an agent configuration dict."""
    errors = []
    warnings = []

    # Required fields
    for field_name in ['name', 'role']:
        if field_name not in config:
            errors.append(ValidationError(field_name, config.get(field_name), 'required field missing'))

    if 'name' in config:
        err = validate_string(config['name'], 'name', min_len=1, max_len=100)
        if err:
            errors.append(err)

    if 'role' in config:
        valid_roles = ['planner', 'designer', 'coder', 'reviewer', 'refiner', 'master', 'child', 'specialist']
        err = validate_enum(config['role'], 'role', valid_roles)
        if err:
            errors.append(err)

    # Validate max_rounds if present
    if 'max_rounds' in config:
        err = validate_positive_int(config['max_rounds'], 'max_rounds', 1, 20)
        if err:
            errors.append(err)

    # Validate prompt if present
    if 'system_prompt' in config:
        err = validate_string(config['system_prompt'], 'system_prompt', min_len=10, max_len=50000)
        if err:
            errors.append(err)

    # Validate allowed_tools if present
    if 'allowed_tools' in config:
        if not isinstance(config['allowed_tools'], list):
            errors.append(ValidationError('allowed_tools', config['allowed_tools'], 'must be a list'))
        else:
            for tool in config['allowed_tools']:
                err = validate_string(tool, f'allowed_tools[{tool}]', min_len=1, max_len=100)
                if err:
                    errors.append(err)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ── Task Config Validation ───────────────────────────────────────────────────

def validate_task_config(config: dict) -> ValidationResult:
    """Validate a task execution configuration."""
    errors = []
    warnings = []

    if 'task_type' in config:
        valid_types = ['llm_call', 'builder_pipeline', 'builder_fast', 'builder_polish',
                       'tool_execution', 'browser_task', 'video_generation', 'research', 'default']
        err = validate_enum(config['task_type'], 'task_type', valid_types)
        if err:
            errors.append(err)

    if 'timeout' in config:
        err = validate_positive_int(config['timeout'], 'timeout', 5, 7200)
        if err:
            errors.append(err)

    if 'max_retries' in config:
        err = validate_positive_int(config['max_retries'], 'max_retries', 0, 10)
        if err:
            errors.append(err)

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ── Full System Config Validation ────────────────────────────────────────────

def validate_system_config() -> ValidationResult:
    """Validate the full system configuration at startup."""
    errors = []
    warnings = []

    # Validate model provider chain
    from llm_provider import (
        OLLAMA_MODELS, GROQ_API_KEY, GEMINI_API_KEY,
        OPENROUTER_API_KEY, FREE_ONLY, PER_PROVIDER_MAX_TOKENS,
        TOKEN_BUDGETS, GROQ_MAX_RPM, GROQ_MAX_TPM,
    )

    has_any_provider = bool(GROQ_API_KEY or GEMINI_API_KEY or OPENROUTER_API_KEY or OLLAMA_MODELS)
    if not has_any_provider:
        errors.append(ValidationError('providers', '(env)', 'No LLM providers configured. At least one of GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, or Ollama must be available.'))

    # Validate token budgets are sane
    for provider, budget in TOKEN_BUDGETS.items():
        if budget.get('tpm', 0) <= 0:
            warnings.append(ValidationError(f'TOKEN_BUDGETS.{provider}.tpm', budget.get('tpm'), 'non-positive TPM budget', severity='warning'))
        if budget.get('daily', 0) <= 0:
            warnings.append(ValidationError(f'TOKEN_BUDGETS.{provider}.daily', budget.get('daily'), 'non-positive daily budget', severity='warning'))

    # Validate per-provider max tokens
    for provider, mt in PER_PROVIDER_MAX_TOKENS.items():
        if mt <= 0 or mt > 100000:
            errors.append(ValidationError(f'PER_PROVIDER_MAX_TOKENS.{provider}', mt, 'must be between 1 and 100000'))

    # Validate rate limits
    if GROQ_MAX_RPM <= 0 or GROQ_MAX_RPM > 1000:
        errors.append(ValidationError('GROQ_MAX_RPM', GROQ_MAX_RPM, 'must be between 1 and 1000'))
    if GROQ_MAX_TPM <= 0 or GROQ_MAX_TPM > 1000000:
        errors.append(ValidationError('GROQ_MAX_TPM', GROQ_MAX_TPM, 'must be between 1 and 1000000'))

    # Validate resource limits
    from resource_admission import REJECT_THRESHOLD_MB, DEGRADE_THRESHOLD_MB, SYSTEM_OVERHEAD_MB
    if REJECT_THRESHOLD_MB >= DEGRADE_THRESHOLD_MB:
        errors.append(ValidationError('REJECT_THRESHOLD_MB', REJECT_THRESHOLD_MB, 'must be less than DEGRADE_THRESHOLD_MB'))
    if SYSTEM_OVERHEAD_MB <= 0:
        errors.append(ValidationError('SYSTEM_OVERHEAD_MB', SYSTEM_OVERHEAD_MB, 'must be positive'))

    # Validate cache config
    from cache_utils import _MAX_ENTRIES, _MAX_BYTES
    if _MAX_ENTRIES <= 0 or _MAX_ENTRIES > 100000:
        errors.append(ValidationError('_MAX_ENTRIES', _MAX_ENTRIES, 'must be between 1 and 100000'))
    if _MAX_BYTES <= 0 or _MAX_BYTES > 500_000_000:
        errors.append(ValidationError('_MAX_BYTES', _MAX_BYTES, 'must be between 1 and 500MB'))

    # Validate builder agent constants
    from builder_agents import PLANNER_PROMPT, DESIGNER_PROMPT, CODER_PROMPT, REVIEWER_PROMPT
    for name, prompt in [('PLANNER_PROMPT', PLANNER_PROMPT), ('DESIGNER_PROMPT', DESIGNER_PROMPT),
                         ('CODER_PROMPT', CODER_PROMPT), ('REVIEWER_PROMPT', REVIEWER_PROMPT)]:
        if not prompt or len(prompt) < 20:
            errors.append(ValidationError(name, '(prompt)', 'prompt is empty or too short'))

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# ── Startup validation hook ──────────────────────────────────────────────────

def run_startup_validation() -> ValidationResult:
    """Run all config validations at startup. Logs errors and warnings."""
    result = validate_system_config()
    for err in result.errors:
        logger.error('CONFIG VALIDATION ERROR: %s — %s', err.field, err.reason)
    for warn in result.warnings:
        logger.warning('CONFIG VALIDATION WARNING: %s — %s', warn.field, warn.reason)
    if result.valid:
        logger.info('CONFIG VALIDATION: all checks passed (%d warnings)', len(result.warnings))
    else:
        logger.error('CONFIG VALIDATION FAILED: %d errors, %d warnings', len(result.errors), len(result.warnings))
    return result
