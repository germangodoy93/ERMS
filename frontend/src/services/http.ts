import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { useAuthStore } from "@/stores/auth";
import type { TokenResponse } from "@/types/api";

declare module "axios" {
  interface AxiosRequestConfig {
    /** Internal: request already retried after a token refresh. */
    _retried?: boolean;
  }
}

/**
 * Single HTTP client for the ERMS API.
 *
 * Development: relative `/api/v1` goes through the Vite proxy (same origin).
 * Production (Railway): the web service reverse-proxies `/api` to the backend.
 */
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  timeout: 15_000,
  withCredentials: true,
  headers: { Accept: "application/json" },
});

http.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token && !config.headers.has("Authorization")) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

const REFRESH_RETRY_DELAY_MS = 400;
let inFlightRefresh: Promise<string | null> | null = null;

async function requestNewAccessToken(): Promise<string> {
  const response = await http.post<TokenResponse>("/auth/refresh");
  return response.data.access_token;
}

/**
 * Obtains a new access token from the refresh cookie. Concurrent callers share one request
 * (single-flight). If another tab rotated the cookie at the same moment the first attempt
 * fails, so it retries once with the updated cookie before giving up.
 */
export function refreshAccessToken(): Promise<string | null> {
  inFlightRefresh ??= (async () => {
    try {
      let token: string;
      try {
        token = await requestNewAccessToken();
      } catch {
        await new Promise((resolve) => setTimeout(resolve, REFRESH_RETRY_DELAY_MS));
        token = await requestNewAccessToken();
      }
      useAuthStore.getState().setAccessToken(token);
      return token;
    } catch {
      useAuthStore.getState().clear();
      return null;
    } finally {
      inFlightRefresh = null;
    }
  })();
  return inFlightRefresh;
}

/** Endpoints that do not use the access token, so a 401 there must not trigger a refresh. */
const PUBLIC_AUTH_ENDPOINTS = [
  "/auth/login",
  "/auth/refresh",
  "/auth/logout",
  "/auth/password/forgot",
  "/auth/password/reset",
];

function isPublicAuthEndpoint(config: InternalAxiosRequestConfig): boolean {
  return PUBLIC_AUTH_ENDPOINTS.includes(config.url ?? "");
}

http.interceptors.response.use(undefined, async (error: AxiosError) => {
  const config = error.config;
  if (
    error.response?.status !== 401 ||
    !config ||
    config._retried ||
    isPublicAuthEndpoint(config) ||
    useAuthStore.getState().status === "anonymous"
  ) {
    throw error;
  }
  const token = await refreshAccessToken();
  if (!token) throw error;
  config._retried = true;
  config.headers.set("Authorization", `Bearer ${token}`);
  return http(config);
});
