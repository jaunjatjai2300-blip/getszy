"""Git operations routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from auth import get_current_admin
from git_ops import (
    init_repo, commit_changes, get_log, get_diff,
    create_branch, list_branches, rollback, get_status, clone_repo
)
from audit_log import log_action

router = APIRouter(prefix='/admin/git', tags=['git'])


class CommitIn(BaseModel):
    project_id: str
    message: str = Field(..., min_length=1, max_length=500)
    files: Optional[List[str]] = None


class BranchIn(BaseModel):
    project_id: str
    branch_name: str = Field(..., min_length=1, max_length=100)


class RollbackIn(BaseModel):
    project_id: str
    commit_hash: str = Field(..., min_length=1, max_length=40)


class CloneIn(BaseModel):
    url: str = Field(..., min_length=1)
    project_id: str


@router.post('/init', dependencies=[Depends(get_current_admin)])
async def init(project_id: str):
    result = await init_repo(project_id)
    if not result['success']:
        raise HTTPException(400, result['stderr'])
    return result


@router.post('/commit', dependencies=[Depends(get_current_admin)])
async def commit(body: CommitIn):
    result = await commit_changes(body.project_id, body.message, body.files)
    if not result['success']:
        raise HTTPException(400, result['stderr'])
    await log_action('git.commit', details={'project': body.project_id, 'message': body.message})
    return result


@router.get('/log/{project_id}', dependencies=[Depends(get_current_admin)])
async def log(project_id: str, limit: int = 20):
    return await get_log(project_id, limit)


@router.get('/diff/{project_id}', dependencies=[Depends(get_current_admin)])
async def diff(project_id: str, commit_hash: Optional[str] = None):
    return {'diff': await get_diff(project_id, commit_hash)}


@router.post('/branch', dependencies=[Depends(get_current_admin)])
async def branch(body: BranchIn):
    result = await create_branch(body.project_id, body.branch_name)
    if not result['success']:
        raise HTTPException(400, result['stderr'])
    return result


@router.get('/branches/{project_id}', dependencies=[Depends(get_current_admin)])
async def branches(project_id: str):
    return await list_branches(project_id)


@router.post('/rollback', dependencies=[Depends(get_current_admin)])
async def rollback_to(body: RollbackIn):
    result = await rollback(body.project_id, body.commit_hash)
    if not result['success']:
        raise HTTPException(400, result['stderr'])
    await log_action('git.rollback', details={'project': body.project_id, 'commit': body.commit_hash})
    return result


@router.get('/status/{project_id}', dependencies=[Depends(get_current_admin)])
async def status(project_id: str):
    return await get_status(project_id)


@router.post('/clone', dependencies=[Depends(get_current_admin)])
async def clone(body: CloneIn):
    result = await clone_repo(body.url, body.project_id)
    if not result['success']:
        raise HTTPException(400, result['stderr'])
    return result
