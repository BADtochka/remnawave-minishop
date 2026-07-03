import { QueryClient } from "@tanstack/svelte-query";
import { createAdsStore } from "../lib/admin/stores/adsStore.js";
import { createBackupsStore } from "../lib/admin/stores/backupsStore.js";
import { createBroadcastStore } from "../lib/admin/stores/broadcastStore.js";
import { createHealthStore } from "../lib/admin/stores/healthStore.js";
import { createLogsStore } from "../lib/admin/stores/logsStore.js";
import { createPaymentsStore } from "../lib/admin/stores/paymentsStore.js";
import { createPromosStore } from "../lib/admin/stores/promosStore.js";
import { createSettingsStore } from "../lib/admin/stores/settingsStore.js";
import { createStatsStore } from "../lib/admin/stores/statsStore.js";
import { createAdminSupportStore } from "../lib/admin/stores/supportStore.js";
import { createTariffsStore } from "../lib/admin/stores/tariffsStore.js";
import { createThemesStore } from "../lib/admin/stores/themesStore.js";
import { createTranslationsStore } from "../lib/admin/stores/translationsStore.js";
import { createUsersStore } from "../lib/admin/stores/usersStore.js";
import {
  setAdsStore,
  setAdminSupportStore,
  setBackupsStore,
  setBroadcastStore,
  setHealthStore,
  setLogsStore,
  setPaymentsStore,
  setPromosStore,
  setSettingsStore,
  setStatsStore,
  setTariffsStore,
  setThemesStore,
  setTranslationsStore,
  setUsersStore,
} from "../lib/admin/context";
import type { TariffsCatalog } from "../lib/admin/stores/tariffsStore";

export type AdminApi = Parameters<typeof createAdsStore>[0]["api"] &
  Parameters<typeof createThemesStore>[0]["api"];
type TranslateFn = (key: string, params?: Record<string, unknown>, fallback?: string) => string;

type AdminStoresOptions = {
  api: AdminApi;
  at: TranslateFn;
  onToast: (message: string) => void;
  onTariffsSaved: (catalog: TariffsCatalog) => void | Promise<void>;
  onThemesSaved: () => void | Promise<void>;
  routePrefix: string;
};

export function createAdminStores({
  api,
  at,
  onToast,
  onTariffsSaved,
  onThemesSaved,
  routePrefix,
}: AdminStoresOptions) {
  const adminQueryClient = new QueryClient({
    defaultOptions: {
      queries: {
        gcTime: 10 * 60 * 1000,
        retry: false,
        staleTime: 60 * 1000,
      },
    },
  });
  const settingsStore = createSettingsStore({ api, onToast, at });
  const adsStore = createAdsStore({ api, onToast, at });
  const backupsStore = createBackupsStore({ api, onToast, at });
  const broadcastStore = createBroadcastStore({ api, onToast, at });
  const healthStore = createHealthStore({ api, at, queryClient: adminQueryClient });
  const logsStore = createLogsStore({ api, onToast, at, queryClient: adminQueryClient });
  const paymentsStore = createPaymentsStore({
    api,
    onToast,
    at,
    routePrefix,
    queryClient: adminQueryClient,
  });
  const promosStore = createPromosStore({ api, onToast, at, queryClient: adminQueryClient });
  const statsStore = createStatsStore({ api, onToast, at, queryClient: adminQueryClient });
  const supportStore = createAdminSupportStore({ api, onToast, at, routePrefix });
  const tariffsStore = createTariffsStore({ api, onTariffsSaved, flash: onToast, at });
  const themesStore = createThemesStore({ api, onThemesSaved, flash: onToast, at });
  const translationsStore = createTranslationsStore({ api, onToast, at });
  const usersStore = createUsersStore({
    api,
    onToast,
    at,
    routePrefix,
    queryClient: adminQueryClient,
  });

  setPromosStore(promosStore);
  setAdsStore(adsStore);
  setHealthStore(healthStore);
  setBackupsStore(backupsStore);
  setBroadcastStore(broadcastStore);
  setLogsStore(logsStore);
  setPaymentsStore(paymentsStore);
  setStatsStore(statsStore);
  setAdminSupportStore(supportStore);
  setSettingsStore(settingsStore);
  setUsersStore(usersStore);
  setTariffsStore(tariffsStore);
  setThemesStore(themesStore);
  setTranslationsStore(translationsStore);

  return {
    adminQueryClient,
    adsStore,
    backupsStore,
    broadcastStore,
    healthStore,
    logsStore,
    paymentsStore,
    promosStore,
    settingsStore,
    statsStore,
    supportStore,
    tariffsStore,
    themesStore,
    translationsStore,
    usersStore,
  };
}
