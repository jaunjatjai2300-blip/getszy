"""Structured JSON logging for the Getszy backend.

Drop-in replacement for basic logging that emits one JSON object per log line,
making it trivially parseable by Loki / Datadog / CloudWatch / jq.
"""
import json
import logging
import sys
import time
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
            'module': record.module,
            'func': record.funcName,
            'line': record.lineno,
        }
        if record.exc_info:
            payload['exc'] = self.formatException(record.exc_info)
        # Attach any extra= kwargs the caller passed (e.g. request_id, user_id)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith('_'):
                payload[key] = value
        return json.dumps(payload, default=str)


_RESERVED = {
    'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename', 'funcName',
    'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message', 'msg',
    'name', 'pathname', 'process', 'processName', 'relativeCreated', 'stack_info',
    'thread', 'threadName', 'taskName',
}


def configure_logging(level: str = 'INFO') -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Quiet down noisy libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('motor').setLevel(logging.WARNING)
