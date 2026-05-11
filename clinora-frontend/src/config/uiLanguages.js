/**
 * Supported UI locales (must match i18n resources + translation files).
 * `native` is shown in the language menu so each name is recognizable globally.
 */
export const UI_LANGUAGES = [
  { code: "en", label: "EN", native: "English" },
  { code: "zh", label: "中", native: "中文" },
  { code: "ja", label: "日", native: "日本語" },
  { code: "es", label: "ES", native: "Español" },
  { code: "fr", label: "FR", native: "Français" },
  { code: "de", label: "DE", native: "Deutsch" },
  { code: "pt", label: "PT", native: "Português" },
  { code: "ru", label: "RU", native: "Русский" },
  { code: "ar", label: "AR", native: "العربية" },
  { code: "hi", label: "HI", native: "हिन्दी" },
  { code: "ko", label: "KO", native: "한국어" },
  { code: "it", label: "IT", native: "Italiano" },
];

export const UI_LANGUAGE_CODES = UI_LANGUAGES.map((l) => l.code);

/** BCP-47 tags for speech / audio analysis (backend query param). */
export const SPEECH_LOCALES = [
  { code: "en-US", label: "EN" },
  { code: "zh-CN", label: "中" },
  { code: "ja-JP", label: "日" },
  { code: "es-ES", label: "ES" },
  { code: "fr-FR", label: "FR" },
  { code: "de-DE", label: "DE" },
  { code: "pt-BR", label: "PT" },
  { code: "ru-RU", label: "RU" },
  { code: "ar-SA", label: "AR" },
  { code: "hi-IN", label: "HI" },
  { code: "ko-KR", label: "KO" },
  { code: "it-IT", label: "IT" },
];
