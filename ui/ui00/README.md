# MKE PRODUCT-UI-00 — Visual Prototype (Bilingual Vietnamese & English)

## Overview
This directory contains the standalone visual prototype for **Math Knowledge Engine (MKE)**, under milestone `PRODUCT-UI-00-R1`.
It demonstrates an authoritative, uncluttered mathematical computing workspace inspired by the visual atmosphere and utility of WolframAlpha, without copying any Wolfram assets, trademarks, or proprietary code.

- **Bilingual Interface:** Default language is **Vietnamese (`vi`)**, with full support for **English (`en`)**. Switching occurs instantly without page reloads.
- **Themes:** Supports **Light**, **Dark**, and **Auto (System)** themes, operating completely independently of language preference.
- **Dependency-Free:** Pure, self-contained HTML5, CSS3, and vanilla JavaScript. Zero external CDNs, zero npm packages, zero network calls.

> **DEMO / MOCK DATA NOTICE**: This prototype contains no production frontend, backend solver, or API integration. All computation outputs, step-by-step solutions, and verification receipts are static or deterministic client-side mock representations for visual demonstration only. Misleading real-verification impressions and placeholder cryptographic hashes have been removed.

---

## Architectural & Technology Decisions
- **Current Prototype (UI-00):** Dependency-free HTML, CSS, and JavaScript.
- **Future Production Frontend:** React + TypeScript + Vite with CSS Modules and CSS Variables.
- **Backend Mathematical Kernel:** Python.
- **Backend API:** FastAPI (only when separately authorized).
- **Code Identifiers:** Strictly English throughout all source code; all user-facing strings originate exclusively from localization resource dictionaries.
- **UI-00 Scope:** UI-00 is NOT migrated to React at this stage.

---

## Deliverables
- [`DESIGN_TOKENS.md`](DESIGN_TOKENS.md): Design tokens for light and dark palettes, typography, spacing, elevation, and 4-column grid.
- [`index.html`](index.html): Semantic, zero-CDN markup featuring MKE branding, language selector (Vietnamese / English), theme selector (Auto / Light / Dark), prominent search field with violet accent border, quick math symbol toolbar, 4-column topic cards, multi-card result stack, and syntax guide.
- [`styles.css`](styles.css): Complete custom property styling for `[data-theme="light"]` and `[data-theme="dark"]`, responsive 4-column desktop to 1-column mobile layouts, keyboard focus rings, and reduced-motion support.
- [`app.js`](app.js): Structured `I18N` dictionaries (`vi` default, `en` supported), fallback mechanism, safe DOM APIs (`textContent`, `setAttribute`), `localStorage` persistence, URL query parameter synchronization (`?lang=vi|en`, `?theme=light|dark`), and dynamic fixture re-rendering.
- [`screenshots/`](screenshots/): High-resolution captures verifying layouts:
  - `desktop-light.png` (1280x900, Vietnamese, Light theme)
  - `desktop-dark.png` (1280x900, Vietnamese, Dark theme)
  - `mobile-light.png` (390x844, Vietnamese, Light theme)
  - `mobile-dark.png` (390x844, Vietnamese, Dark theme)

---

## Local Run Instructions
No build step, package manager, or network connection is required.

### Method 1: Local HTTP Server (Recommended)
From repository root:
```bash
python -m http.server -d ui/ui00 8080
```
Open your browser to:
`http://localhost:8080`

### Method 2: Direct File Open
Open `ui/ui00/index.html` directly in any modern desktop or mobile browser (Chrome, Firefox, Safari, Edge):
```bash
# Windows
start ui/ui00/index.html
```

### URL Query Parameters
- `?lang=vi`: Force Vietnamese interface (Default)
- `?lang=en`: Force English interface
- `?theme=light`: Force Light theme
- `?theme=dark`: Force Dark theme
- `?theme=auto`: Follow system preference
- `?view=result`: Open directly with interactive result stack
- `?view=syntax`: Open directly to the syntax cheat sheet
