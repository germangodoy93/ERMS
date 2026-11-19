import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { UserCreate, UserUpdate } from "@/types/api";

import {
  createUser,
  listRoles,
  listUsers,
  setTemporaryPassword,
  setUserRoles,
  updateUser,
  type UserFilters,
} from "./api";

export const usersKeys = {
  all: ["users"] as const,
  list: (filters: UserFilters) => ["users", "list", filters] as const,
};
export const rolesKey = ["roles"] as const;

export function useUsers(filters: UserFilters) {
  return useQuery({
    queryKey: usersKeys.list(filters),
    queryFn: () => listUsers(filters),
    placeholderData: keepPreviousData,
  });
}

export function useRoles() {
  return useQuery({ queryKey: rolesKey, queryFn: listRoles, staleTime: 60_000 });
}

function useInvalidateUsers() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: usersKeys.all });
}

export function useCreateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: (payload: UserCreate) => createUser(payload),
    onSuccess: invalidate,
  });
}

export interface SaveUserInput {
  id: string;
  changes: UserUpdate;
  roleIds?: string[];
}

/** Updates profile fields and, if they changed, roles (two endpoints, one user action). */
export function useSaveUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: async ({ id, changes, roleIds }: SaveUserInput) => {
      let user = Object.keys(changes).length ? await updateUser(id, changes) : null;
      if (roleIds) user = await setUserRoles(id, roleIds);
      return user;
    },
    onSettled: invalidate,
  });
}

export function useSetActive() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      updateUser(id, { is_active: isActive }),
    onSuccess: invalidate,
  });
}

export function useSetTemporaryPassword() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: ({ id, password }: { id: string; password: string }) =>
      setTemporaryPassword(id, password),
    onSuccess: invalidate,
  });
}
