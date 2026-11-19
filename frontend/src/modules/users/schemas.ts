import { z } from "zod";

import { newPasswordField } from "@/modules/auth/schemas";

const base = {
  full_name: z
    .string()
    .trim()
    .min(2, "Ingrese el nombre completo.")
    .max(160, "Máximo 160 caracteres."),
  email: z.email("Ingrese un correo electrónico válido."),
  phone: z.string().trim().max(30, "Máximo 30 caracteres."),
  role_ids: z.array(z.string()).min(1, "Seleccione al menos un rol."),
};

export const createUserSchema = z.object({ ...base, temporary_password: newPasswordField });
export type CreateUserValues = z.infer<typeof createUserSchema>;

export const editUserSchema = z.object(base);
export type EditUserValues = z.infer<typeof editUserSchema>;

export const temporaryPasswordSchema = z.object({ temporary_password: newPasswordField });
export type TemporaryPasswordValues = z.infer<typeof temporaryPasswordSchema>;
