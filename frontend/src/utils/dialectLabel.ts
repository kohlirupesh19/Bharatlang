import type { TranslationDictionary } from '../i18n/translations';

/**
 * Localised dialect name for the backend's label ("Varhadi (Vidarbha)", "Standard Marathi").
 * Returns null for anything else, so raw backend strings are never shown to citizens.
 */
export function dialectLabel(raw: string | undefined | null, t: TranslationDictionary): string | null {
  const value = (raw ?? '').toLowerCase();
  if (value.includes('varhadi')) return t.dialects.varhadi;
  if (value.includes('standard')) return t.dialects.standard;
  return null;
}
