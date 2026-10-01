#!/usr/bin/env node
/**
 * MKE MVP V1 — API Drift Checker.
 * 
 * Verifies that committed openapi/mke.openapi.json and src/types/api.generated.ts
 * are 100% up-to-date with the current FastAPI application.
 * 
 * Cross-platform (Windows / Linux / macOS) Node.js implementation.
 */

import { execSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_ROOT = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(FRONTEND_ROOT, '..', '..');

const COMMITTED_OPENAPI = path.join(FRONTEND_ROOT, 'openapi', 'mke.openapi.json');
const COMMITTED_TS = path.join(FRONTEND_ROOT, 'src', 'types', 'api.generated.ts');
const TEMP_DIR = path.join(FRONTEND_ROOT, '.drift-temp');

function normalizeLineEndings(str) {
  return str.replace(/\r\n/g, '\n').trim();
}

function cleanTemp() {
  if (fs.existsSync(TEMP_DIR)) {
    fs.rmSync(TEMP_DIR, { recursive: true, force: true });
  }
}

async function main() {
  console.log('🔍 Checking OpenAPI and TypeScript type drift...');
  cleanTemp();
  fs.mkdirSync(TEMP_DIR, { recursive: true });

  const tempOpenAPI = path.join(TEMP_DIR, 'mke.openapi.json');
  const tempTS = path.join(TEMP_DIR, 'api.generated.ts');

  try {
    // 1. Export fresh OpenAPI JSON schema from Python FastAPI app
    const exportScript = path.join(REPO_ROOT, 'scripts', 'export_openapi.py');
    execSync(`python "${exportScript}" --output "${tempOpenAPI}"`, {
      cwd: REPO_ROOT,
      stdio: 'pipe',
    });

    // 2. Generate fresh TypeScript interfaces using openapi-typescript
    execSync(`npx openapi-typescript "${tempOpenAPI}" -o "${tempTS}"`, {
      cwd: FRONTEND_ROOT,
      stdio: 'pipe',
    });

    // 3. Verify committed OpenAPI JSON against fresh export
    if (!fs.existsSync(COMMITTED_OPENAPI)) {
      console.error(`❌ Missing committed OpenAPI file: ${COMMITTED_OPENAPI}`);
      process.exit(1);
    }
    const committedOpenApiContent = normalizeLineEndings(fs.readFileSync(COMMITTED_OPENAPI, 'utf-8'));
    const freshOpenApiContent = normalizeLineEndings(fs.readFileSync(tempOpenAPI, 'utf-8'));

    if (committedOpenApiContent !== freshOpenApiContent) {
      console.error('❌ API Drift Detected: openapi/mke.openapi.json is stale relative to FastAPI.');
      console.error('👉 Run "npm run generate:api" and commit the updated schema.');
      process.exit(1);
    }

    // 4. Verify committed TypeScript types against fresh generation
    if (!fs.existsSync(COMMITTED_TS)) {
      console.error(`❌ Missing committed TypeScript definitions: ${COMMITTED_TS}`);
      process.exit(1);
    }
    const committedTsContent = normalizeLineEndings(fs.readFileSync(COMMITTED_TS, 'utf-8'));
    const freshTsContent = normalizeLineEndings(fs.readFileSync(tempTS, 'utf-8'));

    if (committedTsContent !== freshTsContent) {
      console.error('❌ Type Drift Detected: src/types/api.generated.ts is stale relative to OpenAPI.');
      console.error('👉 Run "npm run generate:api" and commit the updated types.');
      process.exit(1);
    }

    console.log('✅ OpenAPI schema and generated TypeScript types are 100% in sync. Zero drift.');
  } finally {
    cleanTemp();
  }
}

main().catch((err) => {
  console.error('❌ Drift check failed with error:', err);
  cleanTemp();
  process.exit(1);
});
