"""Git integration — actual git operations for projects."""
import os
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger('getszy.git')

REPOS_DIR = Path(__file__).parent / 'repos'
REPOS_DIR.mkdir(parents=True, exist_ok=True)


async def git_command(*args, cwd: str = None) -> dict:
    """Run a git command and return output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            'git', *args,
            cwd=cwd or str(REPOS_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            'success': proc.returncode == 0,
            'stdout': stdout.decode(errors='replace').strip(),
            'stderr': stderr.decode(errors='replace').strip(),
            'returncode': proc.returncode,
        }
    except FileNotFoundError:
        return {'success': False, 'stdout': '', 'stderr': 'git not installed', 'returncode': -1}
    except Exception as e:
        return {'success': False, 'stdout': '', 'stderr': str(e), 'returncode': -1}


async def init_repo(project_id: str) -> dict:
    """Initialize a new git repo for a project."""
    repo_path = str(REPOS_DIR / project_id)
    os.makedirs(repo_path, exist_ok=True)
    result = await git_command('init', cwd=repo_path)
    if result['success']:
        logger.info(f'Git repo initialized: {project_id}')
    return result


async def commit_changes(project_id: str, message: str, files: list = None) -> dict:
    """Stage and commit changes."""
    repo_path = str(REPOS_DIR / project_id)
    if files:
        for f in files:
            await git_command('add', f, cwd=repo_path)
    else:
        await git_command('add', '-A', cwd=repo_path)
    return await git_command('commit', '-m', message, cwd=repo_path)


async def get_log(project_id: str, limit: int = 20) -> list:
    """Get commit log."""
    repo_path = str(REPOS_DIR / project_id)
    result = await git_command(
        'log', f'--max-count={limit}', '--pretty=format:%H|%an|%ae|%ai|%s',
        cwd=repo_path,
    )
    if not result['success']:
        return []
    commits = []
    for line in result['stdout'].split('\n'):
        if '|' in line:
            parts = line.split('|', 4)
            if len(parts) == 5:
                commits.append({
                    'hash': parts[0],
                    'author': parts[1],
                    'email': parts[2],
                    'date': parts[3],
                    'message': parts[4],
                })
    return commits


async def get_diff(project_id: str, commit_hash: str = None) -> str:
    """Get diff of uncommitted changes or specific commit."""
    repo_path = str(REPOS_DIR / project_id)
    if commit_hash:
        result = await git_command('diff', f'{commit_hash}~1', commit_hash, cwd=repo_path)
    else:
        result = await git_command('diff', cwd=repo_path)
    return result.get('stdout', '')


async def create_branch(project_id: str, branch_name: str) -> dict:
    """Create and switch to a new branch."""
    repo_path = str(REPOS_DIR / project_id)
    return await git_command('checkout', '-b', branch_name, cwd=repo_path)


async def list_branches(project_id: str) -> list:
    """List all branches."""
    repo_path = str(REPOS_DIR / project_id)
    result = await git_command('branch', '--list', cwd=repo_path)
    if not result['success']:
        return []
    return [
        b.strip().replace('* ', '')
        for b in result['stdout'].split('\n')
        if b.strip()
    ]


async def rollback(project_id: str, commit_hash: str) -> dict:
    """Rollback to a specific commit."""
    repo_path = str(REPOS_DIR / project_id)
    return await git_command('reset', '--hard', commit_hash, cwd=repo_path)


async def get_status(project_id: str) -> dict:
    """Get git status."""
    repo_path = str(REPOS_DIR / project_id)
    result = await git_command('status', '--porcelain', cwd=repo_path)
    files = []
    if result['success'] and result['stdout']:
        for line in result['stdout'].split('\n'):
            if line.strip():
                status = line[:2].strip()
                filename = line[3:].strip()
                files.append({'status': status, 'file': filename})
    return {'clean': len(files) == 0, 'files': files}


async def clone_repo(url: str, project_id: str) -> dict:
    """Clone a remote repo."""
    repo_path = str(REPOS_DIR / project_id)
    return await git_command('clone', url, repo_path)
