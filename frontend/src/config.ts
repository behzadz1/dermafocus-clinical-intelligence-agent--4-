// src/config.ts
export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

export const API_KEY =
  (import.meta.env.VITE_API_KEY as string | undefined) ?? "";

// Optional safety: warn in production if missing
if (!import.meta.env.VITE_API_BASE_URL) {
  // eslint-disable-next-line no-console
  console.warn("VITE_API_BASE_URL is not set; API calls will be relative.");
}
