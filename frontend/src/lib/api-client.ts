import { config } from "@/lib/config";
import type { APIResponse } from "@/types/api";

/** Error raised when the backend returns `success: false` or a non-2xx status. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Thin fetch wrapper: prefixes the API base URL and unwraps the response envelope. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${config.apiUrl}${config.apiPrefix}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = (await response.json()) as APIResponse<T>;

  if (!response.ok || !body.success) {
    throw new ApiError(body.error ?? response.statusText, response.status);
  }
  return body.data as T;
}
