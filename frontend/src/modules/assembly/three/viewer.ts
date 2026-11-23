/**
 * 3D viewer of the configurator: renderer, orbit camera, part picking, animations and RGB
 * effects. Ported from `init3D()`, `loop()` and `place()` of the owner's simulator.
 */
import * as THREE from "three";

import { setupLayout, type DeskShape, type PcPosition, type SetupParts } from "../setup";
import { Kit, canvasTexture, clear, emptyRgb, type Rgb, type RgbMaterialData } from "./kit";
import { buildPc, type PcInput } from "./pc";
import { buildRoom } from "./room";

export type RgbMode = "rainbow" | "wave" | "breath" | "static" | "off";
export type ViewName = "iso" | "side" | "top";

export interface SceneInput {
  pc: PcInput;
  /** When present the room with the setup is shown around the PC. */
  setup: { parts: SetupParts; shape: DeskShape; position: PcPosition } | null;
}

const VIEWS: Record<ViewName, [number, number]> = {
  iso: [0.55, 0.32],
  side: [0, 0.04],
  top: [0, 1.42],
};
const REDUCED =
  typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

interface Animation {
  object: THREE.Object3D;
  from: THREE.Vector3;
  fromQ: THREE.Quaternion;
  to: THREE.Vector3;
  toQ: THREE.Quaternion;
  start: number;
}

export class Viewer {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(35, 1, 1, 1000);
  private pc = new THREE.Group();
  private room = new THREE.Group();
  private mat: THREE.Mesh;
  private sun: THREE.DirectionalLight;
  private raycaster = new THREE.Raycaster();
  private rgb: Rgb = emptyRgb();
  private animations: Animation[] = [];
  private theta = 0.55;
  private phi = 0.32;
  private zoomFactor = 1;
  private target = { x: 0, y: 20, z: 0, distance: 100 };
  private lightsOn = false;
  private mode: RgbMode = "rainbow";
  private color = new THREE.Color("#ff1a3c");
  private dirty = true;
  private frame = 0;
  private drag: {
    x: number;
    y: number;
    theta: number;
    phi: number;
    moved: boolean;
    touch: boolean;
  } | null = null;
  private resize: ResizeObserver;
  private canvas: HTMLCanvasElement;
  private onPick: (label: string | null) => void;

  constructor(canvas: HTMLCanvasElement, onPick: (label: string | null) => void) {
    this.canvas = canvas;
    this.onPick = onPick;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;

    // Studio environment for reflections.
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const env = new THREE.Scene();
    const box = new THREE.Mesh(
      new THREE.BoxGeometry(120, 70, 120),
      new THREE.MeshBasicMaterial({ color: 0x2a2e34, side: THREE.BackSide }),
    );
    box.position.y = 25;
    env.add(box);
    for (const [x, y, z, w, h, d, k] of [
      [0, 58, 0, 60, 2, 40, 3],
      [-58, 30, 0, 2, 26, 60, 1.4],
      [58, 28, 20, 2, 22, 40, 1.8],
      [10, 30, -58, 50, 22, 2, 0.9],
    ] as const) {
      const panel = new THREE.Mesh(
        new THREE.BoxGeometry(w, h, d),
        new THREE.MeshBasicMaterial({ color: new THREE.Color(k, k, k) }),
      );
      panel.position.set(x, y, z);
      env.add(panel);
    }
    this.scene.environment = pmrem.fromScene(env, 0.03).texture;
    // Legacy light intensities × π for physically based lighting.
    this.scene.add(new THREE.HemisphereLight(0xf2f4f7, 0x3a3d42, 0.7 * Math.PI));
    this.sun = new THREE.DirectionalLight(0xfff6ec, 1.15 * Math.PI);
    this.sun.position.set(35, 85, 60);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    Object.assign(this.sun.shadow.camera, {
      left: -60,
      right: 60,
      top: 60,
      bottom: -60,
      near: 10,
      far: 230,
    });
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.radius = 4;
    this.scene.add(this.sun);
    const fill = new THREE.DirectionalLight(0xdfe8ff, 0.35 * Math.PI);
    fill.position.set(-50, 30, -30);
    this.scene.add(fill);

    // Assembly mat.
    const matTexture = canvasTexture("mat", 512, 512, (g, w, h) => {
      const gr = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
      gr.addColorStop(0, "rgba(52,56,62,1)");
      gr.addColorStop(0.7, "rgba(52,56,62,.95)");
      gr.addColorStop(1, "rgba(52,56,62,0)");
      g.fillStyle = gr;
      g.fillRect(0, 0, w, h);
    });
    this.mat = new THREE.Mesh(
      new THREE.CircleGeometry(80, 72),
      new THREE.MeshStandardMaterial({
        map: matTexture,
        transparent: true,
        roughness: 0.92,
        metalness: 0,
      }),
    );
    this.mat.rotation.x = -Math.PI / 2;
    this.mat.position.y = -0.02;
    this.mat.receiveShadow = true;
    this.mat.userData.noPick = true;
    this.scene.add(this.mat, this.pc, this.room);

    canvas.addEventListener("pointerdown", this.onDown);
    canvas.addEventListener("pointermove", this.onMove);
    canvas.addEventListener("pointerup", this.onUp);
    canvas.addEventListener("pointercancel", this.onCancel);
    canvas.addEventListener("wheel", this.onWheel, { passive: false });
    this.resize = new ResizeObserver(() => this.fit());
    this.resize.observe(canvas.parentElement ?? canvas);
    this.fit();
    this.frame = requestAnimationFrame(this.loop);
  }

  /** Rebuilds the scene from the current parts. */
  update(input: SceneInput): void {
    clear(this.pc);
    clear(this.room);
    this.rgb = emptyRgb();
    this.animations = [];
    this.lightsOn = input.pc.lightsOn;
    const kit = new Kit(this.rgb, this.lightsOn);
    const animate = (
      o: THREE.Object3D,
      from: THREE.Vector3,
      fromQ: THREE.Quaternion,
      to: THREE.Vector3,
      toQ: THREE.Quaternion,
    ) => {
      if (REDUCED) {
        o.position.copy(to);
        o.quaternion.copy(toQ);
        return;
      }
      o.position.copy(from);
      o.quaternion.copy(fromQ);
      this.animations.push({
        object: o,
        from: from.clone(),
        fromQ: fromQ.clone(),
        to: to.clone(),
        toQ: toQ.clone(),
        start: performance.now(),
      });
    };
    const pc = buildPc(this.pc, kit, input.pc, animate);
    const setup = input.setup;
    const camera = this.sun.shadow.camera;
    if (setup) {
      const layout = setupLayout(setup.parts, setup.shape, setup.position);
      const result = buildRoom(
        this.room,
        kit,
        { parts: setup.parts, layout, pc: pc.size, fresh: input.pc.fresh, lightsOn: this.lightsOn },
        animate,
      );
      this.pc.position.set(result.pc.x, result.pc.y, result.pc.z);
      this.pc.rotation.y = -Math.PI / 2;
      this.target = result.focus;
      Object.assign(camera, { left: -170, right: 170, top: 170, bottom: -170, far: 500 });
      this.sun.position.set(90, 230, 170);
    } else {
      this.pc.position.set(0, 0, 0);
      this.pc.rotation.y = 0;
      this.target = pc.focus;
      Object.assign(camera, { left: -60, right: 60, top: 60, bottom: -60, far: 230 });
      this.sun.position.set(35, 85, 60);
    }
    camera.updateProjectionMatrix();
    this.mat.visible = !setup;
    this.addGlows();
    if (this.lightsOn && this.rgb.materials.length && !setup) {
      const { L, H, W } = pc.size;
      for (const [x, y, z] of [
        [L * 0.25, H * 0.8, W / 2 - 4],
        [-L * 0.2, H * 0.3, W / 2 - 5],
      ] as const) {
        const light = new THREE.PointLight(0xff00ff, 0, L * 1.5, 0);
        light.position.set(x, y, z);
        light.userData.strength = 0.55 + Math.min(1, this.rgb.materials.length / 14) * 0.9;
        this.pc.add(light);
        this.rgb.ambients.push(light);
      }
    }
    if (!this.lightsOn) for (const m of this.rgb.materials) m.emissive.setRGB(0, 0, 0);
    this.place();
  }

  setView(view: ViewName, setupMode: boolean) {
    [this.theta, this.phi] = VIEWS[view];
    if (setupMode && view === "iso") [this.theta, this.phi] = [-0.55, 0.46];
    this.place();
  }

  resetCamera(setupMode: boolean) {
    this.theta = setupMode ? -0.55 : 0.55;
    this.phi = setupMode ? 0.46 : 0.32;
    this.zoomFactor = 1;
    this.place();
  }

  zoom(k: number) {
    this.zoomFactor = Math.max(0.45, Math.min(2.2, this.zoomFactor * k));
    this.place();
  }

  setRgb(mode: RgbMode, color: string) {
    this.mode = mode;
    this.color.set(color);
    this.dirty = true;
  }

  dispose() {
    cancelAnimationFrame(this.frame);
    this.resize.disconnect();
    this.canvas.removeEventListener("pointerdown", this.onDown);
    this.canvas.removeEventListener("pointermove", this.onMove);
    this.canvas.removeEventListener("pointerup", this.onUp);
    this.canvas.removeEventListener("pointercancel", this.onCancel);
    this.canvas.removeEventListener("wheel", this.onWheel);
    clear(this.pc);
    clear(this.room);
    this.renderer.dispose();
  }

  /* --- internals ----------------------------------------------------------------------- */

  /** Additive halo around each glowing RGB mesh (as in the simulator). */
  private addGlows() {
    const size = new THREE.Vector3();
    for (const root of [this.pc, this.room]) {
      root.updateMatrixWorld(true);
      const position = new THREE.Vector3();
      root.traverse((o) => {
        const mesh = o as THREE.Mesh;
        const material = mesh.material as THREE.MeshStandardMaterial | undefined;
        const data = material?.userData as Partial<RgbMaterialData> | undefined;
        if (!mesh.isMesh || !data?.rgb) return;
        mesh.getWorldPosition(position);
        if (data.wavePhase === undefined) data.wavePhase = (position.x + position.y * 0.6) / 90;
        if (!data.glow || o.userData.noPick || o.userData.isGlow) return;
        mesh.geometry.computeBoundingBox();
        mesh.geometry.boundingBox?.getSize(size);
        const glow = new THREE.MeshBasicMaterial({
          color: 0,
          transparent: true,
          opacity: 0.32,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });
        const halo = new THREE.Mesh(mesh.geometry, glow);
        halo.scale.set(
          (size.x + 0.7) / Math.max(size.x, 0.01),
          (size.y + 0.7) / Math.max(size.y, 0.01),
          (size.z + 0.7) / Math.max(size.z, 0.01),
        );
        halo.userData.noPick = halo.userData.isGlow = true;
        o.add(halo);
        this.rgb.glows.push({ source: material!, glow });
      });
    }
    if (!this.lightsOn) for (const g of this.rgb.glows) g.glow.visible = false;
  }

  private fit() {
    const parent = this.canvas.parentElement;
    const w = parent?.clientWidth ?? this.canvas.clientWidth;
    const h = parent?.clientHeight ?? this.canvas.clientHeight;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.place();
  }

  private place() {
    const c = Math.cos(this.phi);
    const d = this.target.distance * this.zoomFactor * Math.max(1, 1.05 / this.camera.aspect);
    const t = this.target;
    this.camera.position.set(
      t.x + Math.sin(this.theta) * c * d,
      t.y + Math.sin(this.phi) * d,
      t.z + Math.cos(this.theta) * c * d,
    );
    this.camera.lookAt(t.x, t.y, t.z);
    this.dirty = true;
  }

  private loop = (now: number) => {
    this.frame = requestAnimationFrame(this.loop);
    let busy = false;
    this.animations = this.animations.filter((a) => {
      const t = Math.min(1, (now - a.start) / 850);
      const e = 1 - Math.pow(1 - t, 3);
      a.object.position.lerpVectors(a.from, a.to, e);
      a.object.quaternion.copy(a.fromQ).slerp(a.toQ, e);
      busy = true;
      return t < 1;
    });
    if (this.lightsOn) {
      const t = REDUCED ? 0 : now / 1000;
      const mode = this.mode;
      const breath = 0.12 + 0.88 * (0.5 + 0.5 * Math.sin(t * 2.2));
      if (!REDUCED) for (const f of this.rgb.fans) f.rotation.z += f.userData.speed as number;
      const c = new THREE.Color();
      for (const m of this.rgb.materials) {
        const data = m.userData as RgbMaterialData;
        if (mode === "off") c.setRGB(0, 0, 0);
        else if (mode === "rainbow") c.setHSL((t * 0.12 + data.phase) % 1, 1, 0.5);
        else if (mode === "wave")
          c.setHSL((((t * 0.35 + (data.wavePhase ?? 0)) % 1) + 1) % 1, 1, 0.5);
        else c.copy(this.color).multiplyScalar(mode === "breath" ? breath : 1);
        m.emissive.copy(c).multiplyScalar(data.strength);
      }
      for (const { source, glow } of this.rgb.glows) {
        glow.color.copy(source.emissive);
        glow.visible = mode !== "off";
      }
      this.rgb.ambients.forEach((light, i) => {
        if (mode === "off") {
          light.intensity = 0;
          return;
        }
        if (mode === "rainbow" || mode === "wave")
          light.color.setHSL((t * 0.12 + i * 0.33) % 1, 1, 0.5);
        else light.color.copy(this.color);
        light.intensity =
          (light.userData.strength as number) * Math.PI * (mode === "breath" ? breath : 1);
      });
      busy = !REDUCED || this.dirty;
    }
    if (busy || this.dirty) {
      this.renderer.render(this.scene, this.camera);
      this.dirty = false;
    }
  };

  private onDown = (e: PointerEvent) => {
    this.drag = {
      x: e.clientX,
      y: e.clientY,
      theta: this.theta,
      phi: this.phi,
      moved: false,
      touch: e.pointerType === "touch",
    };
    try {
      this.canvas.setPointerCapture(e.pointerId);
    } catch {
      /* pointer already released */
    }
  };

  private onMove = (e: PointerEvent) => {
    const d = this.drag;
    if (!d) return;
    const dx = e.clientX - d.x;
    const dy = e.clientY - d.y;
    if (Math.abs(dx) + Math.abs(dy) > 5) d.moved = true;
    this.theta = d.theta - dx * 0.008;
    if (!d.touch) this.phi = Math.max(0.02, Math.min(1.45, d.phi + dy * 0.006));
    this.place();
  };

  private onUp = (e: PointerEvent) => {
    const d = this.drag;
    this.drag = null;
    if (d && !d.moved) this.pick(e);
  };

  private onCancel = () => {
    this.drag = null;
  };

  private onWheel = (e: WheelEvent) => {
    e.preventDefault();
    this.zoom(e.deltaY > 0 ? 1.08 : 1 / 1.08);
  };

  private pick(e: PointerEvent) {
    const rect = this.canvas.getBoundingClientRect();
    const v = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1,
    );
    this.raycaster.setFromCamera(v, this.camera);
    const label = (o: THREE.Object3D | null): string | null => {
      while (o) {
        if (typeof o.userData.label === "string") return o.userData.label;
        o = o.parent;
      }
      return null;
    };
    const hit = this.raycaster
      .intersectObjects([...this.pc.children, ...this.room.children], true)
      .find((i) => !i.object.userData.noPick && label(i.object));
    this.onPick(hit ? label(hit.object) : null);
  }
}
