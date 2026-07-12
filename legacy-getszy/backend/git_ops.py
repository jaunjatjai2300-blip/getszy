"""Git operations — init, commit, branch, rollback, clone."""
import os
import subprocess
import logging

logger = logging.getLogger('getszy.git')
REPO_DIR = os.environ.get('GIT_REPO_DIR', '/opt/getszy/legacy-getszy')


def _run(cmd: list, cwd: str = None) -> dict:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=cwd or REPO_DIR)
        return {'stdout': result.stdout.strip(), 'stderr': result.stderr.strip(), 'returncode': result.returncode}
    except Exception as e:
        return {'stdout': '', 'stderr': str(e), 'returncode': 1}


def git_init(path: str = None):
    return _run(['git', 'init'], cwd=path or REPO_DIR)


def git_status():
    return _run(['git', 'status', '--porcelain'])


def git_log(limit: int = 10):
    return _run(['git', 'log', f'-{limit}', '--oneline', '--pretty=format:%h %s (%cr)'])


def git_commit(message: str):
    _run(['git', 'add', '.'])
    return _run(['git', 'commit', '-m', message])


def git_branch_list():
    return _run(['git', 'branch', '-a'])


def git_branch_create(name: str):
    return _run(['git', 'checkout', '-b', name])


def git_checkout(branch: str):
    return _run(['git', 'checkout', branch])


def git_rollback(commit_hash: str):
    return _run(['git', 'reset', '--hard', commit_hash])


def git_pull(remote: str = 'origin', branch: str = 'main'):
    return _run(['git', 'pull', remote, branch])


def git_push(remote: str = 'origin', branch: str = 'main'):
    return _run(['git', 'push', remote, branch])


def git_clone(url: str, dest: str = None):
    target = dest or os.path.join(os.path.dirname(REPO_DIR), os.path.basename(url).replace('.git', ''))
    return _run(['git', 'clone', url, target], cwd=os.path.dirname(REPO_DIR))
