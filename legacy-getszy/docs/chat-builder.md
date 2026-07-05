# Universal AI Chat Builder — Architecture

**Phase 17 · Delivered ****: single chat interface that becomes the entry point for every creator/founder workflow on Getszy.

## Design principles

1. **Do not duplicate business logic.** Existing modules stay untouched. The Chat Builder is a routing + orchestration layer that dispatches to already-implemented capabilities.
2. **Every request is a Project.** Chats, messages, generated assets, progress events, and downstream job references (video jobs, builder projects, workforce runs, sourcing scans, etc.) are all linked to the parent project.
3. **Streaming via polling.** The client polls `/api/chat/session/{id}/events?since=ISO` at ~1s cadence during active runs. Contract is compatible with a future SSE / WebSocket upgrade — no client changes required.
4. **Fail-safe classification.** If the LLM cannot classify a request unambiguously it returns `intent=general_chat` with a clarifying question; nothing is dispatched.

## Package layout

```
backend/
├── chat_builder/
│   ├── __init__.py
│   ├── intents.py          ← LLM-driven intent classifier
│   ├── capabilities.py     ← Registry of 13 capabilities (each wraps an existing module)
│   └── orchestrator.py     ← per-turn: classify → dispatch → persist → emit events
├── routes_chat_builder.py  ← REST endpoints under /api/chat/*
└── server.py               ← includes chat_builder_router

frontend/src/pages/admin/
└── ChatHome.jsx            ← default authenticated route (/admin, /admin/chat, /admin/chat/:id)
```

## Capability registry

`chat_builder/capabilities.py` defines a single dictionary `CAPABILITIES` where each entry declares:

```python
{
  'id':           str,                                    # capability id
  'desc':         str,                                    # human description (LLM sees this)
  'params':       {'field': 'type hint string'},
  'run':          async (user, params, emit) -> dict,     # wraps existing module
  'result_kind':  str,                                    # informs the UI which preview to render
}
```

Current registry (13 capabilities):

| id | Wraps | Result kind |
| --- | --- | --- |
| write_script | `creator.scripts.generate` | script |
| score_hook | `creator.scripts.score_hook` | hook_score |
| viral_score | `creator.scripts.viral_score` | viral_score |
| predict_trends | `creator.trends.predict` | trends |
| competitor_gap | `creator.trends.competitor_gap` | competitor_gap |
| generate_video | `video.pipeline.run_job` (queues) | video_job |
| plan_channel | direct LLM (uses existing channel schema) | channel_plan |
| build_webapp | direct LLM (writes to `builder_projects`) | webapp |
| starter_mobileapp | `builder_starters.gen_mobileapp_zip` | starter_mobileapp |
| starter_fullstack | `builder_starters.gen_fullstack_zip` | starter_fullstack |
| starter_blog | `builder_starters.gen_blog_zip` | starter_blog |
| run_workforce | `workforce.agents.run_agent` | workforce_run |
| sourcing_scan | `sourcing.aggregator.scan` | sourcing_scan |

To add a new capability: append one entry to `CAPABILITIES` and one preview component to `ChatHome.jsx`'s `AssetPreview` dispatcher. **No changes required elsewhere** — the intent classifier picks it up automatically from the registry catalog.

## Data model

| Collection | Purpose | Key fields |
| --- | --- | --- |
| `chat_projects` | One per session | id, user_id, title, capabilities_used[], asset_kinds_used[], last_intent, created_at, updated_at |
| `chat_messages` | Ordered dialogue | id, project_id, role (user/assistant), content, intent, asset_id, meta.phase (ack/result), created_at |
| `chat_events` | Progress stream | id, project_id, kind (status/progress/intent/asset/done/error), payload, created_at |
| `chat_assets` | Deliverables produced by capabilities | id, project_id, kind, title, data (kind-specific), source_intent, source_params, created_at |

Assets reference existing collections by id (e.g. a `video_job` asset stores the `video_jobs.id` in its `data.job_id`, so the original single-project pages continue to work unchanged).

## Orchestration flow (single turn)

```
POST /api/chat/session/{id}/message
   ↓ persists user message + emits 'user_message'
   ↓ emits 'status' phase=thinking
   ↓ chat_builder.intents.classify(msg, history)  ← 1 LLM call
   ↓ persists 'ack' assistant message + emits 'intent'
   ↓ capability.run(user, params, emit)           ← wraps existing module
       ├── emits 'progress' events as it works
       └── returns {kind, title, data}
   ↓ persists chat_asset + emits 'asset'
   ↓ persists final assistant message + emits 'done'
```

The client polls `/events?since=<server_time>` at 1.2s cadence while a turn is in flight, receiving incremental events + messages + assets.

## API surface

Base: `/api/chat`

| Verb | Path | Purpose |
| --- | --- | --- |
| GET | /capabilities | Enumerate what Neo can do |
| POST | /session | Create a project (optionally with `first_message`) |
| GET | /sessions | List user's projects |
| GET | /session/{id} | Full project: messages + assets |
| POST | /session/{id}/message | Send a user message (background dispatch) |
| GET | /session/{id}/events?since=ISO | Poll for new events/messages/assets |
| PATCH | /session/{id} | Rename |
| DELETE | /session/{id} | Delete project + all children |

All endpoints require the standard `Authorization: Bearer <jwt>` header (existing `auth.get_current_user`).

## Frontend surface

Route `/admin/*`:
- `/admin` → ChatHome (default landing after auth)
- `/admin/chat/:sessionId` → ChatHome with a specific project
- `/admin/overview` → the previous stats dashboard (moved from index)
- All previously-existing routes (`/admin/video`, `/admin/build`, …) remain functional for power users

`ChatHome.jsx` is composed of:
- `WelcomeScreen` — big prompt input + 6 suggestion cards
- `ChatWorkspace` — 12-col split: 7 for conversation, 5 for asset preview
- `Bubble` / `ThinkingBubble` — chat rendering
- `AssetPreview` dispatcher → 11 kind-specific renderers (WebappPreview shows iframe, VideoPreview polls job status, ChannelPreview shows calendar, ScriptPreview shows hook/body/cta, etc.)

## Extending Neo

- **Add a capability**: add to `CAPABILITIES`; done. The classifier's `_capabilities_catalog()` reads the registry live.
- **Change LLM provider**: `chat_completion` in `llm_provider.py` is the single seam.
- **Upgrade to SSE**: replace client polling in `ChatHome.jsx` `poll()` with an EventSource; keep server endpoint contract identical.
