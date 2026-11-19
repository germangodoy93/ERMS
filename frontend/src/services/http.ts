import axios from "axios";

/**
 * Single HTTP client for the ERMS API.
 *
 * Development: relative `/api/v1` goes through the Vite proxy (same origin).
 * Production (Railway): the web service reverse-proxies `/api` to the backend, so the
 * same relative URL works. VITE_API_BASE_URL overrides it when the API lives elsewhere.
 */
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  timeout: 10_000,
  withCredentials: true,
  headers: { Accept: "application/json" },
});
