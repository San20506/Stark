#!/usr/bin/env bash
# STARK daily push — pushes the current branch iff it has unpushed commits.
# Run by stark-daily-push.timer (systemd user timer, once daily ~09:00).
# Never commits or stages anything: only committed work is pushed.
set -u

REPO="/home/sandy/Projects/stark"
LOG="$REPO/logs/daily-push.log"

cd "$REPO" || exit 1

branch="$(git branch --show-current 2>/dev/null)"
if [ -z "$branch" ]; then
    echo "$(date -Is) SKIP: detached HEAD" >> "$LOG"
    exit 0
fi

{
    echo "=== $(date -Is) branch=$branch ==="
    if git rev-parse --abbrev-ref "@{u}" >/dev/null 2>&1; then
        ahead="$(git rev-list --count "@{u}..HEAD")"
        if [ "$ahead" -gt 0 ]; then
            git push origin "$branch" 2>&1 && echo "PUSHED $ahead commit(s)"
        else
            echo "SKIP: nothing to push"
        fi
    else
        git push -u origin "$branch" 2>&1 && echo "PUSHED (new upstream)"
    fi
} >> "$LOG" 2>&1
