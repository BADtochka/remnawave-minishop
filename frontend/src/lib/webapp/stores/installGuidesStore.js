import { writable } from "svelte/store";

export function createInstallGuidesStore({ api, t, showToast }) {
  let inFlight = null;
  let loadedPath = "";
  const state = writable({
    enabled: false,
    config: null,
    source: null,
    subscription: null,
    error: "",
    loading: false,
    loaded: false,
  });

  function stateFromResponse(response) {
    return {
      enabled: Boolean(response?.enabled),
      config: response?.config || null,
      source: response?.source || null,
      subscription: response?.subscription || null,
      error: response?.error || "",
      loading: false,
      loaded: true,
    };
  }

  function applyResponse(path, response) {
    const next = stateFromResponse(response);
    loadedPath = path;
    state.set(next);
    return next;
  }

  async function fetchGuides(path, force = false) {
    if (inFlight?.path === path) return inFlight.promise;
    let snapshot;
    state.update((s) => {
      snapshot = s;
      return s;
    });
    if (!force && snapshot?.loaded && loadedPath === path) return snapshot;
    const promise = (async () => {
      state.update((s) => ({
        ...s,
        loading: true,
        loaded: force ? false : s.loaded,
        error: "",
      }));
      try {
        const response = await api(path);
        const next = applyResponse(path, response);
        return next;
      } catch (error) {
        const message =
          error?.message || t("wa_install_unavailable", {}, "Instructions unavailable");
        if (typeof showToast === "function") showToast(message);
        const next = {
          enabled: false,
          config: null,
          source: null,
          subscription: null,
          error: message,
          loading: false,
          loaded: true,
        };
        loadedPath = path;
        state.set(next);
        return next;
      } finally {
        inFlight = null;
      }
    })();
    inFlight = { path, promise };
    return promise;
  }

  async function load(force = false) {
    return fetchGuides("/subscription-guides", force);
  }

  function publicPath(shareToken) {
    const encoded = encodeURIComponent(String(shareToken || ""));
    return `/subscription-guides/public/${encoded}`;
  }

  async function loadPublic(shareToken, force = false) {
    return fetchGuides(publicPath(shareToken), force);
  }

  function hydrate(path, response) {
    inFlight = null;
    return applyResponse(path, response);
  }

  function reset() {
    inFlight = null;
    loadedPath = "";
    state.set({
      enabled: false,
      config: null,
      source: null,
      subscription: null,
      error: "",
      loading: false,
      loaded: false,
    });
  }

  return {
    subscribe: state.subscribe,
    set: state.set,
    update: state.update,
    load,
    loadPublic,
    hydrate,
    publicPath,
    reset,
  };
}
