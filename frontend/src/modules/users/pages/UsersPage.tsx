import { KeyRound, MoreHorizontal, Pencil, Plus, Power, Search } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { toast } from "sonner";

import { Pagination } from "@/components/Pagination";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateTime } from "@/lib/format";
import { ADMIN_ROLE_CODE, PERMS, useCan } from "@/modules/auth/permissions";
import { errorMessage } from "@/services/errors";
import { useAuthStore } from "@/stores/auth";
import type { User } from "@/types/api";

import { TemporaryPasswordDialog } from "../components/TemporaryPasswordDialog";
import { UserFormDialog } from "../components/UserFormDialog";
import { useRoles, useSetActive, useUsers } from "../hooks";

const PAGE_SIZE = 20;
const ALL = "all";

export function UsersPage() {
  const canManage = useCan(PERMS.USERS_MANAGE);
  const canManageAdmins = useCan(PERMS.ROLES_MANAGE);
  const currentUserId = useAuthStore((s) => s.user?.id);
  const roles = useRoles();
  const setActive = useSetActive();

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string>(ALL);
  const [role, setRole] = useState<string>(ALL);
  const [page, setPage] = useState(1);
  const deferredSearch = useDeferredValue(search);

  const users = useUsers({
    page,
    size: PAGE_SIZE,
    q: deferredSearch.trim() || undefined,
    is_active: status === ALL ? undefined : status === "active",
    role: role === ALL ? undefined : role,
  });

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [resetting, setResetting] = useState<User | null>(null);

  const canActOn = (user: User) =>
    canManage && (canManageAdmins || !user.roles.some((r) => r.code === ADMIN_ROLE_CODE));

  const toggleActive = async (user: User) => {
    try {
      await setActive.mutateAsync({ id: user.id, isActive: !user.is_active });
      toast.success(user.is_active ? "Usuario desactivado." : "Usuario activado.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Usuarios</h1>
          <p className="text-muted-foreground text-sm">Personal con acceso a ERMS y sus roles.</p>
        </div>
        {canManage && (
          <Button onClick={() => setCreating(true)}>
            <Plus /> Nuevo usuario
          </Button>
        )}
      </header>

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
          <Input
            placeholder="Buscar por nombre o correo"
            className="pl-8"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            aria-label="Buscar usuarios"
          />
        </div>
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-40" aria-label="Filtrar por estado">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los estados</SelectItem>
            <SelectItem value="active">Activos</SelectItem>
            <SelectItem value="inactive">Inactivos</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={role}
          onValueChange={(v) => {
            setRole(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-44" aria-label="Filtrar por rol">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todos los roles</SelectItem>
            {(roles.data ?? []).map((r) => (
              <SelectItem key={r.id} value={r.code}>
                {r.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead className="hidden md:table-cell">Roles</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="hidden lg:table-cell">Último ingreso</TableHead>
              <TableHead className="w-12">
                <span className="sr-only">Acciones</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.isPending &&
              Array.from({ length: 4 }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className="h-6" />
                  </TableCell>
                </TableRow>
              ))}
            {users.isError && (
              <TableRow>
                <TableCell colSpan={5} className="text-destructive py-8 text-center">
                  {errorMessage(users.error)}
                </TableCell>
              </TableRow>
            )}
            {users.data?.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground py-8 text-center">
                  No hay usuarios que coincidan con los filtros.
                </TableCell>
              </TableRow>
            )}
            {users.data?.items.map((user) => (
              <TableRow key={user.id}>
                <TableCell>
                  <div className="font-medium">{user.full_name}</div>
                  <div className="text-muted-foreground text-xs">{user.email}</div>
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  {user.roles.map((r) => r.name).join(", ")}
                </TableCell>
                <TableCell>
                  <UserStatus user={user} />
                </TableCell>
                <TableCell className="text-muted-foreground hidden text-sm lg:table-cell">
                  {formatDateTime(user.last_login_at)}
                </TableCell>
                <TableCell>
                  {canActOn(user) && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Acciones para ${user.full_name}`}
                        >
                          <MoreHorizontal />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={() => setEditing(user)}>
                          <Pencil /> Editar
                        </DropdownMenuItem>
                        {user.id !== currentUserId && (
                          <>
                            <DropdownMenuItem onSelect={() => setResetting(user)}>
                              <KeyRound /> Contraseña temporal
                            </DropdownMenuItem>
                            <DropdownMenuItem onSelect={() => void toggleActive(user)}>
                              <Power /> {user.is_active ? "Desactivar" : "Activar"}
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {users.data && (
        <Pagination
          page={users.data.page}
          size={users.data.size}
          total={users.data.total}
          onPageChange={setPage}
        />
      )}

      {creating && <UserFormDialog open onOpenChange={setCreating} />}
      {editing && (
        <UserFormDialog
          key={editing.id}
          open
          user={editing}
          onOpenChange={(open) => !open && setEditing(null)}
        />
      )}
      <TemporaryPasswordDialog
        user={resetting}
        onOpenChange={(open) => !open && setResetting(null)}
      />
    </div>
  );
}

function UserStatus({ user }: { user: User }) {
  if (!user.is_active) return <StatusBadge tone="neutral" label="Inactivo" />;
  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    return <StatusBadge tone="danger" label="Bloqueado" />;
  }
  if (user.must_change_password) return <StatusBadge tone="neutral" label="Clave temporal" />;
  return <StatusBadge tone="success" label="Activo" />;
}
