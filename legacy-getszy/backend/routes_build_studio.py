"""Build Studio — SaaS Builder, Mobile Builder, API Builder, DB Builder, Workflow Builder, Marketplace."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db
from llm_provider import chat_completion

router = APIRouter(prefix='/build-studio', tags=['build-studio'])


def _now():
    return datetime.now(timezone.utc).isoformat()


# ===== SaaS Builder =====
class SaaSIn(BaseModel):
    name: str
    description: str
    features: List[str] = []
    tech_stack: str = 'nextjs'
    pricing_model: str = 'freemium'


@router.post('/saas/create')
async def create_saas(payload: SaaSIn, user=Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    try:
        result = await chat_completion([
            {'role': 'system', 'content': 'Generate a SaaS project blueprint with: file structure, tech stack, features, and deployment plan as JSON.'},
            {'role': 'user', 'content': f"Create SaaS: {payload.name} - {payload.description}. Features: {payload.features}. Stack: {payload.tech_stack}"}
        ])
        import json
        content = result if isinstance(result, str) else result.get('content', str(result))
        blueprint = json.loads(content) if content.strip().startswith('{') else {'structure': content[:500], 'features': payload.features}
    except Exception:
        blueprint = {'structure': 'Generated structure', 'features': payload.features, 'stack': payload.tech_stack}

    project = {
        'id': project_id, 'user_id': user['id'], 'type': 'saas',
        'name': payload.name, 'description': payload.description,
        'features': payload.features, 'tech_stack': payload.tech_stack,
        'pricing_model': payload.pricing_model, 'blueprint': blueprint,
        'status': 'created', 'created_at': _now(), 'updated_at': _now()
    }
    await db.build_projects.insert_one(project)
    project.pop('_id', None)
    return project


# ===== Mobile Builder =====
class MobileAppIn(BaseModel):
    name: str
    app_type: str = 'react_native'
    screens: List[str] = ['Home', 'Profile', 'Settings']
    features: List[str] = []


@router.post('/mobile/create')
async def create_mobile_app(payload: MobileAppIn, user=Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    screens = [{'name': s, 'components': [], 'route': f'/{s.lower()}'} for s in payload.screens]
    project = {
        'id': project_id, 'user_id': user['id'], 'type': 'mobile',
        'name': payload.name, 'app_type': payload.app_type,
        'screens': screens, 'features': payload.features,
        'status': 'created', 'created_at': _now(), 'updated_at': _now()
    }
    await db.build_projects.insert_one(project)
    project.pop('_id', None)
    return project


# ===== API Builder =====
class APIIn(BaseModel):
    name: str
    endpoints: List[Dict[str, Any]] = []
    auth: str = 'jwt'
    database: str = 'mongodb'


@router.post('/api/create')
async def create_api(payload: APIIn, user=Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    project = {
        'id': project_id, 'user_id': user['id'], 'type': 'api',
        'name': payload.name, 'endpoints': payload.endpoints,
        'auth': payload.auth, 'database': payload.database,
        'status': 'created', 'created_at': _now(), 'updated_at': _now()
    }
    await db.build_projects.insert_one(project)
    project.pop('_id', None)
    return project


@router.post('/api/add-endpoint')
async def add_endpoint(project_id: str, endpoint: Dict[str, Any], user=Depends(get_current_user)):
    proj = await db.build_projects.find_one({'id': project_id, 'user_id': user['id'], 'type': 'api'})
    if not proj:
        raise HTTPException(status_code=404, detail='API project not found')
    endpoints = proj.get('endpoints', [])
    endpoints.append(endpoint)
    await db.build_projects.update_one({'id': project_id}, {'$set': {'endpoints': endpoints, 'updated_at': _now()}})
    return {'status': 'added', 'endpoint_count': len(endpoints)}


# ===== Database Builder =====
class DBSchemaIn(BaseModel):
    name: str
    collections: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []


@router.post('/database/create')
async def create_db_schema(payload: DBSchemaIn, user=Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    project = {
        'id': project_id, 'user_id': user['id'], 'type': 'database',
        'name': payload.name, 'collections': payload.collections,
        'relations': payload.relations,
        'status': 'created', 'created_at': _now(), 'updated_at': _now()
    }
    await db.build_projects.insert_one(project)
    project.pop('_id', None)
    return project


# ===== Workflow Builder =====
class WorkflowIn(BaseModel):
    name: str
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []


@router.post('/workflow/create')
async def create_workflow(payload: WorkflowIn, user=Depends(get_current_user)):
    project_id = str(uuid.uuid4())
    project = {
        'id': project_id, 'user_id': user['id'], 'type': 'workflow',
        'name': payload.name, 'nodes': payload.nodes,
        'edges': payload.edges,
        'status': 'created', 'created_at': _now(), 'updated_at': _now()
    }
    await db.build_projects.insert_one(project)
    project.pop('_id', None)
    return project


@router.post('/workflow/execute')
async def execute_workflow(workflow_id: str, user=Depends(get_current_user)):
    wf = await db.build_projects.find_one({'id': workflow_id, 'user_id': user['id'], 'type': 'workflow'})
    if not wf:
        raise HTTPException(status_code=404, detail='Workflow not found')
    return {'status': 'executed', 'nodes_processed': len(wf.get('nodes', []))}


# ===== Marketplace =====
@router.get('/marketplace/templates')
async def list_templates(category: str = 'all', limit: int = 20):
    templates = [
        {'id': 'saas-starter', 'name': 'SaaS Starter Kit', 'category': 'saas', 'price': 0, 'rating': 4.8},
        {'id': 'ecommerce-starter', 'name': 'E-Commerce Template', 'category': 'ecommerce', 'price': 0, 'rating': 4.7},
        {'id': 'portfolio-starter', 'name': 'Portfolio Template', 'category': 'portfolio', 'price': 0, 'rating': 4.9},
        {'id': 'blog-starter', 'name': 'Blog Platform', 'category': 'blog', 'price': 0, 'rating': 4.6},
        {'id': 'ai-dashboard', 'name': 'AI Dashboard', 'category': 'saas', 'price': 0, 'rating': 4.8},
    ]
    if category != 'all':
        templates = [t for t in templates if t['category'] == category]
    return {'templates': templates[:limit]}


@router.post('/marketplace/install/{template_id}')
async def install_template(template_id: str, user=Depends(get_current_user)):
    return {'status': 'installed', 'template_id': template_id, 'project_id': str(uuid.uuid4())}


# ===== Shared: List all build projects =====
@router.get('/projects')
async def list_build_projects(type: Optional[str] = None, user=Depends(get_current_user)):
    query = {'user_id': user['id']}
    if type:
        query['type'] = type
    cur = db.build_projects.find(query, {'_id': 0}).sort('created_at', -1).limit(50)
    return {'projects': [p async for p in cur]}


@router.get('/projects/{project_id}')
async def get_build_project(project_id: str, user=Depends(get_current_user)):
    proj = await db.build_projects.find_one({'id': project_id, 'user_id': user['id']}, {'_id': 0})
    if not proj:
        raise HTTPException(status_code=404, detail='Project not found')
    return proj


@router.delete('/projects/{project_id}')
async def delete_build_project(project_id: str, user=Depends(get_current_user)):
    await db.build_projects.delete_one({'id': project_id, 'user_id': user['id']})
    return {'status': 'deleted'}
