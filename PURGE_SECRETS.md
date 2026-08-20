# PURGE_SECRETS.md — Remove the committed GitHub token from git history

**Read this whole file before running anything.**

The repo currently contains a live GitHub Personal Access Token
(`ghp_[REDACTED]…`) committed under `attached_assets-security-backup/` and is
tracked by git (not gitignored). This allows force-push to the repo.

> ⚠️ History rewriting is **destructive and collaborative-breaking**. After a
> force-push, every collaborator must re-clone or `git pull --force`. Only do
> this after you have **rotated the token in GitHub**.

## Step 0 — Rotate the token FIRST (most important)
1. Go to GitHub → Settings → Developer settings → Personal access tokens.
2. **Revoke** the leaked token (`ghp_[REDACTED]…`).
3. Generate a new token only if needed; do not commit it anywhere.
4. Any deploy keys / CI secrets derived from the old token must be updated.

Until the token is revoked, purging history is pointless — it stays valid.

## Step 1 — Stop the leak on disk
Add the folder(s) to `.gitignore` so they can never be re-added:

```bash
# repo root
echo "attached_assets/" >> .gitignore
echo "attached_assets-security-backup/" >> .gitignore
```

Also delete the copies on your local machine that are NOT this clone
(`getszy-repo`, `getszy-check`, the `.zip`) so you don't accidentally
re-push the secret from the wrong directory.

## Step 2 — Clean git history
Use `git filter-repo` (recommended) or BFG. `filter-repo` is the modern tool.

### Option A — git-filter-repo (preferred)
```bash
# install if missing
pip install git-filter-repo

# from the repo root, strip the offending paths from ALL history
git filter-repo --path attached_assets-security-backup --invert-paths
# if there is also a tracked attached_assets/ folder:
git filter-repo --path attached_assets --invert-paths

# verify the token is gone from history
git log --all -p -S 'ghp_[REDACTED]' | wc -l   # should print 0
```

### Option B — BFG Repo-Cleaner
```bash
# 1. Delete the files locally first, commit, then:
java -jar bfg.jar --delete-folders attached_assets-security-backup --delete-folders attached_assets repo.git
git reflog expire --expire=now --all && git gc --prune=now
```

## Step 3 — Force-push the cleaned history
```bash
# ONLY after Step 0 (rotate) is done
git push origin --force --all
git push origin --force --tags
```

⚠️ Force-pushing rewrites `main` for everyone. Notify collaborators to
re-clone. If the repo is protected (branch protection / required reviews),
you may need to temporarily relax protection to push.

## Step 4 — Verify
```bash
# fresh clone in a temp dir and confirm no token remains
git clone https://github.com/jaunjatjai2300-blip/getszy.git /tmp/getszy-verify
cd /tmp/getszy-verify
grep -rIl 'ghp_[REDACTED]' . && echo "STILL PRESENT" || echo "CLEAN"
```

## Step 5 — Damage check
Even after purging, assume the old token was exposed. Confirm:
- No other CI/deploy secret was derived from it.
- No third party pulled the repo while it was public.
- Rotate any DB/API credentials that may have been pasted in the same folder
  (check `Pasted-…txt` files for Razorpay keys, Mongo URLs, SSH commands).

---

*If you are unsure about force-pushing, do Step 0 + Step 1 now, then ask for a
review before Step 2–3.*
