import { useMemo, useState } from "react";

import type { AssemblyChecklist } from "@/types/api";

import { useBuild, useCatalog } from "../hooks";
import { chosen } from "../presentation";
import type { SceneInput } from "../three/viewer";
import { Viewer3D } from "./Viewer3D";

const WEBGL = typeof window !== "undefined" && "WebGLRenderingContext" in window;

/**
 * The PC being assembled, as in the simulator's "Ensamblar" mode: each part appears (with an
 * animation) when its step is ticked; the board stays on the bench until it goes in the case.
 */
export function AssemblyLive3D({ checklist }: { checklist: AssemblyChecklist }) {
  const build = useBuild(checklist.build_id);
  const catalog = useCatalog();
  const [available, setAvailable] = useState(WEBGL);
  const done = useMemo(
    () => new Set(checklist.steps.filter((s) => s.done).map((s) => s.code)),
    [checklist.steps],
  );
  // The step just ticked is animated: compare with the steps of the previous render.
  const [seen, setSeen] = useState(done);
  const [fresh, setFresh] = useState<string | null>(null);
  if (seen !== done) {
    setFresh([...done].find((c) => !seen.has(c)) ?? null);
    setSeen(done);
  }
  const scene = useMemo<SceneInput | null>(() => {
    if (!build.data || !catalog.data) return null;
    const parts = chosen(catalog.data, build.data.selection);
    return {
      pc: {
        parts,
        ramModules: parts.ram
          ? Number(parts.ram.specs.modules ?? 1) * build.data.selection.ram_units
          : 0,
        bad: new Set(),
        done,
        fresh,
        lightsOn: done.has("boot") && build.data.evaluation.ready,
      },
      setup: null,
    };
  }, [build.data, catalog.data, done, fresh]);

  if (!available || !scene) return null;
  return (
    <div className="h-[clamp(320px,55vh,560px)]">
      <Viewer3D scene={scene} setupMode={false} onUnavailable={() => setAvailable(false)} />
    </div>
  );
}
