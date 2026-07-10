# ASSUMPTIONS.md

Running log of defaults chosen where the spec was silent or the environment forced a deviation.
Spec §20 baseline assumptions (currency USD/`$`, +961 default phone code, status flow,
dual-field translations, session cart merge, low-stock threshold 5, price on Product, Turnstile
default OFF, SQLite for demo only, seed admin creds documented) are all adopted as written.

## Environment / structural
- **A1.** Django pinned to `>=5.2,<6.0` (LTS 5.2) per spec "Django 5.x required by client". The
  pre-existing scaffold shipped Django 6.0.7; downgraded to honor the requirement.
- **A2.** Django project package renamed from the scaffold's `ecommers/` to **`config/`** per spec
  §3 folder structure. Settings module is `config.settings`.
- **A3.** Metronic Demo 2 assets live in `metronic_html_v8.2.7_demo2/.../demo2/assets`. They are
  wired into Django via a `theme_static/metronic/` dir listed in `STATICFILES_DIRS` (copied in,
  not symlinked, for cross-platform + WhiteNoise reliability).
- **A4.** **The provided Metronic package does NOT ship a prebuilt RTL CSS bundle** (only the
  webpack RTL plugin *source* under `tools/webpack/plugins/rtl`). Building it requires the full
  Node/webpack toolchain, which is not viable under the demo deadline. RTL is therefore delivered
  via `dir="rtl"` + `lang="ar"` on `<html>` (Bootstrap 5 under Metronic honors logical RTL) plus a
  small custom `rtl.css` override for the key layout flips. Documented deviation from spec §8/§16.

- **A7.** Static storage is `whitenoise.storage.CompressedStaticFilesStorage` (compressed but
  not hashed-manifest). The Metronic bundles reference a handful of optional plugin assets
  (e.g. jstree images) they do not ship, and the *Manifest* variant errors strictly on those.
  Spec §13 requires "WhiteNoise compressed static files" — satisfied. Cache-busting via hashed
  filenames is dropped as a nice-to-have.

- **A9.** `select_for_update` provides real row-level locking only on PostgreSQL; on the
  SQLite demo DB it is a silent no-op (SQLite serializes writes anyway). Concurrent-oversell
  protection at order creation is therefore fully enforced only on the production Postgres DB.
- **A10.** Order-creation rate limit (10/hour/user) uses one shared `django-ratelimit` bucket
  (group `order-create`) across both the web checkout and `POST /api/orders/`, and increments
  only when a COD order is actually attempted (not on invalid forms or ONLINE selection).

- **A11.** GNU gettext (`xgettext`/`msgfmt`) is not installed on the build machine, so the
  `locale/ar` and `locale/en` catalogs were generated/compiled with **polib** (pure Python)
  instead of `makemessages`/`compilemessages`. All 282 strings are translated to Arabic and
  format placeholders are validated. The standard gettext commands are documented in the README
  and run in the Docker image / on PythonAnywhere (both have gettext).
- **A12.** `seed_demo` generates one Pillow placeholder image per product-color (first color is
  the main image) so the product gallery's color filter is demonstrable. Sample orders are created
  through the real `create_order` path (stock is actually decremented). The command is idempotent
  (natural-key `get_or_create`).

## Conventions
- **A5.** Translatable model content uses dual `_en`/`_ar` fields with a `.name` / `.description`
  property returning the active-language value via `django.utils.translation.get_language`.
- **A6.** Phone normalization: strip non-digits (keep leading `+`); if no `+`, prepend
  `DEFAULT_PHONE_COUNTRY_CODE`. Stored as `+<digits>`. Validated by regex `^\+?[0-9]{7,15}$`.
- **A8.** Rate limiting (`django-ratelimit`) uses Django's default in-process cache in the MVP,
  so limits are enforced per worker process. Acceptable for the single-process demo; production
  should configure a shared cache (Redis/memcached) so `5/min/IP` is global. `?next=` redirects
  are validated with `url_has_allowed_host_and_scheme` (rejects absolute, protocol-relative, and
  backslash-normalized cross-origin targets).