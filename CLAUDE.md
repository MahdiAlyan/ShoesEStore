# CLAUDE.md — ShoeStore

Bilingual (AR/EN) shoe e-commerce with COD checkout and WhatsApp order confirmation.
Django monolith: server-rendered templates + DRF viewsets under `/api/` for AJAX.

## Tech stack
- Django 5.x (LTS 5.2); Python 3.12 in Docker (`python:3.12-slim`), 3.13 in local venv
- Django REST Framework — AJAX (cart, admin status) + future mobile
- Django templates + **Metronic Demo 2** theme (in `metronic_html_v8.2.7_demo2/`) for BOTH storefront and dashboard
- PostgreSQL via `DATABASE_URL` (`dj-database-url`); **SQLite fallback when `DATABASE_URL` unset**
- Custom User, **email as username**
- WhiteNoise static files; Gunicorn (Docker) / WSGI (PythonAnywhere)
- Cloudflare Turnstile (env-toggleable); `django-ratelimit`
- Libs: `djangorestframework`, `dj-database-url`, `python-dotenv`, `whitenoise`, `Pillow`, `django-ratelimit`

## Layout
```
config/           settings.py, urls.py, wsgi.py, asgi.py
apps/accounts/    custom User, auth views, password reset
apps/catalog/     products, variants, categories, colors, sizes, images
apps/cart/        session cart + merge-on-login
apps/orders/      checkout, orders, regions, WhatsApp link
apps/dashboard/   Metronic admin dashboard views
templates/        base_store.html, base_dashboard.html, per-app dirs
static/           custom + collected Metronic assets
theme_static/     Metronic Demo2 assets served via STATICFILES_DIRS
media/            uploads
locale/ar, en/    translations
```

## Coding conventions
- **Fat models, thin views.** Business logic (stock, totals, restock) lives on models/managers.
- **i18n from line one.** Every user-facing string wrapped in `{% trans %}` / `{% blocktrans %}` in templates and `gettext_lazy as _` in Python. No bare English strings in responses.
- **Money is always `DecimalField(max_digits=10, decimal_places=2)`.** Never float. Currency USD, `$` prefix in both languages.
- Product/category/color/size/region content translated via **dual fields** (`name_en`/`name_ar`), exposed by a `.name` property that returns the active-language value.
- `select_related` / `prefetch_related` on product list, cart, order queries — no N+1.
- Pagination: 12 products/page (storefront), 25 orders/page (dashboard).

## Non-negotiable rules
- **NEVER commit secrets or `.env`.** Only `.env.example` is committed. Settings read from env via `python-dotenv`.
- **NEVER store, transmit, or attach `name` attributes to card input fields.** The online-payment page is a pure visual placeholder: no `name` attrs, no form submit handler, no JS, no network, no persistence. Include an HTML comment stating this is intentional.
- **ALL stock mutations run inside a `select_for_update` transaction.** Order creation and CANCELLED-restock lock the variant rows, re-check, then mutate.
- Rate limits: login 5/min/IP, signup 5/min/IP, order creation 10/hour/user.
- XSS: rely on autoescaping; never `|safe` on user content. ORM only (no raw SQL). Uploads: Pillow-validated images, ≤5MB.
- Turnstile rendered + verified **only** when `TURNSTILE_ENABLED=true`; missing keys must never crash.

## Status flow
`PENDING → CONFIRMED → OUT_FOR_DELIVERY → DELIVERED`, plus `CANCELLED` and `RETURNED`.
Cancelling restocks items. Order creation decrements stock atomically. `ONLINE` payment is never a reachable final state in MVP.

## Commands (run from repo root, venv active)
```bash
# venv python: .venv/Scripts/python.exe on Windows
python manage.py runserver
python manage.py makemigrations && python manage.py migrate
python manage.py test
python manage.py makemessages -l ar -l en && python manage.py compilemessages
python manage.py collectstatic --noinput
python manage.py seed_demo          # demo data (admin, catalog, regions, orders)
python manage.py createsuperuser
```
Settings module: `config.settings`. Django admin escape hatch at `/dj-admin/`; primary admin UI at `/dashboard/`.

## Testing priority (deadline-aware)
1. Unit: stock decrement/restock, order total = items + region fee snapshot, WhatsApp URL builder.
2. Integration: checkout happy path, anon blocked, insufficient stock, admin status transition + CANCELLED restock, non-staff blocked from admin API.
3. Smoke: every page 200 in both `en` and `ar`.