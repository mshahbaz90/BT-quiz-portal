# BreakThru Assessments — Deployment Guide

## 1. Domain Configuration
- Primary Public Domain: `https://bt.assesment.pk` (or `https://bt.assessment.pk`)
- Alternate / Intranet Domain: `https://breakthru.assesment.portal` (or `https://breakthru.assessment.portal`)
- DNS Setup:
  - Add an **A Record** pointing `bt.assesment.pk` to your server's public IPv4 address.
  - Or configure a **Cloudflare Tunnel** / CNAME record if your server is behind dynamic IP or NAT.
  - For local/intranet testing with `breakthru.assesment.portal`, map it in your workstation `hosts` file (`C:\Windows\System32\drivers\etc\hosts` on Windows or `/etc/hosts` on Linux/macOS):
    ```text
    127.0.0.1  breakthru.assesment.portal
    127.0.0.1  bt.assesment.pk
    ```

## 2. Infrastructure Options
- **Option A: Linux VPS (Ubuntu 24.04 LTS / Debian 12) - Recommended for 300+ Users**
  - Compute: 2 vCPU, 4GB RAM minimum.
  - Web Server: Nginx acting as Reverse Proxy with SSL termination via Let's Encrypt (`certbot`).
  - WSGI Server: Gunicorn with 4-8 worker processes.
  - Database: Managed PostgreSQL 15+ or local PostgreSQL on the VPS (SQLite WAL mode also supported).
- **Option B: Containerized Docker Deployment**
  - Simple Dockerfile + docker-compose.yml configuration with Postgres & Gunicorn.

## 3. Production Environment Setup
1. Clone the repository into `/var/www/breakthru-portal`.
2. Set up Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Configure `/var/www/breakthru-portal/.env`:
   ```ini
   DEBUG=False
   SECRET_KEY=generate-a-secure-random-64-character-string
   ALLOWED_HOSTS=bt.assesment.pk,bt.assessment.pk,breakthru.assesment.portal,assessment.breakthru.pk,127.0.0.1
   DATABASE_URL=postgresql://breakthru_user:dbpassword@127.0.0.1:5432/breakthru_db
   PORTAL_URL=https://bt.assesment.pk
   CSRF_TRUSTED_ORIGINS=https://bt.assesment.pk,https://breakthru.assesment.portal
   ```
4. Run migrations and collect static files:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
5. Configure systemd service for Gunicorn:
   ```ini
   [Unit]
   Description=Gunicorn daemon for BreakThru Assessments
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/breakthru-portal
   ExecStart=/var/www/breakthru-portal/venv/bin/gunicorn --access-logfile - --workers 5 --bind unix:/run/gunicorn.sock breakthru_portal.wsgi:application

   [Install]
   WantedBy=multi-user.target
   ```
6. Configure Nginx with SSL:
   ```nginx
   server {
       server_name bt.assesment.pk bt.assessment.pk breakthru.assesment.portal;

       location = /favicon.ico { access_log off; log_not_found off; }
       location /static/ {
           alias /var/www/breakthru-portal/staticfiles/;
       }
       location /media/ {
           alias /var/www/breakthru-portal/media/;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/run/gunicorn.sock;
       }
   }
   ```
7. Obtain Let's Encrypt SSL:
   ```bash
   sudo certbot --nginx -d bt.assesment.pk -d bt.assessment.pk
   ```
