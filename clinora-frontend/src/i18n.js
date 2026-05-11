import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en/translation.json";
import zh from "./locales/zh/translation.json";
import ja from "./locales/ja/translation.json";
import es from "./locales/es/translation.json";
import fr from "./locales/fr/translation.json";
import de from "./locales/de/translation.json";
import pt from "./locales/pt/translation.json";
import ru from "./locales/ru/translation.json";
import ar from "./locales/ar/translation.json";
import hi from "./locales/hi/translation.json";
import ko from "./locales/ko/translation.json";
import it from "./locales/it/translation.json";
import { UI_LANGUAGE_CODES } from "./config/uiLanguages";

function normalizeStoredLanguage() {
  if (typeof localStorage === "undefined") return "en";
  const raw = localStorage.getItem("clinora_lang");
  const base = raw?.split("-")[0];
  const valid = base && UI_LANGUAGE_CODES.includes(base) ? base : "en";
  if (raw && valid !== raw) localStorage.setItem("clinora_lang", valid);
  return valid;
}

const initialLanguage = normalizeStoredLanguage();

function applyDocumentLanguageAttributes(lng) {
  if (typeof document === "undefined") return;
  const resolved = lng || "en";
  const base = resolved.split("-")[0];
  document.documentElement.lang = resolved;
  document.documentElement.dir = base === "ar" ? "rtl" : "ltr";
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    zh: { translation: zh },
    ja: { translation: ja },
    es: { translation: es },
    fr: { translation: fr },
    de: { translation: de },
    pt: { translation: pt },
    ru: { translation: ru },
    ar: { translation: ar },
    hi: { translation: hi },
    ko: { translation: ko },
    it: { translation: it },
  },
  lng: initialLanguage,
  fallbackLng: "en",
  supportedLngs: UI_LANGUAGE_CODES,
  nonExplicitSupportedLngs: true,
  load: "languageOnly",
  interpolation: { escapeValue: false },
});

applyDocumentLanguageAttributes(i18n.language);

i18n.on("languageChanged", (lng) => {
  localStorage.setItem("clinora_lang", lng);
  applyDocumentLanguageAttributes(lng);
});

export default i18n;
