# MKE PRODUCT-UI-00 — Visual Prototype (Light & Dark)

## Overview
This directory contains the standalone visual prototype for **Math Knowledge Engine (MKE)**, designed under milestone `PRODUCT-UI-00`.
It demonstrates an authoritative, uncluttered mathematical computing workspace inspired by the visual atmosphere and utility of WolframAlpha, without copying any Wolfram assets, trademarks, or proprietary code.

> **DEMO / MOCK DATA NOTICE**: This prototype contains no production frontend, backend solver, or API integration. All computation outputs, step-by-step solutions, and verification receipts are static or deterministic client-side mock representations for visual demonstration only.

---

## Deliverables
- [`DESIGN_TOKENS.md`](DESIGN_TOKENS.md): Design tokens for light and dark palettes, typography, spacing, elevation, and 4-column grid.
- [`index.html`](index.html): Semantic, zero-CDN markup featuring MKE branding, header theme selector, prominent search field with violet accent border, quick math symbol inserter, 4-column topic cards, multi-card result stack, and syntax guide.
- [`styles.css`](styles.css): Complete custom property styling for `[data-theme="light"]` and `[data-theme="dark"]`, responsive 4-column desktop to 1-column mobile layouts, keyboard focus rings, and reduced-motion support.
- [`app.js`](app.js): Pure vanilla JavaScript theme persistence (`localStorage` + `prefers-color-scheme`), screen routing, query mocks (`2*x + 3 = 7`, `-x^2 = 1`, `(-x)^2 = 1`, `x^0 = 1`, `0*x = 0`, `(x-1)/(x-1) = 1`, and syntax error demo `1/2x = 1`), and quick symbol inserters.
- [`screenshots/`](screenshots/): High-resolution captures verifying layouts:
  - `desktop-light.png` (1280x900)
  - `desktop-dark.png` (1280x900)
  - `mobile-light.png` (390x844)
  - `mobile-dark.png` (390x844)

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
- `?theme=light`: Force Light theme
- `?theme=dark`: Force Dark theme
- `?view=result`: Open directly with interactive result stack
- `?view=syntax`: Open directly to the syntax cheat sheet
