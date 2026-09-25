export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ApiOptions = {
  token: string;
  churchId?: string | null;
  init?: RequestInit;
  baseUrl?: string;
  fetchImpl?: typeof fetch;
};

/** Call the FastAPI backend. The server re-checks the church on every request. */
export async function apiFetch<T>(
  path: string,
  {
    token,
    churchId,
    init,
    baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "",
    fetchImpl = fetch,
  }: ApiOptions,
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (churchId) headers.set("X-Church-Id", churchId);

  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");

  let res: Response;
  try {
    res = await fetchImpl(`${normalizedBaseUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.");
  }
  if (res.ok) return (await res.json()) as T;

  let code = "error";
  let message = "Something went wrong.";
  try {
    const body = await res.json();
    code = body?.error?.code ?? code;
    message = body?.error?.message ?? message;
  } catch {
    // Non-JSON error body (e.g. a proxy's HTML page); keep the generic message.
  }
  throw new ApiError(res.status, code, message);
}
