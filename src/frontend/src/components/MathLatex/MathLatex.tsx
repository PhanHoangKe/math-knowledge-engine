import React, { useEffect, useRef } from 'react';
import styles from './MathLatex.module.css';

export interface MathLatexProps {
  latex: string;
  displayMode?: boolean;
  className?: string;
}

/**
 * Strip outer inline or display math delimiters if present before passing to KaTeX render.
 */
function cleanLatexString(raw: string): string {
  if (!raw) return '';
  let trimmed = raw.trim();
  if (trimmed.startsWith('\\\\(') && trimmed.endsWith('\\\\)')) {
    trimmed = trimmed.slice(3, -3).trim();
  } else if (trimmed.startsWith('\\(') && trimmed.endsWith('\\)')) {
    trimmed = trimmed.slice(2, -2).trim();
  } else if (trimmed.startsWith('\\\\[') && trimmed.endsWith('\\\\]')) {
    trimmed = trimmed.slice(3, -3).trim();
  } else if (trimmed.startsWith('\\[') && trimmed.endsWith('\\]')) {
    trimmed = trimmed.slice(2, -2).trim();
  } else if (trimmed.startsWith('$$') && trimmed.endsWith('$$')) {
    trimmed = trimmed.slice(2, -2).trim();
  } else if (trimmed.startsWith('$') && trimmed.endsWith('$') && trimmed.length > 2) {
    trimmed = trimmed.slice(1, -1).trim();
  }
  return trimmed;
}

/**
 * Accessible, offline-capable, security-hardened KaTeX renderer component.
 * 
 * - throwOnError: false
 * - trust: false
 * - NO dangerouslySetInnerHTML
 * - Graceful fallback to text if window.katex is unavailable.
 */
export const MathLatex: React.FC<MathLatexProps> = ({
  latex,
  displayMode = false,
  className = '',
}) => {
  const containerRef = useRef<HTMLSpanElement>(null);
  const cleaned = cleanLatexString(latex);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    if (typeof window !== 'undefined' && window.katex && typeof window.katex.render === 'function') {
      try {
        window.katex.render(cleaned, el, {
          displayMode,
          throwOnError: false,
          trust: false,
        });
        return;
      } catch {
        // Fallback on any unexpected KaTeX error
      }
    }

    // Graceful fallback to text node (Zero dangerouslySetInnerHTML)
    el.textContent = cleaned;
  }, [cleaned, displayMode]);

  return (
    <span
      ref={containerRef}
      className={`${styles.mathContainer} ${displayMode ? styles.displayMath : styles.inlineMath} ${className}`}
      aria-label={cleaned}
    >
      {cleaned}
    </span>
  );
};
