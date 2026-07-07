import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_WEBAPP_API_BASE,
  WEBAPP_API_BASE_URL_PLACEHOLDER,
  buildApiUrl,
  normalizeApiBase,
  runtimeApiBase,
} from "./apiBase";

type RuntimeWindow = Window & {
  __RW_WEBAPP_RUNTIME_CONFIG__?: {
    apiBaseUrl?: unknown;
  };
};

beforeEach(() => {
  vi.stubGlobal("window", {} as RuntimeWindow);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("runtimeApiBase", () => {
  it("prefers inline runtime config over the default", () => {
    (window as RuntimeWindow).__RW_WEBAPP_RUNTIME_CONFIG__ = {
      apiBaseUrl: "https://bot.example.com/api/",
    };
    expect(runtimeApiBase()).toBe("https://bot.example.com/api");
  });

  it("falls back to /api when runtime config is missing", () => {
    expect(runtimeApiBase()).toBe(DEFAULT_WEBAPP_API_BASE);
  });
});

describe("nginx runtime placeholder", () => {
  it("uses a stable placeholder token for container startup substitution", () => {
    expect(WEBAPP_API_BASE_URL_PLACEHOLDER).toBe("__RW_WEBAPP_API_BASE_URL__");
  });
});

describe("normalizeApiBase", () => {
  it("normalizes API base URLs without duplicating the /api prefix", () => {
    expect(normalizeApiBase("https://bot.example.com/api/")).toBe("https://bot.example.com/api");
    expect(buildApiUrl("/me", "https://bot.example.com/api/")).toBe(
      "https://bot.example.com/api/me"
    );
    expect(buildApiUrl("/api/me", "https://bot.example.com/api/")).toBe(
      "https://bot.example.com/api/me"
    );
    expect(buildApiUrl("/bootstrap?i18n_scope=webapp", "/api")).toBe(
      "/api/bootstrap?i18n_scope=webapp"
    );
  });
});
