import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key, options) => options?.defaultValue || key,
  }),
}));

if (!window.URL.createObjectURL) {
  window.URL.createObjectURL = vi.fn(() => "blob:test-object-url");
}

if (!window.URL.revokeObjectURL) {
  window.URL.revokeObjectURL = vi.fn();
}

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}
