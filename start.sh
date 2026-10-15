#!/usr/bin/env bash
# Exit on error
set -o errexit

# Activate Render Python virtual environment
if [ -f "/opt/render/project/src/.venv/bin/activate" ]; then
    . /opt/render/project/src/.venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    . .venv/bin/activate
fi

python manage.py migrate --noinput
exec gunicorn breakthru_portal.wsgi:application --bind 0.0.0.0:$PORT
