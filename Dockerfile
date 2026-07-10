FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# System deps for psycopg + gettext (compilemessages) + Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        gettext libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static at build time (uses a dummy secret; no DB needed).
RUN SECRET_KEY=build-time-dummy DATABASE_URL= python manage.py collectstatic --noinput

RUN chmod +x /app/entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
