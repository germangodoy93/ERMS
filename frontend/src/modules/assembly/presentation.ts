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
  MONITOR: "Monitores",
  KEYBOARD: "Teclado",
  MOUSE: "Mouse",
  PAD: "Pad",
  HEADSET: "Audífonos",
  MIC: "Micrófono",
  SPEAKER: "Parlantes",
  CAMERA: "Cámara",
  STREAM: "Streaming",
  CHAIR: "Silla",
  DESK: "Escritorio",
  LIGHT: "Luces",
};

export const PROFILE_LABELS: Record<UseProfile, string> = {
  OFFICE: "Oficina",
  DESIGN: "Diseño y edición",
  GAMING: "Gaming",
};

const PICK_ONE = "Elija una opción. Las piezas que no encajan muestran el motivo.";
const SETUP_ONE = "Elija una opción; tóquela otra vez para quitarla.";

/** How many parts can be chosen in multi-choice categories (as in the simulator). */
export const MULTI_LIMITS: Partial<Record<AssemblyCategory, number>> = {
  STORAGE: 4,
  RGB: 8,
  MONITOR: 3,
  MIC: 2,
  STREAM: 3,
  LIGHT: 2,
};
export const MULTI: ReadonlySet<AssemblyCategory> = new Set(
  Object.keys(MULTI_LIMITS) as AssemblyCategory[],
);

export const CATEGORY_HINTS: Record<AssemblyCategory, string> = {
  CPU: PICK_ONE,
  BOARD: PICK_ONE,
  RAM: "Los precios son por unidad: elija cuántas instalar.",
  GPU: "Opcional si el procesador tiene gráficos integrados.",
  STORAGE: "Puede elegir varias unidades (hasta 4).",
  PSU: "Elija una opción. La marca naranja del consumo es la potencia recomendada.",
  CASE: PICK_ONE,
  COOLER: PICK_ONE,
  RGB: "Accesorios opcionales: puede combinar varios.",
  MONITOR: "Puede elegir hasta 3.",
  KEYBOARD: SETUP_ONE,
  MOUSE: SETUP_ONE,
  PAD: SETUP_ONE,
  HEADSET: SETUP_ONE,
  MIC: "Puede elegir hasta 2 (por ejemplo, micrófono y brazo).",
  SPEAKER: SETUP_ONE,
  CAMERA: SETUP_ONE,
  STREAM: "Puede elegir hasta 3.",
  CHAIR: SETUP_ONE,
  DESK: SETUP_ONE,
  LIGHT: "Puede elegir hasta 2.",
};

/** Key of the category in the Selection (CPU → cpu, MONITOR → monitor…). */
const key = (category: AssemblyCategory) => category.toLowerCase() as keyof Selection;

export const EMPTY_SELECTION: Selection = {
  ram_units: 2,
  storage: [],
  rgb: [],
  monitor: [],
  mic: [],
  stream: [],
  light: [],
  desk_shape: "STRAIGHT",
  pc_position: "AUTO",
};

export function selectedIds(selection: Selection, category: AssemblyCategory): string[] {
  const value = selection[key(category)];
  if (Array.isArray(value)) return value;
  return typeof value === "string" && value ? [value] : [];
}

/** Choosing an already chosen part removes it (as in the simulator). */
export function toggle(selection: Selection, part: CatalogPart): Selection {
  const { category, id } = part;
  const k = key(category);
  if (MULTI.has(category)) {
    const current = selectedIds(selection, category);
    if (current.includes(id)) return { ...selection, [k]: current.filter((x) => x !== id) };
    if (current.length >= (MULTI_LIMITS[category] ?? 99)) return selection;
    return { ...selection, [k]: [...current, id] };
  }
  return { ...selection, [k]: selection[k] === id ? null : id };
}

export function clearCategory(selection: Selection, category: AssemblyCategory): Selection {
  return { ...selection, [key(category)]: MULTI.has(category) ? [] : null };
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
    case "MONITOR":
      return `${n(s.inches)}"${s.resolution ? ` · ${String(s.resolution)}` : ""}${s.hz ? ` · ${n(s.hz)} Hz` : ""}${s.oled ? " · OLED" : ""}${s.curved ? " · curvo" : ""}${s.pro ? " · para diseño" : ""}`;
    case "KEYBOARD":
      return `${s.size === "PAD" ? "Keypad para juegos" : `Formato ${String(s.size)}`}${s.low_profile ? " · perfil bajo" : ""}${s.hall_effect ? " · switches magnéticos (Hall)" : ""}${s.wireless ? " · inalámbrico" : ""}`;
    case "MOUSE":
      return s.wireless ? "Inalámbrico" : "Con cable";
    case "PAD":
      return `Tamaño ${String(s.size)}`;
    case "HEADSET":
      return s.earbuds
        ? "Audífonos in-ear con estuche"
        : `Diadema${s.wireless ? " inalámbrica" : ""}${s.rgb ? " · RGB" : ""}`;
    case "MIC":
      return s.arm
        ? "Brazo articulado para micrófono"
        : `Micrófono${s.rgb ? " con RGB" : ""}${s.xlr ? " · XLR (necesita interfaz)" : ""}`;
    case "SPEAKER":
      return (
        (
          {
            BAR: "Barra de sonido",
            PAIR: "Par de parlantes",
            ROBOT: "Parlantes de diseño futurista",
          } as Record<string, string>
        )[String(s.kind)] ?? "Parlantes"
      );
    case "CAMERA":
      return `Cámara web${s.resolution ? ` ${String(s.resolution)}` : ""}`;
    case "STREAM":
      return s.kind === "LIGHT"
        ? "Panel de luz para cámara"
        : "Controlador con teclas programables";
    case "CHAIR":
      return "Silla gamer";
    case "DESK":
      return `${n(s.width_cm)} cm de ancho${s.integrated_case ? " · con gabinete integrado" : ""}`;
    case "LIGHT":
      return `Paneles de luz RGB para la pared (${n(s.pieces)} piezas)`;
  }
}

/** Parts of the catalog chosen in the selection, by category. */
export function chosen(catalog: CatalogPart[], selection: Selection) {
  const byId = new Map(catalog.map((p) => [p.id, p]));
  const one = (category: AssemblyCategory) => {
    const id = selectedIds(selection, category)[0];
    return id ? byId.get(id) : undefined;
  };
  const many = (category: AssemblyCategory) =>
    selectedIds(selection, category)
      .map((id) => byId.get(id))
      .filter((p) => p !== undefined);
  return {
    cpu: one("CPU"),
    board: one("BOARD"),
    ram: one("RAM"),
    gpu: one("GPU"),
    psu: one("PSU"),
    case: one("CASE"),
    cooler: one("COOLER"),
    storage: many("STORAGE"),
    rgb: many("RGB"),
    monitor: many("MONITOR"),
    keyboard: one("KEYBOARD"),
    mouse: one("MOUSE"),
    pad: one("PAD"),
    headset: one("HEADSET"),
    mic: many("MIC"),
    speaker: one("SPEAKER"),
    camera: one("CAMERA"),
    stream: many("STREAM"),
    chair: one("CHAIR"),
    desk: one("DESK"),
    light: many("LIGHT"),
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
