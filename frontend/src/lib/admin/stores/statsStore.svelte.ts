import { adminErrorMessage } from "../errors.js";
import {
  unwrap,
  type ApiClient,
  type ApiResponse,
  type GetResponse,
  type PostResponse,
  buildAdminStatsPath,
  buildAdminSyncPath,
} from "../../webapp/publicApi";
import { defineRawStateProperty } from "./rawStateProperty";

type AdminErrorResponse = { ok?: false; error?: string; message?: string; detail?: string };
type AdminApi = <Path extends Parameters<ApiClient["api"]>[0]>(
  path: Path,
  options?: Parameters<ApiClient["api"]>[1]
) => Promise<ApiResponse<Path> | AdminErrorResponse>;
type ToastFn = (message: string) => void;
type TranslateFn = (key: string, params?: Record<string, unknown>, fallback?: string) => string;
type StatsResponse = GetResponse<"/api/admin/stats">;
type SyncResponse = PostResponse<"/api/admin/sync">;
export type StatsState = {
  stats: StatsResponse | null;
  statsLoading: boolean;
  statsError: string;
  syncBusy: boolean;
};
type StatsStoreOptions = {
  api: AdminApi;
  onToast: ToastFn;
  at: TranslateFn;
};
export type StatsStore = StatsState & {
  loadStats: () => Promise<void>;
  triggerSync: () => Promise<void>;
};

function isOkResponse<T extends { ok: true }>(response: T | AdminErrorResponse): response is T {
  return response.ok === true;
}

export function createStatsStore({ api, onToast, at }: StatsStoreOptions): StatsStore {
  let stats = $state.raw<StatsResponse | null>(null);
  const state = $state<Omit<StatsState, "stats">>({
    statsLoading: false,
    statsError: "",
    syncBusy: false,
  });
  const store = Object.create(state) as StatsStore;
  defineRawStateProperty(store, "stats", {
    get: () => stats,
    set: (value) => {
      stats = value;
    },
  });

  async function loadStats(): Promise<void> {
    state.statsLoading = true;
    state.statsError = "";
    try {
      const data = (await api(buildAdminStatsPath())) as StatsResponse | AdminErrorResponse;
      if (!isOkResponse(data)) {
        state.statsError = adminErrorMessage(data, at, "load_failed");
      } else {
        stats = unwrap(data);
      }
    } catch (e: unknown) {
      state.statsError = e instanceof Error ? e.message : String(e);
    } finally {
      state.statsLoading = false;
    }
  }

  async function triggerSync(): Promise<void> {
    if (state.syncBusy) return;

    state.syncBusy = true;
    try {
      const res = (await api(buildAdminSyncPath(), { method: "POST" })) as
        SyncResponse | AdminErrorResponse;
      if (isOkResponse(res)) {
        onToast(at("sync_started", {}, "Синхронизация запущена"));
        await loadStats();
      } else {
        onToast(adminErrorMessage(res, at, at("sync_error", {}, "Ошибка синхронизации")));
      }
    } finally {
      state.syncBusy = false;
    }
  }

  return Object.assign(store, {
    loadStats,
    triggerSync,
  });
}
