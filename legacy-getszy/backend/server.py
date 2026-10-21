from fastapi import FastAPI, APIRouter, Response, Depends
from auth import get_current_admin
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
import logging
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from db import db, client
from app.router_registry import load_all_routers
from monitoring import init_monitoring
from llm_provider import LLMServiceUnavailable

# FastAPI docs remain available on the private backend for local CI and operator
# diagnostics. Caddy explicitly returns 404 for these paths on the public domain.
app = FastAPI(title='getszy API')
api_router = APIRouter(prefix='/api')

# Flipped False when the financial idempotency unique indexes fail to build at
# startup (duplicate legacy data, etc.). Surfaced by /api/health as
# indexes=missing so double-spend protection being off is visible to monitors.
INDEXES_ENSURED = True


@app.exception_handler(LLMServiceUnavailable)
async def _llm_unavailable_handler(request, exc):
    """When every LLM provider in the fallback chain is down, surface a clean 503
    (not a raw 500). Lets clients/users degrade gracefully and lets monitoring
    alert on AI outages without scraping stack traces."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=503,
        content={'error': 'ai_service_unavailable', 'message': 'The AI service is temporarily unavailable. Please try again shortly.'},
    )



@app.exception_handler(Exception)
async def _unhandled_handler(request, exc):
    """Catch any unhandled error: log server-side, return a clean envelope."""
    logger.error(f'Unhandled error {request.method} {request.url.path}: {exc}', exc_info=True)
    return JSONResponse(
        status_code=500,
        content={'error': 'internal_server_error', 'message': 'An unexpected error occurred.'},
    )


@api_router.get('/')
async def root():
    return {'message': 'getszy API live', 'version': '2.0.0', 'ai': 'Getszy AI'}


@api_router.get('/health')
@api_router.get('/healthz')
async def health():
    try:
        await db.command('ping')
    except Exception:
        # A non-2xx response is required for Docker, uptime monitors, and reverse
        # proxies to recognise a database outage instead of treating an error body
        # as a healthy service.
        return JSONResponse(status_code=503, content={'status': 'error', 'detail': 'database_unavailable'})
    # Redis is optional for serving traffic, so a Redis outage degrades the
    # health status (not an error): alerting watches the 'degraded' state.
    from redis_client import check_redis_health
    redis_ok = await check_redis_health()
    if not redis_ok:
        logger.warning('health: redis ping failed — status degraded (auth revocation lists and rate limits are disabled)')
    # Resource admission involves a blocking pgrep/subprocess probe; keep it off
    # the event loop.
    try:
        from resource_admission import resource_status_async
        resource_info = await resource_status_async()
    except Exception:
        resource_info = {}
    return {
        'status': 'ok' if redis_ok else 'degraded',
        'mongo': True,
        'redis': bool(redis_ok),
        'indexes': 'ok' if INDEXES_ENSURED else 'missing',
        'ai': 'Getszy AI',
        'resources': resource_info,
    }


@api_router.get('/factory/status', dependencies=[Depends(get_current_admin)])
async def factory_status():
    """Agent Factory health and resource status endpoint. Admin-only: it exposes
    internal resource/limit/ledger internals that must not leak to customers."""
    try:
        from resource_admission import resource_status
        from task_limits import limits_status
        from attempt_ledger import ledger_status
        from cache_utils import cache_info
        from task_limits import active_task_count

        return {
            'status': 'ok',
            'resources': resource_status(),
            'limits': limits_status(),
            'ledgers': ledger_status(),
            'cache': cache_info(),
            'active_tasks': active_task_count(),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={'status': 'error', 'detail': str(e)})


@api_router.get('/health/llm')
async def llm_health():
    """Lightweight LLM connectivity probe (no credits spent on heavy calls)."""
    try:
        from llm_provider import chat_completion
        provider = os.environ.get('LLM_PROVIDER', 'groq')
        result = await chat_completion('You are a health check. Reply with the single word: pong', 'ping', temperature=0)
        ok = bool(result) and len(result) > 0
        return {
            'status': 'ok' if ok else 'degraded',
            'provider': provider,
            'response': (result or '')[:50],
            'free_only': os.environ.get('FREE_ONLY', 'false'),
        }
    except Exception as e:
        # Unauthenticated endpoint: never echo raw provider errors to the
        # internet (they can leak key names, internal hosts, rate-limit proof).
        # Log server-side and return a generic status only.
        logger.warning('llm_health probe failed: %s', e)
        return {'status': 'error', 'provider': os.environ.get('LLM_PROVIDER', 'groq')}


@app.get('/metrics')
async def metrics():
    """Prometheus scrape endpoint (unauthenticated by design)."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ===== Load all routers via registry =====
registered_router = load_all_routers()
api_router.include_router(registered_router)

app.include_router(api_router)

# ===== Security middleware =====
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        'CORS_ORIGINS',
        'https://getszy.com,https://www.getszy.com'
    ).split(',') if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type', 'Idempotency-Key'],
)

from middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware, PrometheusMiddleware
from redis_rate_limit import RedisRateLimitMiddleware
from metrics_protect import MetricsProtectionMiddleware
app.add_middleware(MetricsProtectionMiddleware)
app.add_middleware(RedisRateLimitMiddleware, requests_per_minute=200)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(PrometheusMiddleware)

from logging_config import configure_logging
configure_logging(os.environ.get('LOG_LEVEL', 'INFO'))
logger = logging.getLogger('getszy')


from retention import _install_createdAt_stamp


async def _check_ai_providers():
    """Startup self-check: warn loudly if NO usable AI provider is configured.

    Without at least one working provider, every AI/video action fails — and
    before the video-factory recovery fix, that left projects stuck at
    'processing' forever. Log this up front so it's caught in deploy logs
    instead of by confused users.
    """
    import httpx

    groq = os.environ.get('GROQ_API_KEY')
    gemini = os.environ.get('GEMINI_API_KEY')
    openrouter = os.environ.get('OPENROUTER_API_KEY')
    emergent = os.environ.get('EMERGENT_LLM_KEY')
    lmstudio = os.environ.get('LMSTUDIO_BASE_URL')
    ollama = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434' if False else 'http://localhost:11434')

    remote = []
    if groq:
        remote.append('Groq')
    if gemini:
        remote.append('Gemini')
    if openrouter:
        remote.append('OpenRouter')
    if emergent:
        remote.append('Emergent')
    if lmstudio:
        remote.append('LM Studio')

    # Ollama is local — don't assume it's up; verify reachability.
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f'{ollama}/api/tags')
            ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False

    usable = list(remote) + (['Ollama(local)'] if ollama_ok else [])
    if usable:
        logger.info('AI PROVIDER SELF-CHECK: usable providers = %s', ', '.join(usable))
    else:
        logger.error(
            'AI PROVIDER SELF-CHECK: NO usable AI provider detected! Ollama at %s is '
            'unreachable AND no GROQ/GEMINI/OPENROUTER/EMERGENT keys are set. ALL AI and '
            'video generation will FAIL. Fix: set GROQ_API_KEY (free) or make Ollama '
            'reachable from this container (e.g. extra_hosts for host.docker.internal).',
            ollama,
        )
        return

    if not ollama_ok:
        logger.warning(
            'AI PROVIDER SELF-CHECK: Ollama at %s unreachable — OK only if relying on '
            'remote keys (%s).', ollama, ', '.join(remote) or 'none',
        )


async def _recover_builder_operations_after_startup():
    """Resume durable website operations that survived a process restart."""
    await asyncio.sleep(5)
    try:
        from routes_builder import recover_pending_builder_operations
        resumed = await recover_pending_builder_operations()
        logger.info('builder operation recovery scheduled %s operation(s)', resumed)
    except Exception as exc:
        logger.warning('builder operation recovery scheduling failed: %s', exc)


async def _periodic_chain_recovery():
    """Self-healing loop: re-run chain recovery every 60s so a factory chain
    killed by a process restart is reset+refunded without manual intervention.
    Heartbeat-based, so live chains are never touched."""
    from routes_video_factory import recover_stuck_chain_jobs
    await asyncio.sleep(30)
    while True:
        try:
            await recover_stuck_chain_jobs()
        except Exception as e:
            logger.warning(f'periodic chain recovery error: {e}')
        await asyncio.sleep(60)


@app.on_event('startup')
async def startup():
    logger.info('getszy backend starting')
    # Fail fast at boot if Mongo is unreachable: the index builds below silently
    # swallowing a dead database meant the app came up without unique indexes
    # (double-spend idempotency protection disabled). Bounded retry per policy.
    for attempt in range(1, 13):
        try:
            await db.command('ping')
            break
        except Exception as e:
            if attempt >= 12:
                raise RuntimeError(f'Mongo unreachable after {attempt} ping attempts — aborting startup: {e}')
            logger.warning('mongo not reachable yet (ping %d/12): %s — retrying in 5s', attempt, e)
            await asyncio.sleep(5)
    global INDEXES_ENSURED
    try:
        # Agent Factory config validation — must run before anything else
        try:
            from config_validation import run_startup_validation
            config_result = run_startup_validation()
            if not config_result.valid:
                logger.error('CONFIG VALIDATION FAILED — %d errors. Continuing with warnings.',
                             len(config_result.errors))
        except Exception as cv_err:
            logger.error('Config validation could not run: %s', cv_err)

        await _check_ai_providers()
        init_monitoring()
        _install_createdAt_stamp()
        from seed import seed_if_empty, seed_courses_if_empty
        await seed_if_empty()
        await seed_courses_if_empty()
        # Migration: restore video URLs that were accidentally blanked
        # (idempotent — see video_restore_migration.py; URL catalog lives there)
        from video_restore_migration import restore_blank_lesson_videos
        restored = await restore_blank_lesson_videos(db)
        if restored:
            logger.info(f'video restore migration: restored {restored} lesson video URLs')
        # Ensure all premium-level courses are flagged
        await db.courses.update_many({'level': 'Advanced'}, {'$set': {'is_premium': True}})
        await db.courses.update_many({'level': {'$in': ['Beginner', 'Intermediate']}}, {'$set': {'is_premium': False}})
        # Financial idempotency unique indexes (payment/credit double-spend
        # protection) get their OWN error boundary: if these fail, the app must
        # still boot, but the gap is recorded (INDEXES_ENSURED) and surfaced by
        # /api/health as indexes=missing instead of the giant try/except hiding it.
        try:
            # Unique index so a Razorpay payment_id can only ever grant credits once
            await db.billing_processed_payments.create_index('payment_id', unique=True)
            # Operation-aware spend ledger projection: one operation reference has one spend row.
            # The users.paid_debit_markers entry remains the financial authority across a crash.
            await db.credit_transactions.create_index(
                [('user_id', 1), ('type', 1), ('ref_id', 1)],
                unique=True,
                partialFilterExpression={'type': 'spend', 'ref_id': {'$exists': True}},
                name='uniq_operation_spend_ref',
            )
            # Race-free refund idempotency: a refund with the same (user_id, ref_id) can
            # only ever be inserted once, so a retried job failure cannot double-refund.
            # NOTE: MongoDB partial filters cannot use `$ne`; `$gt: None` is the supported
            # idiom for "field exists and is not null". credits.refund() omits `ref_id`
            # entirely when absent, so legacy ref_id-less refunds are not uniqueness-bound.
            await db.credit_transactions.create_index(
                [('user_id', 1), ('ref_id', 1), ('type', 1)],
                unique=True,
                partialFilterExpression={'ref_id': {'$gt': None}},
            )
            INDEXES_ENSURED = True
        except Exception as e:
            INDEXES_ENSURED = False
            logger.critical('CRITICAL: financial idempotency unique indexes failed to build — '
                            'payment/credit double-spend protection may be disabled: %s', e)
        # Production indexes
        await db.users.create_index('email', unique=True)
        await db.users.create_index('id', unique=True)
        await db.products.create_index('slug')
        await db.products.create_index('category')
        await db.products.create_index('is_active')
        await db.products.create_index([('is_active', 1), ('is_featured', 1)])
        await db.products.create_index([('is_active', 1), ('is_digital', 1)])
        await db.products.create_index([('is_active', 1), ('category', 1)])
        await db.products.create_index([('category', 1), ('is_active', 1)])
        await db.categories.create_index('slug')
        await db.orders.create_index('user_id')
        await db.orders.create_index('created_at')
        await db.orders.create_index('order_number', unique=True)
        await db.carts.create_index('user_id', unique=True)
        await db.notifications.create_index([('user_id', 1), ('created_at', -1)])
        await db.video_jobs.create_index('user_id')
        # TTL retention indexes. MongoDB TTL only expires docs whose indexed field is a
        # real BSON Date. _install_createdAt_stamp() (below) guarantees every insert to
        # these collections carries a 'createdAt' datetime, so expiry actually runs.
        # (The old request_logs index lived on a *string* 'timestamp' field and never fired.)
        await db.request_logs.create_index('createdAt', expireAfterSeconds=7 * 86400)
        await db.audit_logs.create_index('createdAt', expireAfterSeconds=90 * 86400)
        await db.video_jobs.create_index('createdAt', expireAfterSeconds=30 * 86400)
        await db.deploy_jobs.create_index('createdAt', expireAfterSeconds=30 * 86400)
        await db.credit_transactions.create_index('createdAt', expireAfterSeconds=365 * 86400)
        # New indexes from audit
        await db.credit_transactions.create_index('user_id')
        await db.credit_transactions.create_index('created_at')
        await db.admin_chat.create_index('session_id')
        await db.chat_projects.create_index('user_id')
        await db.chat_messages.create_index('project_id')
        await db.media_assets.create_index('user_id')
        await db.enrollments.create_index('user_id')
        await db.builder_projects.create_index('user_id')
        await db.paid_operations.create_index(
            [('user_id', 1), ('action_type', 1), ('idempotency_key', 1)],
            unique=True,
            name='uniq_customer_paid_operation_intention',
        )
        await db.paid_operations.create_index([('user_id', 1), ('updated_at', -1)])
        await db.paid_operations.create_index([('status', 1), ('lease_expires_at', 1)])
        await db.custom_agents.create_index('user_id')
        await db.deploy_jobs.create_index('created_at')
        # ── DB-audit additions: perf + de-duplication ────────────────────────────
        await db.subscriptions.create_index([('user_id', 1), ('status', 1)])
        await db.agent_chats.create_index([('user_id', 1), ('agent_id', 1), ('created_at', -1)])
        await db.referrals.create_index('referrer_id')
        await db.enrollments.create_index('course_slug')
        # Unique slugs/refs — non-fatal if legacy duplicates exist (logged, not crashed)
        try:
            await db.courses.create_index('slug', unique=True)
        except Exception as e:
            logger.warning(f'courses.slug unique index skipped (duplicate slugs?): {e}')
        try:
            await db.users.create_index('referral_code', unique=True,
                                        partialFilterExpression={'referral_code': {'$gt': None}})
        except Exception as e:
            logger.warning(f'users.referral_code unique index skipped: {e}')
        logger.info('indexes ensured')
        # Launch automated nightly backup (first run ~10 min after start)
        try:
            from backup import backup_scheduler
            asyncio.create_task(backup_scheduler())
        except Exception as e:
            logger.error(f'could not start backup scheduler: {e}')
        # Recover video jobs interrupted by a previous crash/restart (prevents orphaned
        # 'generating_*' jobs and leaked credits).
        try:
            from routes_video_factory import recover_stuck_video_jobs, recover_stuck_chain_jobs
            await recover_stuck_video_jobs()
            # Self-healing: periodically re-check chains so one killed by a restart
            # (its BackgroundTask dies with the process) resets without a manual restart.
            asyncio.create_task(_periodic_chain_recovery())
        except Exception as e:
            logger.error(f'could not run video job recovery: {e}')
        asyncio.create_task(_recover_builder_operations_after_startup())
        # Catalog-to-Video auto-sync watcher (graceful if standalone mongo)
        try:
            from routes_catalog_video import start_catalog_watcher
            asyncio.create_task(start_catalog_watcher())
        except Exception as e:
            logger.error(f'could not start catalog watcher: {e}')
        # DPDP deletion worker — actually erases user data after the grace period.
        try:
            from routes_legal import deletion_worker
            asyncio.create_task(deletion_worker())
        except Exception as e:
            logger.error(f'could not start deletion worker: {e}')
    except Exception as e:
        # Never let a startup task (seeding, migration, index build, scheduler)
        # take the whole server down. The app must always come up and serve
        # /api/health; a partial failure is logged, not fatal.
        logger.error('startup tasks failed (server still starting): %s', e)


@app.on_event('shutdown')
async def shutdown_db():
    client.close()
