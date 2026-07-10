#!/bin/sh
set -e

# Apply migrations, compile translations, then start Gunicorn.
python manage.py migrate --noinput
python manage.py compilemessages || true

exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --access-logfile - \
    --error-logfile -
