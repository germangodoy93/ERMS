/**
 * Small 3D toolkit shared by the PC and the room scenes. Ported from the owner's simulator
 * (three.js r128) to three.js 0.187: colors and textures use the sRGB color space and light
 * intensities are scaled for physically based lighting.
 */
import * as THREE from "three";

export type Part = { name: string; specs: Record<string, unknown> };

/** Texture cache: canvases are drawn once per key. */
const textures = new Map<string, THREE.CanvasTexture>();

export function canvasTexture(
  key: string,
  width: number,
  height: number,
  draw: (g: CanvasRenderingContext2D, w: number, h: number) => void,
  repeat = false,
): THREE.CanvasTexture {
  const cached = textures.get(key);
  if (cached) return cached;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const g = canvas.getContext("2d");
  if (g) draw(g, width, height);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  if (repeat) texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  textures.set(key, texture);
  return texture;
}

/** Text label drawn on a plain background (brands on boards, RAM, PSU…). */
export function labelTexture(
  key: string,
  width: number,
  height: number,
  background: string,
  lines: [text: string, x: number, y: number, size: number, color: string, weight?: string][],
): THREE.CanvasTexture {
  return canvasTexture(key, width, height, (g, w, h) => {
    g.fillStyle = background;
    g.fillRect(0, 0, w, h);
    for (const [text, x, y, size, color, weight = "600"] of lines) {
      g.fillStyle = color;
      g.font = `${weight} ${size}px Geist, Arial, sans-serif`;
      g.textBaseline = "middle";
      g.fillText(text, x, y);
    }
  });
}

/** Deterministic pseudo-random numbers, so textures look the same on every render. */
export function seeded(seed: number): () => number {
  let s = seed >>> 0 || 1;
  return () => {
    s = Math.imul(s ^ (s >>> 15), 2246822507) ^ Math.imul(s ^ (s >>> 13), 3266489909);
    return ((s ^= s >>> 16) >>> 0) / 4294967296;
  };
}

export const hexColor = (n: number) => "#" + n.toString(16).padStart(6, "0");

/** Reads a numeric spec. */
export const num = (p: Part | null | undefined, key: string, fallback = 0): number => {
  const v = p?.specs[key];
  return typeof v === "number" ? v : fallback;
};
export const str = (p: Part | null | undefined, key: string, fallback = ""): string => {
  const v = p?.specs[key];
  return typeof v === "string" ? v : fallback;
};
export const flag = (p: Part | null | undefined, key: string): boolean => p?.specs[key] === true;

/** Visual hint from `specs.style` (color as "#rrggbb", booleans, numbers, labels). */
export function style(p: Part | null | undefined): Record<string, unknown> {
  const s = p?.specs.style;
  return s && typeof s === "object" ? (s as Record<string, unknown>) : {};
}
export const styleColor = (p: Part | null | undefined, key: string, fallback: number): number => {
  const v = style(p)[key];
  return typeof v === "string" && /^#[0-9a-f]{6}$/i.test(v) ? parseInt(v.slice(1), 16) : fallback;
};
export const styleFlag = (p: Part | null | undefined, key: string): boolean =>
  style(p)[key] === true;
export const styleNum = (p: Part | null | undefined, key: string, fallback: number): number => {
  const v = style(p)[key];
  return typeof v === "number" ? v : fallback;
};
export const styleText = (p: Part | null | undefined, key: string, fallback: string): string => {
  const v = style(p)[key];
  return typeof v === "string" ? v : fallback;
};

export interface Rgb {
  /** RGB materials animated by the viewer. */
  materials: THREE.MeshStandardMaterial[];
  /** Additive halos that follow their material's color. */
  glows: { source: THREE.MeshStandardMaterial; glow: THREE.MeshBasicMaterial }[];
  /** Colored room lights that follow the effect. */
  ambients: THREE.PointLight[];
  /** Spinning fan rotors. */
  fans: THREE.Object3D[];
}

export function emptyRgb(): Rgb {
  return { materials: [], glows: [], ambients: [], fans: [] };
}

export interface RgbMaterialData {
  rgb: true;
  phase: number;
  strength: number;
  glow: boolean;
  wavePhase?: number;
}

/** Builder helpers bound to a target group and an RGB registry. */
export class Kit {
  readonly rgb: Rgb;
  readonly lightsOn: boolean;

  constructor(rgb: Rgb, lightsOn: boolean) {
    this.rgb = rgb;
    this.lightsOn = lightsOn;
  }

  material(
    color: number,
    metalness = 0.3,
    roughness = 0.6,
    extra: THREE.MeshStandardMaterialParameters = {},
  ) {
    return new THREE.MeshStandardMaterial({ color, metalness, roughness, ...extra });
  }

  rgbMaterial(strength = 1, glow = true): THREE.MeshStandardMaterial {
    const m = this.material(0x2a2a2e, 0.1, 0.35, { emissive: 0x000000, emissiveIntensity: 1.5 });
    const data: RgbMaterialData = { rgb: true, phase: Math.random(), strength, glow };
    m.userData = data;
    this.rgb.materials.push(m);
    return m;
  }

  box(
    parent: THREE.Object3D,
    w: number,
    h: number,
    d: number,
    material: THREE.Material | THREE.Material[],
    x: number,
    y: number,
    z: number,
  ): THREE.Mesh {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    parent.add(mesh);
    return mesh;
  }

  cylinder(
    parent: THREE.Object3D,
    radius: number,
    height: number,
    material: THREE.Material,
    x: number,
    y: number,
    z: number,
    axis: "x" | "y" | "z" = "z",
    segments = 28,
  ): THREE.Mesh {
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(radius, radius, height, segments),
      material,
    );
    if (axis === "z") mesh.rotation.x = Math.PI / 2;
    if (axis === "x") mesh.rotation.z = Math.PI / 2;
    mesh.position.set(x, y, z);
    mesh.castShadow = true;
    parent.add(mesh);
    return mesh;
  }

  group(label: string, parent: THREE.Object3D): THREE.Group {
    const g = new THREE.Group();
    g.userData.label = label;
    parent.add(g);
    return g;
  }

  tube(
    parent: THREE.Object3D,
    points: THREE.Vector3[],
    radius: number,
    material: THREE.MeshStandardMaterial,
  ): THREE.Mesh {
    const curve = new THREE.CatmullRomCurve3(points);
    const mesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 64, radius, 10, false), material);
    mesh.castShadow = true;
    parent.add(mesh);
    const data = material.userData as Partial<RgbMaterialData>;
    if (data.rgb) {
      const glow = new THREE.MeshBasicMaterial({
        color: 0,
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const halo = new THREE.Mesh(new THREE.TubeGeometry(curve, 64, radius * 2.1, 10, false), glow);
      halo.userData.noPick = true;
      parent.add(halo);
      this.rgb.glows.push({ source: material, glow });
      data.glow = false;
    }
    return mesh;
  }

  /** A fan: frame, spinning blades and an optional RGB ring (as in the simulator). */
  fan(
    parent: THREE.Object3D,
    size: number,
    x: number,
    y: number,
    z: number,
    axis: "x" | "y" | "z",
    opts: {
      frame?: number;
      blade?: number;
      hub?: number;
      noFrame?: boolean;
      blades?: number;
      kit?: boolean;
      infinity?: boolean;
      lcd?: boolean;
      rgb?: boolean;
    } = {},
  ): THREE.Group {
    const f = new THREE.Group();
    const h = size / 2;
    const d = size * 0.21;
    if (!opts.noFrame) {
      const fm = this.material(opts.frame ?? 0x16171a, 0.15, 0.6);
      const bw = size * 0.07;
      this.box(f, size, bw, d, fm, 0, h - bw / 2, 0);
      this.box(f, size, bw, d, fm, 0, -h + bw / 2, 0);
      this.box(f, bw, size, d, fm, h - bw / 2, 0, 0);
      this.box(f, bw, size, d, fm, -h + bw / 2, 0, 0);
      const ring = new THREE.Mesh(
        new THREE.CylinderGeometry(h * 0.94, h * 0.94, d, 40, 1, true),
        this.material(opts.frame ?? 0x16171a, 0.15, 0.6, { side: THREE.DoubleSide }),
      );
      ring.rotation.x = Math.PI / 2;
      f.add(ring);
    }
    const rotor = new THREE.Group();
    let bladeMaterial: THREE.MeshStandardMaterial;
    if (opts.kit) {
      bladeMaterial = this.rgbMaterial(0.35, false);
      bladeMaterial.color.setHex(0xd8dbe0);
      bladeMaterial.transparent = true;
      bladeMaterial.opacity = 0.85;
      bladeMaterial.side = THREE.DoubleSide;
    } else {
      bladeMaterial = this.material(opts.blade ?? 0x1c1d20, 0.05, 0.5, { side: THREE.DoubleSide });
    }
    const n = opts.blades ?? 7;
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const blade = new THREE.Mesh(new THREE.BoxGeometry(h * 0.6, h * 0.36, 0.08), bladeMaterial);
      blade.position.set(Math.cos(a) * h * 0.6, Math.sin(a) * h * 0.6, 0);
      blade.rotation.set(0, 0, a + 0.55);
      blade.rotateX(0.5);
      blade.castShadow = true;
      rotor.add(blade);
    }
    const hub = new THREE.Mesh(
      new THREE.CylinderGeometry(h * 0.3, h * 0.3, d * 0.7, 28),
      this.material(opts.hub ?? opts.blade ?? 0x1c1d20, 0.2, 0.45),
    );
    hub.rotation.x = Math.PI / 2;
    rotor.add(hub);
    rotor.userData.speed = 0.18 + Math.random() * 0.06;
    this.rgb.fans.push(rotor);
    f.add(rotor);
    if (opts.kit) {
      const ringMaterial = this.rgbMaterial();
      for (const zz of [d / 2, -d / 2]) {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(h * 0.94, 0.16, 8, 48), ringMaterial);
        ring.position.z = zz;
        f.add(ring);
      }
      if (opts.infinity) {
        for (let k = 1; k < 4; k++) {
          const ring = new THREE.Mesh(
            new THREE.TorusGeometry(h * (0.94 - k * 0.035), 0.07, 6, 48),
            ringMaterial,
          );
          ring.position.z = d / 2 - k * 0.25;
          ring.userData.noPick = true;
          f.add(ring);
        }
      }
      if (opts.lcd) {
        const screen = canvasTexture("fan-lcd", 128, 128, (g, w, hh) => {
          const gradient = g.createRadialGradient(w / 2, hh / 2, 4, w / 2, hh / 2, w / 2);
          gradient.addColorStop(0, "#ff3ec8");
          gradient.addColorStop(0.6, "#5b2bff");
          gradient.addColorStop(1, "#05060a");
          g.fillStyle = gradient;
          g.fillRect(0, 0, w, hh);
          g.fillStyle = "#fff";
          g.font = "700 34px Geist, Arial";
          g.textAlign = "center";
          g.textBaseline = "middle";
          g.fillText("GG", w / 2, hh / 2);
        });
        const lcd = new THREE.Mesh(
          new THREE.CircleGeometry(h * 0.3, 28),
          this.material(0x050608, 0.2, 0.3, {
            emissive: 0xffffff,
            emissiveMap: screen,
            emissiveIntensity: this.lightsOn ? 1 : 0,
          }),
        );
        lcd.position.z = d * 0.36;
        rotor.add(lcd);
      }
    } else if (opts.rgb) {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(h * 0.94, 0.14, 8, 48),
        this.rgbMaterial(),
      );
      ring.position.z = d / 2;
      f.add(ring);
    }
    if (axis === "x") f.rotation.y = Math.PI / 2;
    if (axis === "y") f.rotation.x = Math.PI / 2;
    f.position.set(x, y, z);
    parent.add(f);
    return f;
  }

  /** Dashed outline of a part that is still missing. */
  ghost(parent: THREE.Object3D, w: number, h: number, d: number, x: number, y: number, z: number) {
    const lines = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(w, h, d)),
      new THREE.LineBasicMaterial({ color: 0x8a9099, transparent: true, opacity: 0.75 }),
    );
    lines.position.set(x, y, z);
    lines.userData.noPick = true;
    parent.add(lines);
  }
}

/** Disposes geometries and materials of everything under `root` and empties it. */
export function clear(root: THREE.Object3D) {
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (mesh.geometry) mesh.geometry.dispose();
    const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
    if (material) for (const m of ([] as THREE.Material[]).concat(material)) m.dispose();
  });
  while (root.children.length) root.remove(root.children[0]!);
}
