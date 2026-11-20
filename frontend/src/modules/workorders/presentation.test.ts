import {
  accessoriesText,
  formatMoney,
  parseMoney,
  reasonRequired,
  statusTone,
} from "./presentation";

describe("work order presentation", () => {
  it("formats Colombian pesos", () => {
    expect(formatMoney("50000.00")).toBe("$ 50.000");
    expect(formatMoney("1250000.50")).toBe("$ 1.250.000,50");
    expect(formatMoney("0.00")).toBe("$ 0");
    expect(formatMoney(null)).toBe("—");
  });

  it("parses amounts typed by reception", () => {
    expect(parseMoney("50.000")).toBe("50000.00");
    expect(parseMoney("$ 50000")).toBe("50000.00");
    expect(parseMoney("1.250.000,5")).toBe("1250000.50");
    expect(parseMoney("")).toBe("0.00");
    expect(parseMoney("50,000.00")).toBeNull();
    expect(parseMoney("abc")).toBeNull();
    expect(parseMoney("-5")).toBeNull();
  });

  it("requires a reason exactly where the backend does", () => {
    expect(reasonRequired("RECIBIDO", "CANCELADO")).toBe(true);
    expect(reasonRequired("EN_REPARACION", "NO_REPARABLE")).toBe(true);
    expect(reasonRequired("PENDIENTE_AUTORIZACION", "COTIZACION_RECHAZADA")).toBe(true);
    expect(reasonRequired("CONTROL_CALIDAD", "EN_REPARACION")).toBe(true);
    expect(reasonRequired("APROBADO", "EN_REPARACION")).toBe(false);
    expect(reasonRequired("RECIBIDO", "INSPECCION")).toBe(false);
  });

  it("describes accessories and status tones", () => {
    expect(accessoriesText([])).toBe("Ninguno");
    expect(accessoriesText([{ code: "CHARGER" }, { code: "OTHER", detail: "Lápiz óptico" }])).toBe(
      "Cargador, Otro: Lápiz óptico",
    );
    expect(statusTone("LISTO_ENTREGA")).toBe("success");
    expect(statusTone("PENDIENTE_AUTORIZACION")).toBe("warning");
    expect(statusTone("CANCELADO")).toBe("danger");
  });
});
