import { readCookie } from "./session.js";
import type { paths } from "../api/openapi.generated";

type HttpMethod = "get" | "put" | "post" | "delete" | "patch";
type ApiPath = keyof paths;
type ApiPathFor<Path extends string> = Path extends `/api${string}` ? Path : `/api${Path}`;
type KnownApiPath<Path extends string> = ApiPathFor<Path> & ApiPath;
type OperationFor<Path extends string, Method extends HttpMethod> =
  KnownApiPath<Path> extends never ? never : NonNullable<paths[KnownApiPath<Path>][Method]>;
type JsonRequestBody<Operation> = Operation extends {
  requestBody: { content: { "application/json": infer Body } };
}
  ? Body
  : Record<string, unknown>;
type JsonResponse<Operation> = Operation extends {
  responses: { 200: { content: { "application/json": infer Body } } };
}
  ? Body
  : Record<string, unknown>;
type ApiResponse<Path extends string> =
  | JsonResponse<OperationFor<Path, "get">>
  | JsonResponse<OperationFor<Path, "post">>
  | JsonResponse<OperationFor<Path, "put">>
  | JsonResponse<OperationFor<Path, "patch">>
  | JsonResponse<OperationFor<Path, "delete">>;
type PostPayload<Path extends string> = JsonRequestBody<OperationFor<Path, "post">>;
type PostResponse<Path extends string> = JsonResponse<OperationFor<Path, "post">>;

type MockContext = Record<string, unknown>;
type MockApi = (
  path: string,
  options: RequestInit,
  context: MockContext
) => unknown | Promise<unknown>;

type ApiClientOptions = {
  apiBase?: string;
  csrfCookieName?: string;
  getCsrfToken?: () => string;
  onUnauthorized?: () => void;
  mockApi?: MockApi | null;
  getMockContext?: () => MockContext;
};

type ApiClient = {
  api<Path extends string>(path: Path, options?: RequestInit): Promise<ApiResponse<Path>>;
  publicApi<Path extends string>(
    path: Path,
    payload?: PostPayload<Path>,
    options?: Pick<RequestInit, "signal">
  ): Promise<PostResponse<Path>>;
};

export function createApiClient({
  apiBase = "",
  csrfCookieName = "rw_webapp_csrf",
  getCsrfToken = () => "",
  onUnauthorized = () => {},
  mockApi = null,
  getMockContext = () => ({}),
}: ApiClientOptions = {}): ApiClient {
  const isFormDataBody = (body: BodyInit | null | undefined) =>
    typeof FormData !== "undefined" && body instanceof FormData;

  async function api<Path extends string>(
    path: Path,
    options: RequestInit = {}
  ): Promise<ApiResponse<Path>> {
    if (mockApi) return (await mockApi(path, options, getMockContext())) as ApiResponse<Path>;

    const method = String(options.method || "GET").toUpperCase();
    const headers = new Headers(options.headers);

    const csrf = getCsrfToken() || readCookie(csrfCookieName) || "";
    if (csrf && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
      headers.set("X-CSRF-Token", csrf);
    }
    if (options.body && !headers.has("Content-Type") && !isFormDataBody(options.body)) {
      headers.set("Content-Type", "application/json");
    }

    const response = await fetch(`${apiBase}${path}`, {
      ...options,
      headers,
      credentials: "same-origin",
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 401) onUnauthorized();
    return payload as ApiResponse<Path>;
  }

  async function publicApi<Path extends string>(
    path: Path,
    payload: PostPayload<Path> = {} as PostPayload<Path>,
    options: Pick<RequestInit, "signal"> = {}
  ): Promise<PostResponse<Path>> {
    if (mockApi) {
      return (await mockApi(
        path,
        { method: "POST", body: JSON.stringify(payload) },
        getMockContext()
      )) as PostResponse<Path>;
    }
    const response = await fetch(`${apiBase}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: options.signal,
      credentials: "same-origin",
    });
    return (await response.json()) as PostResponse<Path>;
  }

  return { api, publicApi };
}
