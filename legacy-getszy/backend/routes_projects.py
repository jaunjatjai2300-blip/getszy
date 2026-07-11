"""Full Projects Workspace API — har project ek complete application hai."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_admin, get_current_user
from db import db

router = APIRouter(prefix='/projects', tags=['projects'])

def _iso():
    return datetime.now(timezone.utc).isoformat()

def _id():
    return str(uuid.uuid4())[:12]

# ─────────────────────────── Models ────────────────────────────

class ProjectIn(BaseModel):
    name: str
    description: str = ""
    type: str = "webapp"  # webapp / saas / store / mobile / api / internal
    icon: str = "📁"
    color: str = "#6366f1"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class SchemaTableIn(BaseModel):
    name: str
    columns: list = []

class EndpointIn(BaseModel):
    method: str = "GET"
    path: str
    description: str = ""
    auth_required: bool = True
    response_example: str = "{}"

class EnvVarIn(BaseModel):
    key: str
    value: str
    is_secret: bool = False

class ProjectFileIn(BaseModel):
    filename: str
    content: str
    language: str = "javascript"

class LogEntry(BaseModel):
    level: str = "info"
    message: str

# ─────────────────────────── Projects CRUD ────────────────────────────

@router.get('')
async def list_projects(user=Depends(get_current_admin)):
    items = [p async for p in db.gs_projects.find({}, {'_id': 0}).sort('created_at', -1).limit(100)]
    return {'items': items, 'total': len(items)}

@router.post('')
async def create_project(body: ProjectIn, user=Depends(get_current_admin)):
    pid = _id()
    doc = {
        'id': pid,
        'name': body.name,
        'description': body.description,
        'type': body.type,
        'icon': body.icon,
        'color': body.color,
        'status': 'draft',
        'owner_id': user['id'],
        'created_at': _iso(),
        'updated_at': _iso(),
        'deploy_url': None,
        'domain': None,
        'tech_stack': [],
        'tags': [],
    }
    await db.gs_projects.insert_one(doc)
    return doc

@router.get('/{pid}')
async def get_project(pid: str, user=Depends(get_current_admin)):
    p = await db.gs_projects.find_one({'id': pid}, {'_id': 0})
    if not p:
        raise HTTPException(404, 'Project nahi mila')
    return p

@router.put('/{pid}')
async def update_project(pid: str, body: ProjectUpdate, user=Depends(get_current_admin)):
    p = await db.gs_projects.find_one({'id': pid})
    if not p:
        raise HTTPException(404, 'Project nahi mila')
    upd = {k: v for k, v in body.dict().items() if v is not None}
    upd['updated_at'] = _iso()
    await db.gs_projects.update_one({'id': pid}, {'$set': upd})
    return {'ok': True}

@router.delete('/{pid}')
async def delete_project(pid: str, user=Depends(get_current_admin)):
    await db.gs_projects.delete_one({'id': pid})
    await db.gs_project_schema.delete_many({'project_id': pid})
    await db.gs_project_endpoints.delete_many({'project_id': pid})
    await db.gs_project_files.delete_many({'project_id': pid})
    await db.gs_project_env.delete_many({'project_id': pid})
    await db.gs_project_logs.delete_many({'project_id': pid})
    return {'ok': True}

# ─────────────────────────── Database Schema ────────────────────────────

@router.get('/{pid}/schema')
async def get_schema(pid: str, user=Depends(get_current_admin)):
    tables = [t async for t in db.gs_project_schema.find({'project_id': pid}, {'_id': 0})]
    return {'tables': tables}

@router.post('/{pid}/schema/tables')
async def add_table(pid: str, body: SchemaTableIn, user=Depends(get_current_admin)):
    doc = {'id': _id(), 'project_id': pid, 'name': body.name, 'columns': body.columns, 'created_at': _iso()}
    await db.gs_project_schema.insert_one(doc)
    return doc

@router.put('/{pid}/schema/tables/{tid}')
async def update_table(pid: str, tid: str, body: dict, user=Depends(get_current_admin)):
    await db.gs_project_schema.update_one({'id': tid, 'project_id': pid}, {'$set': body})
    return {'ok': True}

@router.delete('/{pid}/schema/tables/{tid}')
async def delete_table(pid: str, tid: str, user=Depends(get_current_admin)):
    await db.gs_project_schema.delete_one({'id': tid, 'project_id': pid})
    return {'ok': True}

# ─────────────────────────── API Endpoints ────────────────────────────

@router.get('/{pid}/endpoints')
async def get_endpoints(pid: str, user=Depends(get_current_admin)):
    eps = [e async for e in db.gs_project_endpoints.find({'project_id': pid}, {'_id': 0})]
    return {'endpoints': eps}

@router.post('/{pid}/endpoints')
async def add_endpoint(pid: str, body: EndpointIn, user=Depends(get_current_admin)):
    doc = {'id': _id(), 'project_id': pid, **body.dict(), 'created_at': _iso()}
    await db.gs_project_endpoints.insert_one(doc)
    return doc

@router.delete('/{pid}/endpoints/{eid}')
async def delete_endpoint(pid: str, eid: str, user=Depends(get_current_admin)):
    await db.gs_project_endpoints.delete_one({'id': eid, 'project_id': pid})
    return {'ok': True}

# ─────────────────────────── Files ────────────────────────────

@router.get('/{pid}/files')
async def get_files(pid: str, user=Depends(get_current_admin)):
    files = [f async for f in db.gs_project_files.find({'project_id': pid}, {'_id': 0})]
    return {'files': files}

@router.post('/{pid}/files')
async def add_file(pid: str, body: ProjectFileIn, user=Depends(get_current_admin)):
    doc = {'id': _id(), 'project_id': pid, **body.dict(), 'updated_at': _iso()}
    await db.gs_project_files.insert_one(doc)
    return doc

@router.put('/{pid}/files/{fid}')
async def update_file(pid: str, fid: str, body: dict, user=Depends(get_current_admin)):
    await db.gs_project_files.update_one({'id': fid, 'project_id': pid}, {'$set': {**body, 'updated_at': _iso()}})
    return {'ok': True}

@router.delete('/{pid}/files/{fid}')
async def delete_file(pid: str, fid: str, user=Depends(get_current_admin)):
    await db.gs_project_files.delete_one({'id': fid, 'project_id': pid})
    return {'ok': True}

# ─────────────────────────── Env Vars ────────────────────────────

@router.get('/{pid}/env')
async def get_env(pid: str, user=Depends(get_current_admin)):
    envs = [e async for e in db.gs_project_env.find({'project_id': pid}, {'_id': 0})]
    # Mask secret values
    for e in envs:
        if e.get('is_secret'):
            e['value'] = '••••••••'
    return {'env': envs}

@router.post('/{pid}/env')
async def set_env(pid: str, body: EnvVarIn, user=Depends(get_current_admin)):
    existing = await db.gs_project_env.find_one({'project_id': pid, 'key': body.key})
    doc = {'id': _id(), 'project_id': pid, 'key': body.key, 'value': body.value, 'is_secret': body.is_secret, 'updated_at': _iso()}
    if existing:
        await db.gs_project_env.update_one({'project_id': pid, 'key': body.key}, {'$set': doc})
    else:
        await db.gs_project_env.insert_one(doc)
    return {'ok': True}

@router.delete('/{pid}/env/{key}')
async def delete_env(pid: str, key: str, user=Depends(get_current_admin)):
    await db.gs_project_env.delete_one({'project_id': pid, 'key': key})
    return {'ok': True}

# ─────────────────────────── Analytics ────────────────────────────

@router.get('/{pid}/analytics')
async def get_analytics(pid: str, user=Depends(get_current_admin)):
    p = await db.gs_projects.find_one({'id': pid}, {'_id': 0})
    if not p:
        raise HTTPException(404, 'Project nahi mila')
    return {
        'page_views': p.get('analytics_views', 0),
        'api_calls': p.get('analytics_api_calls', 0),
        'errors': p.get('analytics_errors', 0),
        'uptime': p.get('analytics_uptime', '100%'),
        'last_deployed': p.get('last_deployed'),
        'deploy_count': p.get('deploy_count', 0),
    }

@router.post('/{pid}/analytics/track')
async def track_event(pid: str, body: dict):
    event = body.get('event', 'view')
    field_map = {'view': 'analytics_views', 'api_call': 'analytics_api_calls', 'error': 'analytics_errors'}
    field = field_map.get(event, 'analytics_views')
    await db.gs_projects.update_one({'id': pid}, {'$inc': {field: 1}}, upsert=False)
    return {'ok': True}

# ─────────────────────────── Logs ────────────────────────────

@router.get('/{pid}/logs')
async def get_logs(pid: str, limit: int = 100, user=Depends(get_current_admin)):
    logs = [l async for l in db.gs_project_logs.find({'project_id': pid}, {'_id': 0}).sort('ts', -1).limit(limit)]
    return {'logs': list(reversed(logs))}

@router.post('/{pid}/logs')
async def add_log(pid: str, body: LogEntry, user=Depends(get_current_admin)):
    doc = {'id': _id(), 'project_id': pid, 'level': body.level, 'message': body.message, 'ts': _iso()}
    await db.gs_project_logs.insert_one(doc)
    return {'ok': True}

@router.delete('/{pid}/logs')
async def clear_logs(pid: str, user=Depends(get_current_admin)):
    await db.gs_project_logs.delete_many({'project_id': pid})
    return {'ok': True}

# ─────────────────────────── AI Config ────────────────────────────

@router.get('/{pid}/ai')
async def get_ai_config(pid: str, user=Depends(get_current_admin)):
    cfg = await db.gs_project_ai.find_one({'project_id': pid}, {'_id': 0})
    if not cfg:
        cfg = {'project_id': pid, 'provider': 'ollama', 'model': 'qwen2.5:7b', 'system_prompt': '', 'temperature': 0.7, 'tools': []}
    return cfg

@router.put('/{pid}/ai')
async def update_ai_config(pid: str, body: dict, user=Depends(get_current_admin)):
    body['project_id'] = pid
    body['updated_at'] = _iso()
    await db.gs_project_ai.replace_one({'project_id': pid}, body, upsert=True)
    return {'ok': True}

# ─────────────────────────── Storage ────────────────────────────

@router.get('/{pid}/storage')
async def get_storage(pid: str, user=Depends(get_current_admin)):
    files = [f async for f in db.gs_project_storage.find({'project_id': pid}, {'_id': 0}).sort('uploaded_at', -1).limit(200)]
    total_bytes = sum(f.get('size_bytes', 0) for f in files)
    return {'files': files, 'total_bytes': total_bytes, 'count': len(files)}

# ─────────────────────────── Deploy ────────────────────────────

@router.post('/{pid}/deploy')
async def deploy_project(pid: str, body: dict, user=Depends(get_current_admin)):
    p = await db.gs_projects.find_one({'id': pid})
    if not p:
        raise HTTPException(404, 'Project nahi mila')
    env_str = body.get('env', '')
    deploy_doc = {
        'id': _id(),
        'project_id': pid,
        'status': 'deploying',
        'environment': body.get('environment', 'production'),
        'message': 'Deploy shuru hua...',
        'started_at': _iso(),
    }
    await db.gs_project_deploys.insert_one(deploy_doc)
    await db.gs_projects.update_one({'id': pid}, {'$set': {'status': 'deploying', 'last_deployed': _iso(), '$inc': {'deploy_count': 1}}})
    # Simulate deploy complete (in prod this would trigger VPS webhook)
    import asyncio
    await asyncio.sleep(0.1)
    await db.gs_project_deploys.update_one({'id': deploy_doc['id']}, {'$set': {'status': 'live', 'completed_at': _iso(), 'message': 'Deploy successful!'}})
    await db.gs_projects.update_one({'id': pid}, {'$set': {'status': 'live'}})
    return {'deploy_id': deploy_doc['id'], 'status': 'live'}

@router.get('/{pid}/deploys')
async def list_deploys(pid: str, user=Depends(get_current_admin)):
    deploys = [d async for d in db.gs_project_deploys.find({'project_id': pid}, {'_id': 0}).sort('started_at', -1).limit(20)]
    return {'deploys': deploys}
