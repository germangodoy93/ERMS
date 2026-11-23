import {
  deskFor,
  monitorSize,
  setupAdvice,
  setupLayout,
  type SetupPart,
  type SetupParts,
} from "./setup";

const part = (id: string, specs: Record<string, unknown>, price = "100000.00"): SetupPart => ({
  id,
  name: id,
  sale_price: price,
  specs,
});
const empty: SetupParts = { monitor: [], mic: [], stream: [], light: [] };
const DESKS = [
  part("E-Star 140", { width_cm: 140 }, "884000.00"),
  part("E-Grave 160", { width_cm: 160 }, "1264000.00"),
  part("DK07X", { width_cm: 160, integrated_case: true }, "5807000.00"),
];

describe("setup layout (simulator rules)", () => {
  it("measures monitors by diagonal and aspect ratio", () => {
    const [w, h] = monitorSize(part("27", { inches: 27 }));
    expect(w).toBeCloseTo(59.8, 1);
    expect(h).toBeCloseTo(33.6, 1);
    expect(monitorSize(part("49", { inches: 49, ultrawide: 2 }))[0]).toBeCloseTo(119.8, 1);
  });

  it("sizes a generic desk and decides where the PC goes", () => {
    const parts: SetupParts = {
      ...empty,
      case: part("Lancool", { size: "ATX", max_gpu_mm: 392 }),
      monitor: [part("27", { inches: 27 })],
      keyboard: part("kb", { size: "TKL" }),
      mouse: part("m", {}),
    };
    const straight = setupLayout(parts, "STRAIGHT", "AUTO");
    expect(straight.genericDesk).toBe(true);
    expect(straight.pcOnDesk).toBe(true);
    expect(straight.deskWidth).toBeGreaterThanOrEqual(straight.required);
    const floor = setupLayout(parts, "STRAIGHT", "FLOOR");
    expect(floor.pcOnDesk).toBe(false);
    const L = setupLayout(parts, "L", "AUTO");
    expect(L.pcOnWing).toBe(true);
    expect(L.wingLength).toBeGreaterThanOrEqual(120);
  });

  it("suggests the cheapest desk that fits, never one with a built-in case", () => {
    expect(deskFor(DESKS, 150)?.name).toBe("E-Grave 160");
    expect(deskFor(DESKS, 200)).toBeUndefined();
  });

  it("gives the simulator advice", () => {
    const advice = setupAdvice(
      {
        ...empty,
        mic: [part("Arm", { arm: true }), part("ProCast", { xlr: true })],
        desk: part("E-Star 140", { width_cm: 140 }),
        monitor: [part("49", { inches: 49, ultrawide: 2 }), part("27", { inches: 27 })],
      },
      "STRAIGHT",
      "AUTO",
      DESKS,
    );
    expect(advice.some((a) => a.includes("quedarán amontonados"))).toBe(true);
    expect(advice.some((a) => a.includes("XLR"))).toBe(true);
    expect(setupAdvice(empty, "L", "AUTO", DESKS).join(" ")).toMatch(
      /no trae escritorios en L.*No eligió escritorio.*Sin monitor/,
    );
  });
});
