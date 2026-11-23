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
  warranty_days: z
    .string()
    .trim()
    .regex(/^\d{1,4}$/, "Use días completos.")
    .refine((v) => Number(v) >= 1 && Number(v) <= 3650, "Entre 1 y 3650 días."),
  assembly_bottleneck_gap: z
    .string()
    .trim()
    .regex(/^d{1,3}$/, "Use un número entero.")
    .refine((v) => Number(v) >= 5 && Number(v) <= 100, "Entre 5 y 100 puntos."),
  assembly_margin_percent: z
    .string()
    .trim()
    .regex(/^d{1,3}([.,]d{1,2})?$/, "Use un porcentaje, por ejemplo 15.")
    .refine((v) => Number(v.replace(",", ".")) <= 300, "Máximo 300 %."),
  assembly_min_ram_gb: z
    .string()
    .trim()
    .regex(/^d{1,3}$/, "Use un número entero.")
    .refine((v) => Number(v) >= 4 && Number(v) <= 256, "Entre 4 y 256 GB."),
});
export type OrganizationValues = z.infer<typeof organizationSchema>;

export const POLICY_MIN_LENGTH = 200;
