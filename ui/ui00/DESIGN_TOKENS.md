# MKE PRODUCT-UI-00 Design Tokens & Visual Specification

**Milestone:** PRODUCT-UI-00 — Standalone Light/Dark Visual Prototype  
**Atmosphere Inspiration:** Refined mathematical atmosphere (WolframAlpha inspired, original MKE identity)  
**Status:** Visual Prototype Only (No Production Backend / Zero Network Requests)  
**Date:** September 2026  

---

## 1. Color Palette & Semantic Tokens

### Light Theme
- `--bg-canvas`: `#f8fafc` (Subtle cool off-white)
- `--bg-surface`: `#ffffff` (Pure white card surfaces)
- `--bg-surface-elevated`: `#ffffff`
- `--bg-subtle`: `#f1f5f9` (Input secondary backgrounds, chip fills)
- `--border-subtle`: `#e2e8f0` (Delicate boundary lines)
- `--border-accent`: `#7c3aed` (Thin signature violet input border)
- `--text-primary`: `#0f172a` (Deep slate heading & body)
- `--text-secondary`: `#475569` (Muted explanation labels)
- `--text-muted`: `#94a3b8` (Timestamps, metadata, hints)
- `--accent-primary`: `#7c3aed` (Violet brand color)
- `--accent-hover`: `#6d28d9`
- `--accent-surface`: `#ede9fe` (Violet tint for badges/highlights)
- `--compute-btn`: `#ea580c` (Warm amber/orange compute accent)
- `--compute-btn-hover`: `#c2410c`
- `--status-demo`: `#b45309` (Amber warning for demo/mock labels)
- `--status-demo-bg`: `#fef3c7`
- `--status-planned`: `#475569`
- `--status-planned-bg`: `#f1f5f9`

### Dark Theme
- `--bg-canvas`: `#0b0f19` (Deep obsidian background)
- `--bg-surface`: `#162032` (Charcoal surface with cool blue tint)
- `--bg-surface-elevated`: `#1e293b`
- `--bg-subtle`: `#1e293b`
- `--border-subtle`: `#2a384e` (Restrained dark border)
- `--border-accent`: `#a78bfa` (Luminous violet input border)
- `--text-primary`: `#f8fafc` (Crisp off-white)
- `--text-secondary`: `#94a3b8` (Medium slate)
- `--text-muted`: `#64748b` (Low-contrast metadata)
- `--accent-primary`: `#8b5cf6` (Electric violet)
- `--accent-hover`: `#a78bfa`
- `--accent-surface`: `#2e1065`
- `--compute-btn`: `#f97316` (Vibrant amber/orange compute button)
- `--compute-btn-hover`: `#ea580c`
- `--status-demo`: `#fbbf24`
- `--status-demo-bg`: `#451a03`
- `--status-planned`: `#94a3b8`
- `--status-planned-bg`: `#1e293b`

### Topic Category Accents (Harmonized across both themes)
- **Algebra & Equations:** `#ea580c` (Orange / Terracotta)
- **Arithmetic & Rational Field:** `#059669` (Emerald / Sage)
- **Calculus & Limits (Planned):** `#2563eb` (Royal Blue)
- **Discrete & Logic (Planned):** `#7c3aed` (Violet / Amethyst)

---

## 2. Typography & Type Hierarchy

MKE uses a zero-external-dependency system font stack combining classical mathematical serif authority with modern UI clarity:

- **Heading Font Stack (Serif Math):**  
  `"Cambria Math", "Charter", "Georgia", "Times New Roman", serif`
- **UI & Body Font Stack (Clean Sans):**  
  `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Code & Mathematical Literal Stack (Monospace):**  
  `"Cascadia Code", "Consolas", "Courier New", monospace`

### Scale
- **Display Hero:** `2.5rem` (40px) / `font-weight: 600` / `letter-spacing: -0.02em`
- **Section Heading:** `1.5rem` (24px) / `font-weight: 600`
- **Sub-heading / Card Title:** `1.125rem` (18px) / `font-weight: 600`
- **Body Regular:** `0.9375rem` (15px) / `line-height: 1.6`
- **Small / Metadata:** `0.8125rem` (13px)
- **Mathematical Formula:** `1.25rem` (20px) / `font-family: serif & monospace`

---

## 3. Elevation, Spacing & Layout Grid

- **Search Bar Elevation:** `0 4px 20px -2px rgba(124, 58, 237, 0.08)` (Light) / `0 4px 24px -2px rgba(0, 0, 0, 0.4)` (Dark)
- **Card Radius:** `8px` (Clean, rectangular, mathematical precision)
- **Desktop Grid:** 4-column balanced card grid (`repeat(4, minmax(0, 1fr))`), `gap: 1.5rem`
- **Mobile Grid:** Single-column layout (`repeat(1, minmax(0, 1fr))`) below `768px` breakpoint

---

## 4. Accessibility & Interaction Contracts

- **Keyboard Focus:** High-visibility outline: `2px solid var(--accent-primary)`, `outline-offset: 2px`.
- **Reduced Motion:** Fully conforms to `prefers-reduced-motion: reduce` by disabling transitions and animations.
- **Theme Persistence:** Stored in `localStorage` under key `mke_visual_theme_preference`.
- **Contrast Ratios:** All primary text-to-background combinations exceed WCAG 2.1 AA (4.5:1) and AAA (7:1).
