import { TableHandler } from "@vincjo/datatables";

type TableHandlerArgs = ConstructorParameters<typeof TableHandler>;
type TableRows = NonNullable<TableHandlerArgs[0]>;
type TableOptions = NonNullable<TableHandlerArgs[1]>;
type RowsTable<T> = object & {
  setRows(rows: T[]): void;
};
export function createAdminDatatable(
  rows: TableRows = [],
  options: TableOptions = {}
): TableHandler {
  return new TableHandler(Array.isArray(rows) ? rows : [], options);
}

export function syncAdminDatatable<T>(table: RowsTable<T>, rows: T[] = []): void {
  table.setRows(Array.isArray(rows) ? rows : []);
}
