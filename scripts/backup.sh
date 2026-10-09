#!/usr/bin/env bash
set -euo pipefail
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p backups
source .env

docker compose -f docker-compose.production.yml exec -T db pg_dump -U el_kalel -d el_kalel | gzip > "backups/el_kalel_${STAMP}.sql.gz"
# Keep the most recent 14 local database backups.
ls -1t backups/el_kalel_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
