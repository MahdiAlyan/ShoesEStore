# UI Refactor Audit (M0)

Read-only inventory taken before the Metronic → bespoke design-system refactor.
Scope of truth: templates/, static/, theme_static/, config/, apps/ as of this commit.

## 1. Template inventory

### templates/ (root)
| File | Purpose |
|---|---|
| `base_store.html` | Storefront shell: sticky navbar (brand, category nav, language switcher, cart badge, account), footer, script loads. **Loads Metronic.** |
| `base_dashboard.html` | Dashboard shell: fixed 260px sidebar, header with toggle + language switcher + profile menu. **Loads Metronic.** |
| `404.html` | Extends `base_store.html`. |
| `500.html` | Standalone (no base); loads `metronic/css/style.bundle.css` directly. **Rebuild in M2.** |

### templates/partials/
| File | Purpose |
|---|---|
| `_js_ui.html` | Injects `window.SS` (rtl flag, i18n strings, Django messages) then loads `js/site.js`. |
| `_profile_menu.html` | Account dropdown — **Bootstrap** (`data-bs-toggle="dropdown"`). |
| `_turnstile.html` | Turnstile widget div, only when `TURNSTILE_ENABLED`. |

### templates/accounts/
`auth_base.html` (auth card shell), `_field.html` (form-field partial), `login.html`, `signup.html`, `password_reset_form.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`, `password_reset_email.html` (plain text), `password_reset_subject.txt`.

### templates/catalog/
`home.html` (hero + featured), `product_list.html` (filter sidebar + grid + pagination), `product_detail.html` (gallery + inline variant-picker JS), `_product_card.html`.

### templates/cart/
`detail.html` (line-item table, qty steppers, remove, summary, empty state).

### templates/orders/
`checkout.html` (form, live fee summary, online-payment placeholder modal), `success.html`, `my_orders.html`, `_status_badge.html` (`<span class="badge status-<STATUS>">`).

### templates/dashboard/
`overview.html` (stat cards, recent orders, low stock), `products_list.html`, `product_form.html` (variant/image formsets + bulk-variants modal), `orders_list.html` (filter, inline status select, WhatsApp link, pagination), `order_detail.html`, `categories.html`, `regions.html`.

## 2. Grep results

- **`metronic`** — templates: `base_store.html` (4 refs), `base_dashboard.html` (4 refs), `500.html` (1 ref). `static/css/custom.css:1` (comment). `config/settings.py` references it only indirectly via `STATICFILES_DIRS = [static, theme_static]` (`theme_static/metronic/` holds all theme files, 74MB). Docs mentions: `CLAUDE.md`, `ASSUMPTIONS.md`, `.gitignore`, `.dockerignore`, `README.md`.
- **`jquery`** — `static/js/site.js` (select2 init + language switcher), `static/js/dashboard.js` (select2 change sync, has native fallback), `templates/orders/checkout.html:203` (fee calc binding, has native fallback), `templates/dashboard/product_form.html` (bulk-variants select2). jQuery itself ships inside `metronic/plugins/global/plugins.bundle.js` (with select2, SweetAlert2, Bootstrap JS).
- **`bootstrap` / `data-bs-`** — both bases (`data-bs-theme`), `_profile_menu.html` (dropdown), `checkout.html` (payment modal via `bootstrap.Modal`, guarded by `window.bootstrap`), `product_form.html` (bulk-variants modal).
- **`data-kt-`** — **zero** hits in project templates/JS (only inside `theme_static/`). No Metronic JS behaviors are used.
- **`rtl.css`** — conditional link in both bases; `static/css/rtl.css` is a 21-line custom override (not a Metronic bundle). Dies with the refactor — replaced by logical properties.
- **`theme_static`** — only `config/settings.py` `STATICFILES_DIRS`.

## 3. JS dependency → replacement map

| Current behavior | Where | Depends on | Replacement (milestone) |
|---|---|---|---|
| toast/alert/confirm (`ShoeStore.*`) | `site.js` | SweetAlert2 | `ui.js` toasts + native `<dialog>` (M1) |
| select2 on all `<select>`s | `site.js` | jQuery + select2 | styled native `<select>` (M1) |
| language switcher submit | `site.js` (jQuery-only bind) | jQuery | vanilla change listener in `ui.js` (M1) |
| profile dropdown | `_profile_menu.html` | Bootstrap dropdown | `ui.js` `[data-menu]` component (M1) |
| dashboard sidebar toggle | `site.js` `initDashSidebar` | none (vanilla) | ported into `ui.js` (M1) |
| Django messages → feedback | `site.js` | SweetAlert2 | `ui.js` toasts (M1) |
| `data-confirm` form interception | `site.js` | SweetAlert2 | `ui.js` confirm (M1) |
| cart add/qty/remove + badge | `cart.js` | none (vanilla; uses `ShoeStore.*` + `.d-none`) | kept in M1; rewritten on `api.js` in M2 |
| variant picker | `product_detail.html` inline | none | kept; restyled in M2 |
| checkout fee calc | `checkout.html` inline | jQuery preferred, **native fallback exists** | vanilla rewrite (M3) |
| online-payment placeholder modal | `checkout.html` inline | `bootstrap.Modal` (guarded — no-ops if absent) | `ui.js` dialog (M3). Server guard bounces `payment_method=ONLINE` (`apps/orders/views.py:34-51`), so COD stays safe in the gap. |
| status-change AJAX | `dashboard.js` | jQuery preferred, **native fallback exists**; SweetAlert2 | rewritten on `api.js` + `ui.js` (M4) |
| bulk-variants modal | `product_form.html` inline | jQuery + select2 + Bootstrap Modal + Swal | `ui.js` dialog + native multi-selects (M4). **Nonfunctional M1→M4** (trigger is `data-bs-toggle`; without Bootstrap it simply never opens — no JS error, formsets unaffected). |
| status filter auto-submit | `orders_list.html` inline `onchange` | none | kept (M4 tidy) |

**Load-bearing contracts that must survive every milestone:** `window.CSRF_TOKEN`; `window.SS` shape (`_js_ui.html`); `ShoeStore.toast(icon,title)` / `.alert(icon,title,text)→Promise` / `.confirm(opts)→Promise<{isConfirmed}>`; `window.ShoeStoreBindAddToCart(picker,btn)`; `#cart-badge` + `.d-none`; `#cart-subtotal`, `tr[data-row-id]`, `.line-total/.cart-qty/.qty-step/.cart-remove[data-item-id]`; `#variant-availability`/`#variant-ids` json_script + `#variant-picker[data-add-url]` + `.color-swatch[data-color]`/`.size-btn[data-size]`; `#id_region option[data-fee]`, `#summary-delivery`, `#summary-total`, `#pm-cod`, `#pm-online`, `#continue-cod`; `.status-select[data-order-id]`, `[data-status-badge]`, `.status-<STATUS>` classes; `#dash_layout`/`#dash_sidebar`/`#dash_sidebar_toggle`/`#dash_backdrop`; `.lang-switcher` options with `data-next` + hidden `next`; `cf-turnstile-response` POST field when enabled; `$X.YY` money format; `?page=N` + `filter_qs`/`status`/`q` pagination params. Hardcoded API paths: `/api/cart/items/…`, `/api/admin/orders/<id>/status/` (never locale-prefixed).

## 4. Smoke URL matrix

Every URL is tested in EN (unprefixed) and AR (`/ar/…`) — `i18n_patterns(prefix_default_language=False)`.

| Page | EN | AR |
|---|---|---|
| Home | `/` | `/ar/` |
| Product list | `/products/` | `/ar/products/` |
| Product detail | `/products/<slug>/` | `/ar/products/<slug>/` |
| Cart | `/cart/` | `/ar/cart/` |
| Checkout | `/orders/checkout/` | `/ar/orders/checkout/` |
| Order success | `/orders/success/<pk>/` | `/ar/orders/success/<pk>/` |
| My Orders | `/orders/mine/` | `/ar/orders/mine/` |
| Login | `/accounts/login/` | `/ar/accounts/login/` |
| Signup | `/accounts/signup/` | `/ar/accounts/signup/` |
| Password reset (+done/confirm/complete) | `/accounts/password-reset/…` | `/ar/accounts/password-reset/…` |
| Dashboard overview | `/dashboard/` | `/ar/dashboard/` |
| Dashboard products / new / edit | `/dashboard/products/…` | `/ar/dashboard/products/…` |
| Dashboard categories | `/dashboard/categories/` | `/ar/dashboard/categories/` |
| Dashboard regions | `/dashboard/regions/` | `/ar/dashboard/regions/` |
| Dashboard orders / detail | `/dashboard/orders/…` | `/ar/dashboard/orders/…` |
| 404 / 500 | any bad URL / handler | same |

Existing automated coverage: smoke 200s in both languages across catalog/cart/orders/accounts/dashboard tests plus `orders/test_e2e.py` full-flow (EN+AR). Tests assert text content and `$X.YY` money format only — no CSS classes, template names, or static paths, **except** `.status-<STATUS>` badge classes regenerated by `dashboard.js`.

## 5. Static/settings facts

- `STATICFILES_DIRS = [static/, theme_static/]`; WhiteNoise `CompressedStaticFilesStorage` (not Manifest — deliberate while Metronic's broken internal refs exist; revisit at M6).
- Custom assets today: `static/css/custom.css` (8.9KB), `static/css/rtl.css` (0.9KB), `static/js/site.js` (7.9KB), `static/js/cart.js` (6.1KB), `static/js/dashboard.js` (3.5KB), `static/img/hero.jpg`. No `static/fonts/`.
- Remote loads today: Google Fonts (Inter) in both bases; Turnstile script (conditional, stays).
- `metronic_html_v8.2.7_demo2/` does **not** exist on disk (gitignored source archive); the live copy is `theme_static/metronic/`. M6 deletion target = `theme_static/` + the `STATICFILES_DIRS` entry + collected `staticfiles/metronic/`.
