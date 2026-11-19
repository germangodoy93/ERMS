import { http } from "@/services/http";
import type { Permission, Role } from "@/types/api";

export async function listPermissions(): Promise<Permission[]> {
  const { data } = await http.get<Permission[]>("/permissions");
  return data;
}

export async function setRolePermissions(roleId: string, permissions: string[]): Promise<Role> {
  const { data } = await http.put<Role>(`/roles/${roleId}/permissions`, { permissions });
  return data;
}
