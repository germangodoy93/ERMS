import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Lock } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ADMIN_ROLE_CODE, PERMS, useCan } from "@/modules/auth/permissions";
import { reloadCurrentUser } from "@/modules/auth/session";
import { rolesKey, useRoles } from "@/modules/users/hooks";
import { errorMessage } from "@/services/errors";
import type { Role } from "@/types/api";

import { listPermissions, setRolePermissions } from "../api";

type Draft = Record<string, string[]>;

export function RolesPage() {
  const canEdit = useCan(PERMS.ROLES_MANAGE);
  const queryClient = useQueryClient();
  const roles = useRoles();
  const permissions = useQuery({ queryKey: ["permissions"], queryFn: listPermissions });
  const [draft, setDraft] = useState<Draft>({});

  const save = useMutation({
    mutationFn: ({ roleId, codes }: { roleId: string; codes: string[] }) =>
      setRolePermissions(roleId, codes),
    onSuccess: async (role) => {
      setDraft((d) => Object.fromEntries(Object.entries(d).filter(([id]) => id !== role.id)));
      await queryClient.invalidateQueries({ queryKey: rolesKey });
      await reloadCurrentUser(); // own permissions may have changed
      toast.success(`Permisos de ${role.name} actualizados.`);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const current = (role: Role) => draft[role.id] ?? role.permissions;
  const toggle = (role: Role, code: string, on: boolean) =>
    setDraft((d) => {
      const list = d[role.id] ?? role.permissions;
      return { ...d, [role.id]: on ? [...list, code] : list.filter((c) => c !== code) };
    });

  if (roles.isPending || permissions.isPending) return <Skeleton className="h-64" />;
  if (roles.isError || permissions.isError) {
    return <p className="text-destructive">{errorMessage(roles.error ?? permissions.error)}</p>;
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Roles y permisos</h1>
        <p className="text-muted-foreground text-sm">
          {canEdit
            ? "Los cambios se aplican de inmediato a todos los usuarios del rol."
            : "Solo un Administrador puede modificar los permisos."}
        </p>
      </header>

      <div className="overflow-x-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Permiso</TableHead>
              {roles.data.map((role) => (
                <TableHead key={role.id} className="text-center">
                  <span className="inline-flex items-center gap-1">
                    {role.name}
                    {role.code === ADMIN_ROLE_CODE && (
                      <Lock className="size-3" aria-label="No modificable" />
                    )}
                  </span>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {permissions.data.map((perm) => (
              <TableRow key={perm.code}>
                <TableCell>
                  <div className="font-medium">{perm.description}</div>
                  <div className="text-muted-foreground font-mono text-xs">{perm.code}</div>
                </TableCell>
                {roles.data.map((role) => (
                  <TableCell key={role.id} className="text-center">
                    <Checkbox
                      aria-label={`${perm.code} para ${role.name}`}
                      checked={current(role).includes(perm.code)}
                      disabled={!canEdit || role.code === ADMIN_ROLE_CODE}
                      onCheckedChange={(v) => toggle(role, perm.code, v === true)}
                    />
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {canEdit && (
              <TableRow>
                <TableCell />
                {roles.data.map((role) => (
                  <TableCell key={role.id} className="text-center">
                    {draft[role.id] && (
                      <Button
                        size="sm"
                        disabled={save.isPending}
                        onClick={() => save.mutate({ roleId: role.id, codes: current(role) })}
                      >
                        Guardar
                      </Button>
                    )}
                  </TableCell>
                ))}
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
