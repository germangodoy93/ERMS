import { z } from "zod";

import { ACCESSORIES, PAYMENT_METHODS, PRIORITIES, UNLOCK_METHODS } from "@/types/api";

import { parseMoney } from "./presentation";

const money = z
  .string()
  .trim()
  .refine((v) => parseMoney(v) !== null, "Valor inválido. Ejemplo: 50.000");

export const receptionSchema = z
  .object({
    reported_issue: z
      .string()
      .trim()
      .min(5, "Describa la falla reportada por el cliente.")
      .max(4000, "Máximo 4000 caracteres."),
    physical_condition: z
      .string()
      .trim()
      .min(3, "Describa el estado físico del equipo.")
      .max(4000, "Máximo 4000 caracteres."),
    accessories: z.array(z.enum(ACCESSORIES)),
    other_accessory: z.string().trim().max(120, "Máximo 120 caracteres."),
    unlock_method: z.enum(UNLOCK_METHODS),
    priority: z.enum(PRIORITIES),
    estimated_delivery_date: z.string(),
    diagnostic_fee: money,
    advance_amount: money,
    advance_method: z.union([z.literal(""), z.enum(PAYMENT_METHODS)]),
    technician_id: z.string(),
    notes: z.string().trim().max(4000, "Máximo 4000 caracteres."),
  })
  .superRefine((values, ctx) => {
    if (values.accessories.includes("OTHER") && !values.other_accessory) {
      ctx.addIssue({
        code: "custom",
        message: "Describa el accesorio marcado como 'Otro'.",
        path: ["other_accessory"],
      });
    }
    const advance = parseMoney(values.advance_amount);
    if (advance && Number(advance) > 0 && !values.advance_method) {
      ctx.addIssue({
        code: "custom",
        message: "Indique el medio de pago del anticipo.",
        path: ["advance_method"],
      });
    }
  });
export type ReceptionValues = z.infer<typeof receptionSchema>;
