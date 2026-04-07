#!/bin/bash
# clockify-fetch.sh — fetch Clockify time entries for a date range
# Usage: clockify-fetch.sh START_DATE [END_DATE]
#   START_DATE: YYYY-MM-DD (required)
#   END_DATE:   YYYY-MM-DD (optional, defaults to START_DATE + 1 day)
# Reads CLOCKIFY_API_KEY from .env in repo root

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

source "$REPO_ROOT/.env"

START="$1"
if [ -n "${2:-}" ]; then
  END="$2"
else
  END=$(date -j -v+1d -f "%Y-%m-%d" "$START" "+%Y-%m-%d" 2>/dev/null \
    || date -d "$START + 1 day" "+%Y-%m-%d")
fi

WORKSPACE="658198f8a2695d07b8c9c523"
USER_ID="658198f8a2695d07b8c9c51f"
PROJECT="67b2acf080926120156524ca"

curl -s -H "X-Api-Key: $CLOCKIFY_API_KEY" \
  "https://api.clockify.me/api/v1/workspaces/$WORKSPACE/user/$USER_ID/time-entries?start=${START}T00:00:00Z&end=${END}T00:00:00Z&project=$PROJECT" \
| python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=7))
entries = json.load(sys.stdin)
if not entries:
    print('No entries found.')
    sys.exit(0)

total_min = 0
for e in entries:
    desc = e.get('description', '')
    start = e['timeInterval']['start']
    end = e['timeInterval'].get('end', 'running')
    if end and end != 'running':
        s = datetime.fromisoformat(start.replace('Z', '+00:00'))
        en = datetime.fromisoformat(end.replace('Z', '+00:00'))
        dur = en - s
        mins = int(dur.total_seconds()) // 60
        total_min += mins
        h, m = divmod(mins, 60)
        dur_str = f'{h}h {m:02d}m'
    else:
        dur_str = 'running'
    s_local = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(TZ)
    print(f'{s_local.strftime(\"%a %d.%m %H:%M\")} | {dur_str:>7} | {desc}')

th, tm = divmod(total_min, 60)
print(f'---')
print(f'Total: {th}h {tm:02d}m')
"
