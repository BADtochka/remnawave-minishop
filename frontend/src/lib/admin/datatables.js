import { readable } from "svelte/store";
import { TableHandler } from "@vincjo/datatables";

export function createAdminDatatable(rows = [], options = {}) {
  return new TableHandler(Array.isArray(rows) ? rows : [], options);
}

export function syncAdminDatatable(table, rows = []) {
  table.setRows(Array.isArray(rows) ? rows : []);
}

// The runes-based TableHandler keeps its state (rows, currentPage, pageCount)
// in Svelte 5 signals that legacy-mode admin components ($: and {#each}) do not
// track — Svelte wraps reads of a plain `const` handler in untrack(). Bridge the
// handler's "change" event (fired on paging, setRows and sorting) into a Svelte
// store so legacy reactivity re-runs on every mutation.
export function watchAdminDatatable(table) {
  return readable(table, (set) => {
    if (!table) return;
    let disposed = false;
    const notify = () => {
      if (!disposed) set(table);
    };
    table.event.add("change", notify);
    return () => {
      disposed = true;
    };
  });
}
