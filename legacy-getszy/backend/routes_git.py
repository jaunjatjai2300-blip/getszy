"""Git operations routes."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth import get_current_admin
import git_ops

router = APIRouter(prefix='/admin/git', tags=['git'])


class CommitIn(BaseModel):
    message: str


class BranchIn(BaseModel):
    name: str


class CloneIn(BaseModel):
    url: str


@router.get('/status')
async def status(_=Depends(get_current_admin)):
    return git_ops.git_status()


@router.get('/log')
async def log(limit: int = 10, _=Depends(get_current_admin)):
    result = git_ops.git_log(limit)
    return {'log': result.get('stdout', ''), 'stderr': result.get('stderr', '')}


@router.post('/commit')
async def commit(payload: CommitIn, _=Depends(get_current_admin)):
    return git_ops.git_commit(payload.message)


@router.get('/branches')
async def branches(_=Depends(get_current_admin)):
    return git_ops.git_branch_list()


@router.post('/branch')
async def create_branch(payload: BranchIn, _=Depends(get_current_admin)):
    return git_ops.git_branch_create(payload.name)


@router.post('/checkout')
async def checkout(payload: BranchIn, _=Depends(get_current_admin)):
    return git_ops.git_checkout(payload.name)


@router.post('/rollback')
async def rollback(commit_hash: str, _=Depends(get_current_admin)):
    return git_ops.git_rollback(commit_hash)


@router.post('/pull')
async def pull(_=Depends(get_current_admin)):
    return git_ops.git_pull()


@router.post('/push')
async def push(_=Depends(get_current_admin)):
    return git_ops.git_push()


@router.post('/clone')
async def clone(payload: CloneIn, _=Depends(get_current_admin)):
    return git_ops.git_clone(payload.url)
