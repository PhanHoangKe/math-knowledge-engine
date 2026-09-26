# MKE PRODUCT-UI-00 — Design Tokens & Visual Atmosphere

This specification defines the authoritative design tokens and styling guidelines for the **Math Knowledge Engine (MKE)**, faithfully capturing the visual elegance, atmosphere, and clarity of **WolframAlpha** while preserving MKE's original identity.

---

## 1. Color Palette Tokens

### 1.1 Canvas & Surface
| Token | Light Theme | Dark Theme (Wolfram Charcoal) | Description |
|---|---|---|---|
| `--bg-canvas` | `#ffffff` | `#262626` | Main canvas background |
| `--bg-surface` | `#ffffff` | `#2e2e2e` | Base topic card surface |
| `--bg-surface-elevated` | `#ffffff` | `#363636` | Elevated cards & modals |
| `--bg-subtle` | `#f7f7f9` | `#333333` | Sub-toolbars & inputs |
| `--border-subtle` | `#e2e8f0` | `#3d3d3d` | Header & footer rules |
| `--border-card` | `#e5e7eb` | `#3d3d3d` | Card border |
| `--border-card-hover` | `#cbd5e1` | `#525252` | Card hover border |

### 1.2 Signature Accent & Interaction
| Token | Light Theme | Dark Theme | Purpose |
|---|---|---|---|
| `--border-accent` | `#8e6cd9` | `#9d7fe3` | Signature violet 2px search border |
| `--border-focus` | `#7a54cc` | `#bca4f5` | Focus ring boundary |
| `--compute-btn` | `#8e6cd9` | `#9d7fe3` | Violet capsule `=` compute button |
| `--compute-btn-hover` | `#7b55ca` | `#8b66da` | Compute button hover |
| `--accent-subtle` | `#f3f0fc` | `#3a2e54` | Active chip / pill background |

### 1.3 The 4 Column Topic Domain Colors (WolframAlpha Palette)
| Column | Light Color | Dark Color | Domain Representation |
|---|---|---|---|
| **Column 1 (Mathematics)** | `#8e6cd9` (Violet) | `#a78bfa` | Linear Algebra & Step Solutions |
| **Column 2 (Science & Field)** | `#059669` (Emerald) | `#34d399` | Rational Field Arithmetic \(\mathbb{Q}\) |
| **Column 3 (Society & Polynomials)** | `#e05638` (Terracotta) | `#fb7185` | Quadratics & Factorization |
| **Column 4 (Classroom & Documents)** | `#0284c7` (Sky Blue) | `#38bdf8` | Diagnostic Tutoring & PDF Ingestion |

---

## 2. Typography Hierarchy

### 2.1 Font Stacks
- **UI & System:** `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`
- **Hero Mottos & Taglines:** `"Charter", "Georgia", "Cambria", serif` (styled in italics, capturing Wolfram's expert tagline feel)
- **Mathematical Form:** `"Cambria Math", "Charter", "Georgia", serif`
- **AST & Formal Code:** `"Cascadia Code", "Consolas", monospace`

### 2.2 Scale & Weights
- **Hero Title:** `2.4rem`, weight `700`, tracking `-0.02em`
- **Hero Italic Subtitle:** `1.125rem`, weight `400`, italic, line-height `1.5`
- **Column Header:** `1.05rem`, weight `600`, colored with chevron `›`
- **Topic Card Title:** `0.875rem`, weight `500`, high legibility
- **Search Input:** `1.15rem`, weight `400`, monospace family

---

## 3. Component Architecture

### 3.1 Capsule Search Box
- **Shape:** Rounded lozenge (`border-radius: 20px`).
- **Border:** `2px solid var(--border-accent)` (vibrant violet).
- **Compute Button:** Integrated rounded square (`border-radius: 12px`, violet background) containing `=`.
- **Sub-toolbar:** Mode toggles on left (`Toán Chuẩn xác`, `Ký hiệu Tất định`), quick math keys on right (`*`, `x`, `^2`, `^0`, `/`, `=`, `( )`).

### 3.2 4-Column Topic Cards
- 4 balanced desktop columns transitioning to 2 columns on tablet and 1 column on mobile.
- Each card features a colored icon box (`34px × 34px`) with an authentic domain SVG icon on the left and the title on the right.
- The bottom card in each column is a dedicated `••• Xem thêm Chuyên đề »` card with a 3x3 dot matrix icon in that column's color.

### 3.3 Top-Right Settings Popover (Theme & Language)
- Clean gear/cog trigger icon in header.
- Floating popover modal containing:
  - Theme: Automatic, Light, Dark (with active checkmark)
  - Language: Tiếng Việt (Default), English (with active checkmark)

### 3.4 Architecture Flow Banner
- Flowchart above the footer:
  `MKE = Cú pháp AST Tường minh + Số học Hữu tỉ Q + Suy luận Ký hiệu R ➔ Nghiệm & Minh chứng Tất định`
