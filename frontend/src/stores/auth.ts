import { create } from "zustand";

import type { Me } from "@/types/api";

/**
 * Session state. The access token lives only in memory (never localStorage); on reload
 * the session is restored from the httpOnly refresh cookie (see modules/auth/session.ts).
 */
export type AuthStatus = "unknown" | "authenticated" | "anonymous";

interface AuthState {
  status: AuthStatus;
  accessToken: string | null;
  user: Me | null;
  setSession: (accessToken: string, user: Me) => void;
  setAccessToken: (accessToken: string) => void;
  setUser: (user: Me) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  status: "unknown",
  accessToken: null,
  user: null,
  setSession: (accessToken, user) => set({ status: "authenticated", accessToken, user }),
  setAccessToken: (accessToken) => set({ accessToken }),
  setUser: (user) => set({ user }),
  clear: () => set({ status: "anonymous", accessToken: null, user: null }),
}));
