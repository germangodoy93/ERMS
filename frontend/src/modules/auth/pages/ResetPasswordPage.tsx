import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router";
import { toast } from "sonner";

import { FormField } from "@/components/FormField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/services/errors";

import { resetPassword } from "../api";
import { AuthLayout } from "../components/AuthLayout";
import { PASSWORD_MIN_LENGTH, resetPasswordSchema, type ResetPasswordValues } from "../schemas";

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token");
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({ resolver: zodResolver(resetPasswordSchema) });

  if (!token) {
    return (
      <AuthLayout title="Enlace inválido">
        <div className="grid gap-4">
          <p className="text-muted-foreground text-sm">
            El enlace no contiene un código válido. Solicite uno nuevo.
          </p>
          <Button asChild>
            <Link to="/recuperar-contrasena">Solicitar nuevo enlace</Link>
          </Button>
        </div>
      </AuthLayout>
    );
  }

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await resetPassword(token, values.new_password);
      toast.success("Contraseña actualizada. Inicie sesión con la nueva contraseña.");
      navigate("/login", { replace: true });
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <AuthLayout title="Nueva contraseña" description="El enlace es de un solo uso.">
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        {serverError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}
        <FormField
          label="Nueva contraseña"
          type="password"
          autoComplete="new-password"
          autoFocus
          hint={`Mínimo ${PASSWORD_MIN_LENGTH} caracteres. No incluya su usuario de correo.`}
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <FormField
          label="Confirmar contraseña"
          type="password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...register("confirm_password")}
        />
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Guardando…" : "Guardar contraseña"}
        </Button>
      </form>
    </AuthLayout>
  );
}
