<script>
  import { Check, FileText, RefreshCw, Save } from "$components/ui/icons.js";
  import { getContext, onMount } from "svelte";
  import { AdminBadge, AdminButton, AdminEmptyState } from "$components/patterns/admin/index.js";
  import { localizedThemeName } from "$lib/webapp/themeStyle.js";

  export let at;
  export let currentLang = "ru";

  const themesStore = getContext("themesStore");

  $: ({ themesCatalog, themesLoading, themesDir, themesSaving } = $themesStore);
  $: activeKey = themesCatalog.default_theme;

  function themeTitle(theme) {
    return localizedThemeName(theme, currentLang) || "—";
  }

  function themeDescription(theme) {
    const folder = `${themesDir || "data/themes"}/${theme.key}`;
    return theme.css_file ? `${folder}/${theme.css_file}` : `${folder}/theme.json`;
  }

  function toggleAccent(event, theme) {
    event.stopPropagation();
    themesStore.togglePrimaryAccent(theme.key, event.currentTarget.checked);
  }

  function toggleAdminTheme(event, theme) {
    event.stopPropagation();
    themesStore.toggleAdminUse(theme.key, event.currentTarget.checked);
  }

  function isThemeOptionEvent(event) {
    return Boolean(event?.target?.closest?.(".admin-theme-card-option"));
  }

  function selectTheme(theme, event = null) {
    if (isThemeOptionEvent(event)) return;
    if (!themesSaving) themesStore.setCurrentTheme(theme.key);
  }

  function handleCardKeydown(event, theme) {
    if (isThemeOptionEvent(event)) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    selectTheme(theme);
  }

  onMount(() => {
    themesStore.loadThemes();
  });
</script>

{#if themesLoading}
  <AdminEmptyState>{at("loading", {}, "Загрузка…")}</AdminEmptyState>
{:else}
  <article class="admin-card">
    <header class="admin-card-head">
      <div>
        <h3>{at("themes_catalog_title", {}, "Темы Web App")}</h3>
        <small
          >{at(
            "themes_catalog_sub",
            {},
            "Текущая тема выбирается карточкой; внешний вид редактируется файлами в папке темы"
          )}</small
        >
      </div>
      <div class="admin-editor-section-actions">
        <AdminButton
          size="sm"
          onclick={themesStore.loadThemes}
          disabled={themesLoading || themesSaving}
        >
          <RefreshCw size={13} />
          {at("btn_refresh", {}, "Обновить")}
        </AdminButton>
        <AdminButton
          size="sm"
          variant="primary"
          onclick={themesStore.saveThemes}
          disabled={themesLoading || themesSaving}
        >
          <Save size={13} />
          {at("btn_save", {}, "Сохранить")}
        </AdminButton>
      </div>
    </header>
    <div class="admin-card-body">
      {#if !themesCatalog.themes.length}
        <AdminEmptyState>
          {at(
            "themes_catalog_empty",
            {},
            "Каталог пуст. Добавьте папку темы в data/themes и обновите список."
          )}
        </AdminEmptyState>
      {:else}
        <div class="admin-theme-grid">
          {#each themesCatalog.themes as theme (theme.key)}
            {@const isCurrent = theme.key === activeKey}
            <div
              role="button"
              tabindex={themesSaving ? -1 : 0}
              class="admin-theme-card"
              class:is-current={isCurrent}
              class:is-disabled={theme.enabled === false}
              aria-pressed={isCurrent}
              aria-disabled={themesSaving}
              onclick={(event) => selectTheme(theme, event)}
              onkeydown={(event) => handleCardKeydown(event, theme)}
            >
              <span class="admin-theme-card-main">
                <span class="admin-theme-card-title">
                  <strong>{themeTitle(theme)}</strong>
                  {#if isCurrent}
                    <AdminBadge variant="success">{at("status_current", {}, "Текущая")}</AdminBadge>
                  {/if}
                </span>
                <small>{theme.key}</small>
              </span>
              <span class="admin-theme-card-meta">
                <FileText size={15} />
                <span>{themeDescription(theme)}</span>
              </span>
              <label class="admin-theme-card-option">
                <input
                  type="checkbox"
                  checked={theme.use_primary_accent !== false}
                  disabled={themesSaving}
                  onchange={(event) => toggleAccent(event, theme)}
                />
                <span>{at("themes_use_primary_accent", {}, "Протягивать акцент")}</span>
              </label>
              <label class="admin-theme-card-option">
                <input
                  type="checkbox"
                  checked={theme.use_in_admin !== false}
                  disabled={themesSaving}
                  onchange={(event) => toggleAdminTheme(event, theme)}
                />
                <span>{at("themes_use_in_admin", {}, "Использовать в админке")}</span>
              </label>
              <span class="admin-theme-card-check" aria-hidden="true">
                {#if isCurrent}<Check size={18} />{/if}
              </span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </article>
{/if}

<style>
  .admin-theme-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
  }

  .admin-theme-card {
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
    min-height: 118px;
    padding: 14px;
    border: 1px solid var(--admin-border);
    border-radius: 8px;
    background: var(--admin-surface);
    color: var(--admin-text);
    text-align: left;
    cursor: pointer;
  }

  .admin-theme-card:hover {
    border-color: var(--admin-border-strong);
    background: color-mix(in srgb, var(--admin-surface-2) 72%, var(--admin-surface));
  }

  .admin-theme-card.is-current {
    border-color: var(--accent);
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 44%, transparent);
  }

  .admin-theme-card.is-disabled {
    opacity: 0.58;
  }

  .admin-theme-card-main {
    display: grid;
    align-content: start;
    gap: 5px;
    min-width: 0;
  }

  .admin-theme-card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .admin-theme-card-title strong {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .admin-theme-card-main small,
  .admin-theme-card-meta {
    color: var(--admin-muted);
    font-size: 12px;
  }

  .admin-theme-card-meta {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: 7px;
    min-width: 0;
  }

  .admin-theme-card-meta span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .admin-theme-card-option {
    grid-column: 1 / -1;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    width: fit-content;
    max-width: 100%;
    color: var(--admin-muted);
    font-size: 12px;
    cursor: default;
  }

  .admin-theme-card-option input {
    flex: 0 0 auto;
    width: 15px;
    height: 15px;
    margin: 0;
    accent-color: var(--accent);
  }

  .admin-theme-card-option span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .admin-theme-card-check {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    color: var(--accent);
  }
</style>
