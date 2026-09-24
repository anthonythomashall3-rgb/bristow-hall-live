#!/bin/bash
# THE BRISTOW HALL SYSTEM — publish site/public to Cloudflare Pages (project bristow-hall-system) with Wrangler.
# Authentication, in this order: CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID from
# onset-detector-new-2026-08-23/live_data/config/local.env if present (never printed, Rule 12.6); otherwise the
# Wrangler login already stored on this Mac (wrangler login, OAuth). Run from anywhere: bash deploy.sh
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
# Where the collection is. Resolved from this script's own location, so the system keeps working if the
# ~/mnt symlink that used to be hardcoded here is ever moved or removed. The old path is the fallback.
_SELF="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
COL="$(cd "$_SELF/.." && pwd)"
[ -d "$COL/workspace" ] || COL="$HOME/mnt/Onset Detector Data/105_bristow_hall_system_2026-09-08"
ENV="$HOME/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env"
PROJECT="bhrrealtime"
if [ -f "$ENV" ]; then
  T="$(grep -m1 '^CLOUDFLARE_API_TOKEN=' "$ENV" | cut -d= -f2- | tr -d '"' | tr -d "'")"; A="$(grep -m1 '^CLOUDFLARE_ACCOUNT_ID=' "$ENV" | cut -d= -f2- | tr -d '"' | tr -d "'")"
  if [ -n "$T" ] && [ -n "$A" ]; then export CLOUDFLARE_API_TOKEN="$T"; export CLOUDFLARE_ACCOUNT_ID="$A"; fi
fi
# (17 September 2026, collection 201) every way of not deploying now exits non-zero: until today a missing or logged-out
# Wrangler printed one line and exited 0, so the runner recorded a clean run while the site stood still
if ! command -v wrangler >/dev/null 2>&1; then echo "cloudflare: wrangler not installed (npm install -g wrangler); NOT DEPLOYED"; exit 3; fi
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && ! CI=1 wrangler whoami 2>/dev/null | grep -q "logged in"; then echo "cloudflare: no token in local.env and wrangler is not logged in; site built but NOT DEPLOYED"; exit 4; fi
cd "$COL/site" || exit 5
OUT="$(CI=1 wrangler pages deploy public --project-name "$PROJECT" --commit-dirty=true 2>&1)"; RC=$?
echo "$OUT" | grep -E "Deployment complete|https://|ERROR|error" | head -3
if [ $RC -eq 0 ]; then echo "cloudflare: deployed $(date -u +%Y-%m-%dT%H:%MZ)"; else echo "cloudflare: deploy failed (exit $RC)"; fi
exit $RC
