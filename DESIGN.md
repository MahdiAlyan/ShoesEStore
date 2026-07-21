# ShoeStore Design System

Direction: **warm editorial light theme** — quiet chrome, product photography is
the hero. One accent used sparingly. Everything consumes tokens from
`static/css/tokens.css`; no magic hex values in component CSS. No dark mode in
MVP (future work: a `[data-theme="dark"]` token layer).

## Color

| Role | Token | Value |
|---|---|---|
| Page background | `--color-bg` | `#FAF7F2` warm paper |
| Surface (cards, panels) | `--color-surface` | `#FFFFFF` |
| Sunken surface (wells, table heads) | `--color-surface-sunken` | `#F3EEE7` |
| Dark surface (footer, dash sidebar) | `--color-espresso` | `#241D15` |
| Ink | `--color-ink` | `#211C15` |
| Muted ink | `--color-ink-muted` | `#6B6157` (5.5:1 on bg) |
| Hairline border | `--color-line` | `rgba(33,28,21,.14)` |
| **Accent — burnt sienna** | `--color-accent` | `#A8441F` (6:1 with white) |
| Accent hover | `--color-accent-hover` | `#8E3717` |
| Accent tint | `--color-accent-soft` | `#F6E7DE` |
| Success / Warning / Danger / Info | `--color-success` … | `#2E7D4F` / `#8A6410` / `#B03028` / `#3B6EA5` + `-soft` tints |

Rules: accent only on primary CTAs, active states, sale badges, and the brand
dot. Status colors only on status. All text pairs meet WCAG AA (≥4.5:1).

## Typography

- **Display:** Fraunces 600 (`--font-display`) — h1–h3, brand wordmark, big
  numbers. Letter-spacing −0.01em.
- **Text/UI:** Inter variable 100–900 (`--font-body`) — everything else.
  Weights in use: 400/500/600/700.
- **Arabic:** IBM Plex Sans Arabic 400/500/700 rides both stacks via
  `unicode-range`; Latin faces have no Arabic glyphs so fallthrough is
  automatic. `:root:lang(ar)` bumps line-heights (1.8 body).
- Fluid scale via `clamp()`: `--text-xs` 12px → `--text-display`
  36–64px. Prices and order tables use `.tnum` (tabular numerals).
- Self-hosted woff2 in `static/fonts/` (from Google Fonts static API),
  `font-display: swap`, two preloads per language in the base templates.

## Space, shape, depth, motion

- 8pt spacing scale `--space-1..9` (4→96px).
- Radii: 6 / 10 / 14 / 999px. Hairline 1px borders at low-alpha ink instead of
  boxy card outlines; shadows are soft and layered (`--shadow-sm/md/lg`).
- Motion: 150ms (`--dur-fast`) / 220ms (`--dur`) with ease-out
  `cubic-bezier(.22,.61,.36,1)`. Every animation dies under
  `prefers-reduced-motion`.
- Z-scale: sticky 30 < dropdown 40 < dialog 60 < toast 70.

## RTL

One stylesheet, CSS logical properties everywhere (`margin-inline-start`,
`inset-inline-end`, `text-align: start`, …). No separate RTL file. Physical
left/right appears only with a justifying comment (select chevron
background-position, drawer/skeleton transform directions).

## Components (components.css)

Buttons keep the template's existing class spellings (`.btn-primary`,
`.btn-light`, `.btn-light-danger`, `.btn-icon`, …) implemented on tokens —
44px hit targets (`.btn-sm` grows back to 44px on coarse pointers). Badges are
tinted pills; `.status-<STATUS>` classes are locked (dashboard.js regenerates
them). Toasts stack at the inline-end top corner with `role="status"`.
Dialogs use native `<dialog>` (`ShoeStore.confirm/alert` in ui.js). Dropdowns
are `[data-menu]` blocks. Skeleton shimmer: `.skeleton`.

## Voice

Short, confident, bilingual. One line of copy per empty state + one action.
Currency is always `$X.YY` (the `money` template filter / `.tnum`).
