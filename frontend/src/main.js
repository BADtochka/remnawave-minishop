import { mount } from "svelte";

import App from "./App.svelte";
import "./styles.css";

async function loadBootstrap() {
  if (document.getElementById("webapp-config")) return;
  try {
    const response = await fetch("/api/bootstrap", {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return;
    const payload = await response.json();
    for (const [id, value] of [
      ["webapp-config", payload.config],
      ["i18n", payload.i18n],
    ]) {
      const script = document.createElement("script");
      script.id = id;
      script.type = "application/json";
      script.textContent = JSON.stringify(value || {});
      document.head.appendChild(script);
    }
  } catch (_error) {
    void _error;
  }
}

const target = document.getElementById("app");

if (target) {
  loadBootstrap().finally(() => {
    mount(App, { target });
  });
}
