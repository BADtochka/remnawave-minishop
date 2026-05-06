<script>
  import { onDestroy } from "svelte";

  import { cn } from "./lib/utils.js";

  const LOGO_LOAD_TIMEOUT_MS = 2600;

  export let logoUrl = "";
  export let emoji = "🫥";
  let className = "";
  export { className as class };

  let loaded = false;
  let failed = false;
  let lastLogoUrl = "";
  let logoLoadTimer = null;
  let logoLoadTimerUrl = "";

  $: normalizedLogoUrl = String(logoUrl || "").trim();
  $: normalizedEmoji = String(emoji || "🫥").trim() || "🫥";
  $: if (normalizedLogoUrl !== lastLogoUrl) {
    lastLogoUrl = normalizedLogoUrl;
    loaded = false;
    failed = false;
  }
  $: if (normalizedLogoUrl && !loaded && !failed) armLogoLoadTimeout();
  $: if (!normalizedLogoUrl || loaded || failed) clearLogoLoadTimeout();

  onDestroy(clearLogoLoadTimeout);

  function clearLogoLoadTimeout() {
    if (logoLoadTimer) {
      window.clearTimeout(logoLoadTimer);
      logoLoadTimer = null;
    }
    logoLoadTimerUrl = "";
  }

  function armLogoLoadTimeout() {
    if (typeof window === "undefined") return;
    if (logoLoadTimer && logoLoadTimerUrl === normalizedLogoUrl) return;
    clearLogoLoadTimeout();
    logoLoadTimerUrl = normalizedLogoUrl;
    logoLoadTimer = window.setTimeout(() => {
      if (logoLoadTimerUrl === normalizedLogoUrl && !loaded) failed = true;
    }, LOGO_LOAD_TIMEOUT_MS);
  }
</script>

<div
  class={cn(
    "brand-mark",
    normalizedLogoUrl && !failed && !loaded && "brand-mark-loading",
    normalizedLogoUrl && !failed && loaded && "brand-mark-loaded",
    className,
  )}
  aria-busy={normalizedLogoUrl && !failed && !loaded ? "true" : undefined}
>
  {#if normalizedLogoUrl && !failed}
    {#if !loaded}
      <span class="brand-mark-spinner" aria-hidden="true"></span>
    {/if}
    <img
      class:loaded={loaded}
      src={normalizedLogoUrl}
      alt=""
      loading="lazy"
      decoding="async"
      on:load={() => (loaded = true)}
      on:error={() => (failed = true)}
    />
  {:else}
    <span>{normalizedEmoji}</span>
  {/if}
</div>
