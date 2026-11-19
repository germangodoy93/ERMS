import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/services/errors";
import { useAuthStore } from "@/stores/auth";

import { changePassword } from "../api";
import { AuthLayout } from "../components/AuthLayout";
import { PASSWORD_MIN_LENGTH, changePasswordSchema, type ChangePasswordValues } from "../schemas";
import { reloadCurrentUser, signOut } from "../session";

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const mustChange = useAuthStore((s) => s.user?.must_change_password ?? false);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordValues>({ resolver: zodResolver(changePasswordSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await changePassword(values.current_password, values.new_password);
      await reloadCurrentUser();
      toast.success("Contraseña actualizada. Se cerraron las sesiones en otros equipos.");
      navigate("/", { replace: true });
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <AuthLayout
      title="Cambiar contraseña"
      description={
        mustChange
          ? "Su contraseña es temporal. Debe cambiarla antes de continuar."
          : "Las sesiones abiertas en otros equipos se cerrarán."
      }
    >
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        {mustChange && (
          <Alert>
            <ShieldAlert />
            <AlertDescription>
              Por seguridad, elija una contraseña que solo usted conozca.
            </AlertDescription>
          </Alert>
        )}
        {serverError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}
        <FormField
          label="Contraseña actual"
          type="password"
          autoComplete="current-password"
          autoFocus
          error={errors.current_password?.message}
          {...register("current_password")}
        />
        <FormField
          label="Nueva contraseña"
          type="password"
          autoComplete="new-password"
          hint={`Mínimo ${PASSWORD_MIN_LENGTH} caracteres. No incluya su usuario de correo.`}
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <FormField
          label="Confirmar nueva contraseña"
          type="password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...register("confirm_password")}
        />
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Guardando…" : "Cambiar contraseña"}
        </Button>
        {mustChange ? (
          <Button type="button" variant="ghost" onClick={() => void signOut()}>
            Cerrar sesión
          </Button>
        ) : (
          <Button type="button" variant="ghost" onClick={() => navigate(-1)}>
            Cancelar
          </Button>
        )}
      </form>
    </AuthLayout>
  );
}
