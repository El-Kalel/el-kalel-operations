#!/usr/bin/env bash
set -euo pipefail
FILE=${1:?Usage: ./scripts/restore.sh backups/file.sql.gz}
gunzip -c "$FILE" | docker compose -f docker-compose.production.yml exec -T db psql -U el_kalel -d el_kalel
