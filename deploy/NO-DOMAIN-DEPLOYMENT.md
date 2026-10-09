# No-domain deployment path

The easiest public deployment path is a hosted web service that supplies its own HTTPS subdomain. Render provides each web service a unique `onrender.com` URL and supports FastAPI/Docker deployments.

1. Create a Render account.
2. Put this project in a private Git repository and connect that repository.
3. Create services from the included `render.yaml` Blueprint.
4. Choose a production-capable web/database plan rather than relying on expiring free database storage for company records.
5. Enter `ADMIN_PASSWORD` and the SMS/WhatsApp secrets when prompted.
6. After deployment, use the generated `onrender.com` URL as the application address and Meta WhatsApp webhook base URL.
7. The webhook is:
   `https://YOUR-SERVICE.onrender.com/api/whatsapp`

A custom domain can be added later; the application does not need to be redesigned.
