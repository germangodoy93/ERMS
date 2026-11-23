/**
 * Setup layout and advice, ported from `setupLayout()` and `setupCheck()` of the owner's
 * simulator. Advisory only: it depends on the 3D layout and never blocks a sale.
 */
import { formatMoney } from "@/modules/workorders/presentation";

export type DeskShape = "STRAIGHT" | "L";
export type PcPosition = "AUTO" | "DESK" | "FLOOR";

export interface SetupPart {
  id: string;
  name: string;
  sale_price: string;
  specs: Record<string, unknown>;
}

export interface SetupParts {
  case?: SetupPart;
  monitor: SetupPart[];
  keyboard?: SetupPart;
  mouse?: SetupPart;
  pad?: SetupPart;
  headset?: SetupPart;
  mic: SetupPart[];
  speaker?: SetupPart;
  camera?: SetupPart;
  stream: SetupPart[];
  chair?: SetupPart;
  desk?: SetupPart;
  light: SetupPart[];
}

const n = (p: SetupPart | undefined, key: string, fallback = 0) => {
  const v = p?.specs[key];
  return typeof v === "number" ? v : fallback;
};
const s = (p: SetupPart | undefined, key: string) => {
  const v = p?.specs[key];
  return typeof v === "string" ? v : "";
};
const b = (p: SetupPart | undefined, key: string) => p?.specs[key] === true;

const CASE_WIDTH: Record<string, number> = { XL: 24, ATX: 22, MATX: 20, ITX: 18 };
const KEYBOARD_WIDTH: Record<string, number> = {
  "60%": 29,
  "75%": 32,
  TKL: 36,
  "100%": 44,
  PAD: 18,
};
const PAD_WIDTH: Record<string, number> = { M: 36, L: 45, XL: 90, XXL: 110 };

/** Screen width and height (cm) from the diagonal and the aspect ratio. */
export function monitorSize(m: SetupPart): [number, number] {
  const uw = n(m, "ultrawide");
  const ratio = uw === 2 ? 32 / 9 : uw ? 21 / 9 : 16 / 9;
  const diagonal = n(m, "inches", 24) * 2.54;
  const h = diagonal / Math.sqrt(ratio * ratio + 1);
  return [h * ratio, h];
}

export interface Layout {
  pcL: number;
  pcW: number;
  monitorsWidth: number;
  speakersWidth: number;
  headsetWidth: number;
  micWidth: number;
  headsetMicWidth: number;
  decksWidth: number;
  headsetMicBack: boolean;
  frontWidth: number;
  keyboardWidth: number;
  core: number;
  required: number;
  requiredNoPc: number;
  deskWidth: number;
  deskDepth: number;
  pcOnDesk: boolean;
  pcOnWing: boolean;
  isL: boolean;
  wingWidth: number;
  wingLength: number;
  genericDesk: boolean;
  position: PcPosition;
}

export function setupLayout(p: SetupParts, shape: DeskShape, position: PcPosition): Layout {
  const pcL = p.case ? n(p.case, "max_gpu_mm") / 10 + 6 : 42;
  const pcW = p.case ? (CASE_WIDTH[s(p.case, "size")] ?? 22) : 22;
  const mons = p.monitor;
  const mw = mons.reduce((a, m) => a + monitorSize(m)[0] + 1.6, 0) + Math.max(0, mons.length - 1);
  const mwE = mw * (mons.length === 3 ? 0.9 : mons.length === 2 ? 0.96 : 1);
  const mic = p.mic.find((x) => !b(x, "arm"));
  const arm = p.mic.some((x) => b(x, "arm"));
  const decks = p.stream.filter((x) => s(x, "kind") === "DECK");
  const hsW = p.headset ? (b(p.headset, "earbuds") ? 10 : 18) : 0;
  const micW = mic && !arm ? 14 : 0;
  const hm = hsW + micW + (hsW || micW ? 3 : 0);
  const dkW = decks.reduce((a, t) => a + n(t, "key_columns") * 2.4 + 2 + 3, 0);
  const SPK = p.speaker && s(p.speaker, "kind") !== "BAR" ? 36 : 0;
  const kw = p.keyboard ? (KEYBOARD_WIDTH[s(p.keyboard, "size")] ?? 36) : 0;
  const frontW = Math.max(p.pad ? (PAD_WIDTH[s(p.pad, "size")] ?? 45) : 0, kw + (p.mouse ? 28 : 0));
  const optA = Math.max(mwE + SPK, frontW + hm + dkW, 40);
  const optB = Math.max(mwE + SPK + hm, frontW + dkW, 40);
  const hmBack = optB < optA;
  const core = Math.ceil(Math.min(optA, optB));
  const reqNoPc = core + 8;
  const req = core + pcW + 11;
  const isL = shape === "L";
  const dw = p.desk
    ? n(p.desk, "width_cm", 120)
    : Math.min(
        240,
        Math.max(
          120,
          Math.ceil((position === "FLOOR" || (isL && position === "AUTO") ? reqNoPc : req) / 10) *
            10,
        ),
      );
  const pcWing = isL && position === "AUTO";
  const pcOnDesk = position === "DESK" || (!isL && position === "AUTO" && req <= dw);
  const dd =
    mons.length >= 3 || mons.some((m) => n(m, "ultrawide") === 2) || frontW > 100 ? 80 : 70;
  return {
    pcL,
    pcW,
    monitorsWidth: mwE,
    speakersWidth: SPK,
    headsetWidth: hsW,
    micWidth: micW,
    headsetMicWidth: hm,
    decksWidth: dkW,
    headsetMicBack: hmBack,
    frontWidth: frontW,
    keyboardWidth: kw,
    core,
    required: req,
    requiredNoPc: reqNoPc,
    deskWidth: dw,
    deskDepth: dd,
    pcOnDesk,
    pcOnWing: pcWing,
    isL,
    wingWidth: 60,
    wingLength: Math.max(120, dd + pcL + 14),
    genericDesk: !p.desk,
    position,
  };
}

/** The cheapest desk of the catalog at least `width` cm wide (desks with a case excluded). */
export function deskFor(desks: SetupPart[], width: number): SetupPart | undefined {
  return desks
    .filter((d) => n(d, "width_cm") >= width && !b(d, "integrated_case"))
    .sort((a, c) => Number(a.sale_price) - Number(c.sale_price))[0];
}

export function setupAdvice(
  p: SetupParts,
  shape: DeskShape,
  position: PcPosition,
  desks: SetupPart[],
): string[] {
  const out: string[] = [];
  const L = setupLayout(p, shape, position);
  const dk = p.desk;
  const suggest = (w: number) => {
    const d = deskFor(desks, w);
    const widest = Math.max(0, ...desks.map((x) => n(x, "width_cm")));
    return d
      ? `el ${d.name} (${n(d, "width_cm")} cm, ${formatMoney(d.sale_price)})`
      : `ninguno del catálogo alcanza (el más ancho mide ${widest} cm)`;
  };
  if (dk && L.requiredNoPc > n(dk, "width_cm")) {
    out.push(
      `Los periféricos y monitores necesitan unos ${L.requiredNoPc} cm y el ${dk.name} mide ${n(dk, "width_cm")} cm: quedarán amontonados. Opciones: ${suggest(L.requiredNoPc)}, o menos pantallas o accesorios.`,
    );
  } else if (dk && !L.pcOnDesk && !L.isL && position === "AUTO") {
    out.push(
      `El PC no cabe sobre el ${dk.name} (${n(dk, "width_cm")} cm; harían falta unos ${L.required} cm), así que se muestra en el piso. Para tenerlo encima: ${suggest(L.required)}.`,
    );
  } else if (dk && position === "DESK" && L.required > n(dk, "width_cm")) {
    out.push(
      `Con el PC encima, este setup necesita unos ${L.required} cm y el escritorio mide ${n(dk, "width_cm")} cm: el PC choca con los monitores. Opciones: ${suggest(L.required)}, o ponga el PC en el piso.`,
    );
  }
  if (L.isL) {
    out.push(
      `El catálogo no trae escritorios en L: el ala de ${L.wingWidth} × ${L.wingLength} cm se muestra como extensión genérica y no suma al total.${L.pcOnWing ? " El PC va en el ala." : ""}`,
    );
  }
  if (!dk) {
    const need = L.pcOnDesk ? L.required : L.requiredNoPc;
    out.push(
      `No eligió escritorio: se muestra uno genérico de ${L.deskWidth} cm ajustado a sus equipos${L.pcOnDesk ? " con el PC encima" : L.pcOnWing ? ", con el PC en el ala" : ", con el PC en el piso"}. ${deskFor(desks, need) ? `Del catálogo le sirve ${suggest(need)}.` : "Ningún escritorio del catálogo alcanza: pruebe con el PC en el piso o menos equipos."}`,
    );
  }
  if (p.mic.some((m) => b(m, "arm")) && !p.mic.some((m) => !b(m, "arm"))) {
    out.push("El brazo para micrófono no incluye micrófono: agregue uno.");
  }
  if (p.mic.filter((m) => !b(m, "arm")).length > 1)
    out.push("Hay dos micrófonos: normalmente basta con uno.");
  if (p.mic.some((m) => b(m, "xlr"))) {
    out.push("Hay un micrófono XLR: necesita una interfaz de audio, que no está en la lista.");
  }
  if (!p.monitor.length) out.push("Sin monitor no hay dónde ver la imagen: elija al menos uno.");
  if (p.keyboard && /kit 3 en 1/i.test(p.keyboard.name) && (p.mouse || p.pad)) {
    out.push("El kit 3 en 1 ya trae mouse y pad: puede que no necesite otros.");
  }
  if (dk && b(dk, "integrated_case")) {
    out.push(
      "Este escritorio trae gabinete integrado: en la vista el PC se muestra aparte, sobre el escritorio.",
    );
  }
  return out;
}
