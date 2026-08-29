"use client";
import React, { useEffect, useRef } from "react";

export interface BorromeanVectorCanvasProps {
  className?: string;
  style?: React.CSSProperties;
  speed?: number;
}

export default function BorromeanVectorCanvas({
  className = "w-full h-full",
  style,
  speed = 1.0,
}: BorromeanVectorCanvasProps) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = ref.current;
    if (!svg) return;

    let animId: number, timerId: any, active = true;
    const { sin, cos, hypot, sqrt, PI, min, max, pow, random } = Math, PI2 = PI * 2;

    const saddle = (t: number, v = 1): [number, number, number] => {
      const th = t * PI2;
      return [2.23 * v * cos(th), 1.33 * v * sin(th), 0.38 * pow(v, 1.4) * sin(2 * th)];
    };

    const perm = ([x, y, z]: [number, number, number], r: number): [number, number, number] =>
      r === 0 ? [x, y, z] : r === 1 ? [z, x, y] : [y, z, x];

    const rings = [0, 1, 2].map((r) => ({
      r,
      conc: Array.from({ length: 8 }, (_, c) => ({
        pts: Array.from({ length: 32 }, (_, i) => perm(saddle(i / 32, (c + 1) / 8), r)),
      })),
      rad: Array.from({ length: 12 }, (_, k) =>
        Array.from({ length: 7 }, (_, j) => perm(saddle(k / 12, j / 6), r))
      ),
      rim: Array.from({ length: 32 }, (_, i) => perm(saddle(i / 32, 1), r)),
    }));

    const seams = [0, 1, 2].map((k) =>
      Array.from({ length: 16 }, (_, i) => {
        const s = -1 + (2 * i) / 15;
        return perm([0.57 * s * (1 - s * s), 1.35 * s, -0.38 * (s * s - 1) * sin(s * PI) * 0.8], k);
      })
    );

    const nodes: [number, number, number][] = [
      [0, 1.35, 0], [0, -1.35, 0], [0, 0, 1.35], [0, 0, -1.35], [1.35, 0, 0], [-1.35, 0, 0]
    ];

    const pathD = (pts: [number, number, number][], closed = false) => {
      const n = pts.length;
      let d = `M ${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
      for (let i = 0; i < (closed ? n : n - 1); i++) {
        const p0 = closed ? pts[(i - 1 + n) % n] : i > 0 ? pts[i - 1] : pts[0];
        const p1 = pts[i], p2 = pts[(i + 1) % n], p3 = closed ? pts[(i + 2) % n] : i + 2 < n ? pts[i + 2] : p2;
        d += ` C ${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)} ${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)}, ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)} ${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
      }
      return closed ? d + " Z" : d;
    };

    const dom = [0, 1, 2].map((i) => ({
      rim: svg.getElementById(`r${i}`) as SVGPathElement,
      sheen: svg.getElementById(`s${i}`) as SVGPathElement,
      conc: svg.getElementById(`c${i}`) as SVGPathElement,
      rad: svg.getElementById(`d${i}`) as SVGPathElement,
      wash: svg.getElementById(`w${i}`) as SVGPathElement,
    }));
    const domSeams = svg.getElementById("seams") as SVGPathElement;
    const domNodes = (svg.getElementById("nodes") as SVGGElement)?.children;
    const domBloom = svg.getElementById("bloom") as SVGCircleElement;

    const u1 = random(), u2 = random(), u3 = random();
    const sq1 = sqrt(1 - u1), sq2 = sqrt(u1);
    let Q = [sq1 * sin(PI2 * u2), sq1 * cos(PI2 * u2), sq2 * sin(PI2 * u3), sq2 * cos(PI2 * u3)];

    const seed = random() * 1000;
    const [pX1, pX2, pY1, pY2, pZ1, pZ2, pW1, pW2, pW3] = Array.from({ length: 9 }, () => random() * PI2);

    let lastTime = performance.now(), bumpCount = 0, wasColliding = false;

    const render = (now: number) => {
      if (!active) return;
      const dt = min((now - lastTime) * 0.001 * speed, 0.05);
      lastTime = now;
      const t = (now * 0.001 + seed) * speed;

      const wx = 0.72 + 0.32 * sin(0.35 * t + pW1) + 0.18 * cos(0.68 * t + pW2);
      const wy = 0.98 + 0.38 * cos(0.48 * t + pW2) + 0.22 * sin(0.79 * t + pW3);
      const wz = 0.62 + 0.28 * sin(0.57 * t + pW3) + 0.16 * cos(0.33 * t + pW1);
      const wMag = hypot(wx, wy, wz);

      const hs = sin(wMag * dt * 0.5), hc = cos(wMag * dt * 0.5), sc = hs / wMag;
      const dQ = [hc, wx * sc, wy * sc, wz * sc];
      const nqw = dQ[0]*Q[0] - dQ[1]*Q[1] - dQ[2]*Q[2] - dQ[3]*Q[3];
      const nqx = dQ[0]*Q[1] + dQ[1]*Q[0] + dQ[2]*Q[3] - dQ[3]*Q[2];
      const nqy = dQ[0]*Q[2] - dQ[1]*Q[3] + dQ[2]*Q[0] + dQ[3]*Q[1];
      const nqz = dQ[0]*Q[3] + dQ[1]*Q[2] - dQ[2]*Q[1] + dQ[3]*Q[0];
      const qLen = hypot(nqw, nqx, nqy, nqz);
      Q = [nqw / qLen, nqx / qLen, nqy / qLen, nqz / qLen];

      const curX = (1.9 * sin(0.28 * t + pX1) + 0.7 * cos(0.52 * t + pX2)) * 0.91;
      const curY = (0.85 * cos(0.24 * t + pY1) + 0.4 * sin(0.46 * t + pY2)) * 0.91;
      const curZ = min(0.35, 0.65 * sin(0.21 * t + pZ1) + 0.2 * cos(0.39 * t + pZ2)) * 0.91;

      const x2 = Q[1]*2, y2 = Q[2]*2, z2 = Q[3]*2;
      const xx = Q[1]*x2, xy = Q[1]*y2, xz = Q[1]*z2, yy = Q[2]*y2, yz = Q[2]*z2, zz = Q[3]*z2;
      const wxq = Q[0]*x2, wyq = Q[0]*y2, wzq = Q[0]*z2;
      const M = [1 - (yy + zz), xy - wzq, xz + wyq, xy + wzq, 1 - (xx + zz), yz - wxq, xz - wyq, yz + wxq, 1 - (xx + yy)];

      const proj = ([x, y, z]: [number, number, number]): [number, number, number] => {
        const rx = M[0]*x + M[1]*y + M[2]*z + curX;
        const ry = M[3]*x + M[4]*y + M[5]*z + curY;
        const rz = M[6]*x + M[7]*y + M[8]*z + curZ;
        const d = max(0.1, 7.6 - rz);
        return [960 + (rx / d) * 1220, 540 - (ry / d) * 1220, rz];
      };

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      const projected = rings.map((r) => {
        const rim = r.rim.map(proj);
        rim.forEach(([px, py]) => {
          if (px < minX) minX = px;
          if (px > maxX) maxX = px;
          if (py < minY) minY = py;
          if (py > maxY) maxY = py;
        });
        return {
          r: r.r,
          rim,
          conc: r.conc.map((c) => ({ pts: c.pts.map(proj) })),
          rad: r.rad.map((rib) => rib.map(proj)),
        };
      });

      const pad = 48;
      const isColliding = minX < pad || maxX > 1872 || minY < pad || maxY > 1032;
      if (isColliding && !wasColliding) bumpCount++;
      else if (!isColliding && wasColliding) bumpCount = max(0, bumpCount - 0.25);
      wasColliding = isColliding;

      const repulsion = 1.15 * pow(1.05, bumpCount);
      let sx = 0, sy = 0;
      if (minX < pad) sx = (pad - minX) * repulsion;
      else if (maxX > 1872) sx = (1872 - maxX) * repulsion;
      if (minY < pad) sy = (pad - minY) * repulsion;
      else if (maxY > 1032) sy = (1032 - maxY) * repulsion;

      const shift = (pts: [number, number, number][]) => pts.map(([x, y, z]) => [x + sx, y + sy, z] as [number, number, number]);

      projected.forEach((r) => {
        const dEl = dom[r.r];
        if (!dEl.rim) return;
        const rimD = pathD(shift(r.rim), true);
        dEl.rim.setAttribute("d", rimD);
        dEl.sheen.setAttribute("d", rimD);
        dEl.wash.setAttribute("d", rimD);

        let concD = "";
        r.conc.forEach((c) => { concD += pathD(shift(c.pts), true) + " "; });
        dEl.conc.setAttribute("d", concD);

        let radD = "";
        r.rad.forEach((rib) => { radD += pathD(shift(rib), false) + " "; });
        dEl.rad.setAttribute("d", radD);
      });

      if (domSeams) {
        let seamD = "";
        seams.forEach((s) => { seamD += pathD(shift(s.map(proj)), false) + " "; });
        domSeams.setAttribute("d", seamD);
      }

      if (domNodes) {
        nodes.forEach((pt, idx) => {
          const [px, py, pz] = proj(pt);
          const circle = domNodes[idx] as SVGCircleElement;
          if (circle) {
            circle.setAttribute("cx", (px + sx).toFixed(1));
            circle.setAttribute("cy", (py + sy).toFixed(1));
            circle.setAttribute("opacity", min(0.45, max(0.15, (pz + 2) / 7)).toFixed(2));
          }
        });
      }

      if (domBloom) {
        const [cx, cy] = proj([0, 0, 0]);
        domBloom.setAttribute("cx", (cx + sx).toFixed(1));
        domBloom.setAttribute("cy", (cy + sy).toFixed(1));
      }

      scheduleNext();
    };

    const scheduleNext = () => {
      if (!active) return;
      timerId = setTimeout(() => {
        animId = requestAnimationFrame(render);
      }, 14);
    };

    scheduleNext();

    return () => {
      active = false;
      clearTimeout(timerId);
      cancelAnimationFrame(animId);
    };
  }, [speed]);

  return (
    <svg
      ref={ref}
      viewBox="0 0 1920 1080"
      preserveAspectRatio="xMidYMid meet"
      className={className}
      style={{ width: "100%", height: "100%", backgroundColor: "#000000", ...style }}
    >
      <defs>
        <radialGradient id="g" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fff" stopOpacity="0.95" />
          <stop offset="20%" stopColor="#fbbf24" stopOpacity="0.5" />
          <stop offset="60%" stopColor="#38bdf8" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
        </radialGradient>
      </defs>
      <path id="w0" fill="rgba(14,165,233,0.08)" /><path id="c0" fill="none" stroke="rgba(56,189,248,0.35)" strokeWidth="0.8" /><path id="d0" fill="none" stroke="rgba(56,189,248,0.2)" strokeWidth="0.5" />
      <path id="w1" fill="rgba(234,179,8,0.1)" /><path id="c1" fill="none" stroke="rgba(245,158,11,0.38)" strokeWidth="0.8" /><path id="d1" fill="none" stroke="rgba(253,224,71,0.2)" strokeWidth="0.5" />
      <path id="w2" fill="rgba(245,158,11,0.07)" /><path id="c2" fill="none" stroke="rgba(212,176,106,0.32)" strokeWidth="0.8" /><path id="d2" fill="none" stroke="rgba(245,215,130,0.18)" strokeWidth="0.5" />
      <path id="seams" fill="none" stroke="rgba(224,242,254,0.32)" strokeWidth="0.9" strokeLinecap="round" />
      <path id="r0" fill="none" stroke="#c29b4e" strokeWidth="6.1" strokeLinecap="round" strokeLinejoin="round" />
      <path id="s0" fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" opacity="0.85" />
      <path id="r1" fill="none" stroke="#d4b06a" strokeWidth="6.1" strokeLinecap="round" strokeLinejoin="round" />
      <path id="s1" fill="none" stroke="#fde047" strokeWidth="2" strokeLinecap="round" opacity="0.85" />
      <path id="r2" fill="none" stroke="#c49a4e" strokeWidth="6.1" strokeLinecap="round" strokeLinejoin="round" />
      <path id="s2" fill="none" stroke="#ffd782" strokeWidth="2" strokeLinecap="round" opacity="0.85" />
      <g id="nodes">
        <circle r="1.8" fill="#bae6fd" opacity="0.3" /><circle r="1.8" fill="#bae6fd" opacity="0.3" /><circle r="1.8" fill="#bae6fd" opacity="0.3" />
        <circle r="1.8" fill="#bae6fd" opacity="0.3" /><circle r="1.8" fill="#bae6fd" opacity="0.3" /><circle r="1.8" fill="#bae6fd" opacity="0.3" />
      </g>
      <circle id="bloom" r="16" fill="url(#g)" />
    </svg>
  );
}
