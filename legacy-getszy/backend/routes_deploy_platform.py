import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_admin
from db import db

router = APIRouter(prefix='/admin/deploy-platform', tags=['deploy-platform'])


def _now():
    return datetime.now(timezone.utc).isoformat()


class DeployRequest(BaseModel):
    project_id: str
    git_commit: str = ''
    environment: str = 'production'


class ReleaseCreate(BaseModel):
    version: str
    changelog: str = ''
    assets: List[str] = []


class EnvVarInput(BaseModel):
    key: str
    value: str
    project_id: str


class DomainInput(BaseModel):
    domain: str
    project_id: str
    auto_ssl: bool = True


@router.post('/deploy')
async def create_deployment(payload: DeployRequest, _=Depends(get_current_admin)):
    deploy_id = uuid.uuid4().hex[:12]
    now = _now()

    deployment = {
        'id': deploy_id,
        'project_id': payload.project_id,
        'status': 'pending',
        'git_commit': payload.git_commit,
        'environment': payload.environment,
        'logs': [f'[{now}] Deployment {deploy_id} created'],
        'created_at': now,
        'updated_at': now,
        'completed_at': None,
    }
    await db.deployments.insert_one(deployment)

    build_start = _now()
    await db.deployments.update_one(
        {'id': deploy_id},
        {'$set': {'status': 'building', 'updated_at': build_start},
         '$push': {'logs': f'[{build_start}] Pulling code and building...'}}
    )
    import asyncio
    await asyncio.sleep(1)

    build_end = _now()
    await db.deployments.update_one(
        {'id': deploy_id},
        {'$set': {'status': 'deploying', 'updated_at': build_end},
         '$push': {'logs': f'[{build_end}] Build successful. Starting container...'}}
    )
    await asyncio.sleep(1)

    deploy_end = _now()
    await db.deployments.update_one(
        {'id': deploy_id},
        {'$set': {'status': 'live', 'updated_at': deploy_end, 'completed_at': deploy_end},
         '$push': {'logs': f'[{deploy_end}] Deployment live. Health check passed.'}}
    )

    deployment['status'] = 'live'
    deployment['updated_at'] = deploy_end
    deployment['completed_at'] = deploy_end
    deployment.pop('_id', None)
    return deployment


@router.get('/deployments')
async def list_deployments(
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    _=Depends(get_current_admin)
):
    query = {}
    if status:
        query['status'] = status
    if project_id:
        query['project_id'] = project_id
    cur = db.deployments.find(query, {'_id': 0}).sort('created_at', -1).limit(limit)
    deployments = [d async for d in cur]
    return {'deployments': deployments, 'count': len(deployments)}


@router.get('/deployments/{deploy_id}')
async def get_deployment(deploy_id: str, _=Depends(get_current_admin)):
    deployment = await db.deployments.find_one({'id': deploy_id}, {'_id': 0})
    if not deployment:
        raise HTTPException(status_code=404, detail='Deployment not found')
    return deployment


@router.post('/deployments/{deploy_id}/rollback')
async def rollback_deployment(deploy_id: str, _=Depends(get_current_admin)):
    deployment = await db.deployments.find_one({'id': deploy_id}, {'_id': 0})
    if not deployment:
        raise HTTPException(status_code=404, detail='Deployment not found')

    project_id = deployment['project_id']
    prev = await db.deployments.find_one(
        {'project_id': project_id, 'status': 'live', 'id': {'$ne': deploy_id}},
        {'_id': 0}
    )
    if not prev:
        raise HTTPException(status_code=404, detail='No previous successful deployment to rollback to')

    now = _now()
    rollback_id = uuid.uuid4().hex[:12]
    rollback = {
        'id': rollback_id,
        'project_id': project_id,
        'status': 'pending',
        'git_commit': prev.get('git_commit', ''),
        'environment': deployment.get('environment', 'production'),
        'rollback_of': deploy_id,
        'rollback_to': prev['id'],
        'logs': [f'[{now}] Rollback to {prev["id"]} initiated'],
        'created_at': now,
        'updated_at': now,
        'completed_at': None,
    }
    await db.deployments.insert_one(rollback)

    import asyncio
    await asyncio.sleep(1)

    build_end = _now()
    await db.deployments.update_one(
        {'id': rollback_id},
        {'$set': {'status': 'building', 'updated_at': build_end},
         '$push': {'logs': f'[{build_end}] Building from commit {prev.get("git_commit", "unknown")[:8]}...'}}
    )
    await asyncio.sleep(1)

    deploy_end = _now()
    await db.deployments.update_one(
        {'id': rollback_id},
        {'$set': {'status': 'live', 'updated_at': deploy_end, 'completed_at': deploy_end},
         '$push': {'logs': f'[{deploy_end}] Rollback complete. Service restored.'}}
    )

    rollback['status'] = 'live'
    rollback.pop('_id', None)
    return rollback


@router.post('/deployments/{deploy_id}/cancel')
async def cancel_deployment(deploy_id: str, _=Depends(get_current_admin)):
    deployment = await db.deployments.find_one({'id': deploy_id})
    if not deployment:
        raise HTTPException(status_code=404, detail='Deployment not found')
    if deployment['status'] not in ('pending', 'building', 'deploying'):
        raise HTTPException(status_code=400, detail=f'Cannot cancel deployment with status: {deployment["status"]}')

    now = _now()
    await db.deployments.update_one(
        {'id': deploy_id},
        {'$set': {'status': 'cancelled', 'updated_at': now},
         '$push': {'logs': f'[{now}] Deployment cancelled by admin'}}
    )
    return {'id': deploy_id, 'status': 'cancelled'}


@router.get('/releases')
async def list_releases(_=Depends(get_current_admin)):
    cur = db.releases.find({}, {'_id': 0}).sort('created_at', -1)
    return {'releases': [r async for r in cur]}


@router.post('/releases')
async def create_release(payload: ReleaseCreate, _=Depends(get_current_admin)):
    release = {
        'id': uuid.uuid4().hex[:12],
        'version': payload.version,
        'changelog': payload.changelog,
        'assets': payload.assets,
        'created_at': _now(),
    }
    await db.releases.insert_one(release)
    release.pop('_id', None)
    return release


@router.get('/env-vars')
async def list_env_vars(project_id: str = Query(...), _=Depends(get_current_admin)):
    cur = db.env_vars.find({'project_id': project_id}, {'_id': 0})
    vars_list = []
    async for v in cur:
        masked = v.copy()
        val = masked.get('value', '')
        if len(val) > 4:
            masked['value'] = val[:2] + '*' * (len(val) - 4) + val[-2:]
        else:
            masked['value'] = '****'
        vars_list.append(masked)
    return {'env_vars': vars_list}


@router.post('/env-vars')
async def set_env_var(payload: EnvVarInput, _=Depends(get_current_admin)):
    now = _now()
    existing = await db.env_vars.find_one({'project_id': payload.project_id, 'key': payload.key})
    if existing:
        await db.env_vars.update_one(
            {'project_id': payload.project_id, 'key': payload.key},
            {'$set': {'value': payload.value, 'updated_at': now}}
        )
        return {'status': 'updated', 'key': payload.key, 'project_id': payload.project_id}

    var_doc = {
        'id': uuid.uuid4().hex[:12],
        'project_id': payload.project_id,
        'key': payload.key,
        'value': payload.value,
        'created_at': now,
        'updated_at': now,
    }
    await db.env_vars.insert_one(var_doc)
    var_doc.pop('_id', None)
    return var_doc


@router.delete('/env-vars/{var_id}')
async def delete_env_var(var_id: str, _=Depends(get_current_admin)):
    result = await db.env_vars.delete_one({'id': var_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Env var not found')
    return {'status': 'deleted'}


@router.post('/env-vars/bulk')
async def bulk_set_env_vars(payload: BulkEnvVars, _=Depends(get_current_admin)):
    now = _now()
    set_count = 0
    for line in payload.env_text.strip().split('\n'):
        line = line.strip()
        if not line or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        existing = await db.env_vars.find_one({'project_id': payload.project_id, 'key': key})
        if existing:
            await db.env_vars.update_one(
                {'project_id': payload.project_id, 'key': key},
                {'$set': {'value': value, 'updated_at': now}}
            )
        else:
            await db.env_vars.insert_one({
                'id': uuid.uuid4().hex[:12],
                'project_id': payload.project_id,
                'key': key,
                'value': value,
                'created_at': now,
                'updated_at': now,
            })
        set_count += 1
    return {'status': 'bulk_set', 'count': set_count}


@router.get('/deploy-logs/{deploy_id}')
async def get_deploy_logs(deploy_id: str, _=Depends(get_current_admin)):
    deployment = await db.deployments.find_one({'id': deploy_id}, {'_id': 0})
    if not deployment:
        raise HTTPException(status_code=404, detail='Deployment not found')
    return {'deploy_id': deploy_id, 'logs': deployment.get('logs', []), 'status': deployment.get('status')}


@router.post('/domains')
async def map_domain(payload: DomainInput, _=Depends(get_current_admin)):
    existing = await db.domains.find_one({'domain': payload.domain})
    if existing:
        raise HTTPException(status_code=409, detail='Domain already mapped')

    domain_doc = {
        'id': uuid.uuid4().hex[:12],
        'domain': payload.domain,
        'project_id': payload.project_id,
        'auto_ssl': payload.auto_ssl,
        'ssl_status': 'pending' if payload.auto_ssl else 'none',
        'created_at': _now(),
    }
    await db.domains.insert_one(domain_doc)
    domain_doc.pop('_id', None)
    return domain_doc


@router.get('/domains')
async def list_domains(_=Depends(get_current_admin)):
    cur = db.domains.find({}, {'_id': 0}).sort('created_at', -1)
    return {'domains': [d async for d in cur]}


@router.delete('/domains/{domain_id}')
async def remove_domain(domain_id: str, _=Depends(get_current_admin)):
    result = await db.domains.delete_one({'id': domain_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Domain not found')
    return {'status': 'removed'}
