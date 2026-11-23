/** Public runtime configuration. `NEXT_PUBLIC_*` values are inlined at build time. */
export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  apiPrefix: "/api/v1",
} as const;
