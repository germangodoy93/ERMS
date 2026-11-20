import { parseMoney } from "@/modules/workorders/presentation";
import type { Quote, QuoteItemInput } from "@/types/api";

export interface DraftLine {
  kind: "LABOR" | "PART";
  part_id: string;
  description: string;
  quantity: string;
  unit_price: string;
  discount_percent: string;
  apply_tax: boolean;
  price_includes_tax: boolean;
}

export function toLines(quote: Quote): DraftLine[] {
  return quote.items.map((i) => ({
    kind: i.kind,
    part_id: i.part_id ?? "",
    description: i.description,
    quantity: String(Number(i.quantity)),
    unit_price: String(Number(i.unit_price)),
    discount_percent: String(Number(i.discount_percent)),
    apply_tax: i.tax_rate > 0,
    price_includes_tax: i.price_includes_tax,
  }));
}

/** Converts the editable lines to the API payload; returns an error message if invalid. */
export function toPayload(lines: DraftLine[]): QuoteItemInput[] | string {
  const items: QuoteItemInput[] = [];
  for (const [index, line] of lines.entries()) {
    const price = parseMoney(line.unit_price);
    const quantity = Number(line.quantity.replace(",", "."));
    const discount = Number(line.discount_percent.replace(",", ".") || "0");
    if (price === null) return `Ítem ${index + 1}: valor inválido.`;
    if (!(quantity > 0)) return `Ítem ${index + 1}: cantidad inválida.`;
    if (!(discount >= 0 && discount <= 100)) return `Ítem ${index + 1}: descuento inválido.`;
    if (!line.part_id && !line.description.trim())
      return `Ítem ${index + 1}: falta la descripción.`;
    items.push({
      kind: line.kind,
      part_id: line.kind === "PART" && line.part_id ? line.part_id : null,
      description: line.description.trim() || null,
      quantity: quantity.toFixed(2),
      unit_price: price,
      discount_percent: discount.toFixed(2),
      apply_tax: line.apply_tax,
      price_includes_tax: line.apply_tax && line.price_includes_tax,
    });
  }
  return items.length ? items : "Agregue al menos un ítem.";
}
