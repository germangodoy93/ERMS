import { formatPhone } from "@/lib/format";
import { compactImei, imeiError, luhnIsValid } from "@/modules/devices/validation";

import { consentRows, customerState, formatDocument } from "./presentation";

describe("customer presentation", () => {
  it("formats Colombian phones and keeps foreign ones", () => {
    expect(formatPhone("+573001234567")).toBe("300 123 4567");
    expect(formatPhone("+576012345678")).toBe("601 234 5678");
    expect(formatPhone("+14155550100")).toBe("+14155550100");
    expect(formatPhone(null)).toBe("—");
  });

  it("formats the document only when complete", () => {
    expect(formatDocument({ id_type: "NIT", id_number: "890903938-8" })).toBe("NIT 890903938-8");
    expect(formatDocument({ id_type: null, id_number: null })).toBe("—");
  });

  it("derives the customer state in priority order", () => {
    const base = { is_active: true, anonymized_at: null };
    expect(customerState(base)).toBe("served");
    expect(customerState({ ...base, can_be_served: false })).toBe("no_consent");
    expect(customerState({ ...base, is_active: false })).toBe("inactive");
    expect(
      customerState({ ...base, is_active: false, anonymized_at: "2026-11-19T00:00:00Z" }),
    ).toBe("anonymized");
  });

  it("lists every purpose, including those never asked", () => {
    const rows = consentRows([
      {
        purpose: "PHOTOS",
        granted: true,
        channel: "SCREEN",
        policy_version: 1,
        recorded_at: "2026-11-19T00:00:00Z",
      },
    ]);
    expect(rows.map((r) => [r.purpose, r.status?.granted ?? null])).toEqual([
      ["DATA_PROCESSING", null],
      ["PHOTOS", true],
      ["DIAGNOSTIC_AGENT", null],
    ]);
  });
});

describe("IMEI validation (mirrors the backend)", () => {
  it("accepts a valid IMEI written with separators", () => {
    expect(compactImei("49-015420-323751-8")).toBe("490154203237518");
    expect(imeiError("49 015420 323751 8")).toBeNull();
    expect(luhnIsValid("490154203237518")).toBe(true);
  });

  it("rejects wrong length or check digit", () => {
    expect(imeiError("4901542032375")).toMatch(/15 dígitos/);
    expect(imeiError("490154203237519")).toMatch(/no es válido/);
    expect(imeiError("")).toBeNull();
  });
});
