import type { AssemblyCategory, CatalogPart, Selection, UseProfile } from "@/types/api";

export const CATEGORY_LABELS: Record<AssemblyCategory, string> = {
  CPU: "Procesador",
  BOARD: "Placa base",
  RAM: "Memoria",
  GPU: "Gráfica",
  STORAGE: "Almacenamiento",
  PSU: "Fuente",
  CASE: "Gabinete",
  COOLER: "Refrigeración",
  RGB: "RGB",
};

export const PROFILE_LABELS: Record<UseProfile, string> = {
  OFFICE: "Oficina",
  DESIGN: "Diseño y edición",
  GAMING: "Gaming",
};

export const CATEGORY_HINTS: Record<AssemblyCategory, string> = {
  CPU: "Elija una opción. Las piezas que no encajan muestran el motivo.",
  BOARD: "Elija una opción. Las piezas que no encajan muestran el motivo.",
  RAM: "Los precios son por unidad: elija cuántas instalar.",
  GPU: "Opcional si el procesador tiene gráficos integrados.",
  STORAGE: "Puede elegir varias unidades (hasta 4).",
  PSU: "Elija una opción. La marca naranja del consumo es la potencia recomendada.",
  CASE: "Elija una opción. Las piezas que no encajan muestran el motivo.",
  COOLER: "Elija una opción. Las piezas que no encajan muestran el motivo.",
  RGB: "Accesorios opcionales: puede combinar varios.",
};

const MAX: Partial<Record<AssemblyCategory, number>> = { STORAGE: 4, RGB: 8 };
export const MULTI: ReadonlySet<AssemblyCategory> = new Set(["STORAGE", "RGB"]);

type SingleKey = "cpu" | "board" | "ram" | "gpu" | "psu" | "case" | "cooler";
const SINGLE: Record<Exclude<AssemblyCategory, "STORAGE" | "RGB">, SingleKey> = {
  CPU: "cpu",
  BOARD: "board",
  RAM: "ram",
  GPU: "gpu",
  PSU: "psu",
  CASE: "case",
  COOLER: "cooler",
};

export const EMPTY_SELECTION: Selection = { ram_units: 2, storage: [], rgb: [] };

export function selectedIds(selection: Selection, category: AssemblyCategory): string[] {
  if (category === "STORAGE") return selection.storage;
  if (category === "RGB") return selection.rgb;
  const id = selection[SINGLE[category]];
  return id ? [id] : [];
}

/** Choosing an already chosen part removes it (as in the simulator). */
export function toggle(selection: Selection, part: CatalogPart): Selection {
  const { category, id } = part;
  if (category === "STORAGE" || category === "RGB") {
    const key = category === "STORAGE" ? "storage" : "rgb";
    const current = selection[key];
    if (current.includes(id)) return { ...selection, [key]: current.filter((x) => x !== id) };
    if (current.length >= (MAX[category] ?? 99)) return selection;
    return { ...selection, [key]: [...current, id] };
  }
  const key = SINGLE[category];
  return { ...selection, [key]: selection[key] === id ? null : id };
}

export function clearCategory(selection: Selection, category: AssemblyCategory): Selection {
  if (category === "STORAGE") return { ...selection, storage: [] };
  if (category === "RGB") return { ...selection, rgb: [] };
  return { ...selection, [SINGLE[category]]: null };
}

type Specs = Record<string, unknown>;
const n = (v: unknown) => (typeof v === "number" ? v : Number(v));
const list = (v: unknown) => (Array.isArray(v) ? v.join("/") : String(v ?? ""));

const RGB_KIND: Record<string, string> = {
  STRIMER_24: "Extensión ARGB para el conector de 24 pines de la placa",
  STRIMER_16: "Extensión ARGB para gráficas con conector de 16 pines (12V-2x6)",
  STRIMER_8: "Extensión ARGB de 8 pines para la CPU (EPS)",
  GPU_SUPPORT: "Soporte antipandeo para la gráfica, con tira ARGB",
};

/** One-line description of a part's specs, worded like the simulator. */
export function specText(category: AssemblyCategory, s: Specs): string {
  switch (category) {
    case "CPU":
      return `${s.socket} · ${n(s.cores)} núcleos · hasta ${n(s.tdp_w)} W${s.integrated_graphics ? " · gráficos integrados" : " · sin gráficos integrados"}`;
    case "BOARD":
      return `${s.socket} · ${s.ram_type} · ${s.form_factor} · ${n(s.ram_slots)} ranuras RAM · ${n(s.m2_slots)} M.2${s.max_ram_mhz ? ` · RAM hasta ${n(s.max_ram_mhz)} MHz` : ""}`;
    case "RAM":
      return `${s.ram_type}${s.mhz ? ` · ${n(s.mhz)} MHz` : ""} · ${n(s.modules) > 1 ? `${n(s.modules)} módulos por kit` : "1 módulo por unidad"} · precio por unidad`;
    case "GPU":
      return `${n(s.tdp_w)} W · ${n(s.length_mm)} mm de largo${s.power_connector === "16PIN" ? " · conector de 16 pines" : ""}`;
    case "STORAGE":
      return `Interfaz ${s.interface}`;
    case "PSU":
      return `${n(s.watts)} W · formato ${s.form_factor}`;
    case "CASE":
      return `Placas ${list(s.board_form_factors)} · GPU hasta ${n(s.max_gpu_mm)} mm · disipador hasta ${n(s.max_cooler_mm)} mm · radiador hasta ${n(s.max_radiator_mm)} mm · fuente ${list(s.psu_form_factors)}`;
    case "COOLER":
      return (
        (s.type === "AIR"
          ? `Aire · ${n(s.height_mm)} mm de alto · disipa ~${n(s.tdp_w)} W`
          : `Líquida · radiador ${n(s.radiator_mm)} mm · disipa ~${n(s.tdp_w)} W`) +
        (Array.isArray(s.sockets) && s.sockets.length ? ` · solo ${list(s.sockets)}` : "") +
        (s.includes_fans === false ? " · sin ventiladores" : "")
      );
    case "RGB":
      return s.kind === "FAN_KIT"
        ? `Kit de ${n(s.fan_count)} ventiladores ARGB de 120 mm${s.infinity ? " con efecto infinito" : ""}${s.lcd ? " y pantalla LCD" : ""}`
        : (RGB_KIND[String(s.kind)] ?? String(s.kind));
  }
}

/** Parts of the catalog chosen in the selection, by category. */
export function chosen(catalog: CatalogPart[], selection: Selection) {
  const byId = new Map(catalog.map((p) => [p.id, p]));
  const one = (id: string | null | undefined) => (id ? byId.get(id) : undefined);
  return {
    cpu: one(selection.cpu),
    board: one(selection.board),
    ram: one(selection.ram),
    gpu: one(selection.gpu),
    psu: one(selection.psu),
    case: one(selection.case),
    cooler: one(selection.cooler),
    storage: selection.storage.map((id) => byId.get(id)).filter((p) => p !== undefined),
    rgb: selection.rgb.map((id) => byId.get(id)).filter((p) => p !== undefined),
  };
}

export type Chosen = ReturnType<typeof chosen>;

/** Parses the import file: either `{items: [...]}` or a bare list. */
export function parseCatalogFile(text: string): unknown[] {
  const data: unknown = JSON.parse(text);
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object" && Array.isArray((data as { items?: unknown }).items)) {
    return (data as { items: unknown[] }).items;
  }
  throw new Error("El archivo no tiene una lista de piezas.");
}
