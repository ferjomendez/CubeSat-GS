export class ApiError extends Error {
  status: number;
  error: string;
  detail: string | null;

  constructor(status: number, error: string, detail: string | null) {
    super(detail ?? error);
    this.status = status;
    this.error = error;
    this.detail = detail;
  }
}

async function request<T>(method: string, path: string, body?: unknown, params?: Record<string, unknown>): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
  }
  const r = await fetch(url.toString(), {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let e = { error: "http_error", detail: r.statusText as string | null };
    try {
      e = await r.json();
    } catch {
      /* not json */
    }
    throw new ApiError(r.status, e.error, e.detail ?? null);
  }
  const ct = r.headers.get("content-type") ?? "";
  return (ct.includes("json") ? await r.json() : await r.text()) as T;
}

export const api = {
  get: <T,>(path: string, params?: Record<string, unknown>) => request<T>("GET", path, undefined, params),
  post: <T,>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T,>(path: string, body: unknown) => request<T>("PUT", path, body),
};

export async function downloadExport(body: unknown, filename: string): Promise<void> {
  const r = await fetch("/api/export", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) {
    const e = await r.json();
    throw new ApiError(r.status, e.error, e.detail);
  }
  const blob = await r.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = r.headers.get("content-disposition")?.match(/filename="(.+)"/)?.[1] ?? filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
