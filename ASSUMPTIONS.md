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

## Iteration 2
- **A13.** (M1.1) The language switcher pre-computes each language's target URL in
  the template via `django.urls.translate_url(request.get_full_path(), code)`
  (exposed as the `switch_lang_url` tag in `apps/catalog/templatetags/store_extras.py`),
  emitted as `data-next` per `<option>`. The old switcher passed the raw prefixed
  path (`/ar/...`) as `next`; `set_language`'s own `translate_url` could not strip
  it because the active language during the `/i18n/setlang/` POST is not `ar`.
  Pre-translating at render time (page language active) is the spec-mandated fix.
- **A14.** (M1.3) One canonical money helper `apps/catalog/money.py::format_money`
  (and the `|money` filter in `store_extras`) renders all prices as `$X.YY`
  dot-decimal in both languages. Python's `:.2f` is locale-independent, so no
  `{% localize off %}` is needed. Used in every price-bearing template and the
  WhatsApp message builder.
- **A15.** (M1 side-fix) The dashboard was mounted at `/admin/` in `config/urls.py`,
  but CLAUDE.md and the existing test suite (`apps/dashboard/tests.py`,
  `apps/orders/test_e2e.py`) expect `/dashboard/`. Re-mounted at `/dashboard/` to
  make the pre-existing-red suite green and match the documented primary admin UI.

- **A16.** (M2) `Order.order_number` is computed as `max(existing, 999) + 1` inside
  the existing `create_order` atomic transaction. `next_order_number()` uses a
  `Max` aggregate; on Postgres two truly-concurrent inserts could read the same
  max, so the `unique=True` constraint is the final backstop (the loser's commit
  raises IntegrityError rather than duplicating a number) — consistent with the
  SQLite-only-locking note in A9. The field is `null=True` at the DB level so the
  additive migration + backfill is safe and so any future non-`create_order` path
  fails loud on display rather than at insert; every real creation path assigns it.
  Data migration `0002` backfills existing orders from 1000 in `created_at` order.

- **A17.** (M3) The static `/orders/payment/online/` route, `online_payment` view,
  and `online_payment.html` are removed. Online payment is now a Bootstrap modal on
  the checkout page (visual-only card form, no `name` attrs, no submit). The modal
  opens when "Online Payment" is selected; "Continue with Cash on Delivery" (and any
  other dismissal) reverts the choice to COD, so checkout stays COD-only. A
  server-side guard still bounces a stray ONLINE POST back to checkout without
  creating an order.

- **A18.** (M4.1) `static/img/hero.jpg` is a license-free shoe photo (Unsplash
  license, stored locally, not hotlinked). Hero height is `calc(100vh - 76px)`
  where 76px is the approximate sticky-navbar height (`--ss-navbar-h`). The dark
  overlay (`.hero::before`, ~62% black) guarantees text contrast in both LTR/RTL.
- **A19.** (M4.2) The landing "Featured shoes" grid was already wrapped in the
  site-standard `container-xxl` (horizontal gutters), so it does not touch the
  viewport edges; no change was needed beyond confirming consistency with
  `product_list`.

- **A20.** (M5) select2, SweetAlert2, and jQuery are NOT added as new downloads —
  Metronic's bundled `plugins.bundle.js`/`.css` already ship all three locally
  (verified: `jQuery.fn.select2`, `window.Swal`, select2 CSS). This satisfies the
  "local static, no CDN, works offline/PythonAnywhere" requirement without new
  assets. `static/js/site.js` initializes select2 on every `<select>` (RTL-aware,
  `width:'resolve'`, search hidden for <8 options; opt out with `data-no-select2`)
  and exposes `ShoeStore.toast/alert/confirm`. Server-side Django `messages` are
  serialized into `window.SS.messages` and rendered as SweetAlert2 toasts/alerts
  (success/info→toast, warning→toast, error→modal); the old server-rendered alert
  blocks are removed. `<form data-confirm="…">` gets a SweetAlert2 confirm.

- **A21.** (M6.3) Bulk variant creation lives in a new `AdminProductViewSet`
  (`IsAdminUser`) registered at `api/admin/products`, action `variants/bulk`
  (lookup by pk). SKUs are `{prefix or slug}-{COLOR}-{SIZE}` uppercased, with
  non-alphanumerics collapsed to `-`, and disambiguated with a numeric suffix if
  a global SKU collision occurs. The "Add variants" button appears only when
  editing a saved product (a new product has no id yet); the multi-selects are
  select2-initialized on `shown.bs.modal` (not at page load) so their width
  resolves correctly inside the hidden modal. `{created}`/`{skipped}` tokens in
  the result string are substituted client-side for the SweetAlert2 report.
- **A22.** (M6.1/6.2) Dashboard sidebar and storefront filters use `position:
  sticky` on desktop only (`min-width: 992px`); RTL is handled automatically by
  the existing `dir="rtl"` flex/grid flow, so the sidebar sits on the right.

- **A23.** (M7) One `partials/_profile_menu.html` renders the circular icon-only
  account button + dropdown in both headers; the dashboard header passes
  `on_dashboard=True` so staff get a "Storefront" back-link instead of
  "Dashboard". The email is shown in a non-clickable `dropdown-item-text` row.
  `data-bs-display="static"` + `dropdown-menu-end` keep it from overflowing on
  mobile; RTL edge alignment reuses the existing `rtl.css` `.dropdown-menu-end`
  override.

- **A24.** (M8) Seed placeholder images are now a light neutral 1:1 canvas with a
  centered color swatch and **no text** — the spec's "both scripts or none"
  option. Rendering shaped Arabic in Pillow needs extra libs/fonts not installed
  (see A11), so "none" avoids the previous English-only-label-on-dark-block look
  while keeping images per-color for the gallery filter. `seed_demo --flush` wipes
  catalog/cart/order rows (PROTECT-safe order) but never users, and image seeding
  is idempotent so every product keeps ≥1 image per variant color on any run.

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