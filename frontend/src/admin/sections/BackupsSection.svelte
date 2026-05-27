<script>
  import { getContext, onMount } from "svelte";
  import {
    AdminBadge,
    AdminButton,
    AdminEmptyState,
    AdminTable,
    AdminTableSkeleton,
  } from "$components/patterns/admin/index.js";
  import {
    CheckCircle2,
    Database,
    Plus,
    RefreshCw,
    Server,
    TriangleAlert,
    Upload,
  } from "$components/ui/icons.js";

  export let at = (key) => key;
  export let fmtDate = (value) => value;

  const backupsStore = getContext("backupsStore");

  let selectedName = "";
  let restoreDatabase = true;
  let restoreCompose = false;
  let fileInput = null;

  $: ({
    archives,
    backupDir,
    backupsCreating,
    backupsLoading,
    backupsUploading,
    backupsRestoring,
    lastRestore,
  } = $backupsStore);
  $: if (!selectedName && archives?.length) selectedName = archives[0].name;
  $: if (selectedName && archives?.length && !archives.some((item) => item.name === selectedName)) {
    selectedName = archives[0].name;
  }
  $: selectedArchive = (archives || []).find((item) => item.name === selectedName) || null;
  $: if (selectedArchive && restoreDatabase && !selectedArchive.has_database)
    restoreDatabase = false;
  $: if (selectedArchive && restoreCompose && !selectedArchive.has_compose) restoreCompose = false;
  $: if (selectedArchive && !restoreDatabase && !restoreCompose) {
    if (selectedArchive.has_database) restoreDatabase = true;
    else if (selectedArchive.has_compose) restoreCompose = true;
  }
  $: canRestore = Boolean(
    selectedArchive && (restoreDatabase || restoreCompose) && !backupsRestoring && !backupsCreating
  );
  $: backupHeaders = [
    "",
    at("backups_col_archive", {}, "Архив"),
    at("backups_col_created", {}, "Создан"),
    at("backups_col_size", {}, "Размер"),
    at("backups_col_contents", {}, "Состав"),
    at("backups_col_warnings", {}, "Предупреждения"),
  ];

  function formatSize(sizeBytes) {
    const units = ["B", "KB", "MB", "GB"];
    let value = Number(sizeBytes || 0);
    let unit = units[0];
    for (unit of units) {
      if (value < 1024 || unit === "GB") break;
      value /= 1024;
    }
    return unit === "B" ? `${Math.round(value)} ${unit}` : `${value.toFixed(1)} ${unit}`;
  }

  function archiveDate(archive) {
    return archive?.created_at_local || archive?.created_at || archive?.modified_at || "";
  }

  function selectedComponentsText() {
    const parts = [];
    if (restoreDatabase) parts.push(at("backups_target_database", {}, "БД"));
    if (restoreCompose) parts.push(at("backups_target_compose", {}, "compose-папку"));
    return parts.join(" + ");
  }

  async function uploadSelectedFile(event) {
    const file = event?.currentTarget?.files?.[0];
    if (!file) return;
    const archive = await backupsStore.uploadArchive(file);
    if (archive?.name) selectedName = archive.name;
    event.currentTarget.value = "";
  }

  async function createManualBackup() {
    const archive = await backupsStore.createBackup();
    if (archive?.name) selectedName = archive.name;
  }

  async function restoreSelected() {
    if (!canRestore) return;
    const confirmText = at(
      "backups_restore_confirm",
      { name: selectedName, components: selectedComponentsText() },
      `Запустить восстановление из ${selectedName}?`
    );
    if (typeof window !== "undefined" && !window.confirm(confirmText)) return;

    const ok = await backupsStore.restoreArchive({
      archiveName: selectedName,
      restoreDatabase,
      restoreCompose,
    });
    if (ok) await backupsStore.loadArchives();
  }

  onMount(() => {
    backupsStore.loadArchives();
  });
</script>

<div class="backups-layout">
  <div class="admin-toolbar admin-toolbar-card backups-toolbar">
    <div class="backups-toolbar-main">
      <AdminButton onclick={() => backupsStore.loadArchives()} disabled={backupsLoading}>
        <RefreshCw size={14} />
        {at("btn_refresh", {}, "Обновить")}
      </AdminButton>
      <AdminButton onclick={createManualBackup} disabled={backupsCreating || backupsRestoring}>
        <Plus size={14} />
        {backupsCreating
          ? at("backups_creating", {}, "Создание...")
          : at("backups_create", {}, "Создать бэкап")}
      </AdminButton>
      <AdminButton onclick={() => fileInput?.click()} disabled={backupsUploading}>
        <Upload size={14} />
        {backupsUploading
          ? at("backups_uploading", {}, "Загрузка...")
          : at("backups_upload", {}, "Загрузить архив")}
      </AdminButton>
      <input
        bind:this={fileInput}
        class="backups-file-input"
        type="file"
        accept=".zip,application/zip"
        on:change={uploadSelectedFile}
      />
    </div>
    <div class="admin-toolbar-summary">
      <span class="admin-toolbar-field-label">{at("backups_dir", {}, "Каталог")}</span>
      <strong class="backups-dir">{backupDir || "data/backups"}</strong>
    </div>
  </div>

  <article class="admin-card backups-restore-card">
    <header class="admin-card-head">
      <div>
        <h3>{at("backups_restore_title", {}, "Восстановление")}</h3>
        {#if selectedArchive}
          <small class="backups-selected-name">{selectedArchive.name}</small>
        {/if}
      </div>
      {#if lastRestore}
        <AdminBadge variant="success">
          <CheckCircle2 size={12} />
          {at("backups_last_restore_done", {}, "Готово")}
        </AdminBadge>
      {/if}
    </header>
    <div class="admin-card-body backups-restore-body">
      <label class="backups-check" class:is-disabled={!selectedArchive?.has_database}>
        <input
          type="checkbox"
          bind:checked={restoreDatabase}
          disabled={!selectedArchive?.has_database || backupsRestoring}
        />
        <Database size={16} />
        <span>{at("backups_target_database", {}, "БД")}</span>
      </label>
      <label class="backups-check" class:is-disabled={!selectedArchive?.has_compose}>
        <input
          type="checkbox"
          bind:checked={restoreCompose}
          disabled={!selectedArchive?.has_compose || backupsRestoring}
        />
        <Server size={16} />
        <span>{at("backups_target_compose", {}, "compose-папка")}</span>
      </label>
      <AdminButton variant="danger" onclick={restoreSelected} disabled={!canRestore}>
        <RefreshCw size={14} />
        {backupsRestoring
          ? at("backups_restoring", {}, "Восстановление...")
          : at("backups_restore_run", {}, "Запустить")}
      </AdminButton>
    </div>
    {#if lastRestore?.compose_pre_restore_archive}
      <div class="backups-restore-note">
        {at(
          "backups_pre_restore_snapshot",
          { path: lastRestore.compose_pre_restore_archive },
          "Текущая compose-папка сохранена перед заменой."
        )}
      </div>
    {/if}
  </article>

  <div class="admin-table-wrap">
    {#if backupsLoading}
      <AdminTableSkeleton
        headers={backupHeaders}
        rows={6}
        widths={["36px", "minmax(220px, 1fr)", "150px", "80px", "150px", "120px"]}
      />
    {:else if !archives?.length}
      <AdminEmptyState tone="card">
        <span class="admin-muted">{at("backups_empty", {}, "Архивов пока нет")}</span>
      </AdminEmptyState>
    {:else}
      <AdminTable class="backups-table">
        <thead>
          <tr>
            <th aria-label={at("select", {}, "Выбрать")}></th>
            <th>{at("backups_col_archive", {}, "Архив")}</th>
            <th>{at("backups_col_created", {}, "Создан")}</th>
            <th>{at("backups_col_size", {}, "Размер")}</th>
            <th>{at("backups_col_contents", {}, "Состав")}</th>
            <th>{at("backups_col_warnings", {}, "Предупреждения")}</th>
          </tr>
        </thead>
        <tbody>
          {#each archives as archive (archive.name)}
            <tr class:is-selected={archive.name === selectedName}>
              <td data-label={at("select", {}, "Выбрать")}>
                <input
                  type="radio"
                  name="backup-archive"
                  value={archive.name}
                  checked={archive.name === selectedName}
                  on:change={() => (selectedName = archive.name)}
                  aria-label={archive.name}
                />
              </td>
              <td
                class="admin-cell-wrap backups-name"
                data-label={at("backups_col_archive", {}, "Архив")}
              >
                {archive.name}
              </td>
              <td data-label={at("backups_col_created", {}, "Создан")}
                >{fmtDate(archiveDate(archive))}</td
              >
              <td data-label={at("backups_col_size", {}, "Размер")}
                >{formatSize(archive.size_bytes)}</td
              >
              <td data-label={at("backups_col_contents", {}, "Состав")}>
                <span class="backups-badges">
                  {#if archive.has_database}
                    <AdminBadge variant="success">{at("backups_badge_db", {}, "БД")}</AdminBadge>
                  {/if}
                  {#if archive.has_compose}
                    <AdminBadge variant="muted">
                      {at("backups_badge_compose", {}, "Compose")}
                    </AdminBadge>
                  {/if}
                </span>
              </td>
              <td data-label={at("backups_col_warnings", {}, "Предупреждения")}>
                {#if archive.warnings?.length}
                  <AdminBadge variant="warning">
                    <TriangleAlert size={12} />
                    {archive.warnings.length}
                  </AdminBadge>
                {:else}
                  <span class="admin-muted">-</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </AdminTable>
    {/if}
  </div>
</div>

<style>
  .backups-layout {
    display: grid;
    gap: 12px;
  }

  .backups-toolbar-main {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .backups-file-input {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }

  .backups-dir,
  .backups-selected-name,
  .backups-name {
    font-family: var(--font-mono);
    word-break: break-word;
  }

  .backups-dir {
    max-width: min(420px, 70vw);
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .backups-restore-body {
    display: grid;
    grid-template-columns: repeat(2, minmax(160px, 1fr)) auto;
    gap: 10px;
    align-items: center;
  }

  .backups-check {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 38px;
    padding: 8px 10px;
    border: 1px solid var(--admin-border);
    border-radius: 8px;
    background: var(--admin-surface-2);
    color: var(--admin-text);
    font-size: 13px;
  }

  .backups-check input {
    width: 16px;
    height: 16px;
    margin: 0;
  }

  .backups-check.is-disabled {
    opacity: 0.55;
  }

  .backups-restore-note {
    border-top: 1px solid var(--admin-border);
    padding: 10px 14px;
    color: var(--admin-muted);
    font-size: 12px;
  }

  :global(.backups-table tbody tr.is-selected) {
    background: color-mix(in srgb, var(--accent) 12%, transparent);
  }

  .backups-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  @media (max-width: 760px) {
    .backups-restore-body {
      grid-template-columns: minmax(0, 1fr);
    }

    :global(.backups-restore-body .admin-btn) {
      width: 100%;
    }
  }
</style>
