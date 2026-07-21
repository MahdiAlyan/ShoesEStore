# UI_DEFECTS — Defect-Driven Rework

Forensic visual audit of the current custom UI (real Chromium via Playwright —
Chrome DevTools MCP was not connected; fallback used per spec). Full matrix
captured: 20 pages × {en, ar} × {390, 768, 1440} = 120 cells in `ui_audit/`,
with per-cell console-error, network-failure, computed-font, and
horizontal-scroll capture in `ui_audit/report.json`.

## Programmatic findings (whole matrix)

- **Static assets all load** — zero CSS/JS/font/image 404s anywhere. This is
  NOT a broken-static problem; the design-system fonts (Inter/Fraunces/Plex)
  load and apply on every page that was styled.
- **Horizontal scroll at 390px on every storefront page** and most dashboard
  pages — see D1, D9.
- **404 page** shows system font + a JS error, but only because `DEBUG=True`
  serves Django's debug 404, not the real `404.html`. Verify with `DEBUG=False`
  (tracked in D14); not a production defect on its own.
- No JS console errors on any real (non-debug) page.

## Root-cause summary

The M1 milestone rebuilt only the two base shells; every **inner content
template** (home featured grid, `_product_card`, product list, product detail,
cart, checkout, dashboard CRUD) still carries **Metronic/Bootstrap markup**
(`.container-xxl`, `.row`, `.col-*`, `.card`, `.hero`, `.pagination`,
`ki-duotone` icons, `.modal`) whose CSS left with Metronic. Result: grids
collapse to one giant column, containers lose max-width/padding, modals render
inline, and icon-only controls are empty boxes. The shells look intentional;
the content looks like unstyled HTML. That is the client rejection.

## Ranked defect table

| ID | Page(s) | Lang | Width | Severity | Evidence | Root-cause hypothesis |
|----|---------|------|-------|----------|----------|-----------------------|
| D1 | all storefront | both | 390 | BLOCKER | `home__en__390.png` | `.site-header-actions` overflows to 506px: `.d-none-mobile` (base.css) is overridden by later `.btn{display:inline-flex}` (components.css, equal specificity), so "Sign up" never hides; auth/lang controls don't shrink. |
| D2 | product-list | both | all | BLOCKER | `products__en__1440.png` | `.row/.col-*` unstyled → products stack one-per-row as giant cards; filter `<aside>` not a sidebar; no product grid. |
| D3 | home, product-list | both | all | BLOCKER | `home__en__390.png` | `_product_card.html` has no card/image-well CSS → inconsistent image aspect ratios, oversized placeholders, cramped meta, no hover lift. |
| D4 | product-detail | both | all | BLOCKER | `product-detail__en__1440.png` | No 2-col layout; gallery image full-bleed & huge; color swatches render as broken "— —" dashes not chips; size grid is bare numbers; add-to-cart washed out; breadcrumb is raw numbered `<ol>`. |
| D5 | checkout | both | all | BLOCKER | `checkout__en__1440.png` | Online-payment `.modal` renders **inline** (Bootstrap modal JS removed in M1) → card-details placeholder + inputs always visible on the page. |
| D6 | cart (items) | both | all | BLOCKER | `cart-items__en__1440.png` | Qty stepper `.qty-step` buttons are empty boxes (no +/− glyphs), stacked vertically; `.cart-remove` is an invisible empty pink box (no icon/label). |
| D7 | product-detail | both | all | MAJOR | `product-detail__en__1440.png` | OOS size not visibly struck/disabled beyond faint color; swatch selected-ring missing; thumbnails inconsistent (photo + red circle). |
| D8 | home | both | all | MAJOR | `home__en__1440.png` | Hero (`.hero`, `.container-xxl`, `.display-3`) unstyled → short cramped band, text overlaps, no editorial scale. |
| D9 | dash tables (orders, products, categories, regions, order-detail) | both | 390 | MAJOR | `dash-orders__en__390.png` (724>390) | Wide `<table>` not wrapped in an overflow-x scroller → page-level horizontal scroll on mobile. |
| D10 | dash overview | both | all | POLISH | `dash-overview__en__1440.png` | Stat "cards" are plain stacked `.card` blocks (acceptable but not true KPI tiles with big-number hierarchy). |
| D11 | dash product-form | both | all | MAJOR | `dash-product-form__en__1440.png` | Variant/image formsets + bulk-variants `.modal` unstyled; bulk modal renders inline / can't open (Bootstrap gone). |
| D12 | auth (login/signup/reset) | both | all | POLISH | `login__en__1440.png` | Auth card top-left not centered; helper links (`Create an account`, `Forgot password?`) are plain text, no accent/underline. |
| D13 | product-list, product-detail | both | all | MAJOR | `products__en__1440.png` | `.pagination`/`.page-link` and breadcrumb `<ol>` unstyled; leftover `ki-duotone` icon glyphs render as empty boxes in empty states/cards. |
| D14 | 404, 500 | both | all | MAJOR | `notfound__en__1440.png` | Real error pages unverified (debug served instead); `500.html` still references Metronic CSS and is standalone. Must render styled + bilingual with `DEBUG=False`. |
| D15 | dash order-detail | both | all | MAJOR | `dash-order-detail__en__1440.png` | (to confirm) status timeline component + WhatsApp icon button not present/styled; raw status `<select>`. |

## Severity tally
- BLOCKER: D1, D2, D3, D4, D5, D6 (6)
- MAJOR: D7, D8, D9, D11, D13, D14, D15 (7)
- POLISH: D10, D12 (2)

## Fix order (Phase 2)
D1 (global) → D2/D3 (grid+card, shared) → D4/D7/D13 (detail) → D5/D6 (checkout+cart) → D9/D11/D15/D10 (dashboard) → D8/D12/D14 (hero/auth/errors).
Every fix lands in a shared file (tokens/base/components/storefront/dashboard css, ui.js, or a shared partial); before/after screenshots recorded per fix.

---

## Phase 2 — resolutions (all fixed)

Before screenshots: `ui_audit/<page>__<lang>__<width>.png`. After screenshots: `ui_audit/fix/*` (per-fix) and `ui_audit/final/*` (full re-sweep). Every fix is a root-cause change in a shared file — **zero inline styles or `!important` added**.

| ID | Fix (root file) | After evidence |
|----|-----------------|----------------|
| D1 | Header auth/lang moved to mobile sheet via `.header-inline` wrapper (defeats the `.btn` specificity that kept `.d-none-mobile` from hiding); also fixed a leaking multi-line `{# #}` comment. `base_store.html`, `storefront.css`. **Bonus root fix:** `html{overflow-x:clip}` clips the off-canvas drawer; `min-width:0` on grid children stops wide tables stretching tracks. | `fix/d1-home-390-*`, `final/*__*__390` (sw=390) |
| D2/D3 | Real product grid + card component (consistent 4:5 image well, hover lift); catalog filter sidebar (`<details>` sheet on mobile, forced-open desktop via ui.js). `_product_card.html`, `home.html`, `product_list.html`, `storefront.css`. | `fix/d3-products-en-1440`, `final/products__*` |
| D4/D7 | Two-column PDP, sticky gallery, circular color swatches with selected ring, segmented size grid, OOS struck-through/dashed, styled breadcrumb. Variant-picker JS contract preserved. `product_detail.html`, `storefront.css`. | `fix/d4-detail-selected-1440`, `final/product-detail__*` |
| D5 | Online-payment placeholder rebuilt as native `<dialog>` driven by `ui.js` (was rendering inline); security spec intact (no `name` attrs, no submit/network, disabled inputs, comment). Fee calc rewritten vanilla. `checkout.html`, `storefront.css`. | `fix/d5-checkout-modal` |
| D6 | Cart qty stepper (inline SVG +/−) + visible trash-icon remove; base form styling wrapped in `:where()` so component classes override cleanly; mobile stacked rows. `cart/detail.html`, `storefront.css`, `base.css`. | `fix/d6-cart-1440`, `final/cart-items__ar__390` |
| D9 | `.table-responsive`/`.table-wrap { overflow-x:auto }` in shared `components.css`; all dashboard tables wrapped. | `final/dash-*__*__390` (sw=390) |
| D10 | KPI stat tiles (`.stat-card`, big Fraunces number). `overview.html`, `dashboard.css`. | `final/dash-overview__*` |
| D11 | Bulk-variants modal rebuilt: native `<dialog>` + native multi-selects + `ShoeStore.api` (no jQuery/Bootstrap/select2/Swal); formsets styled. `product_form.html`, `dashboard.css`. | `fix/d13-bulkmodal` |
| D13 | Flat `.pagination`/`.page-link` moved to shared `components.css`; WhatsApp inline-SVG icon button. | `final/dash-orders__*` |
| D15 | Reusable `orders/_status_timeline.html` (PENDING→…→DELIVERED, CANCELLED/RETURNED terminal), CSS-driven from `data-current`. Used on dashboard order detail **and** My Orders + success. | `fix/d13-orderdetail-1440`, `final/my-orders__*`, `final/order-success__*` |
| D8 | Editorial hero with scrim, eyebrow, display title. `home.html`, `storefront.css`. | `final/home__*` |
| D12 | Auth card centered (`.auth-shell`), accent `.link` helper for helper links; `_field.html` design-system markup. | `final/login__en__1440` |
| D14 | 404 rebuilt on `.empty-state`; 500.html rebuilt self-contained on design-system CSS (Metronic reference removed). Verified with `DEBUG=False`. | `final/path/9-404*` |

## Phase 3 — acceptance results

- **Full matrix re-sweep** (20 pages × en/ar × 390/768/1440 = 120 cells, `ui_audit/final/`): **0 console errors, 0 network failures, 0 horizontal scroll at 390px, fonts all Inter/Fraunces/Plex.**
- **AR i18n:** 7 new strings + 1 plural translated (`Cash on delivery`, `View all`, `items`, `Menu`, `Breadcrumb`, `Order status`, `WhatsApp`, order-count plural), `.mo` recompiled. AR pages verified free of untranslated English.
- **Money path** (`ui_audit/final/path/`, both languages): browse → filter (3 items) → PDP (1 OOS size disabled) → guest add-to-cart (toast + badge) → signup (**cart merged**) → checkout COD → success `/success/N/` → My Orders timeline → dashboard status change via AJAX (Pending→Confirmed) → WhatsApp URL valid (`wa.me/<digits>?text=…`). **Zero console errors.**
- **Tests:** `python manage.py test` → **71 passed**.
- **`grep -ri metronic`** on templates/static/config/apps → **clean** (settings `theme_static` entry + 500.html reference removed).
- **Budgets:** custom CSS **58.7KB** (≤60), custom JS (api+ui) **15.4KB**, all JS **25KB** (≤30).
- **`collectstatic --noinput`** clean; no Metronic assets collected.

### Deliberately deferred (POLISH, non-blocking)
- Dark mode remains out of scope (single theme perfected).
- Product-card placeholder art is the seeded neutral swatch (ASSUMPTIONS A24); real photography is a content task, not UI.
