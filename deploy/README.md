# EL-KALEL Production Deployment

## No purchased domain required
Use a public VPS IP with an `sslip.io` hostname. For example, if the server IP is `203.0.113.10`, set:

`PUBLIC_HOST=203-0-113-10.sslip.io`

Caddy will obtain HTTPS automatically. A purchased domain can be added later without changing the application.

## Server requirements
- Ubuntu 24.04 LTS
- 2 vCPU minimum, 4 GB RAM recommended
- 40 GB SSD minimum
- Public IPv4
- Docker + Compose plugin

## Install Docker
Use the official Docker installation instructions for the server OS, then verify:

`docker --version`

`docker compose version`

## Deploy
1. Copy this project to the server.
2. Copy `.env.example` to `.env`.
3. Set strong `POSTGRES_PASSWORD`, `JWT_SECRET`, and `ADMIN_PASSWORD`.
4. Set `PUBLIC_HOST` to `<server-ip-with-dashes>.sslip.io`.
5. Add Meta WhatsApp credentials.
6. Run:

`docker compose -f docker-compose.production.yml up -d --build`

7. Open `https://<PUBLIC_HOST>`.
8. Log in with the configured admin password and immediately create named staff accounts and change the seed credentials.

## WhatsApp webhook
Set Meta webhook callback URL to:

`https://<PUBLIC_HOST>/api/whatsapp`

Use the same value as `WHATSAPP_VERIFY_TOKEN` in `.env` for Meta's verification token.

Subscribe to the WhatsApp `messages` webhook field.

## WhatsApp Cloud API
Required environment variables:
- WHATSAPP_ACCESS_TOKEN
- WHATSAPP_PHONE_NUMBER_ID
- WHATSAPP_BUSINESS_ACCOUNT_ID
- WHATSAPP_APP_SECRET
- WHATSAPP_VERIFY_TOKEN

For outbound messages outside the customer-service window, use approved WhatsApp message templates. Free-form text is intended for the active customer-service window.

## Backups
Run `scripts/backup.sh` daily and copy the resulting encrypted/off-server archive to separate storage. Never keep the only backup on the same VPS.

## Email / SMTP
Set these environment variables to enable live email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, and optionally `SMTP_USE_SSL=true` for an SSL SMTP endpoint. The application supports direct send, queued delivery, logs, and customer payment/collection reminders.
