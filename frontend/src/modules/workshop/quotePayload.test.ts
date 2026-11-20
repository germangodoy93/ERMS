import { balanceLabel } from "./presentation";
import { toPayload, type DraftLine } from "./quotePayload";

function line(overrides: Partial<DraftLine> = {}): DraftLine {
  return {
    kind: "LABOR",
    part_id: "",
    description: "Mano de obra",
    quantity: "1",
    unit_price: "50.000",
    discount_percent: "0",
    apply_tax: false,
    price_includes_tax: false,
    ...overrides,
  };
}

describe("quote payload", () => {
  it("converts typed values to the API format", () => {
    expect(
      toPayload([
        line({
          quantity: "1,5",
          discount_percent: "10",
          apply_tax: true,
          price_includes_tax: true,
        }),
        line({ kind: "PART", part_id: "p1", description: "", unit_price: "119000" }),
      ]),
    ).toEqual([
      {
        kind: "LABOR",
        part_id: null,
        description: "Mano de obra",
        quantity: "1.50",
        unit_price: "50000.00",
        discount_percent: "10.00",
        apply_tax: true,
        price_includes_tax: true,
      },
      {
        kind: "PART",
        part_id: "p1",
        description: null,
        quantity: "1.00",
        unit_price: "119000.00",
        discount_percent: "0.00",
        apply_tax: false,
        price_includes_tax: false,
      },
    ]);
  });

  it("drops 'includes VAT' when VAT does not apply", () => {
    const [item] = toPayload([line({ apply_tax: false, price_includes_tax: true })]) as {
      price_includes_tax: boolean;
    }[];
    expect(item?.price_includes_tax).toBe(false);
  });

  it("reports the first invalid line", () => {
    expect(toPayload([])).toBe("Agregue al menos un ítem.");
    expect(toPayload([line(), line({ unit_price: "abc" })])).toBe("Ítem 2: valor inválido.");
    expect(toPayload([line({ quantity: "0" })])).toBe("Ítem 1: cantidad inválida.");
    expect(toPayload([line({ discount_percent: "120" })])).toBe("Ítem 1: descuento inválido.");
    expect(toPayload([line({ description: " " })])).toBe("Ítem 1: falta la descripción.");
  });

  it("labels the balance", () => {
    expect(balanceLabel("1000.00")).toBe("Saldo pendiente");
    expect(balanceLabel("0.00")).toBe("Pagado");
    expect(balanceLabel("-500.00")).toBe("Saldo a favor del cliente");
  });
});
