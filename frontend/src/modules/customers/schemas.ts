import { z } from "zod";

import { CONSENT_CHANNELS, CUSTOMER_KINDS, ID_TYPES } from "@/types/api";

/** Client-side checks for quick feedback. The backend normalizes and validates the
 * document (NIT check digit) and the phone; its messages are shown on submit. */
const base = z.object({
  kind: z.enum(CUSTOMER_KINDS),
  full_name: z.string().trim().min(2, "Ingrese el nombre.").max(200, "Máximo 200 caracteres."),
  id_type: z.union([z.literal(""), z.enum(ID_TYPES)]),
  id_number: z.string().trim().max(32, "Máximo 32 caracteres."),
  phone: z.string().trim().max(30, "Máximo 30 caracteres."),
  email: z.union([z.literal(""), z.email("Ingrese un correo electrónico válido.")]),
  address: z.string().trim().max(255, "Máximo 255 caracteres."),
  notes: z.string().trim().max(2000, "Máximo 2000 caracteres."),
});

type Contact = Pick<z.infer<typeof base>, "id_type" | "id_number" | "phone" | "email">;

function contactRules(values: Contact, ctx: z.RefinementCtx) {
  // A document type without number simply means "no document" (it is not sent).
  if (values.id_number && !values.id_type) {
    ctx.addIssue({
      code: "custom",
      message: "Seleccione el tipo de documento.",
      path: ["id_number"],
    });
  }
  if (!values.phone && !values.email) {
    ctx.addIssue({
      code: "custom",
      message: "Registre al menos un teléfono o un correo electrónico.",
      path: ["phone"],
    });
  }
}

export const editCustomerSchema = base.superRefine(contactRules);
export type EditCustomerValues = z.infer<typeof editCustomerSchema>;

export const createCustomerSchema = base
  .extend({
    channel: z.enum(CONSENT_CHANNELS),
    data_processing: z.boolean().refine((v) => v, {
      message: "Sin la autorización de tratamiento de datos no se puede registrar al cliente.",
    }),
    photos: z.boolean(),
    diagnostic_agent: z.boolean(),
  })
  .superRefine(contactRules);
export type CreateCustomerValues = z.infer<typeof createCustomerSchema>;
