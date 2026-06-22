import { readable } from "svelte/store";
import { TableHandler } from "@vincjo/datatables";

const watchedTables = new WeakMap();
const watchedTableListeners = new WeakSet();

export function createAdminDatatable(rows = [], options = {}) {
  return new TableHandler(Array.isArray(rows) ? rows : [], options);
}

export function syncAdminDatatable(table, rows = []) {
  table.setRows(Array.isArray(rows) ? rows : []);
  notifyAdminDatatable(table);
}

function notifyAdminDatatable(table) {
  const subscribers = watchedTables.get(table);
  if (!subscribers) return;
  for (const set of subscribers) set(table);
}

function ensureAdminDatatableListener(table) {
  if (!table || watchedTableListeners.has(table)) return;
  watchedTableListeners.add(table);
  table.event.add("change", () => notifyAdminDatatable(table));
}

// The runes-based TableHandler keeps rows, currentPage and pageCount in Svelte 5
// signals that legacy-mode admin components cannot track through a plain const.
// Bridge handler changes into a Svelte store, and notify immediately after
// syncAdminDatatable() so first-load rows render without a user action.
export function watchAdminDatatable(table) {
  return readable(table, (set) => {
    if (!table) return;
    ensureAdminDatatableListener(table);
    let subscribers = watchedTables.get(table);
    if (!subscribers) {
      subscribers = new Set();
      watchedTables.set(table, subscribers);
    }
    subscribers.add(set);
    set(table);
    return () => {
      subscribers.delete(set);
      if (subscribers.size === 0) watchedTables.delete(table);
    };
  });
}
