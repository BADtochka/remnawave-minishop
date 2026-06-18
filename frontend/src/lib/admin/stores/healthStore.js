import { writable } from "svelte/store";
import { adminErrorMessage } from "../errors.js";

const HEALTH_QUERY_KEY = ["admin", "health"];
const HEALTH_STALE_MS = 60 * 1000;

export function createHealthStore({
  api,
  at = (key, _params, fallback) => fallback || key,
  queryClient = null,
}) {
  const state = writable({
    alerts: [],
    checkedAt: null,
    healthLoading: false,
    healthError: "",
  });

  function healthErrorMessage(error) {
    if (error?.payload) return adminErrorMessage(error.payload, at, "load_failed");
    return error?.message || String(error);
  }

  async function requestHealth(refresh) {
    const data = await api(`/admin/health${refresh ? "?refresh=1" : ""}`);
    if (!data?.ok) {
      const error = new Error(adminErrorMessage(data, at, "load_failed"));
      error.payload = data;
      throw error;
    }
    return data;
  }

  async function queryHealth(refresh) {
    if (!queryClient) return requestHealth(refresh);
    if (refresh) await queryClient.invalidateQueries({ queryKey: HEALTH_QUERY_KEY });
    return queryClient.fetchQuery({
      queryKey: HEALTH_QUERY_KEY,
      queryFn: () => requestHealth(refresh),
      retry: false,
      staleTime: HEALTH_STALE_MS,
    });
  }

  async function loadHealth({ refresh = false } = {}) {
    state.update((s) => ({ ...s, healthLoading: true, healthError: "" }));
    try {
      const data = await queryHealth(refresh);
      state.update((s) => ({
        ...s,
        alerts: Array.isArray(data.alerts) ? data.alerts : [],
        checkedAt: data.checked_at || null,
      }));
    } catch (e) {
      state.update((s) => ({ ...s, healthError: healthErrorMessage(e) }));
    } finally {
      state.update((s) => ({ ...s, healthLoading: false }));
    }
  }

  return {
    subscribe: state.subscribe,
    loadHealth,
  };
}
