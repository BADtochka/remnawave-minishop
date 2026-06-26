import type { ApiClient } from "./publicApi";
import {
  buildAdminPaymentsExportPath,
  buildAdminPaymentsUserPath,
  buildAdminSupportPath,
  buildAdminUsersPath,
} from "./publicApi";

type ApiCall = ApiClient["api"];
type ApiUncheckedCall = ApiClient["apiUnchecked"];

declare const apiCall: ApiCall;
declare const apiUncheckedCall: ApiUncheckedCall;

apiCall("/admin/users");
apiCall("/admin/users?page=1");
apiCall("/api/admin/payments/export.csv");
apiCall(buildAdminUsersPath());
apiCall(buildAdminPaymentsExportPath());

const supportPathNoId: ReturnType<typeof buildAdminSupportPath> = buildAdminSupportPath();
const supportPathWithId: ReturnType<typeof buildAdminSupportPath> = buildAdminSupportPath(42);
const paymentsUserPathNoId: ReturnType<typeof buildAdminPaymentsUserPath> =
  buildAdminPaymentsUserPath();
const paymentsUserPathWithId: ReturnType<typeof buildAdminPaymentsUserPath> =
  buildAdminPaymentsUserPath(42);

void supportPathNoId;
void supportPathWithId;
void paymentsUserPathNoId;
void paymentsUserPathWithId;

apiUncheckedCall("/random/unknown/path");

// @ts-expect-error: arbitrary API paths should be rejected by typed api signature
apiCall("/random/unknown/path");
