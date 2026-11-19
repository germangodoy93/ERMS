import { z } from "zod";

/** Mirrors backend app/shared/identifiers.py for instant feedback; the API decides. */
export function luhnIsValid(digits: string): boolean {
  let total = 0;
  for (let index = 0; index < digits.length; index += 1) {
    let value = Number(digits[digits.length - 1 - index]);
    if (index % 2 === 1) {
      value *= 2;
      if (value > 9) value -= 9;
    }
    total += value;
  }
  return total % 10 === 0;
}

export function compactImei(raw: string): string {
  return raw.replace(/[\s.\-()/]/g, "");
}

export function imeiError(raw: string): string | null {
  const imei = compactImei(raw);
  if (!imei) return null;
  if (!/^\d{15}$/.test(imei)) return "El IMEI debe tener 15 dígitos (marque *#06# en el celular).";
  if (!luhnIsValid(imei)) return "El IMEI no es válido: revise los dígitos.";
  return null;
}

export const deviceSchema = z
  .object({
    category_code: z.string().min(1, "Seleccione la categoría."),
    manufacturer_id: z.string().min(1, "Seleccione el fabricante."),
    model_id: z.string().min(1, "Seleccione o cree el modelo."),
    serial_number: z.string().trim().max(64, "Máximo 64 caracteres."),
    imei: z.string().trim().max(30, "Máximo 30 caracteres."),
    operating_system: z.string().trim().max(60, "Máximo 60 caracteres."),
    storage: z.string().trim().max(40, "Máximo 40 caracteres."),
    color: z.string().trim().max(40, "Máximo 40 caracteres."),
    notes: z.string().trim().max(2000, "Máximo 2000 caracteres."),
  })
  .superRefine((values, ctx) => {
    const message = imeiError(values.imei);
    if (message) ctx.addIssue({ code: "custom", message, path: ["imei"] });
    if (values.serial_number && values.serial_number.replace(/\s/g, "").length < 3) {
      ctx.addIssue({
        code: "custom",
        message: "El serial debe tener al menos 3 caracteres.",
        path: ["serial_number"],
      });
    }
  });
export type DeviceValues = z.infer<typeof deviceSchema>;
