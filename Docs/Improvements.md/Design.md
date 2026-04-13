# Design System Style Guide

This document is the agreed visual identity for the Zomato-inspired restaurant recommender UI. Apply it to the web frontend and any future design work.

**Reference:** Design system style guide screenshot (April 2026). If you keep a copy in-repo, place it beside this file, e.g. `Docs/Improvements.md/design-system-reference.png`.

---

## 1. Color palette

Use four main categories. Each has a **primary hex** and a **tonal scale** (dark → light) for states, borders, and surfaces.

| Role | Primary | Usage |
|------|---------|--------|
| **Primary** | `#E23744` | Brand, key CTAs, emphasis |
| **Secondary** | `#2D2D2D` | Body text, strong neutrals, inverted surfaces |
| **Tertiary** | `#008881` | Accents, secondary actions, supportive highlights |
| **Neutral** | `#F8F8F8` | Page background, card shells, subtle fills |

**Implementation notes**

- Build lighter/darker steps from each primary token for hover, disabled, and borders (tonal scale as in the reference).
- Keep sufficient contrast for text on primary and inverted buttons (white on `#E23744` / `#2D2D2D`).

---

## 2. Typography

| Role | Font | Notes |
|------|------|--------|
| **Headline** | **Epilogue** | Bold weight for titles and major headings |
| **Body** | **Plus Jakarta Sans** | Main paragraph and UI copy |
| **Label** | **Plus Jakarta Sans** | Form labels, captions, metadata (adjust size/weight vs body) |

Load fonts via Google Fonts or self-hosted equivalents; fall back to system sans-serif if needed.

---

## 3. Buttons

Rounded corners approximately **4px–8px** border-radius.

| Variant | Style |
|---------|--------|
| **Primary** | Solid `#E23744` background, **white** text |
| **Secondary** | Light grey background, **dark grey** text |
| **Inverted** | Solid `#2D2D2D` background, **white** text |
| **Outlined** | White (or neutral) background, **thin `#E23744` border**, **red** text |

---

## 4. Core UI components

### Search bar

- Rounded input, **light grey** fill.
- **Subtle red-tinted border** (aligned with primary).
- **Magnifying glass** icon on the **left**, placeholder e.g. “Search”.

### Navigation / action bar

- **Pill-shaped** light grey container.
- Icons: e.g. **home** (primary red circle + white icon), **search**, **profile**.

### Progress / dividers

- Horizontal bars may use **primary red**, **secondary charcoal**, and **tertiary teal** for section separation or step indicators.

### Icon buttons

- **Teal** square: white **edit/pencil** icon.
- **Red** rectangular: white pencil + **“Label”** text (pattern for icon + label actions).
- Small **circular** actions in **red**, **charcoal**, and **teal** for tools (e.g. magic wand, blocks, tag, delete)—use consistently for destructive vs neutral vs accent.

---

## 5. Layout and containers

- **Page background:** light grey (aligned with neutral family, e.g. `#F8F8F8` or scale step).
- **Cards / panels:** rounded corners, **slightly lighter** than canvas for modular sections.
- Maintain consistent **spacing**, **radius**, and **shadow** (if any) across Home, History, and Metrics.

---

## 6. Adoption checklist (frontend)

- [ ] Import **Epilogue** + **Plus Jakarta Sans**
- [ ] Map CSS variables: `--color-primary`, `--color-secondary`, `--color-tertiary`, `--color-neutral`
- [ ] Refactor buttons to four variants above
- [ ] Align inputs/search with border and radius rules
- [ ] Apply card + page background rules to existing panels

---

*Last updated from design system reference — April 2026.*
