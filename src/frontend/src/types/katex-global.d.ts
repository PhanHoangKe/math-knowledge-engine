/**
 * Global KaTeX Type Definitions for MKE Frontend.
 */

export interface KaTeXOptions {
  displayMode?: boolean;
  throwOnError?: boolean;
  errorColor?: string;
  macros?: Record<string, string>;
  colorIsTextColor?: boolean;
  maxSize?: number;
  maxExpand?: number;
  allowedProtocols?: string[];
  strict?: boolean | string | ((errorCode: string, errorMsg: string, token?: unknown) => string | boolean);
  trust?: boolean | ((context: { command: string; url: string; protocol: string }) => boolean);
  output?: 'html' | 'mathml' | 'htmlAndMathml';
  leqno?: boolean;
  fleqn?: boolean;
}

export interface KaTeXGlobal {
  render(tex: string, element: HTMLElement, options?: KaTeXOptions): void;
  renderToString(tex: string, options?: KaTeXOptions): string;
}

declare global {
  interface Window {
    katex?: KaTeXGlobal;
  }
}

export {};
