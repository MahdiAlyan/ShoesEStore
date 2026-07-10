# ShoeStore — Bilingual (AR/EN) Shoe E-Commerce

A Django e-commerce store for shoes with size/color variants, a guest→user cart,
Cash-on-Delivery checkout, a Metronic admin dashboard, and per-order **WhatsApp**
order-confirmation links. Fully bilingual **English (LTR)** and **Arabic (RTL)**.

---

## Features

**Storefront**
- Product catalog: categories, product list with filters (category, color, size, price) + pagination.
- Product detail: image gallery, color swatches + size buttons, per-variant stock ("In stock"/"Out of stock"), unavailable combinations disabled.
- Guest **session cart**; add/update/remove via AJAX; **merges into the user's cart on login** (sums quantities, capped at stock).
- Email/password **signup, login, logout, password reset** (console email backend). Email is the username.
- Auth-gated **checkout**: receiver name + phone (may differ from account), delivery region (fee auto-added), address, and payment choice:
  - **Cash on Delivery** — functional.
  - **Online Payment** — a static, non-functional card placeholder (no `name` attributes, no submit, no JS, no network, no storage) with a bilingual "coming soon" notice.
- Orders created as **PENDING**, stock **decremented atomically** at order creation; **My Orders** page; order success page with a bilingual "we'll confirm on WhatsApp" message.

**Admin dashboard (`/dashboard/`, staff only)**
- Overview: orders today, pending orders, low-stock variants (< 5), revenue from DELIVERED orders.
- CRUD for products (inline variants + stock + image upload), categories, and delivery regions.
- Orders table with status filter + search (order #, receiver name, phone), pagination.
- Order detail; **AJAX status changes** (PENDING → CONFIRMED → OUT_FOR_DELIVERY → DELIVERED, plus CANCELLED and RETURNED; **CANCELLED restocks** items; invalid transitions rejected).
- **WhatsApp icon** per order → opens `https://wa.me/<phone>?text=<bilingual order summary>` in a new tab.

**Platform**
- Bilingual AR/EN with full RTL for Arabic; language switcher persists via Django's language cookie.
- DRF API under `/api/` powers the AJAX (cart, admin status) and is mobile-ready.
- Cloudflare **Turnstile** on signup/login/checkout, rendered + verified only when `TURNSTILE_ENABLED=true`.
- Rate limiting (login/signup 5/min/IP, order creation 10/hour/user), CSRF everywhere, atomic stock via `select_for_update`.
- WhiteNoise static files; PostgreSQL in production, SQLite fallback for the demo.

Django's built-in admin remains available at `/dj-admin/` as an escape hatch.

---

## Tech stack

Django 5.2 · Django REST Framework · PostgreSQL (`dj-database-url`, SQLite fallback) ·
custom email-as-username User · WhiteNoise · Gunicorn · Pillow · django-ratelimit ·
Metronic Demo 2 theme · Cloudflare Turnstile.

See `CLAUDE.md` for conventions and `ASSUMPTIONS.md` for design decisions.

---

## Local setup

```bash
# 1. Virtualenv + dependencies
python -m venv .venv
# Windows: .venv\Scripts\activate   |   *nix: source .venv/bin/activate
pip install -r requirements.txt

# 2. Environment (optional locally — SQLite + safe defaults are used if absent)
cp .env.example .env        # then edit as needed

# 3. Database + demo data
python manage.py migrate
python manage.py seed_demo   # admin, catalog, regions, 2 sample orders
python manage.py compilemessages   # build Arabic .mo (needs GNU gettext; see i18n note)

# 4. Run
python manage.py runserver
```

Visit http://127.0.0.1:8000/ (storefront) and http://127.0.0.1:8000/dashboard/ (admin).

**Seed credentials** (documented; rotate before any real launch):
- Admin: `admin@shoestore.local` / `ShoeAdmin!2025`
- Customer: `customer@shoestore.local` / `ShoeCustomer!2025`

Create your own superuser instead with `python manage.py createsuperuser`.

---

## Internationalization

All user-facing strings use Django i18n; `locale/ar` is fully translated.

```bash
python manage.py makemessages -l ar -l en   # extract/update catalogs (needs GNU gettext)
python manage.py compilemessages             # build .mo files
```

> **Note:** `makemessages`/`compilemessages` require the GNU **gettext** toolchain
> (`xgettext`, `msgfmt`). It ships in the Docker image and is available on
> PythonAnywhere. The `.po` catalogs are committed; if gettext is unavailable
> locally, the app still runs (untranslated strings fall back to English).

---

## Deployment — Docker / AWS (production)

```bash
cp .env.example .env          # set SECRET_KEY, DEBUG=false, ALLOWED_HOSTS, etc.
docker compose up --build
```

- `db` (postgres:16, named volume) + `web` (gunicorn on :8000).
- The `web` entrypoint runs `migrate` and `compilemessages`, then Gunicorn.
- `collectstatic` runs at image build time (WhiteNoise-compressed).
- Create an admin and seed once the stack is up:
  ```bash
  docker compose exec web python manage.py createsuperuser
  docker compose exec web python manage.py seed_demo
  ```
- **Cloudflare (production domain):** proxy DNS through Cloudflare and enable
  **WAF / Bot Fight Mode** in the dashboard (no code). To use Turnstile, set
  `TURNSTILE_ENABLED=true` + `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY`.
- Behind a TLS-terminating proxy, set `SECURE_SSL_REDIRECT=true` and ensure the
  proxy sends `X-Forwarded-Proto: https` (`SECURE_PROXY_SSL_HEADER` is configured).

---

## Deployment — PythonAnywhere (demo)

1. **Clone & venv**
   ```bash
   git clone <repo> shoestore && cd shoestore
   python3.12 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Database:** leave `DATABASE_URL` empty to use SQLite (fine for the demo), or set a
   paid-account Postgres URL.
3. **Migrate, seed, translations, static**
   ```bash
   python manage.py migrate
   python manage.py seed_demo
   python manage.py compilemessages
   python manage.py collectstatic --noinput
   python manage.py createsuperuser   # optional (seed_demo already makes an admin)
   ```
4. **WSGI file** — point it at the project settings:
   ```python
   import os, sys
   path = "/home/<user>/shoestore"
   if path not in sys.path:
       sys.path.insert(0, path)
   os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
5. **Static & media mappings** (Web tab):
   - `/static/` → `/home/<user>/shoestore/staticfiles`
   - `/media/`  → `/home/<user>/shoestore/media`
6. Set env vars (Web tab or `.env`): `SECRET_KEY`, `DEBUG=false`, `ALLOWED_HOSTS=<you>.pythonanywhere.com`, `CSRF_TRUSTED_ORIGINS=https://<you>.pythonanywhere.com`. Reload the web app.

---

## Testing

```bash
python manage.py test           # full suite
python manage.py test apps.orders   # a single app
```

Covers: stock decrement/restock, order total = items + region-fee snapshot, WhatsApp URL
builder, full checkout happy path, anonymous checkout blocked, insufficient-stock rejection,
admin status transitions + CANCELLED restock, non-staff blocked from admin API, cart
merge-on-login, and every page returning 200 in both languages.

---

## Environment variables (`.env.example`)

| Var | Purpose |
|---|---|
| `SECRET_KEY` | Django secret (required in production). |
| `DEBUG` | `true`/`false`. |
| `ALLOWED_HOSTS` | Comma-separated hosts. |
| `DATABASE_URL` | Postgres URL; empty → SQLite fallback. |
| `EMAIL_BACKEND` | Defaults to console backend. |
| `DEFAULT_FROM_EMAIL` | Sender for password-reset emails. |
| `TURNSTILE_ENABLED` / `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile. |
| `DEFAULT_PHONE_COUNTRY_CODE` | Prefixed when a receiver phone lacks `+` (default `+961`). |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins for CSRF. |

Never commit `.env`. Only `.env.example` is committed.
