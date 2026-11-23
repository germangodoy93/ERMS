import { Minus, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import type { RgbMode, SceneInput, ViewName, Viewer } from "../three/viewer";

const FX_KEY = "erms.assembly.rgb";
const MODES: [RgbMode, string][] = [
  ["rainbow", "Arcoíris"],
  ["wave", "Ola"],
  ["breath", "Respiración"],
  ["static", "Fijo"],
  ["off", "Apagado"],
];
const SWATCHES: [string, string][] = [
  ["#ff1a3c", "Rojo"],
  ["#ff7a00", "Naranja"],
  ["#39ff6a", "Verde"],
  ["#00e5ff", "Cian"],
  ["#2f6bff", "Azul"],
  ["#8a2bff", "Morado"],
  ["#ff3ec8", "Rosa"],
  ["#ffffff", "Blanco"],
];
const HINT = "Arrastre para girar · toque una pieza para ver qué es";

function savedFx(): { mode: RgbMode; color: string } {
  try {
    const raw = JSON.parse(localStorage.getItem(FX_KEY) ?? "null") as {
      mode?: RgbMode;
      color?: string;
    } | null;
    if (raw?.mode && raw.color) return { mode: raw.mode, color: raw.color };
  } catch {
    /* private mode or corrupt value: use defaults */
  }
  return { mode: "rainbow", color: "#ff1a3c" };
}

/**
 * 3D view of the configured PC (and its setup). three.js is loaded only when this view
 * opens. Without WebGL it calls `onUnavailable` so the page falls back to the 2D view.
 */
export function Viewer3D({
  scene,
  setupMode,
  onUnavailable,
  showRgbControls = true,
}: {
  scene: SceneInput;
  setupMode: boolean;
  onUnavailable: () => void;
  showRgbControls?: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const viewer = useRef<Viewer | null>(null);
  const latest = useRef(scene);
  const [caption, setCaption] = useState(HINT);
  const [ready, setReady] = useState(false);
  const [fx, setFx] = useState(savedFx);

  useEffect(() => {
    let alive = true;
    void import("../three/viewer")
      .then(({ Viewer }) => {
        if (!alive || !canvas.current) return;
        const v = new Viewer(canvas.current, (label) => setCaption(label ?? HINT));
        viewer.current = v;
        v.setRgb(savedFx().mode, savedFx().color);
        v.update(latest.current);
        setReady(true);
      })
      .catch(() => {
        if (alive) onUnavailable();
      });
    return () => {
      alive = false;
      viewer.current?.dispose();
      viewer.current = null;
    };
    // The viewer is created once; scene changes are applied by the next effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    latest.current = scene;
    viewer.current?.update(scene);
  }, [scene]);

  useEffect(() => {
    viewer.current?.resetCamera(setupMode);
  }, [setupMode, ready]);

  const changeFx = (next: { mode: RgbMode; color: string }) => {
    setFx(next);
    viewer.current?.setRgb(next.mode, next.color);
    try {
      localStorage.setItem(FX_KEY, JSON.stringify(next));
    } catch {
      /* storage unavailable: the choice lasts for this page only */
    }
  };
  const view = (name: ViewName) => viewer.current?.setView(name, setupMode);

  return (
    <div className="grid h-full grid-rows-[minmax(0,1fr)_auto] gap-2">
      <div className="relative min-h-0 overflow-hidden rounded-xl border bg-[radial-gradient(120%_90%_at_50%_28%,var(--card),var(--background))]">
        <canvas
          ref={canvas}
          className="absolute inset-0 block h-full w-full cursor-grab touch-pan-y active:cursor-grabbing"
          aria-label="Vista 3D del equipo con sus piezas"
        />
        <div className="pointer-events-none absolute inset-x-2 top-2 flex flex-wrap gap-1.5">
          {(
            [
              ["iso", "3/4"],
              ["side", "Lateral"],
              ["top", "Superior"],
            ] as const
          ).map(([name, label]) => (
            <Button
              key={name}
              size="sm"
              variant="outline"
              className="bg-card/85 pointer-events-auto backdrop-blur"
              onClick={() => view(name)}
            >
              {label}
            </Button>
          ))}
          <Button
            size="icon"
            variant="outline"
            aria-label="Acercar"
            className="bg-card/85 pointer-events-auto"
            onClick={() => viewer.current?.zoom(0.85)}
          >
            <Plus />
          </Button>
          <Button
            size="icon"
            variant="outline"
            aria-label="Alejar"
            className="bg-card/85 pointer-events-auto"
            onClick={() => viewer.current?.zoom(1.18)}
          >
            <Minus />
          </Button>
        </div>
        {!ready && (
          <p className="text-muted-foreground absolute inset-0 grid place-items-center text-sm">
            Cargando vista 3D…
          </p>
        )}
      </div>
      <p className="text-muted-foreground min-h-5 text-sm">{caption}</p>
      {showRgbControls && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted-foreground text-xs">Iluminación RGB</span>
          <div
            className="bg-muted flex flex-wrap gap-1 rounded-lg p-1"
            role="group"
            aria-label="Efecto RGB"
          >
            {MODES.map(([mode, label]) => (
              <button
                key={mode}
                type="button"
                aria-pressed={fx.mode === mode}
                onClick={() => changeFx({ ...fx, mode })}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs",
                  fx.mode === mode && "bg-foreground text-background",
                )}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex gap-1.5" role="group" aria-label="Color">
            {SWATCHES.map(([color, label]) => (
              <button
                key={color}
                type="button"
                aria-label={label}
                title={label}
                aria-pressed={fx.color === color}
                onClick={() =>
                  changeFx({
                    color,
                    mode:
                      fx.mode === "rainbow" || fx.mode === "wave" || fx.mode === "off"
                        ? "static"
                        : fx.mode,
                  })
                }
                className={cn(
                  "size-6 rounded-full border-2",
                  fx.color === color ? "border-foreground" : "border-border",
                )}
                style={{ background: color }}
              />
            ))}
          </div>
          {!scene.pc.lightsOn && (
            <span className="text-muted-foreground basis-full text-xs">
              La iluminación se enciende cuando el equipo está completo y es compatible.
            </span>
          )}
        </div>
      )}
    </div>
  );
}
