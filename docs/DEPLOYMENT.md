# BreakThru Assessments — Deployment Guide

## 1. Domain Configuration
- Target domain: `https://assessments.breakthru.pk`
- Create an **A Record** or **CNAME Record** in your DNS management provider pointing to your server's public IP address.

## 2. Infrastructure Options
- **Option A: Linux VPS (Ubuntu 24.04 LTS / Debian 12) - Recommended for 300+ Users**
  - Compute: 2 vCPU, 4GB RAM minimum.
  - Web Server: Nginx acting as Reverse Proxy with SSL termination via Let's Encrypt (`certbot`).
  - WSGI Server: Gunicorn with 4-8 worker processes.
  - Database: Managed PostgreSQL 15+ or local PostgreSQL on the VPS.
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
   ALLOWED_HOSTS=assessments.breakthru.pk,127.0.0.1
   DATABASE_URL=postgresql://breakthru_user:dbpassword@127.0.0.1:5432/breakthru_db
   PORTAL_URL=https://assessments.breakthru.pk
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
       server_name assessments.breakthru.pk;

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
   sudo certbot --nginx -d assessments.breakthru.pk
   ```
