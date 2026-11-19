import { z } from "zod";

const optionalText = (max: number) => z.string().trim().max(max, `Máximo ${max} caracteres.`);

export const organizationSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, "Ingrese el nombre del taller.")
    .max(200, "Máximo 200 caracteres."),
  legal_name: optionalText(200),
  tax_id: optionalText(32),
  address: optionalText(255),
  city: optionalText(80),
  phone: optionalText(30),
  email: z.union([z.literal(""), z.email("Ingrese un correo electrónico válido.")]),
});
export type OrganizationValues = z.infer<typeof organizationSchema>;

export const POLICY_MIN_LENGTH = 200;
