import { refreshAccessToken } from "@/services/http";
import { useAuthStore } from "@/stores/auth";

import { fetchMe, login, logout } from "./api";

let restoring: Promise<void> | null = null;

/**
 * Restores the session after a page load using the refresh cookie. Shared promise so that
 * React StrictMode (double effects) or several components never send two refreshes.
 */
export function restoreSession(): Promise<void> {
  restoring ??= (async () => {
    const token = await refreshAccessToken();
    if (!token) {
      useAuthStore.getState().clear();
      return;
    }
    try {
      useAuthStore.getState().setSession(token, await fetchMe(token));
    } catch {
      useAuthStore.getState().clear();
    }
  })().finally(() => {
    restoring = null;
  });
  return restoring;
}

export async function signIn(email: string, password: string) {
  const tokens = await login(email, password);
  const user = await fetchMe(tokens.access_token);
  useAuthStore.getState().setSession(tokens.access_token, user);
  return user;
}

export async function signOut(): Promise<void> {
  try {
    await logout();
  } finally {
    useAuthStore.getState().clear();
  }
}

export async function reloadCurrentUser(): Promise<void> {
  useAuthStore.getState().setUser(await fetchMe());
}
