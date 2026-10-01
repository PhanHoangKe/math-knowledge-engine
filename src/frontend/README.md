# MKE Production Frontend Shell & OpenAPI Type Pipeline (Stage S2-03)

This directory contains the production React + TypeScript + Vite frontend foundation for the **Math Knowledge Engine (MKE)**, preserving the visual identity and atmosphere established in `ui/ui00/` while connecting to backend contracts via an automated OpenAPI type generation pipeline.

---

## 1. Prerequisites & Toolchain

- **Node.js:** `>= 20.0.0` (Tested on `v22.17.0`)
- **npm:** `>= 10.0.0` (Tested on `10.9.2`)
- **Python:** `>= 3.10.0` (for backend FastAPI server and OpenAPI schema export)

---

## 2. Quickstart & Installation

```bash
# From repository root
cd src/frontend

# Install exact locked dependencies
npm ci
```

---

## 3. Development Workflow

### Starting the FastAPI Backend (Port 8000)
```bash
# In backend terminal from repository root
uvicorn mke_product.transport.app:app --host 127.0.0.1 --port 8000 --reload
```

### Starting the Vite Development Server (Port 5173)
```bash
# In frontend terminal from src/frontend
npm run dev
```

### Vite Development Proxy
Vite is configured with a development proxy forwarding `/api/*` requests to `http://127.0.0.1:8000`. Frontend code uses relative URLs (`/api/v1/algebra/solve`, `/api/v1/health`) to maintain same-origin semantics without requiring permissive backend CORS.

---

## 4. OpenAPI Export & TypeScript Type Pipeline

The frontend types are strictly generated from the Python FastAPI application without hand-authored duplicate schemas:

```bash
# 1. Export OpenAPI JSON schema & generate TypeScript types
npm run generate:api

# 2. Check for schema / type drift against current FastAPI app
npm run check:api
```

- **OpenAPI Schema:** `src/frontend/openapi/mke.openapi.json`
- **Generated Types:** `src/frontend/src/types/api.generated.ts`
- **Frontend Convenience Aliases:** `src/frontend/src/api/contract.ts`

---

## 5. Build, Typecheck, and Test Commands

```bash
# Run strict TypeScript check
npm run typecheck

# Run Vitest unit tests in jsdom environment
npm run test

# Build production bundle for static hosting
npm run build
```

---

## 6. Architecture & Features

### Preserved Visual Identity (UI00)
- Preserves all design tokens from `ui/ui00/DESIGN_TOKENS.md`: Canvas, Surfaces, Accents, 4 Topic Domain Colors (Violet, Emerald, Terracotta, Sky Blue), and Typography Stacks.
- Supports **Light**, **Dark (Charcoal)**, and **Auto (System `prefers-color-scheme`)** themes.

### Bilingual Localization (i18n)
- Default language: **Vietnamese (`vi`)**; fully supported: **English (`en`)**.
- 100% key parity enforced at compile-time and through automated unit tests.
- Preference priority: **Valid URL parameter (`?lang=vi|en&theme=light|dark|auto`)** ➔ **Persisted localStorage** ➔ **Default (`vi` / `auto`)**.

### Offline KaTeX Mathematical Typesetting
- Vendored KaTeX assets are copied byte-for-byte from `ui/ui00/vendor/katex/` to `public/vendor/katex/` for self-contained, offline operation with zero CDN dependencies.

### Production Authority & Scope Boundaries
- **Stage S2-03 Scope:** Frontend Shell, OpenAPI Type Pipeline, Bilingual UI, Theme Provider, and Accessible Empty Workspace.
- **Solving Engine Integration:** Intentionally deferred to **Stage S2-04**. The S2-03 shell contains **zero** mock roots, fake certificates, or client-side solving derivations. All mathematical solving authority remains strictly in the backend application service.
