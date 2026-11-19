import { z } from "zod";

/** Mirrors the backend policy (PASSWORD_MIN_LENGTH); the backend remains the authority. */
export const PASSWORD_MIN_LENGTH = 12;

const email = z.email("Ingrese un correo electrónico válido.");

export const newPasswordField = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`)
  .max(128, "Debe tener como máximo 128 caracteres.")
  .refine((value) => value.trim() === value, "No puede empezar ni terminar con espacios.");

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Ingrese su contraseña."),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const forgotPasswordSchema = z.object({ email });
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

const confirmation = <T extends { new_password: string; confirm_password: string }>(
  values: T,
  ctx: z.RefinementCtx,
) => {
  if (values.new_password !== values.confirm_password) {
    ctx.addIssue({
      code: "custom",
      path: ["confirm_password"],
      message: "Las contraseñas no coinciden.",
    });
  }
};

export const resetPasswordSchema = z
  .object({ new_password: newPasswordField, confirm_password: z.string() })
  .superRefine(confirmation);
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Ingrese su contraseña actual."),
    new_password: newPasswordField,
    confirm_password: z.string(),
  })
  .superRefine(confirmation)
  .refine((v) => v.current_password !== v.new_password, {
    path: ["new_password"],
    message: "La nueva contraseña debe ser diferente a la actual.",
  });
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>;
