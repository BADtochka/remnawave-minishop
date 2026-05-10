<script>
  import {
    ArrowLeft,
    BarChart3,
    Check,
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    Coins,
    CreditCard,
    Database,
    Download,
    Eye,
    EyeOff,
    FileText,
    LayoutDashboard,
    Megaphone,
    Menu,
    Plus,
    RefreshCw,
    Save,
    Send,
    Settings as SettingsIcon,
    Shield,
    Sliders,
    Sparkles,
    Tag,
    Trash2,
    UserMinus,
    UserPlus,
    UserRound,
    UsersRound,
    X,
  } from "lucide-svelte";
  import { onMount } from "svelte";
  import { Accordion, Label, Select, Separator, Switch, Tabs } from "bits-ui";

  import Dialog from "../lib/components/ui/dialog.svelte";

  export let api;
  export let onClose = () => {};
  export let onToast = () => {};
  export let initialSection = "stats";
  export let onSectionChange = () => {};

  const NAV_GROUPS = [
    {
      id: "overview",
      label: "Overview",
      items: [
        { id: "stats", label: "Дашборд", icon: LayoutDashboard },
      ],
    },
    {
      id: "operations",
      label: "Управление",
      items: [
        { id: "users", label: "Пользователи", icon: UsersRound },
        { id: "payments", label: "Платежи", icon: CreditCard },
        { id: "promos", label: "Промокоды", icon: Tag },
        { id: "ads", label: "Реклама", icon: Sparkles },
      ],
    },
    {
      id: "communication",
      label: "Коммуникации",
      items: [
        { id: "broadcast", label: "Рассылка", icon: Megaphone },
        { id: "logs", label: "Логи", icon: FileText },
      ],
    },
    {
      id: "system",
      label: "Система",
      items: [
        { id: "tariffs", label: "Тарифы", icon: Coins },
        { id: "settings", label: "Настройки", icon: Sliders },
      ],
    },
  ];

  const SECTION_META = {
    stats: { title: "Дашборд", subtitle: "Сводка по магазину и панели" },
    users: { title: "Пользователи", subtitle: "Поиск, баны, действия над аккаунтами" },
    payments: { title: "Платежи", subtitle: "История транзакций и экспорт" },
    promos: { title: "Промокоды", subtitle: "Создание и управление кодами" },
    ads: { title: "Рекламные кампании", subtitle: "UTM-источники и атрибуция" },
    broadcast: { title: "Рассылка", subtitle: "Массовая отправка сообщений в Telegram" },
    logs: { title: "Логи активности", subtitle: "События пользователей и админ-действия" },
    tariffs: { title: "Тарифы", subtitle: "Каталог продаж, периоды, пакеты и лимиты" },
    settings: { title: "Настройки приложения", subtitle: "Оверрайды над .env, применяются мгновенно" },
  };

  const VALID_SECTIONS = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.id));
  function _normalizeSection(value) {
    return VALID_SECTIONS.includes(value) ? value : "stats";
  }
  let active = _normalizeSection(initialSection);
  let sidebarOpen = false;

  // Stats
  let stats = null;
  let statsLoading = false;
  let statsError = "";
  let syncBusy = false;

  // Users
  let users = [];
  let usersTotal = 0;
  let usersPage = 0;
  const USERS_PAGE_SIZE = 25;
  let usersQuery = "";
  let usersFilter = "all";
  let usersLoading = false;
  let openedUser = null;
  let openedUserDetail = null;
  let userDetailLoading = false;
  let userMessageDraft = "";
  let userExtendDays = 30;
  let userActionBusy = false;
  let userDeleteOpen = false;
  let userBanConfirmOpen = false;
  let userDetailTab = "profile";
  let tariffEditorTab = "general";

  // Payments
  let payments = [];
  let paymentsTotal = 0;
  let paymentsPage = 0;
  const PAYMENTS_PAGE_SIZE = 25;
  let paymentsLoading = false;

  // Promos
  let promos = [];
  let promosTotal = 0;
  let promosPage = 0;
  const PROMOS_PAGE_SIZE = 25;
  let promosLoading = false;
  let promoCreateOpen = false;
  let promoDraft = { code: "", bonus_days: 7, max_activations: 1, valid_days: 30 };

  // Broadcast
  let broadcastTarget = "all";
  let broadcastText = "";
  let broadcastBusy = false;
  let broadcastResult = null;

  // Logs
  let logs = [];
  let logsTotal = 0;
  let logsPage = 0;
  const LOGS_PAGE_SIZE = 50;
  let logsUserFilter = "";
  let logsLoading = false;

  // Ads
  let ads = [];
  let adsTotals = null;
  let adsLoading = false;
  let adCreateOpen = false;
  let adDraft = { source: "", start_param: "", cost: 0 };

  // Tariffs
  let tariffsCatalog = {
    default_tariff: "",
    topup_packages_default: { rub: [], stars: [] },
    tariffs: [],
  };
  let tariffsPath = "";
  let tariffsLoading = false;
  let tariffsSaving = false;
  let tariffEditorOpen = false;
  let tariffEditingKey = "";
  let tariffDeleteOpen = false;
  let tariffDeleteTarget = null;
  let tariffDraft = emptyTariffDraft();
  let panelSquads = [];
  let panelSquadsLoading = false;
  let selectedBaseSquad = "";
  let selectedPremiumSquad = "";

  // Settings
  let settingsSections = [];
  let settingsLoading = false;
  let settingsDirty = {};
  let settingsSaving = false;
  let settingsOpenSections = []; // bits-ui Accordion value (multiple)
  let settingsOpenSubsections = {}; // sectionId -> array of open subsection labels
  let isCompact = false;

  function flash(text) {
    onToast(text);
  }

  function setActive(id) {
    const next = _normalizeSection(id);
    if (active === next) {
      sidebarOpen = false;
      return;
    }
    active = next;
    sidebarOpen = false;
    onSectionChange(next);
    loadActive();
  }

  function _readSectionFromPath() {
    if (typeof window === "undefined") return "stats";
    const m = window.location.pathname.match(/^\/admin\/([a-z0-9_-]+)$/i);
    return _normalizeSection(m ? m[1].toLowerCase() : "stats");
  }

  function _onPopState() {
    const next = _readSectionFromPath();
    if (active === next) return;
    active = next;
    sidebarOpen = false;
    loadActive();
  }

  async function loadActive() {
    if (active === "stats") return loadStats();
    if (active === "users") return loadUsers();
    if (active === "payments") return loadPayments();
    if (active === "promos") return loadPromos();
    if (active === "logs") return loadLogs();
    if (active === "ads") return loadAds();
    if (active === "tariffs") return loadTariffs();
    if (active === "settings") return loadSettings();
  }

  // ─── Stats ────────────────────────────────────────────────────
  async function loadStats() {
    statsLoading = true;
    statsError = "";
    try {
      const data = await api("/admin/stats");
      if (!data?.ok) statsError = data?.error || "load_failed";
      else stats = data;
    } catch (e) {
      statsError = e?.message || String(e);
    } finally {
      statsLoading = false;
    }
  }

  async function triggerSync() {
    if (syncBusy) return;
    syncBusy = true;
    try {
      const res = await api("/admin/sync", { method: "POST" });
      if (res?.ok) {
        flash("Синхронизация запущена");
        await loadStats();
      } else {
        flash(res?.error || "Ошибка синхронизации");
      }
    } finally {
      syncBusy = false;
    }
  }

  // ─── Users ────────────────────────────────────────────────────
  async function loadUsers() {
    usersLoading = true;
    try {
      const params = new URLSearchParams({
        page: String(usersPage),
        page_size: String(USERS_PAGE_SIZE),
      });
      if (usersQuery.trim()) params.set("q", usersQuery.trim());
      if (usersFilter === "banned") params.set("filter", "banned");
      const data = await api(`/admin/users?${params.toString()}`);
      if (data?.ok) {
        users = data.users || [];
        usersTotal = data.total || users.length;
      }
    } finally {
      usersLoading = false;
    }
  }

  async function openUser(user) {
    openedUser = user;
    openedUserDetail = null;
    userMessageDraft = "";
    userExtendDays = 30;
    userDetailLoading = true;
    userDetailTab = "profile";
    try {
      const res = await api(`/admin/users/${user.user_id}`);
      if (res?.ok) {
        openedUserDetail = res;
      } else {
        flash(res?.error || "load_failed");
        openedUser = null;
      }
    } finally {
      userDetailLoading = false;
    }
  }

  function closeUser() {
    openedUser = null;
    openedUserDetail = null;
    userDeleteOpen = false;
    userBanConfirmOpen = false;
  }

  function requestBanToggle() {
    if (!openedUser) return;
    if (openedUser.is_banned) {
      // Unbanning is reversible — apply directly without confirmation.
      applyBanToggle(false);
    } else {
      userBanConfirmOpen = true;
    }
  }

  async function applyBanToggle(banned) {
    if (!openedUser) return;
    userActionBusy = true;
    try {
      const res = await api(`/admin/users/${openedUser.user_id}/ban`, {
        method: "POST",
        body: JSON.stringify({ banned }),
      });
      if (res?.ok) {
        openedUser.is_banned = banned;
        users = users.map((u) =>
          u.user_id === openedUser.user_id ? { ...u, is_banned: banned } : u,
        );
        userBanConfirmOpen = false;
        flash(banned ? "Пользователь забанен" : "Пользователь разбанен");
      } else flash(res?.error || "Ошибка");
    } finally {
      userActionBusy = false;
    }
  }

  async function sendUserMessage() {
    if (!openedUser || !userMessageDraft.trim()) return;
    userActionBusy = true;
    try {
      const res = await api(`/admin/users/${openedUser.user_id}/message`, {
        method: "POST",
        body: JSON.stringify({ text: userMessageDraft }),
      });
      if (res?.ok) {
        flash("Сообщение отправлено");
        userMessageDraft = "";
      } else flash(res?.error || "Не удалось отправить");
    } finally {
      userActionBusy = false;
    }
  }

  async function extendUser() {
    if (!openedUser) return;
    const days = Number(userExtendDays);
    if (!days || days <= 0) return;
    userActionBusy = true;
    try {
      const res = await api(`/admin/users/${openedUser.user_id}/extend`, {
        method: "POST",
        body: JSON.stringify({ days }),
      });
      if (res?.ok) {
        flash(`Подписка продлена на ${days} дн.`);
        await openUser(openedUser);
      } else flash(res?.error || "Ошибка");
    } finally {
      userActionBusy = false;
    }
  }

  async function resetTrialUser() {
    if (!openedUser) return;
    userActionBusy = true;
    try {
      const res = await api(`/admin/users/${openedUser.user_id}/reset-trial`, { method: "POST" });
      if (res?.ok) flash("Триал сброшен");
      else flash(res?.error || "Ошибка");
    } finally {
      userActionBusy = false;
    }
  }

  async function deleteUser() {
    if (!openedUser) return;
    userActionBusy = true;
    try {
      const res = await api(`/admin/users/${openedUser.user_id}`, { method: "DELETE" });
      if (res?.ok) {
        flash("Пользователь удалён");
        users = users.filter((u) => u.user_id !== openedUser.user_id);
        closeUser();
      } else flash(res?.error || "Ошибка");
    } finally {
      userActionBusy = false;
    }
  }

  // ─── Payments ─────────────────────────────────────────────────
  async function loadPayments() {
    paymentsLoading = true;
    try {
      const data = await api(`/admin/payments?page=${paymentsPage}&page_size=${PAYMENTS_PAGE_SIZE}`);
      if (data?.ok) {
        payments = data.payments || [];
        paymentsTotal = data.total || 0;
      }
    } finally {
      paymentsLoading = false;
    }
  }

  function exportPayments() {
    window.location.assign("/api/admin/payments/export.csv");
  }

  // ─── Promos ───────────────────────────────────────────────────
  async function loadPromos() {
    promosLoading = true;
    try {
      const data = await api(`/admin/promos?page=${promosPage}&page_size=${PROMOS_PAGE_SIZE}`);
      if (data?.ok) {
        promos = data.promos || [];
        promosTotal = data.total || 0;
      }
    } finally {
      promosLoading = false;
    }
  }

  async function createPromo() {
    if (!promoDraft.code.trim()) return;
    const res = await api("/admin/promos", {
      method: "POST",
      body: JSON.stringify(promoDraft),
    });
    if (res?.ok) {
      flash("Промокод создан");
      promoCreateOpen = false;
      promoDraft = { code: "", bonus_days: 7, max_activations: 1, valid_days: 30 };
      loadPromos();
    } else flash(res?.error || "Ошибка");
  }

  async function togglePromo(promo) {
    const res = await api(`/admin/promos/${promo.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !promo.is_active }),
    });
    if (res?.ok) {
      promos = promos.map((p) => (p.id === promo.id ? res.promo : p));
    } else flash(res?.error || "Ошибка");
  }

  async function deletePromo(promo) {
    const res = await api(`/admin/promos/${promo.id}`, { method: "DELETE" });
    if (res?.ok) {
      promos = promos.filter((p) => p.id !== promo.id);
      flash("Промокод удалён");
    } else flash(res?.error || "Ошибка");
  }

  // ─── Broadcast ────────────────────────────────────────────────
  async function runBroadcast() {
    if (!broadcastText.trim()) return;
    broadcastBusy = true;
    broadcastResult = null;
    try {
      const res = await api("/admin/broadcast", {
        method: "POST",
        body: JSON.stringify({ target: broadcastTarget, text: broadcastText }),
      });
      if (res?.ok) {
        broadcastResult = res;
        broadcastText = "";
        flash(`В очереди: ${res.queued}`);
      } else flash(res?.error || "Ошибка");
    } finally {
      broadcastBusy = false;
    }
  }

  // ─── Logs ─────────────────────────────────────────────────────
  async function loadLogs() {
    logsLoading = true;
    try {
      const params = new URLSearchParams({ page: String(logsPage), page_size: String(LOGS_PAGE_SIZE) });
      if (logsUserFilter.trim()) params.set("user_id", logsUserFilter.trim());
      const data = await api(`/admin/logs?${params.toString()}`);
      if (data?.ok) {
        logs = data.logs || [];
        logsTotal = data.total || 0;
      }
    } finally {
      logsLoading = false;
    }
  }

  // ─── Ads ──────────────────────────────────────────────────────
  async function loadAds() {
    adsLoading = true;
    try {
      const data = await api("/admin/ads");
      if (data?.ok) {
        ads = data.campaigns || [];
        adsTotals = data.totals || {};
      }
    } finally {
      adsLoading = false;
    }
  }

  async function createAd() {
    if (!adDraft.source.trim() || !adDraft.start_param.trim()) return;
    const res = await api("/admin/ads", {
      method: "POST",
      body: JSON.stringify(adDraft),
    });
    if (res?.ok) {
      flash("Кампания создана");
      adCreateOpen = false;
      adDraft = { source: "", start_param: "", cost: 0 };
      loadAds();
    } else flash(res?.error || "Ошибка");
  }

  async function toggleAd(ad) {
    const res = await api(`/admin/ads/${ad.id}/toggle`, {
      method: "POST",
      body: JSON.stringify({ is_active: !ad.is_active }),
    });
    if (res?.ok) {
      ads = ads.map((c) => (c.id === ad.id ? { ...c, is_active: !ad.is_active } : c));
    } else flash(res?.error || "Ошибка");
  }

  async function deleteAd(ad) {
    const res = await api(`/admin/ads/${ad.id}`, { method: "DELETE" });
    if (res?.ok) {
      ads = ads.filter((c) => c.id !== ad.id);
      flash("Удалено");
    } else flash(res?.error || "Ошибка");
  }

  // ─── Tariffs ─────────────────────────────────────────────────
  function emptyTariffDraft() {
    return {
      key: "",
      nameRu: "",
      nameEn: "",
      descriptionRu: "",
      descriptionEn: "",
      squadUuids: [],
      premiumSquadUuids: [],
      billing_model: "period",
      enabled: true,
      monthly_gb: 500,
      premium_monthly_gb: "",
      hwid_device_limit: "",
      conversion_rate_rub_per_gb: "",
      periodRows: [
        { months: 1, rub: 150, stars: "" },
        { months: 3, rub: 400, stars: "" },
        { months: 6, rub: 750, stars: "" },
        { months: 12, rub: 1400, stars: "" },
      ],
      topupRubRows: [],
      topupStarsRows: [],
      premiumTopupRubRows: [],
      premiumTopupStarsRows: [],
      trafficRubRows: [
        { gb: 10, price: 199 },
        { gb: 50, price: 799 },
      ],
      trafficStarsRows: [],
      hwidRubRows: [],
      hwidStarsRows: [],
    };
  }

  function cloneCatalog(catalog) {
    return structuredCloneSafe({
      default_tariff: catalog?.default_tariff || "",
      topup_packages_default: catalog?.topup_packages_default || { rub: [], stars: [] },
      tariffs: catalog?.tariffs || [],
    });
  }

  function rowsFromPackages(packageSet, currency, valueKey) {
    return (packageSet?.[currency] || []).map((pkg) => ({
      [valueKey]: pkg[valueKey],
      price: pkg.price,
    }));
  }

  function draftFromTariff(tariff) {
    const months = new Set([
      ...(tariff.enabled_periods || []),
      ...Object.keys(tariff.prices_rub || {}).map(Number),
      ...Object.keys(tariff.prices_stars || {}).map(Number),
    ]);
    const periodRows = [...months]
      .filter((month) => Number.isFinite(month) && month > 0)
      .sort((a, b) => a - b)
      .map((month) => ({
        months: month,
        rub: tariff.prices_rub?.[String(month)] ?? "",
        stars: tariff.prices_stars?.[String(month)] ?? "",
      }));

    return {
      ...emptyTariffDraft(),
      key: tariff.key || "",
      nameRu: tariff.names?.ru || "",
      nameEn: tariff.names?.en || "",
      descriptionRu: tariff.descriptions?.ru || "",
      descriptionEn: tariff.descriptions?.en || "",
      squadUuids: tariff.squad_uuids || [],
      premiumSquadUuids: tariff.premium_squad_uuids || [],
      billing_model: tariff.billing_model || "period",
      enabled: tariff.enabled !== false,
      monthly_gb: tariff.monthly_gb ?? "",
      premium_monthly_gb: tariff.premium_monthly_gb ?? "",
      hwid_device_limit: tariff.hwid_device_limit ?? "",
      conversion_rate_rub_per_gb: tariff.conversion_rate_rub_per_gb ?? "",
      periodRows: periodRows.length ? periodRows : emptyTariffDraft().periodRows,
      topupRubRows: rowsFromPackages(tariff.topup_packages, "rub", "gb"),
      topupStarsRows: rowsFromPackages(tariff.topup_packages, "stars", "gb"),
      premiumTopupRubRows: rowsFromPackages(tariff.premium_topup_packages, "rub", "gb"),
      premiumTopupStarsRows: rowsFromPackages(tariff.premium_topup_packages, "stars", "gb"),
      trafficRubRows: rowsFromPackages(tariff.traffic_packages, "rub", "gb"),
      trafficStarsRows: rowsFromPackages(tariff.traffic_packages, "stars", "gb"),
      hwidRubRows: rowsFromPackages(tariff.hwid_device_packages, "rub", "count"),
      hwidStarsRows: rowsFromPackages(tariff.hwid_device_packages, "stars", "count"),
    };
  }

  function parseNumber(value, fallback = null) {
    if (value === "" || value === null || value === undefined) return fallback;
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
  }

  function parseIntNumber(value, fallback = null) {
    const num = parseNumber(value, fallback);
    return num === null ? fallback : Math.trunc(num);
  }

  function compactMap(obj) {
    return Object.fromEntries(Object.entries(obj).filter(([, value]) => value !== "" && value !== null && value !== undefined));
  }

  function packagesFromRows(rows, valueKey) {
    return (rows || [])
      .map((row) => ({
        [valueKey]: parseNumber(row[valueKey]),
        price: parseNumber(row.price),
      }))
      .filter((row) => row[valueKey] > 0 && row.price !== null && row.price >= 0);
  }

  function packageSetFromRows(rubRows, starsRows, valueKey) {
    const rub = packagesFromRows(rubRows, valueKey);
    const stars = packagesFromRows(starsRows, valueKey);
    return rub.length || stars.length ? { rub, stars } : null;
  }

  function tariffFromDraft() {
    const key = tariffDraft.key.trim();
    const names = compactMap({
      ru: tariffDraft.nameRu.trim(),
      en: tariffDraft.nameEn.trim(),
    });
    const descriptions = compactMap({
      ru: tariffDraft.descriptionRu.trim(),
      en: tariffDraft.descriptionEn.trim(),
    });
    const tariff = {
      key,
      names,
      descriptions,
      squad_uuids: normalizeUuidList(tariffDraft.squadUuids),
      premium_squad_uuids: normalizeUuidList(tariffDraft.premiumSquadUuids),
      billing_model: tariffDraft.billing_model,
      enabled: Boolean(tariffDraft.enabled),
    };

    const hwidLimit = parseIntNumber(tariffDraft.hwid_device_limit);
    if (hwidLimit !== null) tariff.hwid_device_limit = hwidLimit;
    const hwidPackages = packageSetFromRows(tariffDraft.hwidRubRows, tariffDraft.hwidStarsRows, "count");
    if (hwidPackages) tariff.hwid_device_packages = hwidPackages;
    const premiumMonthlyGb = parseNumber(tariffDraft.premium_monthly_gb);
    if (premiumMonthlyGb !== null) tariff.premium_monthly_gb = premiumMonthlyGb;
    const premiumTopupPackages = packageSetFromRows(
      tariffDraft.premiumTopupRubRows,
      tariffDraft.premiumTopupStarsRows,
      "gb",
    );
    if (premiumTopupPackages) tariff.premium_topup_packages = premiumTopupPackages;

    if (tariff.billing_model === "period") {
      const seenMonths = new Set();
      const rows = (tariffDraft.periodRows || [])
        .map((row) => ({
          months: parseIntNumber(row.months),
          rub: parseNumber(row.rub, 0),
          stars: parseNumber(row.stars, 0),
        }))
        .filter((row) => row.months > 0)
        .filter((row) => {
          if (seenMonths.has(row.months)) return false;
          seenMonths.add(row.months);
          return true;
        })
        .sort((a, b) => a.months - b.months);
      tariff.monthly_gb = parseNumber(tariffDraft.monthly_gb, 0);
      tariff.enabled_periods = rows.map((row) => row.months);
      tariff.prices_rub = Object.fromEntries(rows.map((row) => [String(row.months), row.rub || 0]));
      tariff.prices_stars = Object.fromEntries(rows.map((row) => [String(row.months), row.stars || 0]));
      const topupPackages = packageSetFromRows(tariffDraft.topupRubRows, tariffDraft.topupStarsRows, "gb");
      if (topupPackages) tariff.topup_packages = topupPackages;
    } else {
      const trafficPackages = packageSetFromRows(tariffDraft.trafficRubRows, tariffDraft.trafficStarsRows, "gb");
      if (trafficPackages) tariff.traffic_packages = trafficPackages;
      const conversion = parseNumber(tariffDraft.conversion_rate_rub_per_gb);
      if (conversion !== null) tariff.conversion_rate_rub_per_gb = conversion;
    }

    return tariff;
  }

  async function loadTariffs() {
    tariffsLoading = true;
    try {
      loadPanelSquads();
      const data = await api("/admin/tariffs");
      if (data?.ok) {
        tariffsCatalog = cloneCatalog(data.catalog);
        tariffsPath = data.path || "";
      } else {
        flash(data?.message || data?.error || "Не удалось загрузить тарифы");
      }
    } finally {
      tariffsLoading = false;
    }
  }

  async function loadPanelSquads() {
    if (panelSquadsLoading) return;
    panelSquadsLoading = true;
    try {
      const data = await api("/admin/panel/internal-squads");
      if (data?.ok) panelSquads = data.squads || [];
    } catch (e) {
      panelSquads = [];
    } finally {
      panelSquadsLoading = false;
    }
  }

  function normalizeUuidList(value) {
    if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
    return String(value || "")
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function squadLabel(uuid) {
    const squad = panelSquads.find((item) => item.uuid === uuid);
    return squad ? `${squad.name} · ${uuid.slice(0, 8)}…` : uuid;
  }

  function addSquadToDraft(field, uuid) {
    if (!uuid) return;
    const current = normalizeUuidList(tariffDraft[field]);
    if (current.includes(uuid)) return;
    tariffDraft = { ...tariffDraft, [field]: [...current, uuid] };
  }

  function removeSquadFromDraft(field, uuid) {
    tariffDraft = {
      ...tariffDraft,
      [field]: normalizeUuidList(tariffDraft[field]).filter((item) => item !== uuid),
    };
  }

  async function persistTariffs(nextCatalog, successText) {
    tariffsSaving = true;
    try {
      const res = await api("/admin/tariffs", {
        method: "PUT",
        body: JSON.stringify({ catalog: nextCatalog }),
      });
      if (res?.ok) {
        tariffsCatalog = cloneCatalog(res.catalog);
        tariffsPath = res.path || tariffsPath;
        flash(successText || "Тарифы сохранены");
        tariffEditorOpen = false;
        tariffDeleteOpen = false;
        tariffDeleteTarget = null;
      } else {
        flash(res?.message || res?.error || "Ошибка сохранения тарифов");
      }
    } finally {
      tariffsSaving = false;
    }
  }

  function openCreateTariff() {
    tariffEditingKey = "";
    tariffDraft = emptyTariffDraft();
    tariffEditorTab = "general";
    selectedBaseSquad = "";
    selectedPremiumSquad = "";
    tariffEditorOpen = true;
  }

  function openEditTariff(tariff) {
    tariffEditingKey = tariff.key;
    tariffDraft = draftFromTariff(tariff);
    tariffEditorTab = "general";
    selectedBaseSquad = "";
    selectedPremiumSquad = "";
    tariffEditorOpen = true;
  }

  async function saveTariffDraft() {
    const tariff = tariffFromDraft();
    if (!tariff.key) {
      flash("Укажите ключ тарифа");
      return;
    }
    const existing = (tariffsCatalog.tariffs || []).find((item) => item.key === tariff.key && item.key !== tariffEditingKey);
    if (existing) {
      flash("Тариф с таким ключом уже есть");
      return;
    }
    const current = tariffsCatalog.tariffs || [];
    const tariffs = tariffEditingKey
      ? current.map((item) => (item.key === tariffEditingKey ? tariff : item))
      : [...current, tariff];
    const enabledKeys = tariffs.filter((item) => item.enabled !== false).map((item) => item.key);
    if (!enabledKeys.length) {
      flash("Должен быть хотя бы один включённый тариф");
      return;
    }
    const currentDefault = tariffsCatalog.default_tariff === tariffEditingKey ? tariff.key : tariffsCatalog.default_tariff;
    const defaultTariff = enabledKeys.includes(currentDefault)
      ? currentDefault
      : enabledKeys[0];
    await persistTariffs({ ...cloneCatalog(tariffsCatalog), default_tariff: defaultTariff, tariffs }, "Тариф сохранён");
  }

  async function toggleTariffEnabled(tariff) {
    const tariffs = (tariffsCatalog.tariffs || []).map((item) =>
      item.key === tariff.key ? { ...item, enabled: item.enabled === false } : item,
    );
    const enabledKeys = tariffs.filter((item) => item.enabled !== false).map((item) => item.key);
    if (!enabledKeys.length) {
      flash("Должен остаться хотя бы один включённый тариф");
      return;
    }
    const defaultTariff = enabledKeys.includes(tariffsCatalog.default_tariff) ? tariffsCatalog.default_tariff : enabledKeys[0];
    await persistTariffs({ ...cloneCatalog(tariffsCatalog), default_tariff: defaultTariff, tariffs }, "Статус тарифа обновлён");
  }

  async function setDefaultTariff(key) {
    if (!key || key === tariffsCatalog.default_tariff) return;
    await persistTariffs({ ...cloneCatalog(tariffsCatalog), default_tariff: key }, "Тариф по умолчанию обновлён");
  }

  async function deleteTariff() {
    if (!tariffDeleteTarget) return;
    const tariffs = (tariffsCatalog.tariffs || []).filter((item) => item.key !== tariffDeleteTarget.key);
    const enabledKeys = tariffs.filter((item) => item.enabled !== false).map((item) => item.key);
    if (!enabledKeys.length) {
      flash("Нельзя удалить последний включённый тариф");
      return;
    }
    const defaultTariff = enabledKeys.includes(tariffsCatalog.default_tariff) ? tariffsCatalog.default_tariff : enabledKeys[0];
    await persistTariffs({ ...cloneCatalog(tariffsCatalog), default_tariff: defaultTariff, tariffs }, "Тариф удалён");
  }

  function addDraftRow(field, row) {
    tariffDraft = { ...tariffDraft, [field]: [...(tariffDraft[field] || []), row] };
  }

  function removeDraftRow(field, index) {
    tariffDraft = {
      ...tariffDraft,
      [field]: (tariffDraft[field] || []).filter((_, idx) => idx !== index),
    };
  }

  // ─── Settings ─────────────────────────────────────────────────
  async function loadSettings() {
    settingsLoading = true;
    settingsDirty = {};
    try {
      const data = await api("/admin/settings");
      if (data?.ok) {
        settingsSections = data.sections || [];
        // Expand the first section on phones; expand all on desktop.
        const ids = settingsSections.map((s) => s.id);
        settingsOpenSections = isCompact ? ids.slice(0, 1) : ids.slice();
      }
    } finally {
      settingsLoading = false;
    }
  }

  function toggleAllSections() {
    if (settingsOpenSections.length === settingsSections.length) {
      settingsOpenSections = [];
    } else {
      settingsOpenSections = settingsSections.map((s) => s.id);
    }
  }

  function markDirty(key, value, deleted = false) {
    settingsDirty = { ...settingsDirty, [key]: { value, deleted } };
  }

  function clearDirty(key) {
    const next = { ...settingsDirty };
    delete next[key];
    settingsDirty = next;
  }

  function valueFor(field) {
    if (settingsDirty[field.key]?.deleted) return "";
    if (Object.prototype.hasOwnProperty.call(settingsDirty, field.key)) {
      return settingsDirty[field.key].value;
    }
    return field.value ?? "";
  }

  function isOverridden(field) {
    return Boolean(field.overridden) && !settingsDirty[field.key]?.deleted;
  }

  let revealedSecrets = new Set();
  function isSecretRevealed(key) {
    return revealedSecrets.has(key);
  }
  function toggleSecretReveal(key) {
    const next = new Set(revealedSecrets);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    revealedSecrets = next;
  }

  function groupSectionFields(section) {
    const groups = new Map();
    for (const field of section.fields || []) {
      const key = field.subsection || "_root";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(field);
    }
    return Array.from(groups.entries()).map(([id, fields]) => ({
      id,
      label: id === "_root" ? null : id,
      fields,
    }));
  }

  function resetField(field) {
    if (field.overridden) {
      markDirty(field.key, "", true);
    } else {
      clearDirty(field.key);
    }
  }

  async function saveSettings() {
    if (!Object.keys(settingsDirty).length) return;
    settingsSaving = true;
    try {
      const updates = {};
      const deletes = [];
      for (const [key, change] of Object.entries(settingsDirty)) {
        if (change.deleted) deletes.push(key);
        else updates[key] = change.value;
      }
      const res = await api("/admin/settings", {
        method: "PATCH",
        body: JSON.stringify({ updates, deletes }),
      });
      if (res?.ok) {
        flash("Настройки сохранены");
        settingsDirty = {};
        await loadSettings();
      } else if (res?.errors) {
        const summary = Object.entries(res.errors).map(([k, v]) => `${k}: ${v}`).join("; ");
        flash(`Ошибка: ${summary}`);
      } else {
        flash(res?.error || "Ошибка");
      }
    } finally {
      settingsSaving = false;
    }
  }

  // ─── Helpers ──────────────────────────────────────────────────
  function structuredCloneSafe(value) {
    if (typeof structuredClone === "function") return structuredClone(value);
    return JSON.parse(JSON.stringify(value));
  }

  function pretty(value) {
    if (value === null || value === undefined) return "—";
    if (typeof value === "boolean") return value ? "Да" : "Нет";
    return String(value);
  }

  function fmtDate(value) {
    if (!value) return "—";
    try {
      return new Date(value).toLocaleString("ru-RU");
    } catch {
      return String(value);
    }
  }

  function fmtDateShort(value) {
    if (!value) return "—";
    try {
      return new Date(value).toLocaleDateString("ru-RU");
    } catch {
      return String(value);
    }
  }

  function fmtMoney(amount, currency) {
    const sym = currency === "RUB" ? "₽" : currency || "";
    const num = Number(amount || 0);
    return `${num.toFixed(2)} ${sym}`.trim();
  }

  function tariffName(tariff) {
    return tariff?.names?.ru || tariff?.names?.en || tariff?.key || "—";
  }

  function tariffPriceSummary(tariff) {
    if (tariff.billing_model === "traffic") {
      const rub = tariff.traffic_packages?.rub || [];
      const first = rub[0];
      return first ? `${first.gb} GB за ${fmtMoney(first.price, "RUB")}` : "Пакеты трафика";
    }
    const months = [...(tariff.enabled_periods || [])].sort((a, b) => a - b);
    return months
      .map((month) => {
        const rub = tariff.prices_rub?.[String(month)];
        const stars = tariff.prices_stars?.[String(month)];
        if (rub) return `${month} мес. ${fmtMoney(rub, "RUB")}`;
        if (stars) return `${month} мес. ${stars} ⭐`;
        return `${month} мес.`;
      })
      .join(" · ");
  }

  function packageSummary(packages, valueKey, unit) {
    const rub = packages?.rub || [];
    const stars = packages?.stars || [];
    if (!rub.length && !stars.length) return "—";
    const first = [...rub, ...stars][0];
    const total = rub.length + stars.length;
    return `${first[valueKey]} ${unit}, всего ${total}`;
  }

  function userDisplayName(user) {
    const full = [user?.first_name, user?.last_name].filter(Boolean).join(" ").trim();
    return full || (user?.username ? `@${user.username}` : user?.email || `User #${user?.user_id || "—"}`);
  }

  function userSecondaryName(user) {
    if (user?.username && userDisplayName(user) !== `@${user.username}`) return `@${user.username}`;
    if (user?.email && userDisplayName(user) !== user.email) return user.email;
    return `ID ${user?.user_id || "—"}`;
  }

  function userInitials(user) {
    const source = userDisplayName(user).replace(/^@/, "").trim();
    const parts = source.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return (source.slice(0, 2) || "U").toUpperCase();
  }

  function userAvatarUrl(user) {
    // Prefer the admin cached endpoint (cheap, ETag'd, served from DB cache);
    // fall back to the raw Telegram photo URL only if there's no cache yet.
    const cached = String(user?.avatar_url || "").trim();
    if (cached) return cached;
    const value = String(user?.telegram_photo_url || "").trim();
    return value && !value.startsWith("/api/account/avatar") ? value : "";
  }

  // Gravatar fallback for users with no Telegram avatar but a known email.
  // Gravatar accepts SHA-256 hashes since 2024 — convenient because the
  // browser SubtleCrypto can compute SHA-256 natively (no MD5 dep needed).
  const _gravatarCache = new Map();
  const _gravatarPending = new Map();

  async function _sha256Hex(value) {
    const buf = new TextEncoder().encode(value);
    const digest = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  function userGravatarUrl(user) {
    const email = String(user?.email || "").trim().toLowerCase();
    if (!email) return "";
    if (_gravatarCache.has(email)) return _gravatarCache.get(email);
    if (_gravatarPending.has(email)) return "";
    _gravatarPending.set(
      email,
      _sha256Hex(email)
        .then((h) => {
          _gravatarCache.set(email, `https://gravatar.com/avatar/${h}?d=identicon&s=80`);
          users = users; // trigger reactivity
          openedUser = openedUser;
        })
        .catch(() => _gravatarPending.delete(email)),
    );
    return "";
  }

  function resolvedAvatarUrl(user) {
    return userAvatarUrl(user) || (!user?.telegram_id && user?.email ? userGravatarUrl(user) : "");
  }

  function panelStatusBadge(user) {
    const status = String(user?.panel_status || "").toLowerCase();
    if (user?.is_banned) return { label: "Бан", variant: "danger" };
    switch (status) {
      case "active":
        return { label: "Active", variant: "success" };
      case "expired":
        return { label: "Expired", variant: "warning" };
      case "limited":
        return { label: "Limited", variant: "warning" };
      case "disabled":
        return { label: "Disabled", variant: "muted" };
      case "bot_only":
        return { label: "Только бот", variant: "muted" };
      default:
        return { label: status || "—", variant: "muted" };
    }
  }

  function paymentStatusVariant(status) {
    if (status === "succeeded") return "success";
    if (typeof status === "string" && status.startsWith("pending")) return "warning";
    return "danger";
  }

  function sectionTitle(id) {
    const map = {
      general: "Общие",
      appearance: "Внешний вид",
      pricing: "Тарифы и цены",
      payments: "Платёжные системы",
      trial: "Триал",
      referral: "Реферальная программа",
      notifications: "Уведомления",
      devices: "Устройства",
    };
    return map[id] || id;
  }

  $: dirtyCount = Object.keys(settingsDirty).length;
  $: meta = SECTION_META[active] || { title: active, subtitle: "" };
  $: usersHasMore = users.length === USERS_PAGE_SIZE;
  $: paymentsHasMore = payments.length === PAYMENTS_PAGE_SIZE;
  $: logsHasMore = logs.length === LOGS_PAGE_SIZE;
  $: enabledTariffs = (tariffsCatalog.tariffs || []).filter((tariff) => tariff.enabled !== false);
  $: disabledTariffs = Math.max(0, (tariffsCatalog.tariffs || []).length - enabledTariffs.length);
  $: settingsAllOpen =
    settingsSections.length > 0 && settingsOpenSections.length === settingsSections.length;

  let _compactMql = null;
  function _onCompactChange(event) {
    const next = Boolean(event?.matches);
    if (next === isCompact) return;
    isCompact = next;
    if (settingsSections.length) {
      const ids = settingsSections.map((s) => s.id);
      settingsOpenSections = isCompact ? ids.slice(0, 1) : ids.slice();
    }
  }

  onMount(() => {
    if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
      _compactMql = window.matchMedia("(max-width: 720px)");
      isCompact = _compactMql.matches;
      if (_compactMql.addEventListener) _compactMql.addEventListener("change", _onCompactChange);
      else if (_compactMql.addListener) _compactMql.addListener(_onCompactChange);
    }
    if (typeof window !== "undefined") {
      window.addEventListener("popstate", _onPopState);
    }
    loadActive();
    return () => {
      if (_compactMql) {
        if (_compactMql.removeEventListener) _compactMql.removeEventListener("change", _onCompactChange);
        else if (_compactMql.removeListener) _compactMql.removeListener(_onCompactChange);
      }
      if (typeof window !== "undefined") {
        window.removeEventListener("popstate", _onPopState);
      }
    };
  });
</script>

{#snippet renderField(field)}
  {@const revealed = isSecretRevealed(field.key)}
  <div class="admin-setting" class:is-overridden={isOverridden(field)}>
    <div class="admin-setting-meta">
      <strong>
        {field.label}
        {#if field.secret}
          <span class="admin-badge admin-badge-warning">Secret</span>
        {/if}
        {#if isOverridden(field)}
          <span class="admin-badge admin-badge-success">Override</span>
        {/if}
      </strong>
      <code>{field.key}</code>
      {#if field.description}
        <small>{field.description}</small>
      {/if}
    </div>
    <div class="admin-setting-control">
      {#if field.type === "bool"}
        <label class="admin-switch">
          <input
            type="checkbox"
            checked={Boolean(valueFor(field))}
            on:change={(e) => markDirty(field.key, e.currentTarget.checked)}
          />
          <span class="admin-switch-track" aria-hidden="true"></span>
          <span>{Boolean(valueFor(field)) ? "Включено" : "Выключено"}</span>
        </label>
      {:else if field.type === "color"}
        <input
          class="admin-color"
          type="color"
          value={valueFor(field) || "#00fe7a"}
          on:input={(e) => markDirty(field.key, e.currentTarget.value)}
        />
        <input
          class="input"
          type="text"
          value={valueFor(field) || ""}
          on:input={(e) => markDirty(field.key, e.currentTarget.value)}
        />
      {:else if field.type === "int" || field.type === "float"}
        <input
          class="input"
          type="number"
          step={field.type === "float" ? "0.1" : "1"}
          placeholder={field.placeholder}
          value={valueFor(field) ?? ""}
          on:input={(e) => markDirty(field.key, e.currentTarget.value)}
        />
      {:else if field.secret}
        <input
          class="input"
          type={revealed ? "text" : "password"}
          placeholder={field.placeholder || "••••••••"}
          autocomplete="off"
          value={valueFor(field) ?? ""}
          on:input={(e) => markDirty(field.key, e.currentTarget.value)}
        />
        <button
          type="button"
          class="admin-btn admin-btn-sm admin-btn-ghost"
          aria-label={revealed ? "Скрыть" : "Показать"}
          on:click={() => toggleSecretReveal(field.key)}
        >
          {#if revealed}<EyeOff size={13} />{:else}<Eye size={13} />{/if}
        </button>
      {:else}
        <input
          class="input"
          type="text"
          placeholder={field.placeholder}
          value={valueFor(field) ?? ""}
          on:input={(e) => markDirty(field.key, e.currentTarget.value)}
        />
      {/if}
      {#if isOverridden(field) || settingsDirty[field.key]}
        <button type="button" class="admin-btn admin-btn-sm admin-btn-ghost" on:click={() => resetField(field)}>
          <X size={12} /> Сбросить
        </button>
      {/if}
    </div>
  </div>
{/snippet}

<div class="admin-screen-wrap" class:is-sidebar-open={sidebarOpen}>
  {#if sidebarOpen}
    <button
      type="button"
      class="admin-sidebar-backdrop"
      aria-label="Закрыть меню"
      on:click={() => (sidebarOpen = false)}
    ></button>
  {/if}

  <aside class="admin-sidebar" aria-label="Навигация админки">
    <div class="admin-sidebar-brand">
      <span class="admin-brand-mark"><Shield size={18} /></span>
      <div>
        <strong>Админ-панель</strong>
        <small>Web App</small>
      </div>
      <button type="button" class="admin-btn admin-btn-icon admin-btn-ghost" on:click={onClose} aria-label="Выйти">
        <ArrowLeft size={16} />
      </button>
    </div>

    {#each NAV_GROUPS as group}
      <div class="admin-sidebar-section-label">{group.label}</div>
      <nav class="admin-nav" aria-label={group.label}>
        {#each group.items as item}
          <button
            type="button"
            class="admin-nav-item"
            class:active={active === item.id}
            on:click={() => setActive(item.id)}
          >
            <svelte:component this={item.icon} size={16} />
            <span>{item.label}</span>
            <span></span>
          </button>
        {/each}
      </nav>
    {/each}

    <div class="admin-sidebar-footer">
      <span>Минприложение</span>
      <span>v1 · {new Date().getFullYear()}</span>
    </div>
  </aside>

  <section class="admin-content">
    <header class="admin-header">
      <div style="display:flex; align-items:center; gap:12px; min-width:0;">
        <button
          type="button"
          class="admin-mobile-toggle"
          on:click={() => (sidebarOpen = !sidebarOpen)}
          aria-label="Меню"
        >
          <Menu size={18} />
        </button>
        <div class="admin-header-title">
          <h2>{meta.title}</h2>
          {#if meta.subtitle}<small>{meta.subtitle}</small>{/if}
        </div>
      </div>
      <div class="admin-header-actions">
        {#if active === "stats"}
          <button type="button" class="admin-btn" on:click={triggerSync} disabled={syncBusy}>
            <RefreshCw size={14} /> {syncBusy ? "Синхронизация..." : "Синхронизировать"}
          </button>
        {/if}
        {#if active === "payments"}
          <button type="button" class="admin-btn" on:click={exportPayments}>
            <Download size={14} /> CSV
          </button>
        {/if}
        {#if active === "promos"}
          <button type="button" class="admin-btn admin-btn-primary" on:click={() => (promoCreateOpen = true)}>
            <Plus size={14} /> Создать
          </button>
        {/if}
        {#if active === "ads"}
          <button type="button" class="admin-btn admin-btn-primary" on:click={() => (adCreateOpen = true)}>
            <Plus size={14} /> Кампания
          </button>
        {/if}
        {#if active === "tariffs"}
          <button type="button" class="admin-btn admin-btn-primary" on:click={openCreateTariff}>
            <Plus size={14} /> Тариф
          </button>
        {/if}
        {#if active === "settings"}
          {#if dirtyCount}
            <span class="admin-badge admin-badge-warning">Изменений: {dirtyCount}</span>
          {/if}
          <button type="button" class="admin-btn admin-btn-primary" on:click={saveSettings} disabled={!dirtyCount || settingsSaving}>
            <Save size={14} /> {settingsSaving ? "Сохранение..." : "Сохранить"}
          </button>
        {/if}
      </div>
    </header>

    <main class="admin-main">
      {#if active === "stats"}
        {#if statsError}
          <div class="admin-empty">Не удалось загрузить статистику: {statsError}</div>
        {:else if statsLoading || !stats}
          <div class="admin-empty">Загрузка…</div>
        {:else}
          <div class="admin-stat-grid">
            <article class="admin-stat-card">
              <span class="admin-stat-label"><UsersRound size={14} /> Пользователи</span>
              <span class="admin-stat-value">{stats.users?.total_users ?? 0}</span>
              <span class="admin-stat-trend">В бане: {stats.users?.banned_users ?? 0}</span>
            </article>
            <article class="admin-stat-card">
              <span class="admin-stat-label"><Shield size={14} /> Платные подписки</span>
              <span class="admin-stat-value">{stats.users?.paid_subscriptions ?? 0}</span>
              <span class="admin-stat-trend">Триалы: {stats.users?.trial_users ?? 0}</span>
            </article>
            <article class="admin-stat-card">
              <span class="admin-stat-label"><Coins size={14} /> Доход за день</span>
              <span class="admin-stat-value">{fmtMoney(stats.financial?.today_revenue, stats.currency_symbol)}</span>
              <span class="admin-stat-trend">{stats.financial?.today_payments_count ?? 0} платежей</span>
            </article>
            <article class="admin-stat-card">
              <span class="admin-stat-label"><BarChart3 size={14} /> За неделю</span>
              <span class="admin-stat-value">{fmtMoney(stats.financial?.week_revenue, stats.currency_symbol)}</span>
              <span class="admin-stat-trend">Месяц: {fmtMoney(stats.financial?.month_revenue, stats.currency_symbol)}</span>
            </article>
            <article class="admin-stat-card">
              <span class="admin-stat-label"><Database size={14} /> Всё время</span>
              <span class="admin-stat-value">{fmtMoney(stats.financial?.all_time_revenue, stats.currency_symbol)}</span>
              <span class="admin-stat-trend">Sync: {stats.panel_sync?.status ?? "—"}</span>
            </article>
            {#if stats.queue}
              <article class="admin-stat-card">
                <span class="admin-stat-label"><Send size={14} /> Очередь</span>
                <span class="admin-stat-value">{stats.queue.user_queue_size ?? 0}</span>
                <span class="admin-stat-trend">Группы: {stats.queue.group_queue_size ?? 0}</span>
              </article>
            {/if}
          </div>

          <div class="admin-table-wrap">
            <header class="admin-card-head">
              <h3>Последние платежи</h3>
              <small>{(stats.recent_payments || []).length} записей</small>
            </header>
            {#if (stats.recent_payments || []).length}
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Пользователь</th>
                    <th>Сумма</th>
                    <th>Провайдер</th>
                    <th>Статус</th>
                    <th>Дата</th>
                  </tr>
                </thead>
                <tbody>
                  {#each stats.recent_payments as p}
                    <tr>
                      <td class="admin-cell-id" data-label="ID">#{p.payment_id}</td>
                      <td data-label="Пользователь">{p.user_label || p.user_id}</td>
                      <td data-label="Сумма">{fmtMoney(p.amount, p.currency)}</td>
                      <td data-label="Провайдер">{p.provider}</td>
                      <td data-label="Статус">
                        <span class="admin-badge admin-badge-{paymentStatusVariant(p.status)}">{p.status}</span>
                      </td>
                      <td data-label="Дата">{fmtDate(p.created_at)}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="admin-card-body"><span class="admin-muted">Нет данных</span></div>
            {/if}
          </div>
        {/if}
      {/if}

      {#if active === "users"}
        <div class="admin-toolbar">
          <input
            type="search"
            class="input"
            placeholder="ID, @username или email"
            bind:value={usersQuery}
            on:keydown={(e) => e.key === "Enter" && ((usersPage = 0), loadUsers())}
          />
          <button type="button" class="admin-btn" on:click={() => { usersPage = 0; loadUsers(); }}>Найти</button>
          <div class="admin-segmented" role="tablist" aria-label="Фильтр пользователей">
            <button type="button" class:active={usersFilter === "all"} on:click={() => { usersFilter = "all"; usersPage = 0; loadUsers(); }}>Все</button>
            <button type="button" class:active={usersFilter === "banned"} on:click={() => { usersFilter = "banned"; usersPage = 0; loadUsers(); }}>Забанены</button>
          </div>
          <span class="admin-muted" style="margin-left:auto;">Всего: {usersTotal}</span>
        </div>

        <div class="admin-table-wrap">
          {#if usersLoading}
            <div class="admin-card-body"><span class="admin-muted">Загрузка…</span></div>
          {:else if !users.length}
            <div class="admin-card-body"><span class="admin-muted">Никого не найдено</span></div>
          {:else}
            <ul class="admin-user-list">
              {#each users as user}
                {@const avatar = resolvedAvatarUrl(user)}
                {@const badge = panelStatusBadge(user)}
                <li>
                  <button type="button" class="admin-user-row" on:click={() => openUser(user)}>
                    <span class="admin-avatar admin-avatar-sm">
                      {#if avatar}
                        <img src={avatar} alt="" loading="lazy" referrerpolicy="no-referrer" />
                      {:else}
                        <span>{userInitials(user)}</span>
                      {/if}
                    </span>
                    <span class="admin-user-main">
                      <strong>{userDisplayName(user)}</strong>
                      <small>{userSecondaryName(user)}</small>
                    </span>
                    <span class="admin-user-side">
                      <span class="admin-badge admin-badge-{badge.variant}">{badge.label}</span>
                      <span class="admin-user-tertiary">{fmtDateShort(user.registration_date)}</span>
                    </span>
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>

        <div class="admin-pagination">
          <span class="admin-pagination-meta">Страница {usersPage + 1}</span>
          <div class="admin-pagination-buttons">
            <button type="button" class="admin-btn admin-btn-sm" disabled={usersPage === 0} on:click={() => { usersPage = Math.max(0, usersPage - 1); loadUsers(); }}>
              <ChevronLeft size={14} /> Назад
            </button>
            <button type="button" class="admin-btn admin-btn-sm" disabled={!usersHasMore} on:click={() => { usersPage += 1; loadUsers(); }}>
              Далее <ChevronRight size={14} />
            </button>
          </div>
        </div>
      {/if}

      {#if active === "payments"}
        <div class="admin-table-wrap">
          {#if paymentsLoading}
            <div class="admin-card-body"><span class="admin-muted">Загрузка…</span></div>
          {:else if !payments.length}
            <div class="admin-card-body"><span class="admin-muted">Нет платежей</span></div>
          {:else}
            <table class="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Пользователь</th>
                  <th>Сумма</th>
                  <th>Провайдер</th>
                  <th>Описание</th>
                  <th>Статус</th>
                  <th>Дата</th>
                </tr>
              </thead>
              <tbody>
                {#each payments as p}
                  <tr>
                    <td class="admin-cell-id" data-label="ID">#{p.payment_id}</td>
                    <td data-label="Пользователь">{p.user_label || p.user_id}</td>
                    <td data-label="Сумма">{fmtMoney(p.amount, p.currency)}</td>
                    <td data-label="Провайдер">{p.provider}</td>
                    <td class="admin-cell-wrap" data-label="Описание">{p.description || "—"}</td>
                    <td data-label="Статус">
                      <span class="admin-badge admin-badge-{paymentStatusVariant(p.status)}">{p.status}</span>
                    </td>
                    <td data-label="Дата">{fmtDate(p.created_at)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>

        <div class="admin-pagination">
          <span class="admin-pagination-meta">Стр. {paymentsPage + 1} · Всего {paymentsTotal}</span>
          <div class="admin-pagination-buttons">
            <button type="button" class="admin-btn admin-btn-sm" disabled={paymentsPage === 0} on:click={() => { paymentsPage = Math.max(0, paymentsPage - 1); loadPayments(); }}>
              <ChevronLeft size={14} /> Назад
            </button>
            <button type="button" class="admin-btn admin-btn-sm" disabled={!paymentsHasMore} on:click={() => { paymentsPage += 1; loadPayments(); }}>
              Далее <ChevronRight size={14} />
            </button>
          </div>
        </div>
      {/if}

      {#if active === "promos"}
        <div class="admin-table-wrap">
          {#if promosLoading}
            <div class="admin-card-body"><span class="admin-muted">Загрузка…</span></div>
          {:else if !promos.length}
            <div class="admin-card-body"><span class="admin-muted">Промокодов нет</span></div>
          {:else}
            <table class="admin-table">
              <thead>
                <tr>
                  <th>Код</th>
                  <th>Бонус</th>
                  <th>Активаций</th>
                  <th>Действует до</th>
                  <th>Статус</th>
                  <th class="admin-cell-actions">Действия</th>
                </tr>
              </thead>
              <tbody>
                {#each promos as p}
                  <tr>
                    <td class="admin-cell-mono" data-label="Код">{p.code}</td>
                    <td data-label="Бонус">+{p.bonus_days} дн.</td>
                    <td data-label="Активаций">{p.current_activations}/{p.max_activations}</td>
                    <td data-label="Действует до">{p.valid_until ? fmtDateShort(p.valid_until) : "∞"}</td>
                    <td data-label="Статус">
                      {#if p.is_active}
                        <span class="admin-badge admin-badge-success">Активен</span>
                      {:else}
                        <span class="admin-badge admin-badge-muted">Выключен</span>
                      {/if}
                    </td>
                    <td class="admin-cell-actions" data-label="Действия">
                      <button type="button" class="admin-btn admin-btn-sm" on:click={() => togglePromo(p)}>
                        {p.is_active ? "Выкл" : "Вкл"}
                      </button>
                      <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => deletePromo(p)}>
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      {/if}

      {#if active === "broadcast"}
        <div class="admin-card">
          <header class="admin-card-head">
            <h3>Рассылка</h3>
            <small>Доставка через очередь сообщений</small>
          </header>
          <div class="admin-card-body">
            <div class="admin-form">
              <label>
                <span>Аудитория</span>
                <div class="admin-segmented">
                  {#each [["all", "Все активные"], ["active", "С подпиской"], ["inactive", "Без подписки"]] as [value, label]}
                    <button type="button" class:active={broadcastTarget === value} on:click={() => (broadcastTarget = value)}>
                      {label}
                    </button>
                  {/each}
                </div>
              </label>
              <label>
                <span>Текст сообщения</span>
                <small>Поддерживается HTML-разметка Telegram</small>
                <textarea class="admin-textarea" rows="6" bind:value={broadcastText}></textarea>
              </label>
              <div style="display:flex; gap:8px; align-items:center;">
                <button type="button" class="admin-btn admin-btn-primary" on:click={runBroadcast} disabled={broadcastBusy || !broadcastText.trim()}>
                  <Send size={14} /> {broadcastBusy ? "Отправка..." : "Поставить в очередь"}
                </button>
                {#if broadcastResult}
                  <span class="admin-muted">В очереди: {broadcastResult.queued} · Неудач: {broadcastResult.failed}</span>
                {/if}
              </div>
            </div>
          </div>
        </div>
      {/if}

      {#if active === "logs"}
        <div class="admin-toolbar">
          <input
            type="search"
            class="input"
            placeholder="Фильтр по ID пользователя"
            bind:value={logsUserFilter}
            on:keydown={(e) => e.key === "Enter" && ((logsPage = 0), loadLogs())}
          />
          <button type="button" class="admin-btn" on:click={() => { logsPage = 0; loadLogs(); }}>Применить</button>
          <button type="button" class="admin-btn admin-btn-ghost" on:click={() => { logsUserFilter = ""; logsPage = 0; loadLogs(); }}>Сбросить</button>
          <span class="admin-muted" style="margin-left:auto;">Всего: {logsTotal}</span>
        </div>

        <div class="admin-table-wrap">
          {#if logsLoading}
            <div class="admin-card-body"><span class="admin-muted">Загрузка…</span></div>
          {:else if !logs.length}
            <div class="admin-card-body"><span class="admin-muted">Записей нет</span></div>
          {:else}
            <table class="admin-table">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Событие</th>
                  <th>User</th>
                  <th>Target</th>
                  <th>Контент</th>
                </tr>
              </thead>
              <tbody>
                {#each logs as entry}
                  <tr>
                    <td data-label="Дата">{fmtDate(entry.timestamp)}</td>
                    <td class="admin-cell-mono" data-label="Событие">{entry.event_type}</td>
                    <td class="admin-cell-mono" data-label="User">{entry.user_id || "—"}</td>
                    <td class="admin-cell-mono" data-label="Target">{entry.target_user_id || "—"}</td>
                    <td class="admin-cell-wrap" data-label="Контент">{entry.content || ""}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>

        <div class="admin-pagination">
          <span class="admin-pagination-meta">Стр. {logsPage + 1}</span>
          <div class="admin-pagination-buttons">
            <button type="button" class="admin-btn admin-btn-sm" disabled={logsPage === 0} on:click={() => { logsPage = Math.max(0, logsPage - 1); loadLogs(); }}>
              <ChevronLeft size={14} /> Назад
            </button>
            <button type="button" class="admin-btn admin-btn-sm" disabled={!logsHasMore} on:click={() => { logsPage += 1; loadLogs(); }}>
              Далее <ChevronRight size={14} />
            </button>
          </div>
        </div>
      {/if}

      {#if active === "ads"}
        <div class="admin-table-wrap">
          {#if adsLoading}
            <div class="admin-card-body"><span class="admin-muted">Загрузка…</span></div>
          {:else if !ads.length}
            <div class="admin-card-body"><span class="admin-muted">Кампаний нет</span></div>
          {:else}
            <table class="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Источник</th>
                  <th>Параметр</th>
                  <th>Стоимость</th>
                  <th>Регистрации</th>
                  <th>Конверсии</th>
                  <th>Статус</th>
                  <th class="admin-cell-actions">Действия</th>
                </tr>
              </thead>
              <tbody>
                {#each ads as ad}
                  <tr>
                    <td class="admin-cell-id" data-label="ID">#{ad.id}</td>
                    <td data-label="Источник">{ad.source}</td>
                    <td class="admin-cell-mono" data-label="Параметр">{ad.start_param}</td>
                    <td data-label="Стоимость">{fmtMoney(ad.cost)}</td>
                    <td data-label="Регистрации">{ad.stats?.registrations ?? 0}</td>
                    <td data-label="Конверсии">{ad.stats?.conversions ?? 0}</td>
                    <td data-label="Статус">
                      {#if ad.is_active}
                        <span class="admin-badge admin-badge-success">Активна</span>
                      {:else}
                        <span class="admin-badge admin-badge-muted">Выключена</span>
                      {/if}
                    </td>
                    <td class="admin-cell-actions" data-label="Действия">
                      <button type="button" class="admin-btn admin-btn-sm" on:click={() => toggleAd(ad)}>
                        {ad.is_active ? "Выкл" : "Вкл"}
                      </button>
                      <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => deleteAd(ad)}>
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      {/if}

      {#if active === "tariffs"}
        {#if tariffsLoading}
          <div class="admin-empty">Загрузка…</div>
        {:else}
          <div class="admin-stat-grid">
            <div class="admin-stat-card">
              <span class="admin-stat-label">Всего тарифов</span>
              <strong class="admin-stat-value">{tariffsCatalog.tariffs.length}</strong>
              <span class="admin-stat-trend">Включено: {enabledTariffs.length}</span>
            </div>
            <div class="admin-stat-card">
              <span class="admin-stat-label">По умолчанию</span>
              <strong class="admin-stat-value">{tariffsCatalog.default_tariff || "—"}</strong>
              <span class="admin-stat-trend">Используется для новых подписок</span>
            </div>
            <div class="admin-stat-card">
              <span class="admin-stat-label">Отключено</span>
              <strong class="admin-stat-value">{disabledTariffs}</strong>
              <span class="admin-stat-trend">Скрыто с витрины</span>
            </div>
          </div>

          <article class="admin-card">
            <header class="admin-card-head">
              <div>
                <h3>Каталог тарифов</h3>
                <small>{tariffsPath || "config/tariffs.json"}</small>
              </div>
              <button type="button" class="admin-btn admin-btn-sm" on:click={loadTariffs} disabled={tariffsLoading || tariffsSaving}>
                <RefreshCw size={13} /> Обновить
              </button>
            </header>
            <div class="admin-card-body">
              {#if !tariffsCatalog.tariffs.length}
                <div class="admin-empty">
                  Каталог пуст. Добавьте первый тариф, после сохранения будет создан JSON-файл каталога.
                </div>
              {:else}
                <div class="admin-tariff-grid">
                  {#each tariffsCatalog.tariffs as tariff}
                    <article class="admin-tariff-card" class:is-disabled={tariff.enabled === false}>
                      <div class="admin-tariff-top">
                        <div>
                          <div class="admin-tariff-title">
                            <strong>{tariffName(tariff)}</strong>
                            {#if tariff.key === tariffsCatalog.default_tariff}
                              <span class="admin-badge admin-badge-success">Default</span>
                            {/if}
                          </div>
                          <code>{tariff.key}</code>
                        </div>
                        {#if tariff.enabled === false}
                          <span class="admin-badge admin-badge-muted">Выключен</span>
                        {:else}
                          <span class="admin-badge admin-badge-success">Активен</span>
                        {/if}
                      </div>
                      <p>{tariff.descriptions?.ru || tariff.descriptions?.en || "Без описания"}</p>
                      <div class="admin-tariff-facts">
                        <span>{tariff.billing_model === "traffic" ? "Трафик" : "Периоды"}</span>
                        <span>{tariffPriceSummary(tariff)}</span>
                        <span>Squads: {(tariff.squad_uuids || []).length}</span>
                        <span>Premium: {(tariff.premium_squad_uuids || []).length ? `${tariff.premium_monthly_gb || 0} GB` : "—"}</span>
                        <span>Устройства: {tariff.hwid_device_limit ?? "env"}</span>
                      </div>
                      <div class="admin-tariff-actions">
                        <button type="button" class="admin-btn admin-btn-sm" on:click={() => openEditTariff(tariff)}>
                          Настроить
                        </button>
                        <button type="button" class="admin-btn admin-btn-sm" on:click={() => toggleTariffEnabled(tariff)} disabled={tariffsSaving}>
                          {tariff.enabled === false ? "Включить" : "Выключить"}
                        </button>
                        <button
                          type="button"
                          class="admin-btn admin-btn-sm"
                          on:click={() => setDefaultTariff(tariff.key)}
                          disabled={tariffsSaving || tariff.enabled === false || tariff.key === tariffsCatalog.default_tariff}
                        >
                          По умолчанию
                        </button>
                        <button
                          type="button"
                          class="admin-btn admin-btn-sm admin-btn-danger"
                          on:click={() => { tariffDeleteTarget = tariff; tariffDeleteOpen = true; }}
                          disabled={tariffsSaving}
                          aria-label="Удалить тариф"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </article>
                  {/each}
                </div>
              {/if}
            </div>
          </article>
        {/if}
      {/if}

      {#if active === "settings"}
        {#if settingsLoading || !settingsSections.length}
          <div class="admin-empty">{settingsLoading ? "Загрузка…" : "Нет данных"}</div>
        {:else}
          <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;">
            <p class="admin-muted" style="margin:0;">
              Изменения в админке имеют приоритет над <code>.env</code>. Кнопка «Восстановить» возвращает значение из переменных окружения.
            </p>
            <button type="button" class="admin-btn admin-btn-sm admin-btn-ghost" on:click={toggleAllSections}>
              {settingsAllOpen ? "Свернуть всё" : "Развернуть всё"}
            </button>
          </div>
          <Accordion.Root type="multiple" bind:value={settingsOpenSections} class="admin-accordion">
            {#each settingsSections as section}
              {@const dirtyInSection = section.fields.filter((f) => Boolean(settingsDirty[f.key])).length}
              {@const overriddenInSection = section.fields.filter((f) => isOverridden(f)).length}
              <Accordion.Item value={section.id} class="admin-accordion-item admin-card">
                <Accordion.Header class="admin-accordion-header">
                  <Accordion.Trigger class="admin-accordion-trigger">
                    <span class="admin-accordion-title">{sectionTitle(section.id)}</span>
                    <span class="admin-accordion-meta">
                      {section.fields.length} параметров{#if overriddenInSection} · {overriddenInSection} override{/if}{#if dirtyInSection} · {dirtyInSection} изм.{/if}
                    </span>
                    <ChevronRight size={16} class="admin-accordion-chev" />
                  </Accordion.Trigger>
                </Accordion.Header>
                <Accordion.Content class="admin-accordion-content">
                  {@const groups = groupSectionFields(section)}
                  {@const rootGroup = groups.find((g) => !g.label)}
                  {@const labelGroups = groups.filter((g) => g.label)}
                  <div class="admin-settings-fields">
                    {#if rootGroup}
                      {#each rootGroup.fields as field}
                        {@render renderField(field)}
                      {/each}
                    {/if}
                    {#if labelGroups.length}
                      <Accordion.Root
                        type="multiple"
                        value={settingsOpenSubsections[section.id] || []}
                        onValueChange={(v) => (settingsOpenSubsections = { ...settingsOpenSubsections, [section.id]: v })}
                        class="admin-subsection-accordion"
                      >
                        {#each labelGroups as group}
                          {@const subDirty = group.fields.filter((f) => Boolean(settingsDirty[f.key])).length}
                          {@const subOverridden = group.fields.filter((f) => isOverridden(f)).length}
                          <Accordion.Item value={group.id} class="admin-settings-subsection">
                            <Accordion.Header class="admin-accordion-header">
                              <Accordion.Trigger class="admin-settings-subsection-trigger">
                                <strong>{group.label}</strong>
                                <span class="admin-settings-subsection-meta">
                                  {group.fields.length} полей{#if subOverridden} · {subOverridden} override{/if}{#if subDirty} · {subDirty} изм.{/if}
                                </span>
                                <ChevronRight size={14} class="admin-accordion-chev" />
                              </Accordion.Trigger>
                            </Accordion.Header>
                            <Accordion.Content class="admin-accordion-content">
                              <div class="admin-settings-subsection-body">
                                {#each group.fields as field}
                                  {@render renderField(field)}
                                {/each}
                              </div>
                            </Accordion.Content>
                          </Accordion.Item>
                        {/each}
                      </Accordion.Root>
                    {/if}
                  </div>
                </Accordion.Content>
              </Accordion.Item>
            {/each}
          </Accordion.Root>
        {/if}
      {/if}
    </main>
  </section>
</div>

<Dialog
  open={tariffEditorOpen}
  title={tariffEditingKey ? "Настройка тарифа" : "Новый тариф"}
  description={tariffEditingKey || "Каталог будет сохранён в JSON после подтверждения"}
  closeLabel="Закрыть"
  onclose={() => (tariffEditorOpen = false)}
  class="admin-dialog admin-tariff-dialog"
>
  <Tabs.Root bind:value={tariffEditorTab} class="admin-tabs-root">
    <Tabs.List class="admin-tabs-list">
      <Tabs.Trigger value="general" class="admin-tabs-trigger">Основное</Tabs.Trigger>
      <Tabs.Trigger value="pricing" class="admin-tabs-trigger">Цены</Tabs.Trigger>
      <Tabs.Trigger value="topup" class="admin-tabs-trigger">Докупки</Tabs.Trigger>
      <Tabs.Trigger value="premium" class="admin-tabs-trigger">Premium</Tabs.Trigger>
      <Tabs.Trigger value="hwid" class="admin-tabs-trigger">Устройства</Tabs.Trigger>
    </Tabs.List>

    <Tabs.Content value="general" class="admin-tabs-content">
      <div class="admin-form-row admin-form-row-2">
        <Label.Root class="admin-field-label">
          <span>Ключ</span>
          <small>Стабильный ID для платежей и подписок</small>
          <input class="input" type="text" placeholder="standard" bind:value={tariffDraft.key} />
        </Label.Root>

        <div class="admin-field-label">
          <span>Модель тарификации</span>
          <small>Период — фикс. длительность; Трафик — оплата за GB</small>
          <Select.Root type="single" bind:value={tariffDraft.billing_model}>
            <Select.Trigger class="admin-select-trigger" aria-label="Модель">
              <span>{tariffDraft.billing_model === "traffic" ? "Трафик" : "Период"}</span>
              <ChevronDown size={14} class="admin-select-icon" />
            </Select.Trigger>
            <Select.Portal>
              <Select.Content class="admin-select-content" sideOffset={6}>
                <Select.Item value="period" class="admin-select-item">
                  <span>Период</span>
                  <Check size={14} class="admin-select-item-check" />
                </Select.Item>
                <Select.Item value="traffic" class="admin-select-item">
                  <span>Трафик</span>
                  <Check size={14} class="admin-select-item-check" />
                </Select.Item>
              </Select.Content>
            </Select.Portal>
          </Select.Root>
        </div>
      </div>

      <div class="admin-action-row admin-action-row-bordered">
        <Switch.Root
          checked={tariffDraft.enabled}
          onCheckedChange={(v) => (tariffDraft.enabled = v)}
          class="admin-switch-root"
        >
          <Switch.Thumb class="admin-switch-thumb" />
        </Switch.Root>
        <Label.Root class="admin-action-label">
          <strong>{tariffDraft.enabled ? "Тариф включён" : "Тариф выключен"}</strong>
          <small>Скрытые тарифы не отображаются на витрине</small>
        </Label.Root>
      </div>

      <div class="admin-form-row admin-form-row-2">
        <Label.Root class="admin-field-label">
          <span>Название · RU</span>
          <input class="input" type="text" placeholder="Стандарт" bind:value={tariffDraft.nameRu} />
        </Label.Root>
        <Label.Root class="admin-field-label">
          <span>Название · EN</span>
          <input class="input" type="text" placeholder="Standard" bind:value={tariffDraft.nameEn} />
        </Label.Root>
      </div>

      <div class="admin-form-row admin-form-row-2">
        <Label.Root class="admin-field-label">
          <span>Описание · RU</span>
          <input class="input" type="text" placeholder="Базовый набор серверов" bind:value={tariffDraft.descriptionRu} />
        </Label.Root>
        <Label.Root class="admin-field-label">
          <span>Описание · EN</span>
          <input class="input" type="text" placeholder="Base server pool" bind:value={tariffDraft.descriptionEn} />
        </Label.Root>
      </div>

      <div class="admin-field-label">
        <span>Основные Internal Squads</span>
        <small>{panelSquadsLoading ? "Загружаю список из панели…" : "Выберите сквады из Remnawave"}</small>
        <Select.Root
          type="single"
          bind:value={selectedBaseSquad}
          onValueChange={(value) => {
            addSquadToDraft("squadUuids", value);
            selectedBaseSquad = "";
          }}
        >
          <Select.Trigger class="admin-select-trigger" aria-label="Добавить основной сквад">
            <span>Добавить сквад</span>
            <ChevronDown size={14} class="admin-select-icon" />
          </Select.Trigger>
          <Select.Portal>
            <Select.Content class="admin-select-content" sideOffset={6}>
              {#each panelSquads as squad}
                <Select.Item value={squad.uuid} class="admin-select-item">
                  <span>{squad.name}</span>
                  <Check size={14} class="admin-select-item-check" />
                </Select.Item>
              {/each}
            </Select.Content>
          </Select.Portal>
        </Select.Root>
        <div class="admin-chip-list">
          {#each normalizeUuidList(tariffDraft.squadUuids) as uuid}
            <button type="button" class="admin-chip" on:click={() => removeSquadFromDraft("squadUuids", uuid)}>
              {squadLabel(uuid)} <X size={12} />
            </button>
          {/each}
        </div>
      </div>

      <div class="admin-form-row admin-form-row-2">
        <Label.Root class="admin-field-label">
          <span>Базовый лимит устройств</span>
          <small>Пусто — значение из env, 0 — безлимит</small>
          <input class="input" type="number" min="0" placeholder="5" bind:value={tariffDraft.hwid_device_limit} />
        </Label.Root>
        {#if tariffDraft.billing_model === "period"}
          <Label.Root class="admin-field-label">
            <span>Месячный лимит, GB</span>
            <small>0 — безлимит</small>
            <input class="input" type="number" min="0" step="0.1" bind:value={tariffDraft.monthly_gb} />
          </Label.Root>
        {:else}
          <Label.Root class="admin-field-label">
            <span>Курс конвертации, RUB/GB</span>
            <small>Нужен для перехода period → traffic</small>
            <input class="input" type="number" min="0" step="0.01" placeholder="20" bind:value={tariffDraft.conversion_rate_rub_per_gb} />
          </Label.Root>
        {/if}
      </div>
    </Tabs.Content>

    <Tabs.Content value="premium" class="admin-tabs-content">
      <section class="admin-editor-section">
        <header class="admin-editor-section-head">
          <strong>Premium-сквад и отдельный лимит</strong>
        </header>
        <div class="admin-form-row admin-form-row-2">
          <div class="admin-field-label">
            <span>Premium Internal Squads</span>
            <small>Ноды для учета трафика будут взяты из accessible nodes этих сквадов</small>
            <Select.Root
              type="single"
              bind:value={selectedPremiumSquad}
              onValueChange={(value) => {
                addSquadToDraft("premiumSquadUuids", value);
                selectedPremiumSquad = "";
              }}
            >
              <Select.Trigger class="admin-select-trigger" aria-label="Добавить premium-сквад">
                <span>Добавить premium-сквад</span>
                <ChevronDown size={14} class="admin-select-icon" />
              </Select.Trigger>
              <Select.Portal>
                <Select.Content class="admin-select-content" sideOffset={6}>
                  {#each panelSquads as squad}
                    <Select.Item value={squad.uuid} class="admin-select-item">
                      <span>{squad.name}</span>
                      <Check size={14} class="admin-select-item-check" />
                    </Select.Item>
                  {/each}
                </Select.Content>
              </Select.Portal>
            </Select.Root>
            <div class="admin-chip-list">
              {#each normalizeUuidList(tariffDraft.premiumSquadUuids) as uuid}
                <button type="button" class="admin-chip" on:click={() => removeSquadFromDraft("premiumSquadUuids", uuid)}>
                  {squadLabel(uuid)} <X size={12} />
                </button>
              {/each}
            </div>
          </div>
          <Label.Root class="admin-field-label">
            <span>Premium лимит, GB/мес.</span>
            <small>0 или пусто — нет отдельного premium-лимита</small>
            <input class="input" type="number" min="0" step="0.1" placeholder="50" bind:value={tariffDraft.premium_monthly_gb} />
          </Label.Root>
        </div>
      </section>

      <section class="admin-editor-section">
        <header class="admin-editor-section-head">
          <strong>Докупка premium-трафика</strong>
          <div class="admin-editor-section-actions">
            <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("premiumTopupRubRows", { gb: 10, price: "" })}><Plus size={12} /> RUB</button>
            <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("premiumTopupStarsRows", { gb: 10, price: "" })}><Plus size={12} /> Stars</button>
          </div>
        </header>
        <div class="admin-package-columns">
          <div class="admin-row-editor">
            <span class="admin-row-editor-caption">RUB</span>
            {#each tariffDraft.premiumTopupRubRows as row, index}
              <div class="admin-row-editor-line">
                <input class="input" type="number" min="0.1" step="0.1" placeholder="GB" bind:value={row.gb} aria-label="Premium GB" />
                <input class="input" type="number" min="0" step="0.01" placeholder="Цена" bind:value={row.price} aria-label="Цена RUB" />
                <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("premiumTopupRubRows", index)} aria-label="Удалить"><Trash2 size={13} /></button>
              </div>
            {/each}
          </div>
          <div class="admin-row-editor">
            <span class="admin-row-editor-caption">Stars</span>
            {#each tariffDraft.premiumTopupStarsRows as row, index}
              <div class="admin-row-editor-line">
                <input class="input" type="number" min="0.1" step="0.1" placeholder="GB" bind:value={row.gb} aria-label="Premium GB" />
                <input class="input" type="number" min="0" step="1" placeholder="Stars" bind:value={row.price} aria-label="Цена Stars" />
                <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("premiumTopupStarsRows", index)} aria-label="Удалить"><Trash2 size={13} /></button>
              </div>
            {/each}
          </div>
        </div>
      </section>
    </Tabs.Content>

    <Tabs.Content value="pricing" class="admin-tabs-content">
      {#if tariffDraft.billing_model === "period"}
        <section class="admin-editor-section">
          <header class="admin-editor-section-head">
            <strong>Периоды и цены</strong>
            <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("periodRows", { months: 1, rub: "", stars: "" })}>
              <Plus size={13} /> Период
            </button>
          </header>
          {#if !tariffDraft.periodRows.length}
            <p class="admin-muted">Добавьте хотя бы один период.</p>
          {/if}
          <div class="admin-row-editor">
            {#each tariffDraft.periodRows as row, index}
              <div class="admin-row-editor-line admin-row-editor-4">
                <input class="input" type="number" min="1" placeholder="Мес." bind:value={row.months} aria-label="Период (месяцы)" />
                <input class="input" type="number" min="0" step="0.01" placeholder="RUB" bind:value={row.rub} aria-label="Цена RUB" />
                <input class="input" type="number" min="0" step="1" placeholder="Stars" bind:value={row.stars} aria-label="Цена Stars" />
                <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("periodRows", index)} aria-label="Удалить">
                  <Trash2 size={13} />
                </button>
              </div>
            {/each}
          </div>
        </section>
      {:else}
        <section class="admin-editor-section">
          <header class="admin-editor-section-head">
            <strong>Пакеты трафика</strong>
            <div class="admin-editor-section-actions">
              <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("trafficRubRows", { gb: 10, price: "" })}><Plus size={12} /> RUB</button>
              <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("trafficStarsRows", { gb: 10, price: "" })}><Plus size={12} /> Stars</button>
            </div>
          </header>
          <div class="admin-package-columns">
            <div class="admin-row-editor">
              <span class="admin-row-editor-caption">RUB</span>
              {#each tariffDraft.trafficRubRows as row, index}
                <div class="admin-row-editor-line">
                  <input class="input" type="number" min="0.1" step="0.1" placeholder="GB" bind:value={row.gb} aria-label="Объём GB" />
                  <input class="input" type="number" min="0" step="0.01" placeholder="Цена" bind:value={row.price} aria-label="Цена RUB" />
                  <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("trafficRubRows", index)} aria-label="Удалить"><Trash2 size={13} /></button>
                </div>
              {/each}
            </div>
            <div class="admin-row-editor">
              <span class="admin-row-editor-caption">Stars</span>
              {#each tariffDraft.trafficStarsRows as row, index}
                <div class="admin-row-editor-line">
                  <input class="input" type="number" min="0.1" step="0.1" placeholder="GB" bind:value={row.gb} aria-label="Объём GB" />
                  <input class="input" type="number" min="0" step="1" placeholder="Stars" bind:value={row.price} aria-label="Цена Stars" />
                  <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("trafficStarsRows", index)} aria-label="Удалить"><Trash2 size={13} /></button>
                </div>
              {/each}
            </div>
          </div>
        </section>
      {/if}
    </Tabs.Content>

    <Tabs.Content value="topup" class="admin-tabs-content">
      {#if tariffDraft.billing_model === "period"}
        <section class="admin-editor-section">
          <header class="admin-editor-section-head">
            <strong>Докупка трафика для тарифа</strong>
            <div class="admin-editor-section-actions">
              <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("topupRubRows", { gb: 10, price: "" })}><Plus size={12} /> RUB</button>
              <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("topupStarsRows", { gb: 10, price: "" })}><Plus size={12} /> Stars</button>
            </div>
          </header>
          <div class="admin-package-columns">
            <div class="admin-row-editor">
              <span class="admin-row-editor-caption">RUB</span>
              {#each tariffDraft.topupRubRows as row, index}
                <div class="admin-row-editor-line">
                  <input class="input" type="number" min="0.1" step="0.1" placeholder="GB" bind:value={row.gb} aria-label="Объём GB" />
                  <input class="input" type="number" min="0" step="0.01" placeholder="Цена" bind:value={row.price} aria-label="Цена RUB" />
                  <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("topupRubRows", index)} aria-label="Удалить"><Trash2 size={13} /></button>
                </div>
              {/each}
            </div>
            <div class="admin-row-editor">
              <span class="admin-row-editor-caption">Stars</span>
              {#each tariffDraft.topupStarsRows as row, index}
                <div class="admin-row-editor-line">
                  <input class="input" type="number" min="0.1" step="0.1" placeholder="GB" bind:value={row.gb} aria-label="Объём GB" />
                  <input class="input" type="number" min="0" step="1" placeholder="Stars" bind:value={row.price} aria-label="Цена Stars" />
                  <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("topupStarsRows", index)} aria-label="Удалить"><Trash2 size={13} /></button>
                </div>
              {/each}
            </div>
          </div>
        </section>
      {:else}
        <p class="admin-muted">Для трафиковой модели докупки не нужны — настройте пакеты трафика на вкладке «Цены».</p>
      {/if}
    </Tabs.Content>

    <Tabs.Content value="hwid" class="admin-tabs-content">
      <section class="admin-editor-section">
        <header class="admin-editor-section-head">
          <strong>Пакеты HWID-устройств</strong>
          <div class="admin-editor-section-actions">
            <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("hwidRubRows", { count: 1, price: "" })}><Plus size={12} /> RUB</button>
            <button type="button" class="admin-btn admin-btn-sm" on:click={() => addDraftRow("hwidStarsRows", { count: 1, price: "" })}><Plus size={12} /> Stars</button>
          </div>
        </header>
        <div class="admin-package-columns">
          <div class="admin-row-editor">
            <span class="admin-row-editor-caption">RUB</span>
            {#each tariffDraft.hwidRubRows as row, index}
              <div class="admin-row-editor-line">
                <input class="input" type="number" min="1" step="1" placeholder="Шт." bind:value={row.count} aria-label="Количество устройств" />
                <input class="input" type="number" min="0" step="0.01" placeholder="Цена" bind:value={row.price} aria-label="Цена RUB" />
                <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("hwidRubRows", index)} aria-label="Удалить"><Trash2 size={13} /></button>
              </div>
            {/each}
          </div>
          <div class="admin-row-editor">
            <span class="admin-row-editor-caption">Stars</span>
            {#each tariffDraft.hwidStarsRows as row, index}
              <div class="admin-row-editor-line">
                <input class="input" type="number" min="1" step="1" placeholder="Шт." bind:value={row.count} aria-label="Количество устройств" />
                <input class="input" type="number" min="0" step="1" placeholder="Stars" bind:value={row.price} aria-label="Цена Stars" />
                <button type="button" class="admin-btn admin-btn-sm admin-btn-danger" on:click={() => removeDraftRow("hwidStarsRows", index)} aria-label="Удалить"><Trash2 size={13} /></button>
              </div>
            {/each}
          </div>
        </div>
      </section>
    </Tabs.Content>
  </Tabs.Root>

  <div class="admin-dialog-actions">
    <button type="button" class="admin-btn" on:click={() => (tariffEditorOpen = false)}>Отмена</button>
    <button type="button" class="admin-btn admin-btn-primary" on:click={saveTariffDraft} disabled={tariffsSaving || !tariffDraft.key.trim()}>
      <Save size={14} /> {tariffsSaving ? "Сохранение..." : "Сохранить тариф"}
    </button>
  </div>
</Dialog>

<Dialog
  open={tariffDeleteOpen}
  title="Удалить тариф?"
  description={tariffDeleteTarget ? `Тариф ${tariffDeleteTarget.key} исчезнет из каталога продаж.` : ""}
  closeLabel="Закрыть"
  onclose={() => (tariffDeleteOpen = false)}
  class="admin-dialog"
>
  <div class="admin-form-row">
    <button type="button" class="admin-btn" on:click={() => (tariffDeleteOpen = false)}>Отмена</button>
    <button type="button" class="admin-btn admin-btn-danger" on:click={deleteTariff} disabled={tariffsSaving}>
      <Trash2 size={14} /> Подтвердить удаление
    </button>
  </div>
</Dialog>

<Dialog
  open={Boolean(openedUser)}
  title={openedUser ? `Пользователь #${openedUser.user_id}` : ""}
  description={openedUser?.username ? "@" + openedUser.username : ""}
  closeLabel="Закрыть"
  onclose={closeUser}
  class="admin-dialog admin-user-dialog"
>
  {#if openedUser}
    {#if userDetailLoading || !openedUserDetail}
      <p class="admin-muted">Загрузка…</p>
    {:else}
      <div class="admin-user-summary">
        <span class="admin-avatar admin-avatar-lg">
          {#if resolvedAvatarUrl(openedUser)}
            <img src={resolvedAvatarUrl(openedUser)} alt="" loading="lazy" referrerpolicy="no-referrer" />
          {:else}
            <span>{userInitials(openedUser)}</span>
          {/if}
        </span>
        <div class="admin-user-summary-meta">
          <strong>{userDisplayName(openedUser)}</strong>
          <small>{userSecondaryName(openedUser)}</small>
          <div class="admin-user-summary-tags">
            {#if openedUser.is_banned}
              <span class="admin-badge admin-badge-danger">Бан</span>
            {:else}
              <span class="admin-badge admin-badge-success">Активен</span>
            {/if}
            {#if openedUserDetail.active_subscription}
              <span class="admin-badge admin-badge-success">Подписка</span>
            {:else}
              <span class="admin-badge admin-badge-muted">Без подписки</span>
            {/if}
            <span class="admin-badge admin-badge-muted">Заплачено: {fmtMoney(openedUserDetail.total_paid)}</span>
          </div>
        </div>
      </div>

      <Tabs.Root bind:value={userDetailTab} class="admin-tabs-root">
        <Tabs.List class="admin-tabs-list">
          <Tabs.Trigger value="profile" class="admin-tabs-trigger">Профиль</Tabs.Trigger>
          <Tabs.Trigger value="subscription" class="admin-tabs-trigger">Подписка</Tabs.Trigger>
          <Tabs.Trigger value="activity" class="admin-tabs-trigger">Активность</Tabs.Trigger>
          <Tabs.Trigger value="actions" class="admin-tabs-trigger">Действия</Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="profile" class="admin-tabs-content">
          <ul class="admin-meta-list">
            <li><span>ID</span><strong>{openedUser.user_id}</strong></li>
            <li><span>Telegram ID</span><strong>{openedUser.telegram_id || "—"}</strong></li>
            <li><span>Username</span><strong>{openedUser.username ? "@" + openedUser.username : "—"}</strong></li>
            <li><span>Email</span><strong>{openedUser.email || "—"}</strong></li>
            <li><span>Регистрация</span><strong>{fmtDate(openedUser.registration_date)}</strong></li>
            <li><span>Реф. код</span><strong>{openedUserDetail.user?.referral_code || "—"}</strong></li>
            <li><span>Логов</span><strong>{openedUserDetail.log_count}</strong></li>
          </ul>
        </Tabs.Content>

        <Tabs.Content value="subscription" class="admin-tabs-content">
          {#if openedUserDetail.active_subscription}
            <ul class="admin-meta-list">
              <li><span>Активна до</span><strong>{fmtDate(openedUserDetail.active_subscription.end_date)}</strong></li>
              <li><span>Тариф</span><strong>{openedUserDetail.active_subscription.tariff_key || "—"}</strong></li>
              <li><span>Авто-продление</span><strong>{pretty(openedUserDetail.active_subscription.auto_renew_enabled)}</strong></li>
              <li><span>Провайдер</span><strong>{openedUserDetail.active_subscription.provider || "—"}</strong></li>
            </ul>
          {:else}
            <p class="admin-muted">Активной подписки нет</p>
          {/if}

          {#if (openedUserDetail.subscriptions || []).length}
            <Separator.Root class="admin-separator" />
            <div class="admin-subsection-title">История подписок · {openedUserDetail.subscriptions.length}</div>
            <div class="admin-mini-list">
              {#each openedUserDetail.subscriptions.slice(0, 8) as sub}
                <div class="admin-mini-list-row">
                  <div>
                    <strong>{sub.tariff_key || "Без тарифа"}</strong>
                    <small>до {fmtDate(sub.end_date)}</small>
                  </div>
                  {#if sub.is_active}
                    <span class="admin-badge admin-badge-success">Активна</span>
                  {:else}
                    <span class="admin-badge admin-badge-muted">{sub.status_from_panel || "История"}</span>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </Tabs.Content>

        <Tabs.Content value="activity" class="admin-tabs-content">
          <div class="admin-subsection-title">Последние платежи · {(openedUserDetail.recent_payments || []).length}</div>
          {#if (openedUserDetail.recent_payments || []).length}
            <div class="admin-mini-list">
              {#each openedUserDetail.recent_payments.slice(0, 8) as payment}
                <div class="admin-mini-list-row">
                  <div>
                    <strong>{fmtMoney(payment.amount, payment.currency)}</strong>
                    <small>{payment.provider} · {fmtDateShort(payment.created_at)}</small>
                  </div>
                  <span class="admin-badge admin-badge-{paymentStatusVariant(payment.status)}">{payment.status}</span>
                </div>
              {/each}
            </div>
          {:else}
            <p class="admin-muted">Платежей нет</p>
          {/if}
        </Tabs.Content>

        <Tabs.Content value="actions" class="admin-tabs-content">
          <section class="admin-action-section">
            <header class="admin-action-section-head">
              <strong>Безопасные действия</strong>
              <small>Можно выполнять без подтверждения</small>
            </header>
            <div class="admin-action-grid">
              <button type="button" class="admin-btn" on:click={resetTrialUser} disabled={userActionBusy}>
                <RefreshCw size={14} /> Сбросить триал
              </button>
              <div class="admin-input-row">
                <input class="input" type="number" min="1" bind:value={userExtendDays} aria-label="Дней" />
                <button type="button" class="admin-btn" on:click={extendUser} disabled={userActionBusy}>
                  <Plus size={14} /> Продлить
                </button>
              </div>
            </div>
          </section>

          <Label.Root class="admin-field-label">
            <span>Сообщение в Telegram</span>
            <small>Поддерживается HTML-разметка Telegram</small>
            <textarea class="admin-textarea" rows="3" placeholder="Текст сообщения" bind:value={userMessageDraft}></textarea>
          </Label.Root>
          <button type="button" class="admin-btn admin-btn-primary" on:click={sendUserMessage} disabled={userActionBusy || !userMessageDraft.trim()}>
            <Send size={14} /> Отправить сообщение
          </button>

          <section class="admin-danger-zone">
            <header class="admin-danger-zone-head">
              <strong>Опасные действия</strong>
              <small>Эти действия требуют подтверждения и (для удаления) необратимы</small>
            </header>
            <div class="admin-action-grid">
              {#if openedUser.is_banned}
                <button type="button" class="admin-btn admin-btn-danger-soft" on:click={requestBanToggle} disabled={userActionBusy}>
                  <UserPlus size={14} /> Разбанить пользователя
                </button>
              {:else}
                <button type="button" class="admin-btn admin-btn-danger" on:click={requestBanToggle} disabled={userActionBusy}>
                  <UserMinus size={14} /> Заблокировать
                </button>
              {/if}
              <button type="button" class="admin-btn admin-btn-danger" on:click={() => (userDeleteOpen = true)} disabled={userActionBusy}>
                <Trash2 size={14} /> Удалить аккаунт
              </button>
            </div>
          </section>
        </Tabs.Content>
      </Tabs.Root>
    {/if}
  {/if}
</Dialog>

<Dialog
  open={userBanConfirmOpen}
  title="Заблокировать пользователя?"
  description={openedUser ? `${userDisplayName(openedUser)} больше не сможет взаимодействовать с ботом. Действие можно отменить позже.` : ""}
  closeLabel="Закрыть"
  onclose={() => (userBanConfirmOpen = false)}
  class="admin-dialog"
>
  <div class="admin-dialog-actions">
    <button type="button" class="admin-btn" on:click={() => (userBanConfirmOpen = false)}>Отмена</button>
    <button type="button" class="admin-btn admin-btn-danger" on:click={() => applyBanToggle(true)} disabled={userActionBusy}>
      <UserMinus size={14} /> Заблокировать
    </button>
  </div>
</Dialog>

<Dialog
  open={userDeleteOpen}
  title="Удалить пользователя?"
  description="Действие необратимо. Удалятся все платежи, подписки и логи."
  closeLabel="Закрыть"
  onclose={() => (userDeleteOpen = false)}
  class="admin-dialog"
>
  <div class="admin-form-row">
    <button type="button" class="admin-btn" on:click={() => (userDeleteOpen = false)}>Отмена</button>
    <button type="button" class="admin-btn admin-btn-danger" on:click={deleteUser} disabled={userActionBusy}>
      <Trash2 size={14} /> Подтвердить удаление
    </button>
  </div>
</Dialog>

<Dialog open={promoCreateOpen} title="Новый промокод" closeLabel="Закрыть" onclose={() => (promoCreateOpen = false)} class="admin-dialog">
  <div class="admin-form">
    <label>
      <span>Код</span>
      <input class="input" type="text" placeholder="WELCOME10" bind:value={promoDraft.code} />
    </label>
    <div class="admin-form-row">
      <label>
        <span>Бонус (дней)</span>
        <input class="input" type="number" min="1" bind:value={promoDraft.bonus_days} />
      </label>
      <label>
        <span>Макс. активаций</span>
        <input class="input" type="number" min="1" bind:value={promoDraft.max_activations} />
      </label>
      <label>
        <span>Срок действия</span>
        <small>0 — бессрочно</small>
        <input class="input" type="number" min="0" bind:value={promoDraft.valid_days} />
      </label>
    </div>
    <button type="button" class="admin-btn admin-btn-primary" on:click={createPromo} disabled={!promoDraft.code.trim()}>
      <Check size={14} /> Создать
    </button>
  </div>
</Dialog>

<Dialog open={adCreateOpen} title="Новая кампания" closeLabel="Закрыть" onclose={() => (adCreateOpen = false)} class="admin-dialog">
  <div class="admin-form">
    <label>
      <span>Источник</span>
      <input class="input" type="text" placeholder="telegram_ads" bind:value={adDraft.source} />
    </label>
    <label>
      <span>start-параметр</span>
      <small>Передаётся в /start, должен быть уникален</small>
      <input class="input" type="text" placeholder="ads_summer25" bind:value={adDraft.start_param} />
    </label>
    <label>
      <span>Стоимость, RUB</span>
      <input class="input" type="number" step="0.01" min="0" bind:value={adDraft.cost} />
    </label>
    <button type="button" class="admin-btn admin-btn-primary" on:click={createAd} disabled={!adDraft.source.trim() || !adDraft.start_param.trim()}>
      <Check size={14} /> Создать
    </button>
  </div>
</Dialog>
