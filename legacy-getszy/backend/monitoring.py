"""Observability — Sentry (error tracking) + Logtail (structured logging)."""
import os
import logging
import sys

SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
LOGTAIL_TOKEN = os.environ.get('LOGTAIL_TOKEN', '')


def setup_sentry():
    """Initialize Sentry SDK for error tracking."""
    if not SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(transaction_style='endpoint'),
                sentry_logging,
            ],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=os.environ.get('ENVIRONMENT', 'production'),
            send_default_pii=False,
        )
        logging.getLogger('getszy').info('Sentry initialized')
    except ImportError:
        logging.getLogger('getszy').warning('sentry-sdk not installed — run: pip install sentry-sdk')
    except Exception as e:
        logging.getLogger('getszy').warning(f'Sentry init failed: {e}')


def setup_logtail():
    """Initialize Logtail handler for structured log shipping."""
    if not LOGTAIL_TOKEN:
        return
    try:
        from logtail import LogtailHandler

        handler = LogtailHandler(LOGTAIL_TOKEN)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('%(message)s'))

        root = logging.getLogger('getszy')
        root.addHandler(handler)
        root.info('Logtail initialized')
    except ImportError:
        logging.getLogger('getszy').warning('logtail-python not installed — run: pip install logtail-python')
    except Exception as e:
        logging.getLogger('getszy').warning(f'Logtail init failed: {e}')


def init_monitoring():
    """Called once at server startup."""
    setup_sentry()
    setup_logtail()
