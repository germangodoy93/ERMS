/** The PC in 3D, ported from `build3D()` of the owner's simulator. */
import * as THREE from "three";

import {
  Kit,
  canvasTexture,
  flag,
  hexColor,
  labelTexture,
  num,
  seeded,
  str,
  style,
  styleColor,
  styleFlag,
  styleNum,
  styleText,
  type Part,
} from "./kit";

export interface PcParts {
  cpu?: Part;
  board?: Part;
  ram?: Part;
  gpu?: Part;
  psu?: Part;
  case?: Part;
  cooler?: Part;
  storage: Part[];
  rgb: Part[];
}

export interface PcInput {
  parts: PcParts;
  ramModules: number;
  /** Categories involved in an incompatibility (drawn red). */
  bad: ReadonlySet<string>;
  /** Assembly steps done; null outside the assembly checklist (everything is shown). */
  done: ReadonlySet<string> | null;
  /** Part just added, animated into place. */
  fresh: string | null;
  lightsOn: boolean;
}

export interface PcResult {
  /** Case size, used by the room to place the PC. */
  size: { L: number; H: number; W: number };
  /** Where the camera should look. */
  focus: { x: number; y: number; z: number; distance: number };
}

export type Animate = (
  object: THREE.Object3D,
  from: THREE.Vector3,
  fromQuaternion: THREE.Quaternion,
  to: THREE.Vector3,
  toQuaternion: THREE.Quaternion,
) => void;

const RED = 0xd9262c;
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
const CASE_HEIGHT: Record<string, number> = { XL: 52, ATX: 46, MATX: 40, ITX: 32 };
const CASE_WIDTH: Record<string, number> = { XL: 24, ATX: 22, MATX: 20, ITX: 18 };

export function buildPc(root: THREE.Group, kit: Kit, input: PcInput, animate: Animate): PcResult {
  const { parts: r, done, fresh } = input;
  const A = done !== null;
  const H = (step: string) => !A || done.has(step);
  const BAD = (c: string) => !A && input.bad.has(c);
  const on = input.lightsOn;
  const M = kit.material.bind(kit);
  const box = kit.box.bind(kit);
  const cyl = kit.cylinder.bind(kit);
  const grp = (label: string, parent: THREE.Object3D = root) => kit.group(label, parent);
  const off = (o: THREE.Object3D, dx: number, dy: number, dz: number) => {
    const to = o.position.clone();
    animate(o, to.clone().add(V(dx, dy, dz)), o.quaternion.clone(), to, o.quaternion.clone());
  };
  const slv = M(0xb8bec6, 0.9, 0.25);
  const blk = M(0x111214, 0.2, 0.6);
  const kinds = r.rgb.map((x) => str(x, "kind"));
  const kitFans = r.rgb.filter((x) => str(x, "kind") === "FAN_KIT");

  /* ---- case ---- */
  const cs = r.case;
  const size = str(cs, "size", "ATX");
  const L = cs ? num(cs, "max_gpu_mm") / 10 + 6 : 42;
  const Hc = cs ? (CASE_HEIGHT[size] ?? 46) : 46;
  const W = cs ? (CASE_WIDTH[size] ?? 22) : 22;
  const t = 0.4;
  const caseColor = styleColor(cs, "color", 0x1a1b1e);
  const front = styleText(cs, "front", "mesh");
  if (cs) {
    const g = grp(`Gabinete · ${cs.name}`);
    const body = M(caseColor, 0.15, 0.55);
    const inner = M(styleColor(cs, "inner", 0x141517), 0.05, 0.85);
    box(g, L, t, W, body, 0, t / 2, 0);
    box(g, L, t, W, body, 0, Hc - t / 2, 0);
    box(g, L, Hc, t, inner, 0, Hc / 2, -W / 2 + t / 2);
    box(g, t, Hc, W, body, -L / 2 + t / 2, Hc / 2, 0);
    for (let i = 0; i < 7 && i * 2.03 < Hc * 0.45; i++) {
      box(
        g,
        0.12,
        1.6,
        W * 0.7,
        M(0x8e949b, 0.8, 0.35),
        -L / 2 + t + 0.06,
        Hc * 0.18 + i * 2.03,
        -W * 0.1,
      );
    }
    let frontMaterial: THREE.MeshStandardMaterial;
    if (front === "mesh") {
      const tx = canvasTexture(
        `mesh${caseColor}`,
        128,
        128,
        (g2, w, h) => {
          g2.fillStyle = hexColor(caseColor);
          g2.fillRect(0, 0, w, h);
          g2.fillStyle = "rgba(0,0,0,.75)";
          for (let yy = 0; yy < h; yy += 8)
            for (let xx = ((yy / 8) % 2) * 4; xx < w; xx += 8) {
              g2.beginPath();
              g2.arc(xx, yy, 2.6, 0, 7);
              g2.fill();
            }
        },
        true,
      ).clone();
      tx.needsUpdate = true;
      tx.repeat.set(W / 4, Hc / 4);
      frontMaterial = M(0xffffff, 0.3, 0.55, { map: tx });
    } else if (front === "wood") {
      const tx = canvasTexture(
        "wood",
        256,
        256,
        (g2, w, h) => {
          const rand = seeded(3);
          g2.fillStyle = "#8a5a33";
          g2.fillRect(0, 0, w, h);
          for (let i = 0; i < 120; i++) {
            g2.strokeStyle = `rgba(${(60 + rand() * 40) | 0},${(35 + rand() * 20) | 0},15,${0.25 + rand() * 0.35})`;
            g2.lineWidth = 1 + rand() * 3;
            const yy = rand() * h;
            g2.beginPath();
            g2.moveTo(0, yy);
            g2.bezierCurveTo(
              w * 0.3,
              yy + rand() * 8 - 4,
              w * 0.6,
              yy + rand() * 8 - 4,
              w,
              yy + rand() * 6 - 3,
            );
            g2.stroke();
          }
        },
        true,
      );
      tx.rotation = Math.PI / 2;
      frontMaterial = M(0xffffff, 0, 0.7, { map: tx });
    } else {
      frontMaterial = M(0x9fb0bc, 0, 0.03, {
        transparent: true,
        opacity: 0.07,
        depthWrite: false,
        envMapIntensity: 0.9,
      });
    }
    box(g, t, Hc, W, frontMaterial, L / 2 - t / 2, Hc / 2, 0).userData.noPick = front === "glass";
    const glass = new THREE.Mesh(
      new THREE.PlaneGeometry(L - 1.6, Hc - 1.6),
      M(0x9fb0bc, 0, 0.02, {
        transparent: true,
        opacity: 0.05,
        depthWrite: false,
        envMapIntensity: 0.9,
      }),
    );
    glass.position.set(0, Hc / 2, W / 2);
    glass.userData.noPick = true;
    g.add(glass);
    const frame = M(0x0d0d0f, 0.2, 0.4);
    for (const [w, h, x, y] of [
      [L, 0.8, 0, Hc - 0.4],
      [L, 0.8, 0, 0.4],
      [0.8, Hc, -L / 2 + 0.4, Hc / 2],
      [0.8, Hc, L / 2 - 0.4, Hc / 2],
    ] as const) {
      box(g, w, h, 0.05, frame, x, y, W / 2 - 0.03).userData.noPick = true;
    }
    if (BAD("CASE")) {
      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(L, Hc, W)),
        new THREE.LineBasicMaterial({ color: RED }),
      );
      edges.position.set(0, Hc / 2, 0);
      edges.userData.noPick = true;
      g.add(edges);
    }
    const fanColor = styleColor(cs, "fan_color", 0x151618);
    const caseFans = {
      frame: fanColor,
      blade: fanColor === 0xeeeff1 ? 0xe2e3e5 : 0x18191b,
      rgb: styleFlag(cs, "rgb"),
    };
    const kits = !A || H("rgb") ? kitFans : [];
    if (!kits.length) {
      kit.fan(g, 12, L / 2 - 1.6, Hc * 0.68, 0, "x", caseFans);
      if (Hc > 36) kit.fan(g, 12, L / 2 - 1.6, Hc * 0.68 - 12.5, 0, "x", caseFans);
      if (size !== "ITX") kit.fan(g, 12, -L / 2 + 1.6, Hc - 8.5, 1, "x", caseFans);
    } else {
      const slots: [number, number, number, "x" | "y"][] = [];
      for (let y = Hc - 7.6; y > 9 && slots.length < 3; y -= 12.4)
        slots.push([L / 2 - 1.6, y, 0, "x"]);
      if (size !== "ITX") slots.push([-L / 2 + 1.6, Hc - 8.5, 1, "x"]);
      if (str(r.cooler, "type") !== "AIO") {
        for (let x = -L / 2 + 11; x + 6 < L / 2 - 4 && slots.length < 12; x += 12.4)
          slots.push([x, Hc - 1.6, 2, "y"]);
      }
      const list = kits.flatMap((k) => Array<Part>(Math.max(1, num(k, "fan_count"))).fill(k));
      const placed: THREE.Object3D[] = [];
      list.slice(0, slots.length).forEach((k, i) => {
        const [x, y, z, ax] = slots[i]!;
        placed.push(
          kit.fan(g, 12, x, y, z, ax, {
            frame: 0x121315,
            kit: true,
            infinity: flag(k, "infinity"),
            lcd: flag(k, "lcd"),
          }),
        );
      });
      if (fresh === "rgb") for (const o of placed) off(o, 0, 0, 12);
    }
    const accent = style(cs).accent;
    if (typeof accent === "string") {
      const ac = parseInt(accent.slice(1), 16);
      box(
        g,
        L * 0.8,
        0.3,
        0.3,
        M(ac, 0.2, 0.4, { emissive: ac, emissiveIntensity: on ? 0.8 : 0 }),
        0,
        Hc - 1,
        W / 2 - 0.4,
      );
    }
    const interior = new THREE.PointLight(0xf4f1ea, (on ? 0.9 : 0.55) * Math.PI, L * 1.6, 0);
    interior.position.set(L * 0.1, Hc * 0.75, W / 2 - 3);
    g.add(interior);
    if (fresh === "case") off(g, 0, 14, 0);
  } else kit.ghost(root, L, Hc, W, 0, Hc / 2, 0);

  /* ---- motherboard ---- */
  const mb = r.board;
  const f = str(mb, "form_factor", "ATX");
  const [bw, bh] =
    f === "ITX"
      ? [17, 17]
      : f === "mATX"
        ? [24.4, 24.4]
        : f === "EATX"
          ? [27.7, 30.5]
          : [24.4, 30.5];
  const sx = f === "ITX" ? 7.5 : 10;
  const sy = bh - (f === "ITX" ? 6.5 : 8);
  const py = f === "ITX" ? 2.2 : sy - 10;
  const ry = sy - 1;
  const rx = sx + 5.2;
  const mP = V(-L / 2 + 3, Hc - 2.5 - bh, -W / 2 + 1.2);
  const mQ = new THREE.Quaternion();
  const bP = V(-bw / 2, 0.3, W / 2 + 8 + bh);
  const bQ = new THREE.Quaternion().setFromAxisAngle(V(1, 0, 0), -Math.PI / 2);
  const bench = A && !!mb && !H("board");
  const focus = {
    x: bench ? -2 : 0,
    y: Hc * 0.42,
    z: bench ? W / 2 : 0,
    distance: Math.max(L, Hc) * 2.25 + (bench ? 32 : 0),
  };
  const cableColor = caseColor === 0xe7e8ea ? 0xe6e7e9 : 0x17181a;
  if (!mb) kit.ghost(root, bw, bh, 0.2, mP.x + bw / 2, mP.y + bh / 2, mP.z);
  else {
    const bg = grp(`Placa base · ${mb.name}`);
    if (bench) {
      bg.position.copy(bP);
      bg.quaternion.copy(bQ);
    } else {
      bg.position.copy(mP);
      if (fresh === "board") {
        if (A) animate(bg, bP, bQ, mP, mQ);
        else off(bg, 0, 0, 18);
      }
    }
    const PX = 512 / bw;
    const pcb = canvasTexture(`pcb${mb.name}`, 512, Math.round(bh * PX), (g, w, h) => {
      const rand = seeded(mb.name.length * 7919);
      g.fillStyle = "#14171a";
      g.fillRect(0, 0, w, h);
      g.strokeStyle = "rgba(70,80,90,.28)";
      g.lineWidth = 1;
      for (let i = 0; i < 260; i++) {
        const x0 = rand() * w;
        const y0 = rand() * h;
        g.beginPath();
        g.moveTo(x0, y0);
        const L1 = 20 + rand() * 80;
        if (rand() < 0.5) g.lineTo(x0 + L1, y0);
        else g.lineTo(x0, y0 + L1);
        g.lineTo(x0 + L1 * 0.7, y0 + L1 * 0.7);
        g.stroke();
      }
      g.fillStyle = "rgba(200,170,90,.5)";
      for (let i = 0; i < 200; i++) g.fillRect(rand() * w, rand() * h, 2, 2);
      const X = (v: number) => v * PX;
      const Y = (v: number) => h - v * PX;
      g.strokeStyle = "rgba(235,238,240,.55)";
      g.lineWidth = 1.5;
      g.fillStyle = "rgba(235,238,240,.7)";
      g.font = "600 11px Geist, Arial";
      g.strokeRect(X(sx - 3.2), Y(sy + 3.2), X(6.4), X(6.4));
      g.fillText("CPU", X(sx - 3.2), Y(sy + 3.6));
      g.fillText(`${str(mb, "ram_type")}_A2  B2`, X(rx - 0.3), Y(ry + 7.4));
      g.fillText("PCIE1", X(1), Y(py + 1));
      g.fillText("M2_1", X(sx - 4), Y(sy - 4));
      g.font = "700 15px Geist, Arial";
      g.fillStyle = "rgba(235,238,240,.5)";
      g.fillText(
        mb.name.replace(/^(ASRock|ASUS|MSI|Aorus) /, "").toUpperCase(),
        X(bw * 0.42),
        Y(2.2),
      );
    });
    const plain = M(BAD("BOARD") ? RED : 0x1a1d20, 0.25, 0.6);
    const face = M(BAD("BOARD") ? RED : 0xffffff, 0.25, 0.55, BAD("BOARD") ? {} : { map: pcb });
    box(bg, bw, bh, 0.16, [plain, plain, plain, plain, face, plain], bw / 2, bh / 2, 0.08);
    const hsColor = styleColor(mb, "heatsink", 0x41464d);
    const hs = M(hsColor, 0.65, 0.32);
    const acc = M(styleColor(mb, "accent", 0x8a9098), 0.7, 0.3);
    const io = Math.min(15, bh - 2);
    box(bg, 2.6, io, 3.6, hs, 1.3, bh - 1 - io / 2, 2);
    box(bg, 0.2, io * 0.8, 0.4, acc, 2.65, bh - 1 - io / 2, 3.2);
    let yy = bh - 2.5;
    for (const [c, h] of [
      [0x1d5fd6, 1],
      [0x1d5fd6, 1],
      [0x111111, 1],
      [0xd11a2a, 1],
      [0x111111, 1.4],
    ] as const) {
      box(bg, 0.3, h, 1.3, M(c, 0.3, 0.5), -0.12, yy, 1.2);
      box(bg, 0.3, h, 1.3, M(c, 0.3, 0.5), -0.12, yy, 2.8);
      yy -= h + 0.6;
    }
    [0x6fb84a, 0xe9a03b, 0xe05a8a].forEach((c, i) =>
      cyl(bg, 0.35, 0.3, M(c, 0.3, 0.5), -0.12, bh - io + 1 + i * 0.9, 1.5, "x", 16),
    );
    box(bg, 1.7, 8.2, 1.7, hs, sx - 4.5, sy - 0.5, 1);
    box(bg, 8.4, 1.7, 1.7, hs, sx, sy + 4.3, 1);
    box(bg, 0.25, 8, 0.3, acc, sx - 3.6, sy - 0.5, 1.8);
    for (let i = 0; i < 4; i++)
      cyl(bg, 0.32, 0.9, M(0x26282b, 0.4, 0.4), sx - 2.8 + i * 0.9, sy - 3.6, 0.6, "z", 14);
    box(bg, 6.2, 6.2, 0.25, slv, sx, sy, 0.3);
    box(bg, 4.6, 4.6, 0.27, M(0x1c1e21, 0.4, 0.5), sx, sy, 0.32);
    if (/LGA/.test(str(mb, "socket"))) cyl(bg, 0.12, 5.2, slv, sx + 3.3, sy, 0.55, "y", 8);
    const slots = num(mb, "ram_slots", 4);
    for (let i = 0; i < slots; i++) {
      box(bg, 0.7, 13.6, 0.7, M(i % 2 ? 0x202226 : 0x3d4148, 0.2, 0.6), rx + i * 0.95, ry, 0.5);
      box(bg, 0.6, 0.6, 1, M(0xe8e9eb, 0.1, 0.6), rx + i * 0.95, ry + 7.1, 0.7);
    }
    box(bg, 1, 5.4, 1.4, M(0x1a1b1d, 0.1, 0.6), bw - 0.6, bh * 0.55, 0.8);
    box(bg, 2.2, 1, 1.3, M(0x1a1b1d, 0.1, 0.6), 1.8, bh - 1.1, 0.75);
    box(bg, 8.2, 2.3, 0.1, M(0x0e1113, 0.2, 0.8), sx, sy - 5.5, 0.21);
    box(bg, 9, 1, 1.1, slv, 5.5, py, 0.65);
    box(bg, 8.6, 0.4, 1.15, blk, 5.5, py, 0.66);
    if (f !== "ITX") {
      box(bg, 9, 1, 1, blk, 5.5, py - 4.1, 0.6);
      if (py - 8.2 > 1) box(bg, 3, 1, 1, blk, 2.5, py - 8.2, 0.6);
      const chip = mb.name.match(/[A-Z]\d{3}[A-Z]?/)?.[0] ?? "";
      const ct = labelTexture(`chip${mb.name}`, 128, 128, hexColor(hsColor), [
        [chip, 18, 64, 34, hsColor > 0xa00000 ? "#3a3e44" : "#c9ced4", "700"],
      ]);
      box(
        bg,
        5,
        5,
        0.9,
        [hs, hs, hs, hs, M(0xffffff, 0.6, 0.35, { map: ct }), hs],
        bw - 6.5,
        4.5,
        0.6,
      );
    }
    cyl(bg, 0.9, 0.25, slv, bw - 3, py - 2.5 > 1 ? py - 2.5 : 1.5, 0.3, "z");

    /* cpu */
    if (r.cpu && H("cpu")) {
      const c = r.cpu;
      const g = grp(`Procesador · ${c.name}`, bg);
      const amd = /AMD/.test(c.name);
      const ihs = labelTexture(`ihs${c.name}`, 256, 256, "#c7ccd2", [
        [amd ? "AMD" : "intel", 22, 48, 40, "#4a4f56", "700"],
        [amd ? "RYZEN" : "CORE", 22, 98, 30, "#4a4f56", "600"],
        [c.name.replace(/^(AMD Ryzen|Intel Core) /, ""), 22, 150, 26, "#5c6168", "500"],
      ]);
      box(g, 4, 4, 0.12, M(BAD("CPU") ? RED : 0x2f5d3a, 0.3, 0.5), sx, sy, 0.5);
      box(
        g,
        3.5,
        3.5,
        0.28,
        [slv, slv, slv, slv, M(BAD("CPU") ? RED : 0xffffff, 0.85, 0.28, { map: ihs }), slv],
        sx,
        sy,
        0.7,
      );
      if (fresh === "cpu") off(g, 0, 0, 8);
    }
    if (A && H("paste") && !H("cool")) {
      const g = grp("Pasta térmica", bg);
      const drop = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 12), M(0xb9bec4, 0.4, 0.7));
      drop.scale.set(1.2, 1.2, 0.18);
      drop.position.set(sx, sy, 0.86);
      g.add(drop);
      if (fresh === "paste") off(g, 0, 0, 4);
    }

    /* ram */
    if (r.ram && H("ram")) {
      const ram = r.ram;
      const color = styleColor(ram, "color", 0x1d1f23);
      const g = grp(`Memoria · ${ram.name}`, bg);
      const count = Math.min(input.ramModules, slots);
      const idx = count === 2 && slots === 4 ? [1, 3] : [0, 1, 2, 3].slice(0, count);
      const sp = M(BAD("RAM") ? RED : color, 0.55, 0.38);
      const lt = labelTexture(`ram${ram.name}`, 256, 64, hexColor(color), [
        [
          styleText(ram, "label", "DDR"),
          14,
          32,
          26,
          color > 0xa00000 ? "#4a4f56" : "#d0d4d9",
          "700",
        ],
        [str(ram, "ram_type"), 180, 32, 18, color > 0xa00000 ? "#6c7178" : "#8a9098", "600"],
      ]);
      const side = M(BAD("RAM") ? RED : 0xffffff, 0.55, 0.38, BAD("RAM") ? {} : { map: lt });
      for (const i of idx) {
        const x = rx + i * 0.95;
        box(g, 0.72, 13.3, 3.1, [side, side, sp, sp, sp, sp], x, ry, 2.4);
        box(g, 0.74, 13, 0.45, styleFlag(ram, "rgb") ? kit.rgbMaterial() : sp, x, ry, 4.15);
      }
      if (fresh === "ram") off(g, 0, 0, 8);
    }

    /* m.2 */
    const m2 = r.storage.filter((d) => str(d, "interface") === "M.2");
    if (m2.length && H("m2")) {
      const g = grp(`SSD M.2 · ${m2.map((d) => d.name).join(" + ")}`, bg);
      m2.slice(0, f === "ITX" ? 1 : 2).forEach((d, i) => {
        const y2 = i ? py + 2.2 : sy - 5.5;
        const brand = styleText(d, "label", "ADATA");
        const xpg = brand === "XPG";
        const lt = labelTexture(`m2${d.name}`, 256, 64, xpg ? "#1b1c1f" : "#2d3a4a", [
          [brand, 12, 32, 24, xpg ? "#e3262f" : "#e9eef3", "700"],
          [d.name.match(/\d+ (GB|TB)/)?.[0] ?? "", 150, 32, 20, "#c9ced4", "600"],
        ]);
        box(g, 8, 2.2, 0.12, M(0x1b4d2e, 0.3, 0.5), sx, y2, 0.3);
        box(g, 6.2, 2, 0.06, M(0xffffff, 0.2, 0.5, { map: lt }), sx + 0.6, y2, 0.4);
      });
      if (fresh === "m2") off(g, 0, 0, 8);
    }

    /* cooler */
    if (r.cooler && H("cool")) {
      const c = r.cooler;
      const g = grp(`Refrigeración · ${c.name}`, bg);
      const bad = BAD("COOLER");
      const finM = M(
        bad ? RED : styleColor(c, "fin", 0xc9ced4),
        styleNum(c, "fin_metal", 0.9),
        0.3,
      );
      const pipeM = M(styleColor(c, "pipe", 0xb87333), 0.95, 0.22);
      const frame = styleColor(c, "frame", 0x16171a);
      const blade = styleColor(c, "blade", 0x1c1d20);
      const height = num(c, "height_mm");
      if (str(c, "type") === "AIR" && height <= 70) {
        box(g, 9.5, 9.5, 0.6, M(0x1d1e20, 0.6, 0.4), sx, sy, 1);
        const n = 8;
        const fins = new THREE.InstancedMesh(new THREE.BoxGeometry(9.5, 0.08, 1.3), finM, n);
        const o = new THREE.Object3D();
        for (let i = 0; i < n; i++) {
          o.position.set(sx, sy - 4.5 + (i * 9) / (n - 1), 1.95);
          o.updateMatrix();
          fins.setMatrixAt(i, o.matrix);
        }
        fins.castShadow = true;
        g.add(fins);
        kit.fan(g, 9.2, sx, sy, 3.3, "z", { frame, blade });
      } else if (str(c, "type") === "AIR") {
        box(g, 4, 4, 1.6, M(0xc8ccd1, 0.95, 0.2), sx, sy, 1.6);
        const top = height / 10;
        const h0 = 2.8;
        const sh = top - h0;
        const two = flag(c, "dual_tower");
        const sw = two ? 3.6 : 5;
        const xs = two ? [sx - 3.3, sx + 2.6] : [sx - 0.3];
        const n = Math.max(1, Math.floor(sh / 0.2));
        const finGeometry = new THREE.BoxGeometry(sw, 12.5, 0.06);
        for (const x of xs) {
          const fins = new THREE.InstancedMesh(finGeometry, finM, n);
          const o = new THREE.Object3D();
          for (let i = 0; i < n; i++) {
            o.position.set(x, sy, h0 + 0.1 + i * 0.2);
            o.updateMatrix();
            fins.setMatrixAt(i, o.matrix);
          }
          fins.castShadow = fins.receiveShadow = true;
          g.add(fins);
          if (/chromax|Noctua/i.test(c.name))
            box(
              g,
              sw + 0.05,
              12.55,
              0.25,
              M(styleColor(c, "fin", 0xc9ced4), 0.7, 0.35),
              x,
              sy,
              top,
            );
          for (let i = 0; i < 3; i++)
            for (const sd of [-1, 1]) {
              const px = x - sw / 2 + 1 + (i * (sw - 2)) / 2;
              const py2 = sy + sd * (3 + i * 0.6);
              kit.tube(
                g,
                [
                  V(sx + (i - 1) * 1.1, sy, 2.2),
                  V(px, sy + sd * 1.5, 2.6),
                  V(px, py2, h0),
                  V(px, py2, top + 0.35),
                ],
                0.3,
                pipeM,
              );
            }
        }
        const fx = two ? sx - 0.35 : sx + 3.45;
        kit.fan(g, 12, fx + (two ? 0 : 0.3), sy, h0 + sh / 2, "x", {
          frame,
          blade,
          rgb: styleFlag(c, "rgb"),
        });
        if (two && /D15/.test(c.name) && !/D15S/.test(c.name))
          kit.fan(g, 12, sx + 5.2, sy, h0 + sh / 2, "x", { frame, blade });
      } else {
        const pump = grp(`Bomba · ${c.name}`, g);
        const body = styleColor(c, "body", 0x18191c);
        cyl(pump, 3.2, 2.2, M(bad ? RED : body, 0.4, 0.4), sx, sy, 1.9);
        if (styleFlag(c, "lcd")) {
          const lcd = canvasTexture(`lcd${c.name}`, 256, 256, (gg, w, h) => {
            const gr = gg.createRadialGradient(w / 2, h / 2, 10, w / 2, h / 2, w / 2);
            gr.addColorStop(0, "#1d3f6e");
            gr.addColorStop(1, "#05070c");
            gg.fillStyle = gr;
            gg.fillRect(0, 0, w, h);
            gg.strokeStyle = "#38c6ff";
            gg.lineWidth = 10;
            gg.beginPath();
            gg.arc(w / 2, h / 2, 96, Math.PI * 0.75, Math.PI * 1.9);
            gg.stroke();
            gg.fillStyle = "#eaf6ff";
            gg.font = "700 64px Geist, Arial";
            gg.textAlign = "center";
            gg.textBaseline = "middle";
            gg.fillText("38°", w / 2, h / 2);
            gg.font = "500 22px Geist, Arial";
            gg.fillText("CPU", w / 2, h / 2 + 52);
          });
          const screen = cyl(
            pump,
            2.7,
            0.06,
            M(0x050608, 0.2, 0.2, {
              emissive: 0xffffff,
              emissiveMap: lcd,
              emissiveIntensity: on ? 1 : 0,
            }),
            sx,
            sy,
            3.03,
          );
          screen.rotation.set(Math.PI / 2, 0, 0);
        } else if (styleFlag(c, "rgb")) {
          const ring = new THREE.Mesh(new THREE.TorusGeometry(2.6, 0.18, 8, 40), kit.rgbMaterial());
          ring.position.set(sx, sy, 3.05);
          pump.add(ring);
        }
        const radiator = num(c, "radiator_mm", 240);
        const rl = radiator / 10 + 2;
        const rg = grp(`Radiador · ${c.name}`);
        const yr = Hc - 0.4 - 1.6;
        const rt = canvasTexture(
          "rad",
          128,
          32,
          (gg, w, h) => {
            gg.fillStyle = "#202226";
            gg.fillRect(0, 0, w, h);
            gg.fillStyle = "#3a3e44";
            for (let i = 0; i < w; i += 3) gg.fillRect(i, 0, 1, h);
          },
          true,
        ).clone();
        rt.needsUpdate = true;
        rt.repeat.set(rl / 3, 1);
        const rm = M(bad ? RED : 0xffffff, 0.6, 0.45, bad ? {} : { map: rt });
        const tank = M(body, 0.4, 0.45);
        box(rg, rl - 3, 2.8, 12, rm, 0, yr, 2);
        box(rg, 1.5, 3, 12.2, tank, -rl / 2 + 0.75, yr, 2);
        box(rg, 1.5, 3, 12.2, tank, rl / 2 - 0.75, yr, 2);
        if (flag(c, "includes_fans") || c.specs.includes_fans === undefined) {
          for (let i = 0; i < radiator / 120; i++) {
            kit.fan(rg, 12, -rl / 2 + 7.5 + i * 12, yr - 2.8, 2, "y", {
              frame: frame === 0xd7c3a2 ? 0x16171a : frame,
              blade,
              rgb: styleFlag(c, "rgb"),
            });
          }
        }
        const pw = V(mP.x + sx, mP.y + sy, mP.z + 3);
        const tubeM = M(0x141416, 0.05, 0.85);
        for (const k of [-0.9, 0.9]) {
          kit.tube(
            rg,
            [
              V(pw.x + k, pw.y + 2.6, pw.z),
              V(pw.x + k, pw.y + 5, pw.z + 5),
              V(-rl / 2 - 1, yr - 3, 3 + k * 3),
              V(-rl / 2 + 0.6, yr, 3 + k * 3),
            ],
            0.55,
            tubeM,
          );
        }
        if (fresh === "cool") off(rg, 0, 10, 0);
      }
      if (fresh === "cool") off(g, 0, 0, 10);
    }

    /* gpu */
    if (r.gpu && H("gpu")) {
      const gp = r.gpu;
      const watts = num(gp, "tdp_w");
      const len = num(gp, "length_mm", 250) / 10;
      const th = watts > 400 ? 6 : watts > 280 ? 5.4 : watts > 100 ? 4.2 : 1.8;
      const ht = watts > 400 ? 13.5 : watts > 100 ? 12 : 7;
      const g = grp(`Tarjeta gráfica · ${gp.name}`, bg);
      const bad = BAD("GPU");
      const shroud = styleColor(gp, "shroud", 0x1b1d20);
      const sh = M(bad ? RED : shroud, 0.55, 0.38);
      const edge = labelTexture(`gpu${gp.name}`, 512, 64, hexColor(shroud), [
        [
          styleText(gp, "brand", "GEFORCE"),
          len > 25 ? 150 : 60,
          32,
          30,
          shroud > 0xa00000 ? "#3b3f46" : "#d7dbe0",
          "700",
        ],
      ]);
      const topFace = M(bad ? RED : 0xffffff, 0.55, 0.38, bad ? {} : { map: edge });
      const under = M(0x111214, 0.3, 0.6);
      box(g, 0.15, th + 0.6, ht, slv, -2.6, py - th / 2, 1.2 + ht / 2);
      for (let i = 0; i < 3; i++) box(g, 0.2, 0.9, 1.6, blk, -2.7, py - th / 2, 2.5 + i * 2.4);
      box(
        g,
        len,
        th,
        ht,
        [sh, sh, sh, under, topFace, sh],
        len / 2 - 2.5,
        py - th / 2,
        1.2 + ht / 2,
      );
      box(
        g,
        len * 0.94,
        0.25,
        ht * 0.94,
        M(shroud > 0xa00000 ? 0xd9dce0 : 0x2b2e33, 0.8, 0.3),
        len / 2 - 2.5,
        py + 0.15,
        1.2 + ht / 2,
      );
      box(
        g,
        len * 0.3,
        0.05,
        ht * 0.4,
        M(0x0e0f11, 0.3, 0.5),
        len * 0.6 - 2.5,
        py + 0.3,
        1.2 + ht * 0.55,
      );
      box(
        g,
        len * 0.7,
        0.3,
        0.12,
        styleFlag(gp, "rgb") ? kit.rgbMaterial() : M(styleColor(gp, "accent", 0x5d636b), 0.7, 0.3),
        len * 0.5 - 2.5,
        py - th * 0.88,
        1.25 + ht,
      );
      if (watts > 100) box(g, 1.8, 0.9, 0.8, blk, len * 0.8 - 2.5, py - th / 2, 1.6 + ht);
      const fans = styleNum(gp, "fans", watts > 100 ? 2 : 0);
      if (fans) {
        for (let i = 0; i < fans; i++) {
          kit.fan(g, ht * 0.74, -2.5 + (len * (i + 0.5)) / fans, py - th - 0.1, 1.2 + ht / 2, "y", {
            noFrame: true,
            blade: styleColor(gp, "blade", 0x18191b),
            blades: 9,
          });
        }
      } else {
        const fins = new THREE.InstancedMesh(
          new THREE.BoxGeometry(0.06, th * 0.8, ht * 0.8),
          M(0x2b2e33, 0.8, 0.3),
          24,
        );
        const o = new THREE.Object3D();
        for (let i = 0; i < 24; i++) {
          o.position.set(len * 0.2 + i * len * 0.025 - 2.5, py - th * 0.6, 1.2 + ht / 2);
          o.updateMatrix();
          fins.setMatrixAt(i, o.matrix);
        }
        g.add(fins);
      }
      if (fresh === "gpu") off(g, 0, 0, 20);
    }
  }

  /* gpu support */
  if (r.gpu && mb && H("gpu") && (!A || H("rgb")) && kinds.includes("GPU_SUPPORT")) {
    const watts = num(r.gpu, "tdp_w");
    const th = watts > 400 ? 6 : watts > 280 ? 5.4 : 4.2;
    const ht = watts > 400 ? 13.5 : 12;
    const yb = mP.y + py - th;
    const xs = mP.x + num(r.gpu, "length_mm", 250) / 10 - 6;
    const g = grp("Soporte ARGB para GPU");
    const z = mP.z + 1.2 + ht * 0.5;
    box(g, 1.4, yb - 0.4, 1.4, M(0x1a1b1e, 0.6, 0.35), xs, (yb + 0.4) / 2, z);
    box(g, 4, 0.4, 3, M(0x1a1b1e, 0.6, 0.35), xs, 0.6, z);
    box(g, 0.15, yb - 1.4, 0.5, kit.rgbMaterial(), xs, (yb + 0.4) / 2, z + 0.72);
  }

  /* ---- psu ---- */
  const sfx = str(r.psu, "form_factor") === "SFX";
  const [pl, ph, pd] = sfx ? [12.5, 6.4, 10] : [15, 8.6, 14];
  const px = -L / 2 + 1 + pl / 2;
  const pyy = 0.4 + ph / 2;
  if (r.psu && H("psu")) {
    const ps = r.psu;
    const g = grp(`Fuente · ${ps.name}`);
    const bad = BAD("PSU");
    const efficiency = styleText(ps, "efficiency", "BRONZE");
    const labelColor =
      { BRONZE: "#b0754a", GOLD: "#d4a32c", PLATINUM: "#c9ced6", TITANIUM: "#8fa3b5" }[
        efficiency
      ] ?? "#b0754a";
    const label = labelTexture(`psu${ps.name}`, 256, 96, "#17181b", [
      [`${num(ps, "watts")} W`, 16, 36, 34, "#eef0f2", "700"],
      [`80 PLUS ${efficiency}`, 16, 74, 18, labelColor, "700"],
    ]);
    const grill = canvasTexture(
      "grill",
      128,
      128,
      (gg, w, h) => {
        gg.fillStyle = "#1c1d20";
        gg.fillRect(0, 0, w, h);
        gg.fillStyle = "#050506";
        for (let y = 0; y < h; y += 9)
          for (let x = ((y / 9) % 2) * 5; x < w; x += 10) {
            gg.beginPath();
            for (let k = 0; k < 6; k++) {
              const a = (k / 6) * Math.PI * 2;
              gg.lineTo(x + Math.cos(a) * 3.6, y + Math.sin(a) * 3.6);
            }
            gg.fill();
          }
      },
      true,
    );
    grill.repeat.set(3, 3);
    const pb = M(bad ? RED : 0x1b1c1f, 0.45, 0.55);
    box(
      g,
      pl,
      ph,
      pd,
      [
        pb,
        pb,
        M(bad ? RED : 0xffffff, 0.4, 0.55, bad ? {} : { map: grill }),
        pb,
        M(bad ? RED : 0xffffff, 0.3, 0.5, bad ? {} : { map: label }),
        pb,
      ],
      px,
      pyy,
      0,
    );
    for (let i = 0; i < 3; i++)
      for (let j = 0; j < 2; j++)
        box(
          g,
          0.1,
          1.4,
          1.8,
          M(0x0a0a0b, 0.1, 0.7),
          px + pl / 2 + 0.03,
          pyy + 2 - i * 1.9,
          -4 + j * 2.4,
        );
    if (fresh === "psu") off(g, 0, 0, 20);
  } else kit.ghost(root, pl, ph, pd, px, pyy, 0);

  /* ---- sata drives ---- */
  const sata = r.storage.filter((d) => str(d, "interface") === "SATA");
  let ys = 0.4;
  if (H("sata")) {
    for (const d of sata) {
      const g = grp(`Almacenamiento SATA · ${d.name}`);
      box(g, 10, 0.7, 7, M(0x22262b, 0.6, 0.4), L / 2 - 1.2 - 5, ys + 0.35, 0);
      ys += 1.1;
      if (fresh === "sata") off(g, 0, 0, 18);
    }
  }

  /* ---- cables ---- */
  if (mb && r.psu && (A ? H("cables") : true)) {
    const g = grp("Cables de alimentación");
    const cm = M(cableColor, 0.05, 0.75);
    const top = pyy + ph / 2;
    const w = (p: THREE.Vector3) => p.add(mP);
    const hasL = (k: string) => kinds.includes(k);
    const b24 = w(V(bw - 0.6, bh * 0.55, 0.8));
    const zt = -W / 2 + 0.75;
    for (let k = -1; k <= 1; k++) {
      kit.tube(
        g,
        [
          V(px + pl / 2 - 2, top, k * 0.9 - 2),
          V(b24.x + 2.6, top + 2, zt),
          V(b24.x + 2.6, b24.y + k * 1.6, zt),
          V(b24.x + 2.4, b24.y + k * 1.6, b24.z + 1.4),
          V(b24.x + 0.4, b24.y + k * 1.6, b24.z + 0.8),
        ],
        0.42,
        hasL("STRIMER_24") ? kit.rgbMaterial() : cm,
      );
    }
    const eps = w(V(1.8, bh - 1.1, 0.8));
    kit.tube(
      g,
      [
        V(px - pl / 2 + 2, top, -2),
        V(-L / 2 + 1.8, top + 4, -W / 2 + 3.5),
        V(-L / 2 + 1.8, Hc - 2, -W / 2 + 3.5),
        V(eps.x, eps.y + 0.5, eps.z + 1),
      ],
      0.45,
      hasL("STRIMER_8") ? kit.rgbMaterial() : cm,
    );
    if (r.gpu && num(r.gpu, "tdp_w") > 100) {
      const watts = num(r.gpu, "tdp_w");
      const ht = watts > 400 ? 13.5 : 12;
      const th = watts > 400 ? 6 : watts > 280 ? 5.4 : 4.2;
      const gc = w(V((num(r.gpu, "length_mm", 250) / 10) * 0.8 - 2.5, py - th / 2, 1.6 + ht));
      const strimer = hasL("STRIMER_16") && str(r.gpu, "power_connector") === "16PIN";
      kit.tube(
        g,
        [
          V(px + pl / 2 - 4, top, 2),
          V(gc.x, mP.y + py - th - 2, W / 2 - 2.5),
          V(gc.x, gc.y, gc.z + 2),
          V(gc.x, gc.y, gc.z + 0.3),
        ],
        0.5,
        strimer ? kit.rgbMaterial() : cm,
      );
    }
    if (sata.length)
      kit.tube(
        g,
        [V(px + pl / 2, pyy, -3), V(px + pl / 2 + 4, pyy + 3, -4), V(L / 2 - 1.2 - 10, 0.75, -3)],
        0.3,
        cm,
      );
    if (fresh === "cables") off(g, 0, 0, 6);
  }

  return { size: { L, H: Hc, W }, focus };
}
