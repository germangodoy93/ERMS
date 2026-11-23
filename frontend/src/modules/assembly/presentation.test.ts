import type { CatalogPart } from "@/types/api";

import {
  EMPTY_SELECTION,
  clearCategory,
  parseCatalogFile,
  selectedIds,
  specText,
  toggle,
} from "./presentation";

const part = (id: string, category: CatalogPart["category"]): CatalogPart => ({
  id,
  sku: id,
  name: id,
  category,
  sale_price: "100.00",
  stock: 0,
  specs: {},
});

describe("assembly presentation", () => {
  it("toggles single and multiple choices like the simulator", () => {
    let s = toggle(EMPTY_SELECTION, part("c1", "CPU"));
    expect(s.cpu).toBe("c1");
    s = toggle(s, part("c2", "CPU"));
    expect(s.cpu).toBe("c2");
    s = toggle(s, part("c2", "CPU"));
    expect(s.cpu).toBeNull();
    for (const id of ["s1", "s2", "s3", "s4", "s5"]) s = toggle(s, part(id, "STORAGE"));
    expect(selectedIds(s, "STORAGE")).toEqual(["s1", "s2", "s3", "s4"]); // max 4
    s = toggle(s, part("s2", "STORAGE"));
    expect(s.storage).toEqual(["s1", "s3", "s4"]);
    expect(clearCategory(s, "STORAGE").storage).toEqual([]);
  });

  it("describes specs in plain Spanish", () => {
    expect(
      specText("CPU", {
        socket: "AM5",
        cores: 8,
        tdp_w: 162,
        integrated_graphics: true,
      }),
    ).toBe("AM5 · 8 núcleos · hasta 162 W · gráficos integrados");
    expect(
      specText("COOLER", { type: "AIO", radiator_mm: 360, tdp_w: 320, includes_fans: false }),
    ).toBe("Líquida · radiador 360 mm · disipa ~320 W · sin ventiladores");
    expect(specText("RGB", { kind: "FAN_KIT", fan_count: 3, infinity: true })).toBe(
      "Kit de 3 ventiladores ARGB de 120 mm con efecto infinito",
    );
  });

  it("reads the catalog file with or without the items wrapper", () => {
    expect(parseCatalogFile('{"source":"x","items":[{"sku":"a"}]}')).toEqual([{ sku: "a" }]);
    expect(parseCatalogFile('[{"sku":"b"}]')).toEqual([{ sku: "b" }]);
    expect(() => parseCatalogFile('{"x":1}')).toThrow("lista de piezas");
  });
});
