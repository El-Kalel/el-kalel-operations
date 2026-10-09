# EL-KALEL Enterprise Waste Management Operations System — v7

Production-oriented operations platform for EL-KALEL ENTERPRISE.

## Core modules
- Dashboard and daily operations KPIs
- Customer registration, balances and statements
- Door-to-door collection recording
- GPS capture and offline mobile collection sync
- Collection proof-photo storage
- Staff, teams and area assignments
- Truck/fleet, fuel, odometer and service tracking
- Transport trips and landfill delivery/weight reconciliation
- Payments, references and customer balances
- SMS queue, templates, reminders and dispatch
- Email/SMTP delivery, logs, templates and payment/collection reminders
- **WhatsApp Business platform** with customer self-service and inbound/outbound messaging
- Audit trail and operational reporting
- Responsive PWA for mobile/tablet/desktop
- Capacitor mobile shell for Android/iOS packaging
- PostgreSQL + Docker production stack
- HTTPS reverse proxy with Caddy
- Database backup/restore scripts

## WhatsApp platform
Customers can message the EL-KALEL WhatsApp Business number. The webhook stores inbound messages and can automatically answer:

- `MENU` — customer menu
- `1` / `BALANCE` — outstanding balance
- `2` / `COLLECTION` — latest collection status
- `3` / `PAYMENT` — payment information
- `4` / `SUPPORT` — support request

The admin interface includes WhatsApp message history, direct text messaging and approved-template messaging.

### Meta credentials required
- WhatsApp Cloud API access token
- WhatsApp phone number ID
- WhatsApp Business account ID
- Meta app secret
- Webhook verification token

Do not commit these secrets to Git or send them in chat. Put them in the production `.env` file.

## No domain required initially
The deployment guide supports a public VPS IP through an `sslip.io` hostname. This provides a stable HTTPS address without buying a domain. A purchased domain can be pointed to the same server later.

Example:
`203-0-113-10.sslip.io`

## Production deployment
Read `deploy/README.md`.

Quick start after obtaining a VPS:

```bash
cp .env.example .env
./scripts/generate-secrets.sh
# put generated values into .env

docker compose -f docker-compose.production.yml up -d --build
```

Then open the HTTPS host in a browser.

## Development
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

Default development username: `admin`.
The password comes from `ADMIN_PASSWORD`.

## Important production rule
This repository is an application package. A live WhatsApp number, SMS gateway, SMTP/email account, VPS, Meta Business account and payment/communications provider accounts cannot be created without the company's external account authorization and credentials.


## EL-KALEL branding
The supplied EL-KALEL ENTERPRISE logo is included under `frontend/branding/` and is used throughout the sign-in screen, navigation and PWA icons.

## Cost-conscious deployment
The application package does not require a paid domain. Live email, SMS and WhatsApp delivery require the relevant provider accounts/credentials. The core operations system can run while those communication channels remain unconfigured.
