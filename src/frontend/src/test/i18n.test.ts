import { describe, it, expect } from 'vitest';
import { vi } from '../i18n/vi';
import { en } from '../i18n/en';
import { getTranslation } from '../i18n';

describe('Bilingual I18N Foundation', () => {
  it('exposes 100% identical key structure across Vietnamese and English dictionaries', () => {
    const viKeys = Object.keys(vi).sort();
    const enKeys = Object.keys(en).sort();

    expect(viKeys).toEqual(enKeys);
    expect(viKeys.length).toBeGreaterThan(20);
  });

  it('contains non-empty string values for all keys in both languages', () => {
    for (const value of Object.values(vi)) {
      expect(typeof value).toBe('string');
      expect((value as string).trim().length).toBeGreaterThan(0);
    }

    for (const value of Object.values(en)) {
      expect(typeof value).toBe('string');
      expect((value as string).trim().length).toBeGreaterThan(0);
    }
  });

  it('resolves translations accurately through getTranslation() helper', () => {
    expect(getTranslation('vi', 'nav_home')).toBe('Trang chủ');
    expect(getTranslation('en', 'nav_home')).toBe('Home');
    expect(getTranslation('vi', 'empty_workspace_msg')).toBe('Nhập phương trình để bắt đầu phân tích.');
    expect(getTranslation('en', 'empty_workspace_msg')).toBe('Enter an equation to begin analysis.');
  });

  it('falls back to Vietnamese if an invalid language code is passed', () => {
    // @ts-expect-error test fallback for unknown language
    expect(getTranslation('fr', 'nav_home')).toBe('Trang chủ');
  });
});
