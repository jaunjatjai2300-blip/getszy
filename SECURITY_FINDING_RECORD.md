# Security Finding — SEC-01 (Corrected)

## Original claim
"Live GitHub PAT (ghp_…) committed to Git history across all branches."

## Corrected finding (2026-08-23)
No live GitHub or Hugging Face token was evidenced in reachable Git history.
Credential exposure may exist only in local shell history / logs and should be
remediated there.

## Evidence (full mirror clone + backup bundle)
- `git filter-repo` with GitHub-PAT regexes (ghp_/gho_/ghu_/ghs_/ghr_/github_pat_)
  produced **0 `***REMOVED***` replacements** across all branches/tags.
- `ghp_` appears in only 2 commits, always as `ghp_` + 0 trailing alnum chars
  → documentation / runbook placeholder text, not a token.
- `HF_TOKEN` references are the env-var NAME; actual `hf_` values are only 5-char
  fragments → not real tokens.
- `sk-` / `eyJ` long matches occur only in `pnpm-lock.yaml` (base64 integrity/URL
  substrings) and `admin_audit_report.json` (encoded audit blob) → not credentials.

## Decision (per release review)
- Do NOT force-push a history rewrite (no evidence of a committed secret; would
  cause operational damage without security benefit).
- Remote repository: left unchanged.
- Backup bundle + mirror: retained until all release work is complete.
- Placeholder text / short fragments: harmless, no purge.
- HF token in shell commands/history: rotate + remove local history/log exposure.
- GitHub token: rotate only if actually exposed outside Git or placeholder unproven.

## Remediation (owner action)
1. Rotate HF_TOKEN at Hugging Face.
2. Clear shell history on affected machines:
   - PowerShell: clear `%USERPROFILE%\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` (and any profile history).
   - Bash: `history -c` and overwrite/remove `~/.bash_history`.
3. Rotate the GitHub token only if proven exposed outside Git.

## Release-record artifacts
- Backup bundle: `../getszy-sec/getszy-backup.bundle`
- Mirror clone (rewritten, UNPUSHED, safe to delete): `../getszy-sec/getszy-mirror`
- Search evidence retained in this file.

## Status
SEC-01 no longer blocks Git operations for the dashboard sprint, provided this
evidence is retained. Next step: P0-B paid-operations integration.
