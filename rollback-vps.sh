#!/usr/bin/env bash
#
# Getszy VPS rollback.
#
# deploy-vps.sh has no rollback path: it does `git pull origin main` then a
# --no-cache rebuild, so there is no way to get back to a known-good commit
# without doing it by hand — and doing it by hand is booby-trapped, because
# /opt/getszy carries local commits (the preview-subdomain Caddyfile change).
# A naive `git reset --hard <upstream-sha>` discards those and can take Caddy's
# TLS down, turning a cosmetic rollback into an outage.
#
# Usage:
#   ./rollback-vps.sh --capture           save the current commit as a rollback point
#   ./rollback-vps.sh <commit-sha>        roll back to that commit and rebuild
#   ./rollback-vps.sh --to-saved          roll back to the captured point
#
# This script never guesses a target. It refuses to run without an explicit one.
#
set -euo pipefail

REPO_DIR="/opt/getszy"
LEGACY_DIR="$REPO_DIR/legacy-getszy"
POINT_FILE="$HOME/getszy-rollback-point.txt"

die() { echo "ERROR: $*" >&2; exit 1; }

[ -d "$REPO_DIR/.git" ] || die "$REPO_DIR is not a git repository."

# ── capture ──────────────────────────────────────────────────────────────────
if [ "${1:-}" = "--capture" ]; then
  cd "$REPO_DIR"
  sha="$(git rev-parse HEAD)"
  printf '%s\n' "$sha" > "$POINT_FILE"
  echo "Rollback point saved to $POINT_FILE"
  echo "  $sha  $(git log -1 --format=%s "$sha")"
  echo
  echo "Local commits that a rollback must preserve (not on origin/main):"
  git log --oneline origin/main..HEAD 2>/dev/null | sed 's/^/  /' || true
  exit 0
fi

# ── resolve target ───────────────────────────────────────────────────────────
if [ "${1:-}" = "--to-saved" ]; then
  [ -f "$POINT_FILE" ] || die "No saved rollback point at $POINT_FILE. Run --capture before deploying."
  TARGET="$(tr -d '[:space:]' < "$POINT_FILE")"
elif [ -n "${1:-}" ]; then
  TARGET="$1"
else
  cat >&2 <<'USAGE'
Refusing to run without an explicit target.

  ./rollback-vps.sh --capture      before deploying, save the current commit
  ./rollback-vps.sh --to-saved     roll back to that saved commit
  ./rollback-vps.sh <commit-sha>   roll back to a specific commit
USAGE
  exit 2
fi

cd "$REPO_DIR"
git rev-parse --verify --quiet "${TARGET}^{commit}" >/dev/null \
  || die "'$TARGET' is not a commit in $REPO_DIR."

CURRENT="$(git rev-parse HEAD)"
TARGET_FULL="$(git rev-parse "${TARGET}^{commit}")"

if [ "$CURRENT" = "$TARGET_FULL" ]; then
  echo "Already at $TARGET_FULL — nothing to roll back."
  exit 0
fi

# ── show the blast radius before touching anything ───────────────────────────
echo "=== ROLLBACK PLAN ==="
echo "  from : $CURRENT  $(git log -1 --format=%s "$CURRENT")"
echo "  to   : $TARGET_FULL  $(git log -1 --format=%s "$TARGET_FULL")"
echo
echo "  commits that will be REMOVED from the working tree:"
git log --oneline "$TARGET_FULL..$CURRENT" | sed 's/^/    /' || true
echo
echo "  files that will change:"
git diff --stat "$CURRENT" "$TARGET_FULL" | tail -20 | sed 's/^/    /'
echo
if [ -n "$(git status --porcelain)" ]; then
  echo "  WARNING: uncommitted local changes present. reset --hard will DISCARD them:"
  git status --short | sed 's/^/    /'
  echo
fi
echo "  This stops the site, rebuilds all images without cache, and restarts."
echo "  Expect roughly a minute of downtime."
echo

read -r -p "Type 'rollback' to proceed: " confirm
[ "$confirm" = "rollback" ] || die "Aborted — nothing changed."

# ── execute ──────────────────────────────────────────────────────────────────
echo "=== Stopping services ==="
cd "$LEGACY_DIR" && docker compose down

echo "=== Resetting $REPO_DIR to $TARGET_FULL ==="
cd "$REPO_DIR" && git reset --hard "$TARGET_FULL"

echo "=== Rebuilding ==="
cd "$LEGACY_DIR" && docker compose build --no-cache && docker compose up -d

echo "=== Waiting for backend health ==="
for i in $(seq 1 30); do
  if curl -sf http://localhost:8001/api/health >/dev/null 2>&1; then
    echo "Backend healthy."
    break
  fi
  [ "$i" -eq 30 ] && die "Backend did not become healthy after rollback. Check: cd $LEGACY_DIR && docker compose logs --tail=80"
  sleep 2
done

echo
echo "=== Rollback complete ==="
cd "$REPO_DIR"
echo "  now at: $(git rev-parse --short HEAD)  $(git log -1 --format=%s)"
echo "  verify: curl -s https://getszy.com | grep -oE 'main\.[a-f0-9]+\.js'"
