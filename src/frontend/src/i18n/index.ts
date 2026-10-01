/**
 * MKE MVP V1 — I18N Aggregator & Translation Hook.
 */

import { vi, type TranslationKey, type Translations } from './vi';
import { en } from './en';

export type Language = 'vi' | 'en';

export const dictionaries: Record<Language, Translations> = {
  vi,
  en,
};

export function getTranslation(lang: Language, key: TranslationKey): string {
  const dict = dictionaries[lang] ?? dictionaries.vi;
  return dict[key] ?? dictionaries.vi[key] ?? key;
}

export type { TranslationKey, Translations };
