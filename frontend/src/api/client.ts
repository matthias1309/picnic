/**
 * Resolves the API base path from the environment (REQ-019).
 *
 * Defaults to today's dev/staging value so a host with no VITE_API_BASE set
 * behaves exactly as before. Production sets VITE_API_BASE=/api to call its
 * own domain's root-relative API instead.
 *
 * Kept as a small pure function so it's unit-testable directly — see
 * frontend/tests/UrlConfig.test.ts.
 */
export function resolveApiBase(env: { VITE_API_BASE?: string }): string {
  return env.VITE_API_BASE ?? "/picnic/api";
}

const API_BASE = resolveApiBase(import.meta.env);

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchJson<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const response = await fetch(url.pathname + url.search, { credentials: "include" });
  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);

  const response = await fetch(url.pathname, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export async function putJson<T>(path: string, body: unknown): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);

  const response = await fetch(url.pathname, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export async function deleteJson(path: string): Promise<void> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);

  const response = await fetch(url.pathname, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed with status ${response.status}`, response.status);
  }
}
