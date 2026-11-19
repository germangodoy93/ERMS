import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, MailCheck } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";

import { FormField } from "@/components/FormField";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { errorMessage } from "@/services/errors";

import { requestPasswordReset } from "../api";
import { AuthLayout } from "../components/AuthLayout";
import { forgotPasswordSchema, type ForgotPasswordValues } from "../schemas";

export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({ resolver: zodResolver(forgotPasswordSchema) });

  const onSubmit = handleSubmit(async ({ email }) => {
    setServerError(null);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (error) {
      setServerError(errorMessage(error));
    }
  });

  return (
    <AuthLayout
      title="Recuperar contraseña"
      description="Le enviaremos un enlace de un solo uso para crear una nueva contraseña."
    >
      {sent ? (
        <div className="grid gap-4">
          <Alert>
            <MailCheck />
            <AlertDescription>
              Si el correo está registrado, recibirá un enlace en los próximos minutos. Revise
              también la carpeta de correo no deseado.
            </AlertDescription>
          </Alert>
          <Button asChild variant="outline">
            <Link to="/login">Volver a iniciar sesión</Link>
          </Button>
        </div>
      ) : (
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
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Enviando…" : "Enviar enlace"}
          </Button>
          <Link
            to="/login"
            className="text-muted-foreground hover:text-foreground text-center text-sm underline-offset-4 hover:underline"
          >
            Volver a iniciar sesión
          </Link>
        </form>
      )}
    </AuthLayout>
  );
}
