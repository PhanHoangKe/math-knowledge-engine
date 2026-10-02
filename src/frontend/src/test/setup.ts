import '@testing-library/jest-dom/vitest';
import { beforeEach, vi } from 'vitest';

export const createMatchMediaMock = () =>
  vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  document.documentElement.removeAttribute('lang');
  window.history.replaceState({}, '', '/');
  window.matchMedia = createMatchMediaMock() as any;
});
