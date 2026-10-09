#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import secrets
print('JWT_SECRET='+secrets.token_urlsafe(48))
print('POSTGRES_PASSWORD='+secrets.token_urlsafe(32))
print('WHATSAPP_VERIFY_TOKEN='+secrets.token_urlsafe(32))
print('ADMIN_PASSWORD='+secrets.token_urlsafe(20))
PY
