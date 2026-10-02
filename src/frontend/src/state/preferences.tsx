import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';
import { getTranslation, type Language, type TranslationKey } from '../i18n';

export type Theme = 'auto' | 'light' | 'dark';

export interface PreferencesContextValue {
  language: Language;
  theme: Theme;
  effectiveTheme: 'light' | 'dark';
  setLanguage: (lang: Language) => void;
  setTheme: (theme: Theme) => void;
  t: (key: TranslationKey) => string;
}

const STORAGE_KEY_LANG = 'mke_pref_lang';
const STORAGE_KEY_THEME = 'mke_pref_theme';

function getInitialLanguage(): Language {
  if (typeof window !== 'undefined' && window.location) {
    const params = new URLSearchParams(window.location.search);
    const langParam = params.get('lang');
    if (langParam === 'vi' || langParam === 'en') {
      return langParam;
    }
  }

  if (typeof window !== 'undefined' && window.localStorage) {
    const saved = localStorage.getItem(STORAGE_KEY_LANG);
    if (saved === 'vi' || saved === 'en') {
      return saved;
    }
  }

  return 'vi';
}

function getInitialTheme(): Theme {
  if (typeof window !== 'undefined' && window.location) {
    const params = new URLSearchParams(window.location.search);
    const themeParam = params.get('theme');
    if (themeParam === 'auto' || themeParam === 'light' || themeParam === 'dark') {
      return themeParam;
    }
  }

  if (typeof window !== 'undefined' && window.localStorage) {
    const saved = localStorage.getItem(STORAGE_KEY_THEME);
    if (saved === 'auto' || saved === 'light' || saved === 'dark') {
      return saved;
    }
  }

  return 'auto';
}

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    const res = window.matchMedia('(prefers-color-scheme: dark)');
    return res && res.matches ? 'dark' : 'light';
  }
  return 'light';
}

const PreferencesContext = createContext<PreferencesContextValue | null>(null);

export interface PreferencesProviderProps {
  children: React.ReactNode;
  initialLanguage?: Language;
  initialTheme?: Theme;
}

export const PreferencesProvider: React.FC<PreferencesProviderProps> = ({
  children,
  initialLanguage,
  initialTheme,
}) => {
  const [language, setLanguageState] = useState<Language>(() => initialLanguage ?? getInitialLanguage());
  const [theme, setThemeState] = useState<Theme>(() => initialTheme ?? getInitialTheme());
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark'>(() => getSystemTheme());

  // Listen to system prefers-color-scheme changes when theme is auto
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    if (!mediaQuery) return;

    const handler = (e: MediaQueryListEvent) => {
      setSystemTheme(e && e.matches ? 'dark' : 'light');
    };

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler);
      return () => mediaQuery.removeEventListener('change', handler);
    }
  }, []);

  const effectiveTheme: 'light' | 'dark' = theme === 'auto' ? systemTheme : theme;

  // Apply theme & language to DOM document element
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', effectiveTheme);
      document.documentElement.setAttribute('lang', language);
    }
  }, [effectiveTheme, language]);

  const setLanguage = useCallback((newLang: Language) => {
    setLanguageState(newLang);
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem(STORAGE_KEY_LANG, newLang);
    }
  }, []);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem(STORAGE_KEY_THEME, newTheme);
    }
  }, []);

  const t = useCallback((key: TranslationKey) => {
    return getTranslation(language, key);
  }, [language]);

  const value = useMemo(
    () => ({
      language,
      theme,
      effectiveTheme,
      setLanguage,
      setTheme,
      t,
    }),
    [language, theme, effectiveTheme, setLanguage, setTheme, t]
  );

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  );
};

export function usePreferences(): PreferencesContextValue {
  const ctx = useContext(PreferencesContext);
  if (!ctx) {
    throw new Error('usePreferences must be used within a PreferencesProvider');
  }
  return ctx;
}
