import { describe, it, expect } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';

/**
 * MKE MVP V1 — Frontend Mathematical Authority Static Purity Audit.
 * 
 * Verifies that production frontend source files (excluding tests & generated types)
 * contain ZERO client-side mathematical solving logic, CAS formulas, or synthetic certificates.
 */

function getProductionSourceFiles(dir: string): string[] {
  let results: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'test' || entry.name === 'types' || entry.name === 'node_modules') {
        continue;
      }
      results = results.concat(getProductionSourceFiles(fullPath));
    } else if (entry.isFile() && (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx'))) {
      results.push(fullPath);
    }
  }
  return results;
}

describe('Frontend Mathematical Authority Static Purity Audit (Section 36)', () => {
  const srcRoot = path.resolve(__dirname, '..');
  const prodFiles = getProductionSourceFiles(srcRoot);

  it('scans all production frontend files and asserts zero client-side mathematical derivations', () => {
    expect(prodFiles.length).toBeGreaterThan(0);

    const forbiddenPatterns = [
      { name: 'Discriminant Formula', pattern: /b\s*\*\s*b\s*-\s*4\s*\*\s*a\s*\*\s*c/i },
      { name: 'Square Root Discriminant', pattern: /Math\.sqrt\s*\(\s*(?:delta|discriminant)/i },
      { name: 'Quadratic Root Calculation', pattern: /\(-b\s*[+-]\s*Math\.sqrt/i },
      { name: 'Polynomial Degree Extraction Regex', pattern: /(?:\.match|\.exec|RegExp)\s*\(\s*\/?[^/]*x\s*\^\s*\d+/i },
      { name: 'Client SHA-256 Hash Implementation', pattern: /crypto\.subtle\.digest|createHash\s*\(\s*['"]sha256/i },
      { name: 'Certificate Fabrication', pattern: /certificate_id\s*:\s*[`'"]cert_/i },
      { name: 'SymPy or CAS execution', pattern: /sympy|mathjs|nerdamer|algebrite/i },
    ];

    for (const file of prodFiles) {
      const content = fs.readFileSync(file, 'utf-8');

      for (const { name, pattern } of forbiddenPatterns) {
        const matches = pattern.test(content);
        if (matches) {
          throw new Error(
            `Mathematical Authority Purity Violation: Pattern "${name}" found in production source file ${file}`
          );
        }
      }
    }
  });
});
