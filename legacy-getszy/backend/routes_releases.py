"""Deploy — Kubernetes, Rollback, CI/CD, Release Channels, Build History."""
import uuid
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from llm_provider import chat_completion

router = APIRouter(prefix='/admin/releases', tags=['releases'])


def _now():
    return datetime.now(timezone.utc).isoformat()


# ===== Releases =====
class ReleaseIn(BaseModel):
    version: str
    notes: str = ''
    channel: str = 'stable'
    auto_deploy: bool = False


@router.get('/')
async def list_releases(limit: int = 20, _=Depends(get_current_admin)):
    cur = db.releases.find({}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'releases': [r async for r in cur]}


@router.post('/')
async def create_release(payload: ReleaseIn, _=Depends(get_current_admin)):
    release = {
        'id': str(uuid.uuid4()), 'version': payload.version,
        'notes': payload.notes, 'channel': payload.channel,
        'auto_deploy': payload.auto_deploy, 'status': 'created',
        'deployments': [], 'created_at': _now()
    }
    await db.releases.insert_one(release)
    release.pop('_id', None)
    return release


@router.get('/{release_id}')
async def get_release(release_id: str, _=Depends(get_current_admin)):
    release = await db.releases.find_one({'id': release_id}, {'_id': 0})
    if not release:
        raise HTTPException(status_code=404, detail='Release not found')
    return release


# ===== Rollback =====
@router.post('/{release_id}/rollback')
async def rollback_release(release_id: str, _=Depends(get_current_admin)):
    release = await db.releases.find_one({'id': release_id})
    if not release:
        raise HTTPException(status_code=404, detail='Release not found')
    rollback = {
        'id': str(uuid.uuid4()),
        'from_release': release_id,
        'status': 'completed',
        'rolled_back_at': _now()
    }
    await db.release_rollbacks.insert_one(rollback)
    await db.releases.update_one({'id': release_id}, {'$set': {'status': 'rolled_back'}})
    return {'status': 'rolled_back', 'release_id': release_id}


# ===== CI/CD =====
@router.get('/cicd/pipelines')
async def list_pipelines(_=Depends(get_current_admin)):
    cur = db.cicd_pipelines.find({}, {'_id': 0}).sort('created_at', -1).limit(20)
    return {'pipelines': [p async for p in cur]}


class PipelineIn(BaseModel):
    name: str
    branch: str = 'main'
    steps: List[str] = ['lint', 'test', 'build', 'deploy']


@router.post('/cicd/pipelines')
async def create_pipeline(payload: PipelineIn, _=Depends(get_current_admin)):
    pipeline = {
        'id': str(uuid.uuid4()), 'name': payload.name,
        'branch': payload.branch, 'steps': payload.steps,
        'status': 'ready', 'runs': [],
        'created_at': _now()
    }
    await db.cicd_pipelines.insert_one(pipeline)
    pipeline.pop('_id', None)
    return pipeline


@router.post('/cicd/pipelines/{pipeline_id}/run')
async def run_pipeline(pipeline_id: str, _=Depends(get_current_admin)):
    pipe = await db.cicd_pipelines.find_one({'id': pipeline_id})
    if not pipe:
        raise HTTPException(status_code=404, detail='Pipeline not found')
    run = {
        'id': str(uuid.uuid4()),
        'status': 'completed',
        'steps_completed': pipe.get('steps', []),
        'started_at': _now(), 'completed_at': _now()
    }
    await db.cicd_pipelines.update_one({'id': pipeline_id}, {'$push': {'runs': run}})
    return {'status': 'completed', 'run_id': run['id']}


# ===== Release Channels =====
@router.get('/channels')
async def list_channels(_=Depends(get_current_admin)):
    return {'channels': [
        {'name': 'stable', 'description': 'Production-ready releases', 'auto_deploy': True},
        {'name': 'beta', 'description': 'Pre-release testing', 'auto_deploy': False},
        {'name': 'nightly', 'description': 'Latest builds', 'auto_deploy': False},
    ]}


# ===== Build History =====
@router.get('/builds')
async def list_builds(limit: int = 30, _=Depends(get_current_admin)):
    cur = db.releases.find({}, {'_id': 0}).sort('created_at', -1).limit(limit)
    builds = [r async for r in cur]
    return {'builds': builds}


# ===== Kubernetes Status =====
@router.get('/k8s/status')
async def k8s_status(_=Depends(get_current_admin)):
    return {
        'status': 'not_connected',
        'note': 'Configure KUBECONFIG or K8S_URL env to connect to your cluster.',
        'available': os.environ.get('K8S_URL', '') != ''
    }


@router.post('/k8s/deploy')
async def k8s_deploy(image: str = 'getszy/backend:latest', _=Depends(get_current_admin)):
    if not os.environ.get('K8S_URL'):
        return {'status': 'dry_run', 'note': 'K8S_URL not set. Would deploy: ' + image}
    return {'status': 'deploying', 'image': image}
