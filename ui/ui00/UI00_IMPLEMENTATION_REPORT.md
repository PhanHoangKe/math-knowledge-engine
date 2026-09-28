# MKE PRODUCT-UI-00 — Visual Design & WolframAlpha Fidelity Report

**Milestone:** PRODUCT-UI-00 (Visual Prototype Polish & WolframAlpha Atmospheric Alignment)  
**Branch:** `design/ui00-light-dark`  
**Base Commit:** `9a4b031e9f60ad1df8438eed0a7d5fef14a3c4f5`  
**Scope:** Pure visual & interaction polish in native HTML5/CSS3/JavaScript. Zero backend/API dependencies, zero external CDNs.

---

## 1. Visual Alignment with WolframAlpha
Following user review and direct screenshot reference from [wolframalpha.com](https://www.wolframalpha.com/), the UI prototype was elevated across colors, typography, iconography, and layout structure:

### 1.1 Colors & Theming
- **Dark Theme (Authentic Charcoal):** Switched from navy blue to WolframAlpha's warm charcoal (`#262626` background, `#2e2e2e` surface cards, `#3d3d3d` borders) providing optimal mathematical contrast and reduced eye fatigue.
- **Light Theme (Crisp Clean):** Pure `#ffffff` canvas with clean `#e5e7eb` card borders and soft hover elevations.
- **Signature Violet Accent:** `#8e6cd9` (Light) and `#9d7fe3` (Dark) applied as a 2px border around the prominent search capsule, with glowing focus rings.
- **4-Column Domain Palette:**
  - Column 1 (Mathematics / Algebra): Violet (`#8e6cd9` / `#a78bfa`)
  - Column 2 (Rational Field / Science): Emerald (`#059669` / `#34d399`)
  - Column 3 (Quadratics / Society): Terracotta Coral (`#e05638` / `#fb7185`)
  - Column 4 (Classroom / Everyday Life): Sky Blue (`#0284c7` / `#38bdf8`)

### 1.2 Search Capsule & Controls
- **Capsule Lozenge Shape:** Smooth `border-radius: 20px` with 2px violet border.
- **Violet Equals Button:** Right-aligned compute button with rounded corners (`border-radius: 12px`, purple background) containing the iconic `=` symbol.
- **Sub-search Toolbar:** Mode indicators (`Toán Chuẩn xác`, `Ký hiệu Tất định`) and quick math buttons (`*`, `x`, `^2`, `^0`, `/`, `=`, `( )`).

### 1.3 Topic Grid & Iconography
- **4 Balanced Columns:** Column headers colored according to their domain with chevrons (`Toán học & Đại số ›`, `Trường Số Hữu tỉ ›`, etc.).
- **Compact Tile Layout:** Each card contains a dedicated colored icon box (`34px × 34px`) featuring authentic mathematical line icons (checklist, linear formula, fraction, Euclidean GCD, parabola, discriminant Delta, tutoring tree, OCR document).
- **More Topics Card:** Bottom card in every column formatted as `••• Xem thêm Chuyên đề »` with an authentic 3x3 dot matrix SVG icon in that column's color.

### 1.4 Top-Right Settings Popover (Theme & Language)
- Circular gear button in the header triggers a floating popover card matching Wolfram's settings modal:
  - **Theme Section:** Automatic, Light, Dark with active checkmarks.
  - **Language Section:** Tiếng Việt (Default), English with active checkmarks.
- Fully interactive with click-outside dismiss and keyboard accessibility.

### 1.5 Architecture Formula Flow Banner
- Elegant flow banner above footer:
  `MKE = Cú pháp AST Tường minh + Số học Hữu tỉ Q + Suy luận Ký hiệu R ➔ Nghiệm & Minh chứng Tất định`

---

## 2. Verification Results
- **Automated Bilingual Tests (`test_ui00_i18n.py`):** 7/7 PASSED.
- **Live Local Server:** Running on port `8088` (Status 200).
- **Updated Screenshots:**
  - `desktop-light.png`: 101,618 bytes (1280x900, Light theme)
  - `desktop-dark.png`: 101,369 bytes (1280x900, Charcoal Dark theme)
  - `mobile-light.png`: 49,663 bytes (390x844, Mobile Light)
  - `mobile-dark.png`: 50,028 bytes (390x844, Mobile Dark)
