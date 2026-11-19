import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router";

import { FormField } from "@/components/FormField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/services/errors";
import { useAuthStore } from "@/stores/auth";

import { AuthLayout } from "../components/AuthLayout";
import { safeNextPath } from "../redirect";
import { loginSchema, type LoginValues } from "../schemas";
import { signIn } from "../session";

export function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const status = useAuthStore((s) => s.status);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  if (status === "authenticated") return <Navigate to="/" replace />;

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      const user = await signIn(values.email, values.password);
      navigate(
        user.must_change_password ? "/cambiar-contrasena" : safeNextPath(params.get("next")),
        { replace: true },
      );
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <AuthLayout title="Iniciar sesión" description="Ingrese con su correo corporativo.">
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        {serverError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}
        <FormField
          label="Correo electrónico"
          type="email"
          autoComplete="username"
          autoFocus
          error={errors.email?.message}
          {...register("email")}
        />
        <FormField
          label="Contraseña"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        <Button type="submit" disabled={isSubmitting} className="w-full">
          {isSubmitting ? "Ingresando…" : "Ingresar"}
        </Button>
        <Link
          to="/recuperar-contrasena"
          className="text-muted-foreground hover:text-foreground text-center text-sm underline-offset-4 hover:underline"
        >
          ¿Olvidó su contraseña?
        </Link>
      </form>
    </AuthLayout>
  );
}
