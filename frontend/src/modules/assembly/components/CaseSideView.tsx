import type { AssemblyCategory } from "@/types/api";

import type { Chosen } from "../presentation";

/**
 * Schematic side view of the case, ported from the owner's simulator (`pic()`): every part
 * appears where it goes and turns red when it is involved in an incompatibility.
 */
export function CaseSideView({
  parts,
  modules,
  bad,
}: {
  parts: Chosen;
  modules: number;
  bad: ReadonlySet<AssemblyCategory>;
}) {
  const B = (c: AssemblyCategory) => (bad.has(c) ? BAD : {});
  const spec = (p: { specs: Record<string, unknown> } | undefined, key: string) =>
    p?.specs[key] as never;

  const cs = parts.case;
  const size = String(spec(cs, "size") ?? "ATX");
  const gl = cs ? Number(spec(cs, "max_gpu_mm")) : 360;
  const cx = Math.round(380 - gl * 0.9 - 20);
  const ch = cs ? ({ XL: 430, ATX: 420, MATX: 380, ITX: 330 }[size] ?? 420) : 420;
  const bot = 20 + ch;

  const mb = parts.board;
  const f = mb ? String(spec(mb, "form_factor")) : "ATX";
  const [bw, bh] =
    f === "ITX" ? [146, 146] : f === "mATX" ? [210, 210] : f === "EATX" ? [226, 262] : [210, 262];
  const bx = 170;
  const by = 50;
  const sx = Math.round(bx + bw * 0.42 - 20);
  const sy = by + 50;
  const gy = f === "ITX" ? by + bh - 40 : Math.round(by + bh * 0.62);
  const my = f === "ITX" ? by + bh - 14 : sy + 65;
  const x0 = sx + 58;
  const rh = Math.min(110, Math.round(bh * 0.55));
  const slots = mb ? Number(spec(mb, "ram_slots")) : 0;
  const m2 = parts.storage.filter((d) => d.specs.interface === "M.2").length;
  const sata = parts.storage.filter((d) => d.specs.interface === "SATA");

  const psu = parts.psu;
  const sfx = psu?.specs.form_factor === "SFX";
  const [pw, ph] = sfx ? [120, 50] : [170, 60];
  const px = 388 - pw;
  const py = bot - 12 - ph;

  const cooler = parts.cooler;
  const gpu = parts.gpu;

  return (
    <svg
      viewBox="0 0 420 460"
      role="img"
      aria-label="Vista lateral del gabinete con las piezas elegidas"
      className="h-full w-full"
    >
      <rect
        x={cx}
        y={20}
        width={400 - cx}
        height={ch}
        rx={14}
        {...(cs ? CASE : GHOST)}
        {...B("CASE")}
      />
      {!cs && <Label x={cx + 14} y={44} muted text="Gabinete" />}
      {cs && (
        <>
          {[70, 122].map((y) => (
            <g key={y}>
              <circle cx={cx + 30} cy={y} r={20} fill="var(--muted)" stroke="var(--border)" />
              <circle cx={cx + 30} cy={y} r={6} fill="var(--border)" />
            </g>
          ))}
          <rect
            x={cx + 10}
            y={bot - 112}
            width={84}
            height={92}
            rx={4}
            fill="none"
            stroke="var(--border)"
            strokeWidth={1.5}
          />
        </>
      )}

      {!mb ? (
        <>
          <rect x={bx} y={by} width={bw} height={bh} rx={4} {...GHOST} />
          <Label x={bx + 12} y={by + 22} muted text="Placa base" />
        </>
      ) : (
        <g>
          <rect
            x={bx}
            y={by}
            width={bw}
            height={bh}
            rx={4}
            fill="#1f2a26"
            stroke="#0e1513"
            {...B("BOARD")}
          />
          <rect x={sx} y={sy} width={40} height={40} rx={2} fill="#11161a" stroke="#7d848c" />
          <rect x={bx + 24} y={my} width={64} height={10} rx={1} fill="#0b0e10" />
          <rect x={bx + bw - 100} y={gy + 20} width={88} height={5} fill="#0b0e10" />
          {Array.from({ length: slots }, (_, i) => (
            <rect key={i} x={x0 + i * 9} y={by + 18} width={6} height={rh} fill="#0b0e10" />
          ))}
          <Label x={x0} y={by + 14} text="RAM" />
          {parts.cpu && (
            <rect
              x={sx + 4}
              y={sy + 4}
              width={32}
              height={32}
              rx={2}
              fill="#c3c8cf"
              stroke="#6b7079"
              {...B("CPU")}
            />
          )}
          {parts.ram &&
            Array.from({ length: Math.min(modules, slots) }, (_, i) => (
              <rect
                key={i}
                x={x0 + i * 9}
                y={by + 18}
                width={6}
                height={rh}
                rx={1}
                fill="#6d7782"
                stroke="#30363c"
                {...B("RAM")}
              />
            ))}
          {m2 > 0 && (
            <>
              <rect
                x={bx + 24}
                y={my}
                width={64}
                height={10}
                rx={1}
                fill="#56606b"
                stroke="#22272c"
                {...B("STORAGE")}
              />
              <Label x={bx + 92} y={my + 10} text={`M.2${m2 > 1 ? ` ×${m2}` : ""}`} />
            </>
          )}
          {cooler && cooler.specs.type === "AIR" && (
            <g>
              <rect
                x={sx - 10}
                y={sy - 10}
                width={60}
                height={60}
                rx={4}
                fill="#9aa1aa"
                stroke="#4b5058"
                {...B("COOLER")}
              />
              {[1, 2, 3, 4, 5].map((k) => (
                <line
                  key={k}
                  x1={sx - 10 + k * 10}
                  y1={sy - 6}
                  x2={sx - 10 + k * 10}
                  y2={sy + 46}
                  stroke="#5c636c"
                  strokeWidth={1.5}
                />
              ))}
            </g>
          )}
          {cooler && cooler.specs.type === "AIO" && (
            <AioLoop
              cx={cx}
              sx={sx}
              sy={sy}
              radiator={Number(cooler.specs.radiator_mm)}
              bad={bad.has("COOLER")}
            />
          )}
        </g>
      )}

      {gpu && (
        <GpuCard
          length={Number(gpu.specs.length_mm) * 0.9}
          x={Math.round(bx + bw - 12 - Number(gpu.specs.length_mm) * 0.9)}
          y={gy}
          bad={bad.has("GPU")}
        />
      )}

      {psu ? (
        <g>
          <rect
            x={px}
            y={py}
            width={pw}
            height={ph}
            rx={3}
            fill="#33373d"
            stroke="#16181b"
            {...B("PSU")}
          />
          <Label x={px + 10} y={py + ph / 2 + 4} text={`Fuente ${Number(psu.specs.watts)} W`} />
        </g>
      ) : (
        <>
          <rect x={px} y={py} width={pw} height={ph} rx={3} {...GHOST} />
          <Label x={px + 10} y={py + ph / 2 + 4} muted text="Fuente" />
        </>
      )}
      {cs &&
        sata.map((d, i) => (
          <rect
            key={d.id + i}
            x={cx + 18}
            y={bot - 104 + i * 22}
            width={68}
            height={16}
            rx={2}
            fill="#7d858f"
            stroke="#3f454c"
          />
        ))}
    </svg>
  );
}

const CASE = { fill: "var(--card)", stroke: "var(--border)", strokeWidth: 2 };
const GHOST = {
  fill: "none",
  stroke: "var(--muted-foreground)",
  strokeDasharray: "6 5",
  strokeWidth: 1.5,
};
const BAD = { stroke: "var(--destructive)", strokeWidth: 3 };

function Label({ x, y, text, muted }: { x: number; y: number; text: string; muted?: boolean }) {
  return (
    <text
      x={x}
      y={y}
      fontSize={12}
      fontWeight={muted ? 400 : 500}
      fill={muted ? "var(--muted-foreground)" : "#eceef0"}
    >
      {text}
    </text>
  );
}

function GpuCard({ length, x, y, bad }: { length: number; x: number; y: number; bad: boolean }) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={length}
        height={24}
        rx={3}
        fill="#2b2f35"
        stroke="#0c0d0f"
        {...(bad ? BAD : {})}
      />
      <circle cx={x + length * 0.32} cy={y + 12} r={9} fill="#43484f" stroke="#16181b" />
      <circle cx={x + length * 0.68} cy={y + 12} r={9} fill="#43484f" stroke="#16181b" />
      <Label x={x + 8} y={y + 16} text="GPU" />
    </g>
  );
}

function AioLoop({
  cx,
  sx,
  sy,
  radiator,
  bad,
}: {
  cx: number;
  sx: number;
  sy: number;
  radiator: number;
  bad: boolean;
}) {
  const rw = radiator * 0.9;
  const rx = Math.round(cx + (400 - cx - rw) / 2);
  const tube = { fill: "none", stroke: "#2a2d31", strokeWidth: 4 };
  const red = bad ? BAD : {};
  return (
    <g>
      <path
        d={`M${sx + 12} ${sy + 4} C${sx + 12} ${sy - 30},${rx + 30} 70,${rx + 30} 44`}
        {...tube}
      />
      <path
        d={`M${sx + 28} ${sy + 4} C${sx + 28} ${sy - 24},${rx + 48} 74,${rx + 48} 44`}
        {...tube}
      />
      <rect x={rx} y={26} width={rw} height={18} rx={3} fill="#3b4047" stroke="#1a1c1f" {...red} />
      <rect
        x={sx + 2}
        y={sy + 2}
        width={36}
        height={36}
        rx={8}
        fill="#9aa1aa"
        stroke="#4b5058"
        {...red}
      />
      <circle cx={sx + 20} cy={sy + 20} r={7} fill="var(--border)" />
    </g>
  );
}
