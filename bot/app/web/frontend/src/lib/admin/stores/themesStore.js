function cloneCatalog(catalog) {
  return JSON.parse(JSON.stringify(catalog || { default_theme: "dark", themes: [] }));
}

import { writable } from "svelte/store";

export function createThemesStore({ api, onThemesSaved, flash, at }) {
  const state = writable({
    themesCatalog: { default_theme: "dark", themes: [] },
    themesDir: "",
    themesLoading: false,
    themesSaving: false,
  });

  async function loadThemes() {
    state.update((s) => ({ ...s, themesLoading: true }));
    try {
      const data = await api("/admin/themes");
      if (data?.ok) {
        state.update((s) => ({
          ...s,
          themesCatalog: cloneCatalog(data.catalog),
          themesDir: data.themes_dir || "",
        }));
      } else {
        flash(data?.message || data?.error || at("load_failed", {}, "Не удалось загрузить темы"));
      }
    } finally {
      state.update((s) => ({ ...s, themesLoading: false }));
    }
  }

  async function saveThemes(options = {}) {
    const silent = Boolean(options.silent);
    let catalog = null;
    state.update((s) => {
      catalog = cloneCatalog(s.themesCatalog);
      return { ...s, themesSaving: true };
    });
    try {
      const data = await api("/admin/themes", {
        method: "PUT",
        body: JSON.stringify({ catalog }),
      });
      if (data?.ok) {
        state.update((s) => ({
          ...s,
          themesCatalog: cloneCatalog(data.catalog),
          themesDir: data.themes_dir || s.themesDir,
        }));
        if (!silent) flash(at("themes_saved", {}, "Темы сохранены"));
        if (typeof onThemesSaved === "function") onThemesSaved();
      } else {
        flash(data?.message || data?.error || at("themes_save_failed", {}, "Не удалось сохранить"));
      }
    } finally {
      state.update((s) => ({ ...s, themesSaving: false }));
    }
  }

  async function setCurrentTheme(key) {
    let changed = false;
    state.update((s) => ({
      ...s,
      themesCatalog: {
        ...s.themesCatalog,
        default_theme: key,
        themes: (s.themesCatalog.themes || []).map((theme) => ({
          ...theme,
          default: theme.key === key,
        })),
      },
    }));
    state.update((s) => {
      changed = s.themesCatalog.default_theme === key;
      return s;
    });
    if (changed) await saveThemes({ silent: true });
  }

  function togglePrimaryAccent(key, enabled) {
    state.update((s) => ({
      ...s,
      themesCatalog: {
        ...s.themesCatalog,
        themes: (s.themesCatalog.themes || []).map((theme) =>
          theme.key === key ? { ...theme, use_primary_accent: Boolean(enabled) } : theme
        ),
      },
    }));
  }

  function toggleAdminUse(key, enabled) {
    state.update((s) => ({
      ...s,
      themesCatalog: {
        ...s.themesCatalog,
        themes: (s.themesCatalog.themes || []).map((theme) =>
          theme.key === key ? { ...theme, use_in_admin: Boolean(enabled) } : theme
        ),
      },
    }));
  }

  return {
    subscribe: state.subscribe,
    loadThemes,
    saveThemes,
    setCurrentTheme,
    togglePrimaryAccent,
    toggleAdminUse,
  };
}
