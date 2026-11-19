import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PASSWORD_MIN_LENGTH } from "@/modules/auth/schemas";
import { errorMessage } from "@/services/errors";
import type { User } from "@/types/api";

import { useSetTemporaryPassword } from "../hooks";
import { temporaryPasswordSchema, type TemporaryPasswordValues } from "../schemas";

export function TemporaryPasswordDialog({
  user,
  onOpenChange,
}: {
  user: User | null;
  onOpenChange: (open: boolean) => void;
}) {
  const mutation = useSetTemporaryPassword();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TemporaryPasswordValues>({ resolver: zodResolver(temporaryPasswordSchema) });

  const close = (open: boolean) => {
    if (!open) {
      reset();
      setServerError(null);
    }
    onOpenChange(open);
  };

  const onSubmit = handleSubmit(async ({ temporary_password }) => {
    if (!user) return;
    setServerError(null);
    try {
      await mutation.mutateAsync({ id: user.id, password: temporary_password });
      toast.success("Contraseña temporal asignada. Sus sesiones abiertas se cerraron.");
      close(false);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <Dialog open={user !== null} onOpenChange={close}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Asignar contraseña temporal</DialogTitle>
          <DialogDescription>
            {user?.full_name} deberá cambiarla al ingresar. Se cerrarán sus sesiones abiertas.
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
            label="Contraseña temporal"
            type="password"
            autoComplete="new-password"
            hint={`Mínimo ${PASSWORD_MIN_LENGTH} caracteres.`}
            error={errors.temporary_password?.message}
            {...register("temporary_password")}
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => close(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              Asignar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
