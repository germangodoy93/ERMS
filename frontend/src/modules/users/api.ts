import { http } from "@/services/http";
import type { Page, Role, User, UserCreate, UserUpdate } from "@/types/api";

export interface UserFilters {
  page: number;
  size: number;
  q?: string;
  is_active?: boolean;
  role?: string;
}

export async function listUsers(filters: UserFilters): Promise<Page<User>> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== undefined && value !== ""),
  );
  const { data } = await http.get<Page<User>>("/users", { params });
  return data;
}

export async function createUser(payload: UserCreate): Promise<User> {
  const { data } = await http.post<User>("/users", payload);
  return data;
}

export async function updateUser(id: string, payload: UserUpdate): Promise<User> {
  const { data } = await http.patch<User>(`/users/${id}`, payload);
  return data;
}

export async function setUserRoles(id: string, roleIds: string[]): Promise<User> {
  const { data } = await http.put<User>(`/users/${id}/roles`, { role_ids: roleIds });
  return data;
}

export async function setTemporaryPassword(id: string, password: string): Promise<User> {
  const { data } = await http.post<User>(`/users/${id}/temporary-password`, {
    temporary_password: password,
  });
  return data;
}

export async function listRoles(): Promise<Role[]> {
  const { data } = await http.get<Role[]>("/roles");
  return data;
}
