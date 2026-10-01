import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { PreferencesProvider, usePreferences } from '../state/preferences';

const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <PreferencesProvider>{children}</PreferencesProvider>
);

describe('User Preferences State & Priority', () => {
  it('defaults to Vietnamese language and auto theme', () => {
    const { result } = renderHook(() => usePreferences(), { wrapper });
    expect(result.current.language).toBe('vi');
    expect(result.current.theme).toBe('auto');
    expect(document.documentElement.getAttribute('lang')).toBe('vi');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('updates language and persists to localStorage', () => {
    const { result } = renderHook(() => usePreferences(), { wrapper });

    act(() => {
      result.current.setLanguage('en');
    });

    expect(result.current.language).toBe('en');
    expect(localStorage.getItem('mke_pref_lang')).toBe('en');
    expect(document.documentElement.getAttribute('lang')).toBe('en');
    expect(result.current.t('nav_home')).toBe('Home');
  });

  it('updates theme to light explicitly and reflects in document data-theme attribute', () => {
    const { result } = renderHook(() => usePreferences(), { wrapper });

    act(() => {
      result.current.setTheme('light');
    });

    expect(result.current.theme).toBe('light');
    expect(result.current.effectiveTheme).toBe('light');
    expect(localStorage.getItem('mke_pref_theme')).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('updates theme to dark explicitly and reflects in document data-theme attribute', () => {
    const { result } = renderHook(() => usePreferences(), { wrapper });

    act(() => {
      result.current.setTheme('dark');
    });

    expect(result.current.theme).toBe('dark');
    expect(result.current.effectiveTheme).toBe('dark');
    expect(localStorage.getItem('mke_pref_theme')).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('resolves auto theme to dark when system prefers-color-scheme is dark', () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('dark'),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { result } = renderHook(() => usePreferences(), { wrapper });
    expect(result.current.theme).toBe('auto');
    expect(result.current.effectiveTheme).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('responds dynamically to system preference changes when theme is auto', () => {
    let listener: ((e: MediaQueryListEvent) => void) | null = null;
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn((event: string, cb: (e: MediaQueryListEvent) => void) => {
        if (event === 'change') {
          listener = cb;
        }
      }),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { result } = renderHook(() => usePreferences(), { wrapper });
    expect(result.current.effectiveTheme).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    // System switches to dark mode
    act(() => {
      listener?.({ matches: true } as MediaQueryListEvent);
    });
    expect(result.current.effectiveTheme).toBe('dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');

    // System switches back to light mode
    act(() => {
      listener?.({ matches: false } as MediaQueryListEvent);
    });
    expect(result.current.effectiveTheme).toBe('light');
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('honors localStorage preferences over defaults', () => {
    localStorage.setItem('mke_pref_lang', 'en');
    localStorage.setItem('mke_pref_theme', 'dark');

    const { result } = renderHook(() => usePreferences(), { wrapper });
    expect(result.current.language).toBe('en');
    expect(result.current.theme).toBe('dark');
    expect(document.documentElement.getAttribute('lang')).toBe('en');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('honors valid URL parameters over localStorage preferences', () => {
    localStorage.setItem('mke_pref_lang', 'vi');
    localStorage.setItem('mke_pref_theme', 'light');

    window.history.replaceState({}, '', '/?lang=en&theme=dark');

    const { result } = renderHook(() => usePreferences(), { wrapper });
    expect(result.current.language).toBe('en');
    expect(result.current.theme).toBe('dark');
    expect(document.documentElement.getAttribute('lang')).toBe('en');
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });
});
