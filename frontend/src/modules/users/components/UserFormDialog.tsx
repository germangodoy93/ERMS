import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle } from "lucide-react";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { ADMIN_ROLE_CODE, PERMS, useCan } from "@/modules/auth/permissions";
import { PASSWORD_MIN_LENGTH } from "@/modules/auth/schemas";
import { errorMessage } from "@/services/errors";
import type { Role, User, UserUpdate } from "@/types/api";

import { useCreateUser, useRoles, useSaveUser } from "../hooks";
import {
  createUserSchema,
  editUserSchema,
  type CreateUserValues,
  type EditUserValues,
} from "../schemas";

type Values = CreateUserValues | EditUserValues;

function sameIds(a: string[], b: string[]): boolean {
  return a.length === b.length && [...a].sort().join() === [...b].sort().join();
}

/** Create (user = undefined) or edit a user. */
export function UserFormDialog({
  open,
  onOpenChange,
  user,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: User;
}) {
  const isEdit = Boolean(user);
  const canManageAdmins = useCan(PERMS.ROLES_MANAGE);
  const roles = useRoles();
  const createUser = useCreateUser();
  const saveUser = useSaveUser();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(isEdit ? editUserSchema : createUserSchema),
    defaultValues: {
      full_name: user?.full_name ?? "",
      email: user?.email ?? "",
      phone: user?.phone ?? "",
      role_ids: user?.roles.map((r) => r.id) ?? [],
      ...(isEdit ? {} : { temporary_password: "" }),
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      if (user) {
        const changes: UserUpdate = {};
        if (values.full_name !== user.full_name) changes.full_name = values.full_name;
        if (values.email.toLowerCase() !== user.email) changes.email = values.email;
        if ((values.phone || null) !== user.phone) changes.phone = values.phone || null;
        const currentRoleIds = user.roles.map((r) => r.id);
        await saveUser.mutateAsync({
          id: user.id,
          changes,
          roleIds: sameIds(values.role_ids, currentRoleIds) ? undefined : values.role_ids,
        });
        toast.success("Usuario actualizado.");
      } else {
        const created = values as CreateUserValues;
        await createUser.mutateAsync({
          email: created.email,
          full_name: created.full_name,
          phone: created.phone || null,
          temporary_password: created.temporary_password,
          role_ids: created.role_ids,
        });
        toast.success("Usuario creado. Entréguele la contraseña temporal de forma segura.");
      }
      onOpenChange(false);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar usuario" : "Nuevo usuario"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Los cambios quedan registrados en la auditoría."
              : "El usuario deberá cambiar la contraseña temporal en su primer ingreso."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="grid gap-4" noValidate>
          {serverError && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}
          <FormField
            label="Nombre completo"
            autoComplete="off"
            error={errors.full_name?.message}
            {...register("full_name")}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              label="Correo electrónico"
              type="email"
              autoComplete="off"
              error={errors.email?.message}
              {...register("email")}
            />
            <FormField
              label="Teléfono (opcional)"
              type="tel"
              autoComplete="off"
              error={errors.phone?.message}
              {...register("phone")}
            />
          </div>
          {!isEdit && (
            <FormField
              label="Contraseña temporal"
              type="password"
              autoComplete="new-password"
              hint={`Mínimo ${PASSWORD_MIN_LENGTH} caracteres.`}
              error={
                "temporary_password" in errors ? errors.temporary_password?.message : undefined
              }
              {...register("temporary_password" as keyof Values)}
            />
          )}

          <fieldset className="grid gap-2">
            <legend className="mb-1 text-sm font-medium">Roles</legend>
            <Controller
              control={control}
              name="role_ids"
              render={({ field }) => (
                <div className="grid gap-2 sm:grid-cols-2">
                  {(roles.data ?? []).map((role: Role) => {
                    const locked = role.code === ADMIN_ROLE_CODE && !canManageAdmins;
                    const checked = field.value.includes(role.id);
                    return (
                      <Label
                        key={role.id}
                        className="flex items-center gap-2 font-normal"
                        title={locked ? "Solo un Administrador puede asignar este rol" : undefined}
                      >
                        <Checkbox
                          checked={checked}
                          disabled={locked}
                          onCheckedChange={(value) =>
                            field.onChange(
                              value
                                ? [...field.value, role.id]
                                : field.value.filter((id) => id !== role.id),
                            )
                          }
                        />
                        {role.name}
                      </Label>
                    );
                  })}
                </div>
              )}
            />
            {errors.role_ids && (
              <p className="text-destructive text-xs">{errors.role_ids.message}</p>
            )}
          </fieldset>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Guardando…" : isEdit ? "Guardar cambios" : "Crear usuario"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
