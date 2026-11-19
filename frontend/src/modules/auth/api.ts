import { http } from "@/services/http";
import type { Me, TokenResponse } from "@/types/api";

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await http.post<TokenResponse>("/auth/login", { email, password });
  return data;
}

export async function logout(): Promise<void> {
  await http.post("/auth/logout");
}

/** Pass the token explicitly right after login, before it is stored. */
export async function fetchMe(accessToken?: string): Promise<Me> {
  const { data } = await http.get<Me>("/auth/me", {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  return data;
}

export async function requestPasswordReset(email: string): Promise<void> {
  await http.post("/auth/password/forgot", { email });
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await http.post("/auth/password/reset", { token, new_password: newPassword });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await http.post("/auth/password/change", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}
