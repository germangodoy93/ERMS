import { z } from "zod";

import { parseMoney } from "@/modules/workorders/presentation";
import type { Modality } from "@/types/api";

const duration = z
  .string()
  .trim()
  .regex(/^\d{2,3}$/, "Use minutos, por ejemplo 60.")
  .refine((v) => Number(v) >= 15 && Number(v) <= 480, "Entre 15 y 480 minutos.")
  .refine((v) => Number(v) % 5 === 0, "Use múltiplos de 5 minutos.");

/** Fields of the new / edit appointment form. The modality comes from the chosen service. */
export function appointmentSchema(modalityOf: (serviceId: string) => Modality | undefined) {
  return z
    .object({
      service_id: z.string().min(1, "Elija el servicio."),
      date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Elija la fecha."),
      time: z.string().regex(/^\d{2}:\d{2}$/, "Elija la hora."),
      duration,
      technician_id: z.string(),
      reason: z
        .string()
        .trim()
        .min(5, "Describa qué necesita el cliente.")
        .max(2000, "Máximo 2000 caracteres."),
      address: z.string().trim().max(255, "Máximo 255 caracteres."),
      locality: z.string(),
      notes: z.string().trim().max(2000, "Máximo 2000 caracteres."),
      consent_channel: z.string(),
    })
    .superRefine((values, ctx) => {
      const modality = modalityOf(values.service_id);
      if (modality === "ON_SITE") {
        if (!values.address)
          ctx.addIssue({ code: "custom", path: ["address"], message: "Indique la dirección." });
        if (!values.locality)
          ctx.addIssue({ code: "custom", path: ["locality"], message: "Elija la localidad." });
      }
      if (modality === "REMOTE" && !values.consent_channel) {
        ctx.addIssue({
          code: "custom",
          path: ["consent_channel"],
          message: "Registre cómo autorizó el cliente el acceso remoto.",
        });
      }
    });
}
export type AppointmentValues = z.infer<ReturnType<typeof appointmentSchema>>;

export const fieldServiceSchema = z.object({
  name: z.string().trim().min(3, "Mínimo 3 caracteres.").max(120, "Máximo 120 caracteres."),
  modality: z.enum(["REMOTE", "ON_SITE"]),
  duration_minutes: duration,
  price: z
    .string()
    .trim()
    .refine((v) => v === "" || parseMoney(v) !== null, "Use un valor como 80.000."),
  tax_rate: z.enum(["0", "19"]),
  price_includes_tax: z.boolean(),
  description: z.string().trim().max(1000, "Máximo 1000 caracteres."),
  is_active: z.boolean(),
});
export type FieldServiceValues = z.infer<typeof fieldServiceSchema>;
