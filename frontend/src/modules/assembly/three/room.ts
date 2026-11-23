/** The setup room in 3D, ported from `buildRoom()` of the owner's simulator. */
import * as THREE from "three";

import { monitorSize, type Layout, type SetupParts } from "../setup";
import {
  Kit,
  canvasTexture,
  num,
  seeded,
  str,
  flag,
  styleColor,
  styleFlag,
  styleText,
  type Part,
} from "./kit";
import type { Animate } from "./pc";

export interface RoomInput {
  parts: SetupParts;
  layout: Layout;
  pc: { L: number; W: number };
  fresh: string | null;
  lightsOn: boolean;
}

export interface RoomResult {
  pc: { x: number; y: number; z: number };
  focus: { x: number; y: number; z: number; distance: number };
}

const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

export function buildRoom(
  room: THREE.Group,
  kit: Kit,
  input: RoomInput,
  animate: Animate,
): RoomResult {
  const { parts: s, layout: Lo, fresh } = input;
  const on = input.lightsOn;
  const M = kit.material.bind(kit);
  const box = kit.box.bind(kit);
  const grp = (label: string, parent: THREE.Object3D = room) => kit.group(label, parent);
  const cyl = (
    p: THREE.Object3D,
    r1: number,
    r2: number,
    h: number,
    m: THREE.Material,
    x: number,
    y: number,
    z: number,
    seg = 28,
  ) => {
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(r1, r2, h, seg), m);
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    p.add(mesh);
    return mesh;
  };
  const drop = (o: THREE.Object3D, key: string) => {
    if (fresh !== key) return;
    const to = o.position.clone();
    animate(o, to.clone().add(V(0, 25, 0)), o.quaternion.clone(), to, o.quaternion.clone());
  };

  /* room */
  const floorTx = canvasTexture(
    "floor",
    512,
    512,
    (g, w, h) => {
      const rand = seeded(11);
      for (let i = 0; i < 8; i++) {
        const y = (i * h) / 8;
        const base = [96, 70, 48].map((v) => v + ((rand() * 24 - 12) | 0));
        g.fillStyle = `rgb(${base.join(",")})`;
        g.fillRect(0, y, w, h / 8);
        for (let k = 0; k < 30; k++) {
          g.strokeStyle = `rgba(40,25,15,${rand() * 0.25})`;
          g.beginPath();
          const yy = y + (rand() * h) / 8;
          g.moveTo(0, yy);
          g.lineTo(w, yy + rand() * 4 - 2);
          g.stroke();
        }
        g.fillStyle = "rgba(0,0,0,.45)";
        g.fillRect(0, y, w, 2);
        g.fillRect(rand() * w, y, 2, h / 8);
      }
    },
    true,
  );
  floorTx.repeat.set(8, 7);
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(1000, 700),
    M(0xffffff, 0, 0.75, { map: floorTx }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.z = 60;
  floor.receiveShadow = true;
  floor.userData.noPick = true;
  room.add(floor);
  const wallTx = canvasTexture(
    "wall",
    256,
    256,
    (g, w, h) => {
      const rand = seeded(5);
      g.fillStyle = "#2b2f36";
      g.fillRect(0, 0, w, h);
      for (let i = 0; i < 4000; i++) {
        g.fillStyle = `rgba(255,255,255,${rand() * 0.025})`;
        g.fillRect(rand() * w, rand() * h, 2, 2);
      }
    },
    true,
  );
  wallTx.repeat.set(10, 3);
  const wall = new THREE.Mesh(
    new THREE.PlaneGeometry(1000, 300),
    M(0xffffff, 0, 0.95, { map: wallTx }),
  );
  wall.position.set(0, 150, -52);
  wall.receiveShadow = true;
  wall.userData.noPick = true;
  room.add(wall);
  box(room, 1000, 10, 2, M(0x1d2026, 0.1, 0.7), 0, 5, -51).userData.noPick = true;

  /* desk */
  const dk = s.desk;
  const dw = Lo.deskWidth;
  const dd = Lo.deskDepth;
  const top = 75;
  const wood = styleText(dk, "finish", "black") === "wood";
  const dg = grp(
    dk ? `Escritorio · ${dk.name}` : `Escritorio genérico de ${dw} cm (no incluido en el total)`,
  );
  const woodTx = () =>
    canvasTexture("dwood", 512, 256, (g, w, h) => {
      const rand = seeded(9);
      g.fillStyle = "#7a5235";
      g.fillRect(0, 0, w, h);
      for (let i = 0; i < 160; i++) {
        g.strokeStyle = `rgba(${(50 + rand() * 40) | 0},${(30 + rand() * 20) | 0},12,${0.2 + rand() * 0.3})`;
        g.lineWidth = 1 + rand() * 2.5;
        const y = rand() * h;
        g.beginPath();
        g.moveTo(0, y);
        g.bezierCurveTo(
          w * 0.3,
          y + rand() * 10 - 5,
          w * 0.7,
          y + rand() * 10 - 5,
          w,
          y + rand() * 8 - 4,
        );
        g.stroke();
      }
    });
  const carbonTx = (w: number, d: number) => {
    const t = canvasTexture(
      "dcarbon",
      128,
      128,
      (g, cw, ch) => {
        g.fillStyle = "#16171a";
        g.fillRect(0, 0, cw, ch);
        for (let y = 0; y < ch; y += 8)
          for (let x = 0; x < cw; x += 8) {
            g.fillStyle = ((x + y) / 8) % 2 ? "#1c1e22" : "#121316";
            g.fillRect(x, y, 8, 8);
          }
      },
      true,
    ).clone();
    t.needsUpdate = true;
    t.repeat.set(w / 14, d / 14);
    return t;
  };
  const topMaterial = (w: number, d: number) =>
    M(0xffffff, wood ? 0 : 0.2, wood ? 0.55 : 0.45, { map: wood ? woodTx() : carbonTx(w, d) });
  const frame = M(0x111215, 0.6, 0.4);
  box(dg, dw, 2.5, dd, topMaterial(dw, dd), 0, top - 1.25, 0);
  for (const sd of [-1, 1]) {
    box(dg, 5, top - 2.5, 5, frame, sd * (dw / 2 - 6), (top - 2.5) / 2, 0);
    box(dg, 6, 2, dd - 6, frame, sd * (dw / 2 - 6), 1, 0);
    box(dg, 4, 4, dd - 10, frame, sd * (dw / 2 - 6), top - 5, 0);
  }
  box(dg, dw - 12, 5, 3, frame, 0, top - 5, -dd / 2 + 6);
  if (styleFlag(dk, "rgb"))
    box(dg, dw - 4, 0.5, 0.5, kit.rgbMaterial(), 0, top - 2.6, dd / 2 - 0.3);
  if (Lo.isL) {
    const ww = Lo.wingWidth;
    const wl = Lo.wingLength;
    const wx = dw / 2 + ww / 2 - 0.01;
    box(dg, ww, 2.5, wl, topMaterial(ww, wl - dd), wx, top - 1.25, -dd / 2 + wl / 2);
    box(dg, 5, top - 2.5, 5, frame, wx + ww / 2 - 6, (top - 2.5) / 2, -dd / 2 + wl - 6);
    box(dg, 5, top - 2.5, 5, frame, wx - ww / 2 + 6, (top - 2.5) / 2, -dd / 2 + wl - 6);
    box(dg, ww - 12, 4, 4, frame, wx, top - 5, -dd / 2 + wl - 6);
    box(dg, 4, 4, wl - 12, frame, wx + ww / 2 - 6, top - 5, -dd / 2 + wl / 2);
    box(dg, 5, top - 2.5, 5, frame, wx + ww / 2 - 6, (top - 2.5) / 2, -dd / 2 + 6);
    if (styleFlag(dk, "rgb"))
      box(
        dg,
        0.5,
        0.5,
        wl - dd - 4,
        kit.rgbMaterial(),
        wx - ww / 2 + 0.3,
        top - 2.6,
        dd / 2 + (wl - dd) / 2,
      );
  }
  drop(dg, "desk");

  /* pc position */
  const pcx = Lo.pcOnWing
    ? dw / 2 + Lo.wingWidth / 2
    : Lo.pcOnDesk
      ? -dw / 2 + 4 + input.pc.W / 2
      : -dw / 2 - input.pc.W / 2 - 10;
  const pcz = Lo.pcOnWing
    ? -dd / 2 + Lo.wingLength - input.pc.L / 2 - 5
    : -dd / 2 + input.pc.L / 2 + 3;
  const pcPosition = { x: pcx, y: Lo.pcOnDesk || Lo.pcOnWing ? top : 0, z: pcz };

  /* monitors */
  const mons = s.monitor;
  const left = -dw / 2 + 4;
  const zs = Lo.pcOnDesk ? left + input.pc.W + 3 : left;
  const ze = dw / 2 - 4;
  const cx = (zs + (Lo.headsetMicBack ? ze - Lo.headsetMicWidth : ze)) / 2;
  const hmX = ze - Lo.headsetMicWidth;
  let mx = cx;
  const widths = mons.map((m) => monitorSize(m)[0] + 1.6);
  const total = widths.reduce((a, c) => a + c, 0) + (mons.length - 1);
  let xx = cx - total / 2;
  mons.forEach((m, i) => {
    const [w, h] = monitorSize(m);
    const uw = num(m, "ultrawide");
    const g = grp(`Monitor · ${m.name}`);
    const angle =
      mons.length === 1
        ? 0
        : mons.length === 2
          ? i
            ? -0.2
            : 0.2
          : i === 0
            ? 0.42
            : i === 2
              ? -0.42
              : 0;
    const xcen =
      mons.length === 3
        ? i === 1
          ? cx
          : cx + (i - 1) * (widths[1]! / 2 + widths[i]! * 0.45)
        : xx + widths[i]! / 2;
    xx += widths[i]! + 1;
    const yb = top + (uw === 2 ? 8 : 11);
    const zc = -dd / 2 + (mons.length === 3 && i !== 1 ? 18 : 14);
    const kind = flag(m, "pro") ? "pro" : i === 0 ? "game" : "desk";
    const screen = M(0x050507, 0.2, 0.12, {
      emissive: 0xffffff,
      emissiveMap: screenTexture(kind + (uw ? `u${uw}` : ""), w, h),
      emissiveIntensity: on ? (flag(m, "oled") ? 1.15 : 0.95) : 0,
    });
    const body = M(styleFlag(m, "white") ? 0xe9eaec : 0x16171a, 0.35, 0.4);
    if (flag(m, "curved")) {
      const inches = num(m, "inches", 27);
      const R = inches <= 27 ? 100 : inches < 40 ? 150 : 180;
      const arc = w / R;
      screen.side = THREE.DoubleSide;
      const sc = new THREE.Mesh(
        new THREE.CylinderGeometry(R, R, h, 64, 1, true, Math.PI - arc / 2, arc),
        screen,
      );
      sc.position.set(0, h / 2, R);
      g.add(sc);
      const back = new THREE.Mesh(
        new THREE.CylinderGeometry(
          R + 1.2,
          R + 1.2,
          h + 1.4,
          64,
          1,
          true,
          Math.PI - (arc + 0.02) / 2,
          arc + 0.02,
        ),
        M(0x0f1012, 0.3, 0.5, { side: THREE.DoubleSide }),
      );
      back.position.set(0, h / 2, R + 0.05);
      back.castShadow = true;
      g.add(back);
      box(g, w * 0.55, h * 0.6, 4, body, 0, h * 0.48, -2.8);
    } else {
      box(g, w + 1.4, h + 1.6, 1.4, M(0x0b0b0d, 0.3, 0.45), 0, h / 2, 0);
      const sc = new THREE.Mesh(new THREE.PlaneGeometry(w, h), screen);
      sc.position.set(0, h / 2 + 0.1, 0.72);
      g.add(sc);
      box(g, w * 0.6, h * 0.62, 3.2, body, 0, h * 0.5, -2.2);
    }
    box(g, 4.5, yb - top + h * 0.45, 2.4, body, 0, h * 0.45 - (yb - top) / 2, -4.6);
    box(g, uw === 2 ? 40 : 24, 1.2, uw === 2 ? 22 : 19, body, 0, -(yb - top) + 0.6, -4);
    if (on) {
      const glow = new THREE.PointLight(
        kind === "pro" ? 0xf2c8a0 : 0xb05cff,
        0.55 * Math.PI,
        90,
        0,
      );
      glow.position.set(0, h / 2, 18);
      g.add(glow);
    }
    g.position.set(xcen, yb, zc);
    g.rotation.y = angle;
    if (i === 0) mx = xcen;
    drop(g, "monitor");
  });
  const main = mons[0];
  const mh = main ? monitorSize(main)[1] : 30;
  const myb = top + (main && num(main, "ultrawide") === 2 ? 8 : 11);

  /* pad, keyboard, mouse */
  const pd = s.pad;
  const kb = s.keyboard;
  const ms = s.mouse;
  const kz = dd / 2 - 20;
  const kw = Lo.keyboardWidth;
  const kbSize = str(kb, "size");
  const kd = kb ? (kbSize === "PAD" ? 16 : kbSize === "100%" ? 14 : 12.5) : 0;
  const fS = zs + Lo.decksWidth;
  const fE = ze - (Lo.headsetMicBack ? 0 : Lo.headsetMicWidth);
  const kx = Math.max(fS + kw / 2 + 2, Math.min(mx - (ms ? 6 : 0), fE - kw / 2 - (ms ? 26 : 2)));
  if (pd) {
    const [pw, pdd] = (
      { M: [36, 28], L: [45, 40], XL: [90, 40], XXL: [110, 45] } as Record<string, [number, number]>
    )[str(pd, "size")] ?? [45, 40];
    const big = pw > 60;
    const g = grp(`Pad · ${pd.name}`);
    const art = styleFlag(pd, "art")
      ? canvasTexture("kimfa", 512, 256, (g2, w, h) => {
          const gr = g2.createLinearGradient(0, 0, w, h);
          gr.addColorStop(0, "#2b1b5a");
          gr.addColorStop(0.5, "#c2417a");
          gr.addColorStop(1, "#f3a65a");
          g2.fillStyle = gr;
          g2.fillRect(0, 0, w, h);
          const rand = seeded(2);
          for (let i = 0; i < 40; i++) {
            g2.fillStyle = `rgba(255,255,255,${rand() * 0.25})`;
            g2.beginPath();
            g2.arc(rand() * w, rand() * h, 4 + rand() * 30, 0, 7);
            g2.fill();
          }
        })
      : null;
    const padX = big ? kx + 6 : kx + kw / 2 + 14;
    box(
      g,
      pw,
      0.3,
      pdd,
      M(art ? 0xffffff : styleColor(pd, "color", 0x141518), 0, 0.92, art ? { map: art } : {}),
      padX,
      top + 0.15,
      kz + 2,
    );
    const edge = styleColor(pd, "edge", -1);
    if (edge >= 0) {
      for (const [a, bb, c, x, z] of [
        [pw, 0.4, 0.4, 0, pdd / 2],
        [pw, 0.4, 0.4, 0, -pdd / 2],
        [0.4, 0.4, pdd, pw / 2, 0],
        [0.4, 0.4, pdd, -pw / 2, 0],
      ] as const) {
        box(g, a, bb, c, M(edge, 0, 0.7), padX + x, top + 0.2, kz + 2 + z);
      }
    }
    drop(g, "pad");
  }
  const py = top + (pd ? 0.3 : 0);
  if (kb) {
    const g = grp(`Teclado · ${kb.name}`);
    const white = styleFlag(kb, "white");
    const accent = styleColor(kb, "accent", -1);
    const bh = flag(kb, "low_profile") ? 1.6 : 2.6;
    const rows = kbSize === "60%" || kbSize === "PAD" ? 5 : 6;
    const cols =
      kbSize === "60%"
        ? 15
        : kbSize === "75%"
          ? 16
          : kbSize === "TKL"
            ? 18
            : kbSize === "PAD"
              ? 6
              : 22;
    const keys = canvasTexture(`keys${kb.name}`, 512, Math.round((512 * kd) / kw), (g2, w, h) => {
      g2.clearRect(0, 0, w, h);
      const kwp = w / cols;
      const khp = h / rows;
      const keyColor = (r: number, c: number) =>
        white ? "#f1f2f4" : accent >= 0 && (r + c) % 5 === 0 ? "#f2c230" : "#1d1f23";
      for (let r = 0; r < rows; r++)
        for (let c = 0; c < cols; c++) {
          if (kbSize === "100%" && (c === 15 || (c === 19 && r === 0))) continue;
          if (r === rows - 1 && c > 3 && c < 10 && kbSize !== "PAD") {
            if (c === 4) {
              g2.fillStyle = white ? "#f1f2f4" : accent >= 0 ? "#f2c230" : "#1d1f23";
              g2.fillRect(c * kwp + 2, r * khp + 2, kwp * 6 - 4, khp - 4);
            }
            continue;
          }
          g2.fillStyle = keyColor(r, c);
          g2.fillRect(c * kwp + 2, r * khp + 2, kwp - 4, khp - 4);
          g2.fillStyle = white ? "rgba(0,0,0,.35)" : "rgba(255,255,255,.45)";
          g2.fillRect(c * kwp + kwp * 0.3, r * khp + khp * 0.35, kwp * 0.25, 2);
        }
    });
    const body = M(white ? 0xe4e5e7 : 0x141518, 0.4, 0.4);
    box(g, kw, bh, kd, body, kx, py + bh / 2, kz);
    const caps = new THREE.Mesh(new THREE.BoxGeometry(kw - 1, 1, kd - 1), [
      body,
      body,
      M(0xffffff, 0.1, 0.55, { map: keys, transparent: true, alphaTest: 0.5 }),
      body,
      body,
      body,
    ]);
    caps.position.set(kx, py + bh + 0.5, kz);
    caps.castShadow = true;
    g.add(caps);
    const glowMat = kit.rgbMaterial(0.9, false);
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(kw - 1.4, kd - 1.4), glowMat);
    glow.rotation.x = -Math.PI / 2;
    glow.position.set(kx, py + bh + 0.08, kz);
    g.add(glow);
    drop(g, "keyboard");
  }
  if (ms) {
    const g = grp(`Mouse · ${ms.name}`);
    const mxp = kb ? kx + kw / 2 + 11 : mx + 12;
    const body = new THREE.Mesh(
      new THREE.SphereGeometry(1, 28, 18),
      M(styleColor(ms, "color", 0x151618), 0.2, 0.35),
    );
    body.scale.set(3.2, 1.9, 6);
    body.position.set(mxp, py + 0.2, kz);
    body.castShadow = true;
    g.add(body);
    cyl(g, 0.45, 0.45, 0.8, M(0x0c0c0d, 0.2, 0.5), mxp, py + 1.9, kz - 2.4, 14).rotation.z =
      Math.PI / 2;
    const logo = new THREE.Mesh(new THREE.CircleGeometry(0.9, 20), kit.rgbMaterial(1, false));
    logo.rotation.x = -Math.PI / 2 + 0.5;
    logo.position.set(mxp, py + 1.75, kz + 2.4);
    g.add(logo);
    drop(g, "mouse");
  }

  /* headset */
  const hs = s.headset;
  if (hs) {
    const g = grp(`Audífonos · ${hs.name}`);
    const c = styleColor(hs, "color", 0x151618);
    const hx = hmX + Lo.headsetWidth / 2;
    const hz = Lo.headsetMicBack ? -dd / 2 + 22 : dd / 2 - 24;
    if (flag(hs, "earbuds")) {
      const caseMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 16), M(c, 0.2, 0.3));
      caseMesh.scale.set(3.4, 1.6, 2.4);
      caseMesh.position.set(hx, top + 1.5, hz);
      caseMesh.castShadow = true;
      g.add(caseMesh);
    } else {
      const stand = M(0x1b1c1f, 0.6, 0.35);
      cyl(g, 5, 5.4, 1, stand, hx, top + 0.5, hz);
      cyl(g, 0.7, 0.7, 24, stand, hx, top + 12.5, hz, 16);
      const band = new THREE.Mesh(
        new THREE.TorusGeometry(8.2, 0.9, 10, 36, Math.PI),
        M(c, 0.25, 0.4),
      );
      band.position.set(hx, top + 18, hz);
      band.castShadow = true;
      g.add(band);
      for (const sd of [-1, 1]) {
        cyl(g, 4.2, 4.2, 3.2, M(c, 0.25, 0.4), hx + sd * 8.2, top + 16.5, hz).rotation.z =
          Math.PI / 2;
        cyl(g, 3.9, 3.9, 1.4, M(0x0d0d0e, 0, 0.9), hx + sd * 6.2, top + 16.5, hz).rotation.z =
          Math.PI / 2;
        if (flag(hs, "rgb")) {
          const ring = new THREE.Mesh(new THREE.TorusGeometry(3.3, 0.25, 8, 32), kit.rgbMaterial());
          ring.rotation.y = Math.PI / 2;
          ring.position.set(hx + sd * 9.85, top + 16.5, hz);
          g.add(ring);
        }
      }
    }
    drop(g, "headset");
  }

  /* microphone */
  const mic = s.mic.find((x) => !flag(x, "arm"));
  const arm = s.mic.find((x) => flag(x, "arm"));
  if (mic || arm) {
    const g = grp(`Micrófono · ${s.mic.map((x) => x.name).join(" + ")}`);
    const am = M(0x141518, 0.5, 0.35);
    let mp = V(
      hmX + Lo.headsetWidth + (Lo.headsetWidth ? 3 : 0) + 7,
      top + 14,
      Lo.headsetMicBack ? -dd / 2 + 22 : dd / 2 - 24,
    );
    if (arm) {
      const base = V(dw / 2 - 8, top, -dd / 2 + 8);
      const j1 = V(dw / 2 - 8, top + 22, -dd / 2 + 10);
      const j2 = V(dw / 2 - 14, top + 36, -dd / 2 + 24);
      const j3 = V(dw / 2 - 24, top + 26, kz - 6);
      box(g, 5, 6, 8, am, base.x, top - 1, base.z);
      for (const [a, c] of [
        [base, j1],
        [j1, j2],
        [j2, j3],
      ] as const) {
        const segment = cyl(
          g,
          0.7,
          0.7,
          a.distanceTo(c),
          am,
          (a.x + c.x) / 2,
          (a.y + c.y) / 2,
          (a.z + c.z) / 2,
          14,
        );
        segment.lookAt(c);
        segment.rotateX(Math.PI / 2);
      }
      mp = V(j3.x, j3.y - 4, j3.z);
    }
    if (mic) {
      const c = styleFlag(mic, "white") ? 0xeceef0 : 0x18191c;
      const mesh = canvasTexture(
        "grille",
        64,
        64,
        (g2, w, h) => {
          g2.fillStyle = "#2a2d32";
          g2.fillRect(0, 0, w, h);
          g2.fillStyle = "#0c0d0f";
          for (let y = 0; y < h; y += 4)
            for (let x = ((y / 4) % 2) * 2; x < w; x += 4) g2.fillRect(x, y, 2, 2);
        },
        true,
      );
      mesh.repeat.set(4, 4);
      if (!arm) {
        cyl(g, 4, 4.5, 1, M(c, 0.4, 0.4), mp.x, top + 0.5, mp.z);
        cyl(g, 0.6, 0.6, 8, M(c, 0.4, 0.4), mp.x, top + 5, mp.z, 12);
        mp.y = top + 14;
      }
      cyl(g, 2.8, 2.8, 10, M(0xffffff, 0.5, 0.45, { map: mesh }), mp.x, mp.y, mp.z);
      cyl(g, 2.9, 2.9, 2.4, M(c, 0.4, 0.4), mp.x, mp.y - 5.5, mp.z);
      if (flag(mic, "rgb")) {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(2.95, 0.25, 8, 32), kit.rgbMaterial());
        ring.rotation.x = Math.PI / 2;
        ring.position.set(mp.x, mp.y - 6.8, mp.z);
        g.add(ring);
      }
    }
    drop(g, "mic");
  }

  /* speakers */
  const sp = s.speaker;
  if (sp) {
    const g = grp(`Parlantes · ${sp.name}`);
    const mw = main ? monitorSize(main)[0] : 50;
    const kind = str(sp, "kind");
    if (kind === "BAR") {
      const grille = canvasTexture(
        "sgr",
        64,
        16,
        (g2, w, h) => {
          g2.fillStyle = "#1b1c1f";
          g2.fillRect(0, 0, w, h);
          g2.fillStyle = "#08090a";
          for (let x = 1; x < w; x += 3) for (let y = 1; y < h; y += 3) g2.fillRect(x, y, 1.5, 1.5);
        },
        true,
      );
      grille.repeat.set(10, 2);
      const dark = M(0x1b1c1f);
      box(
        g,
        Math.min(55, mw * 0.8),
        6,
        7,
        [dark, dark, dark, dark, M(0xffffff, 0.2, 0.7, { map: grille }), dark],
        mx,
        top + 3,
        -dd / 2 + 28,
      );
      if (flag(sp, "rgb"))
        box(
          g,
          Math.min(55, mw * 0.8) - 2,
          0.4,
          0.4,
          kit.rgbMaterial(),
          mx,
          top + 0.4,
          -dd / 2 + 31.6,
        );
    } else {
      for (const sd of [-1, 1]) {
        const x = cx + sd * (Lo.monitorsWidth / 2 + 9);
        const z = -dd / 2 + 16;
        if (kind === "PAIR") {
          cyl(g, 6.5, 7, 1.4, M(0x141518, 0.4, 0.4), x, top + 0.7, z);
          cyl(g, 1, 1, 10, M(0x141518, 0.4, 0.4), x, top + 6, z, 12);
          cyl(g, 6, 6, 8, M(0x18191c, 0.35, 0.35), x, top + 16, z).rotation.x = Math.PI / 2 - 0.2;
          const ring = new THREE.Mesh(new THREE.TorusGeometry(6.6, 0.3, 8, 32), kit.rgbMaterial());
          ring.rotation.x = -Math.PI / 2;
          ring.position.set(x, top + 1.5, z);
          g.add(ring);
        } else {
          const ico = new THREE.Mesh(
            new THREE.IcosahedronGeometry(7, 0),
            M(0x5d636b, 0.85, 0.3, { flatShading: true }),
          );
          ico.scale.set(1, 1.4, 1);
          ico.position.set(x, top + 10, z);
          ico.castShadow = true;
          g.add(ico);
          const eye = new THREE.Mesh(
            new THREE.CircleGeometry(2.4, 24),
            M(0x111111, 0.2, 0.3, { emissive: 0xff7a1a, emissiveIntensity: on ? 1.4 : 0 }),
          );
          eye.position.set(x, top + 11, z + 6.7);
          g.add(eye);
          for (const l of [-1, 1])
            cyl(g, 0.5, 0.5, 8, M(0x3b3f45, 0.8, 0.3), x + l * 3, top + 3, z, 10);
        }
      }
    }
    drop(g, "speaker");
  }

  /* camera */
  if (s.camera && main) {
    const g = grp(`Cámara web · ${s.camera.name}`);
    box(g, 9, 3, 3.2, M(0x151618, 0.3, 0.4), mx, myb + mh + 2, -dd / 2 + 15);
    cyl(g, 1.1, 1.1, 0.4, M(0x0a0a0c, 0.9, 0.05), mx, myb + mh + 2, -dd / 2 + 16.7, 24).rotation.x =
      Math.PI / 2;
    box(g, 4, 0.6, 5, M(0x151618), mx, myb + mh + 0.3, -dd / 2 + 13);
    drop(g, "camera");
  }

  /* streaming */
  let sx2 = Math.max(zs, (kb ? kx - kw / 2 : cx - 20) - 4 - Lo.decksWidth);
  for (const t of s.stream) {
    const g = grp(`Streaming · ${t.name}`);
    if (str(t, "kind") === "DECK") {
      const c = num(t, "key_columns", 4);
      const rw = num(t, "key_rows", 2);
      const dials = flag(t, "dials");
      const dw2 = c * 2.4 + 2;
      const dh = rw * 2.4 + 2 + (dials ? 3 : 0);
      const keys = canvasTexture(`deck${t.name}`, 256, Math.round((256 * dh) / dw2), (g2, w, h) => {
        g2.fillStyle = "#08090b";
        g2.fillRect(0, 0, w, h);
        const colors = [
          "#ff3e8a",
          "#3ad1ff",
          "#7cff8a",
          "#ffb547",
          "#9146ff",
          "#ff5a5f",
          "#ffffff",
        ];
        const kw2 = w / (c + 0.8);
        for (let r = 0; r < rw; r++)
          for (let k = 0; k < c; k++) {
            g2.fillStyle = colors[(r * c + k) % colors.length]!;
            g2.fillRect(kw2 * 0.4 + k * kw2 + 4, kw2 * 0.4 + r * kw2 + 4, kw2 - 8, kw2 - 8);
          }
      });
      const dark = M(0x111214);
      const deck = box(
        g,
        dw2,
        1.6,
        dh,
        [
          dark,
          dark,
          M(0x050506, 0.2, 0.3, {
            emissive: 0xffffff,
            emissiveMap: keys,
            emissiveIntensity: on ? 0.9 : 0,
          }),
          dark,
          dark,
          dark,
        ],
        sx2 + dw2 / 2,
        top + 1.8,
        kz - 1,
      );
      deck.rotation.x = 0.35;
      if (dials)
        for (let k = 0; k < 4; k++)
          kit.cylinder(
            g,
            0.8,
            1,
            M(0x2a2c30, 0.7, 0.3),
            sx2 + 2 + (k * (dw2 - 4)) / 3,
            top + 2.2,
            kz - 1 + dh / 2 - 1.6,
            "y",
            16,
          );
      sx2 += dw2 + 4;
    } else {
      const bx = dw / 2 - 6;
      const bz = -dd / 2 + 4;
      const pole = M(0x141518, 0.6, 0.35);
      cyl(g, 0.8, 0.8, 70, pole, bx, top + 35, bz, 12);
      const panelLight = kit.rgbMaterial(0.6, false);
      panelLight.color.setHex(0xfff4e6);
      const panel = box(
        g,
        34,
        24,
        2.5,
        [pole, pole, pole, pole, panelLight, pole],
        bx - 16,
        top + 68,
        bz + 10,
      );
      panel.rotation.set(-0.35, -0.55, 0);
      if (on) {
        const spot = new THREE.SpotLight(0xfff1dd, 0.9 * Math.PI, 260, 0.7, 0.6, 0);
        spot.position.set(bx - 16, top + 68, bz + 12);
        spot.target.position.set(mx, top + 20, dd / 2 + 50);
        g.add(spot, spot.target);
      }
    }
    drop(g, "stream");
  }

  /* chair */
  const ch = s.chair;
  if (ch) {
    const g = grp(`Silla · ${ch.name}`);
    const c = M(styleColor(ch, "color", 0x1a1b1e), 0.05, 0.7);
    const a = M(styleColor(ch, "accent", 0xff7a00), 0.05, 0.6);
    const metal = M(0x1a1b1e, 0.7, 0.35);
    for (let k = 0; k < 5; k++) {
      const ang = (k / 5) * Math.PI * 2;
      const leg = box(g, 30, 2.2, 4, metal, Math.cos(ang) * 14, 4, Math.sin(ang) * 14);
      leg.rotation.y = -ang;
      const caster = new THREE.Mesh(new THREE.SphereGeometry(2.4, 12, 8), M(0x0c0c0d, 0.2, 0.6));
      caster.position.set(Math.cos(ang) * 28, 2.4, Math.sin(ang) * 28);
      g.add(caster);
    }
    cyl(g, 2.2, 2.6, 26, metal, 0, 17, 0, 16);
    box(g, 52, 9, 50, c, 0, 34, 0);
    box(g, 48, 1.2, 44, a, 0, 38.8, 0);
    const back = new THREE.Group();
    back.position.set(0, 36, -22);
    back.rotation.x = -0.18;
    g.add(back);
    box(back, 50, 78, 10, c, 0, 40, 0);
    for (const sd of [-1, 1]) {
      box(back, 7, 58, 13, c, sd * 26, 32, 2);
      box(back, 2, 70, 0.6, a, sd * 16, 40, 5.2);
    }
    box(back, 30, 12, 8, a, 0, 70, 6);
    box(back, 22, 10, 6, c, 0, 20, 6);
    for (const sd of [-1, 1]) {
      box(g, 4, 16, 4, metal, sd * 27, 46, -2);
      box(g, 7, 2.4, 24, M(0x141518, 0.1, 0.7), sd * 27, 55, -2);
    }
    if (Lo.isL) {
      g.position.set(cx + 12, 0, dd / 2 + 46);
      g.rotation.y = Math.PI - 0.35;
    } else {
      g.position.set(cx + 28, 0, dd / 2 + 50);
      g.rotation.y = Math.PI + 0.55;
    }
    drop(g, "chair");
  }

  /* wall lights */
  s.light.forEach((lt) => {
    const g = grp(`Luces · ${lt.name}`);
    const m = kit.rgbMaterial();
    const zw = -51.5;
    const lines = str(lt, "kind") === "LINES";
    const ox = lines ? 45 : -80;
    const oy = top + 75;
    if (lines) {
      const R2 = 16;
      const pts: [number, number][] = [];
      for (let k = 0; k < 6; k++) {
        const a = (k / 6) * Math.PI * 2 + Math.PI / 6;
        pts.push([Math.cos(a) * R2, Math.sin(a) * R2]);
      }
      const hexes: [number, number][] = [
        [0, 0],
        [R2 * Math.sqrt(3), 0],
        [(R2 * Math.sqrt(3)) / 2, R2 * 1.5],
      ];
      const seen = new Set<string>();
      for (const [hx, hy] of hexes)
        pts.forEach((p, k) => {
          const q = pts[(k + 1) % 6]!;
          const a1: [number, number] = [hx + p[0], hy + p[1]];
          const b1: [number, number] = [hx + q[0], hy + q[1]];
          const key = [a1, b1]
            .map((v) => v.map(Math.round).join())
            .sort()
            .join();
          if (seen.has(key) || seen.size >= num(lt, "pieces", 9)) return;
          seen.add(key);
          const length = Math.hypot(b1[0] - a1[0], b1[1] - a1[1]);
          const bar = box(
            g,
            length,
            0.9,
            0.9,
            m,
            ox + (a1[0] + b1[0]) / 2,
            oy + (a1[1] + b1[1]) / 2,
            zw + 0.6,
          );
          bar.rotation.z = Math.atan2(b1[1] - a1[1], b1[0] - a1[0]);
        });
    } else {
      for (let k = 0; k < num(lt, "pieces", 6); k++) {
        const dark = M(0x111111);
        const tile = kit.rgbMaterial();
        (tile.userData as { phase: number }).phase = k / 6;
        box(
          g,
          15,
          15,
          1,
          [dark, dark, dark, dark, tile, dark],
          ox + (k % 3) * 16.5,
          oy + Math.floor(k / 3) * 16.5,
          zw + 0.5,
        );
      }
    }
    if (on) {
      const ambient = new THREE.PointLight(0xff00ff, 0, 140, 0);
      ambient.position.set(ox + 15, oy + 10, zw + 20);
      ambient.userData.strength = 1.1;
      room.add(ambient);
      kit.rgb.ambients.push(ambient);
    }
    drop(g, "light");
  });

  return {
    pc: pcPosition,
    focus: {
      x: Lo.isL ? Lo.wingWidth / 2 : Lo.pcOnDesk ? 0 : -(input.pc.W / 2 + 6),
      y: top + 8,
      z: Lo.isL ? (Lo.wingLength - dd) / 2 + 8 : 12,
      distance:
        Math.max(
          dw + (Lo.isL ? Lo.wingWidth : Lo.pcOnDesk ? 0 : input.pc.W + 24),
          Lo.isL ? Lo.wingLength + 60 : 0,
          150,
        ) * 1.9,
    },
  };
}

function screenTexture(key: string, w: number, h: number): THREE.CanvasTexture {
  const kind = key.replace(/u\d$/, "");
  return canvasTexture(`scr${key}`, 1024, Math.round((1024 * h) / w), (g, W, Hh) => {
    if (kind === "game") {
      const sky = g.createLinearGradient(0, 0, 0, Hh * 0.62);
      sky.addColorStop(0, "#120a33");
      sky.addColorStop(0.55, "#6b1d7a");
      sky.addColorStop(1, "#ff7a3d");
      g.fillStyle = sky;
      g.fillRect(0, 0, W, Hh);
      const rand = seeded(4);
      for (let i = 0; i < 140; i++) {
        g.fillStyle = `rgba(255,255,255,${rand() * 0.8})`;
        g.fillRect(rand() * W, rand() * Hh * 0.45, 1.5, 1.5);
      }
      const cxs = W / 2;
      const cy = Hh * 0.5;
      const sr = Hh * 0.22;
      const sun = g.createLinearGradient(0, cy - sr, 0, cy + sr);
      sun.addColorStop(0, "#ffe36b");
      sun.addColorStop(1, "#ff3e8a");
      g.fillStyle = sun;
      g.beginPath();
      g.arc(cxs, cy, sr, 0, 7);
      g.fill();
      g.fillStyle = "#6b1d7a";
      for (let i = 0; i < 6; i++)
        g.fillRect(cxs - sr, cy + i * sr * 0.16 + sr * 0.05, sr * 2, sr * 0.05 + i * 1.2);
      g.fillStyle = "#1a0d2e";
      g.beginPath();
      g.moveTo(0, Hh * 0.62);
      for (let x = 0; x <= W; x += W / 16)
        g.lineTo(x, Hh * 0.62 - (Math.sin(x * 0.013) * 0.5 + 0.6) * Hh * 0.12 * (1 + rand() * 0.6));
      g.lineTo(W, Hh * 0.62);
      g.fill();
      g.fillStyle = "#0b0618";
      g.fillRect(0, Hh * 0.62, W, Hh);
      g.strokeStyle = "#ff3ec8";
      g.lineWidth = 2;
      for (let i = 1; i < 14; i++) {
        const y = Hh * 0.62 + Math.pow(i / 14, 2) * Hh * 0.38;
        g.beginPath();
        g.moveTo(0, y);
        g.lineTo(W, y);
        g.stroke();
      }
      for (let i = -14; i <= 14; i++) {
        g.beginPath();
        g.moveTo(cxs + i * W * 0.012, Hh * 0.62);
        g.lineTo(cxs + i * W * 0.12, Hh);
        g.stroke();
      }
      g.fillStyle = "rgba(0,0,0,.35)";
      g.fillRect(24, Hh - 70, 260, 44);
      g.fillStyle = "#7cff8a";
      g.fillRect(34, Hh - 58, 180, 8);
      g.fillStyle = "#3ad1ff";
      g.fillRect(34, Hh - 44, 130, 8);
    } else if (kind === "pro") {
      g.fillStyle = "#1b1d21";
      g.fillRect(0, 0, W, Hh);
      g.fillStyle = "#26292e";
      g.fillRect(0, 0, W, 28);
      g.fillRect(0, 28, 70, Hh);
      g.fillRect(W - 230, 28, 230, Hh);
      const photo = g.createLinearGradient(120, 60, W - 280, Hh - 60);
      photo.addColorStop(0, "#0f4c75");
      photo.addColorStop(0.45, "#f2a65a");
      photo.addColorStop(1, "#c33c54");
      g.fillStyle = photo;
      g.fillRect(110, 60, W - 370, Hh - 120);
      g.fillStyle = "rgba(255,255,255,.85)";
      g.beginPath();
      g.arc(W * 0.42, Hh * 0.42, Hh * 0.12, 0, 7);
      g.fill();
      ["#e63946", "#f4a261", "#2a9d8f", "#457b9d", "#a8dadc"].forEach((c, i) => {
        g.fillStyle = c;
        g.fillRect(W - 210, 60 + i * 36, 190, 26);
      });
      for (let i = 0; i < 10; i++) {
        g.fillStyle = "#3a3e45";
        g.fillRect(16, 50 + i * 42, 38, 30);
      }
    } else {
      const bg = g.createLinearGradient(0, 0, W, Hh);
      bg.addColorStop(0, "#10233f");
      bg.addColorStop(1, "#3a1452");
      g.fillStyle = bg;
      g.fillRect(0, 0, W, Hh);
      g.fillStyle = "rgba(18,20,26,.92)";
      g.fillRect(W * 0.05, Hh * 0.08, W * 0.5, Hh * 0.62);
      g.fillRect(W * 0.6, Hh * 0.08, W * 0.34, Hh * 0.84);
      g.fillStyle = "#9146ff";
      g.fillRect(W * 0.05, Hh * 0.08, W * 0.5, 22);
      g.fillStyle = "#2b2f38";
      for (let i = 0; i < 9; i++)
        g.fillRect(
          W * 0.62,
          Hh * 0.14 + i * Hh * 0.085,
          W * 0.3 * (0.4 + ((i * 37) % 60) / 100),
          Hh * 0.05,
        );
      const ig = g.createLinearGradient(W * 0.06, 0, W * 0.54, 0);
      ig.addColorStop(0, "#ff3e8a");
      ig.addColorStop(1, "#3ad1ff");
      g.fillStyle = ig;
      g.fillRect(W * 0.07, Hh * 0.14, W * 0.46, Hh * 0.5);
      g.fillStyle = "rgba(10,11,14,.9)";
      g.fillRect(0, Hh - 34, W, 34);
    }
  });
}

export type { Part };
