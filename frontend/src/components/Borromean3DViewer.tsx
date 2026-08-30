"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

export interface Borromean3DViewerProps {
  height?: number | string;
  width?: number | string;
  speed?: "normal" | "fast" | number;
  interactive?: boolean;
  label?: string;
  className?: string;
  style?: React.CSSProperties;
  color?: "gold" | "blue";
}

export default function Borromean3DViewer({
  height = 360,
  width = "100%",
  speed = "normal",
  interactive = true,
  label,
  className,
  style,
  color = "gold",
}: Borromean3DViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const speedMult =
    typeof speed === "number"
      ? speed
      : speed === "fast"
      ? 6.0
      : 1.0;

  useEffect(() => {
    let active = true;
    let animId: number;
    let cleanupFn: (() => void) | undefined;

    const init = () => {
      if (!active) return;

      const container = containerRef.current;
      if (!container) return;

      // 1. Scene, Camera, 4K Super-Sampled WebGL Renderer
      const scene = new THREE.Scene();
      const initialW = (typeof width === "number" ? width : container.clientWidth) || 400;
      const initialH = (typeof height === "number" ? height : container.clientHeight) || 360;

      const camera = new THREE.PerspectiveCamera(40, initialW / initialH, 0.1, 100);
      camera.position.set(0, 0, 7.6);

      const renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: "high-performance",
        precision: "highp",
      });

      // 24/7 Super-Sampling (2.5x - 4x native pixel density for ultra-sharp anti-aliased edges)
      const getOptimalPixelRatio = () => Math.max((window.devicePixelRatio || 1) * 2, 2.5);
      renderer.setPixelRatio(getOptimalPixelRatio());
      renderer.setSize(initialW, initialH, true);
      if ("outputColorSpace" in renderer && THREE.SRGBColorSpace) {
        renderer.outputColorSpace = THREE.SRGBColorSpace;
      }

      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
      container.appendChild(renderer.domElement);

      const dom = renderer.domElement;
      dom.style.display = "block";
      dom.style.width = "100%";
      dom.style.height = "100%";

      const isBlue = color === "blue";

      // 2. Studio Lighting
      scene.add(new THREE.AmbientLight(0xffffff, isBlue ? 1.6 : 1.4));

      const keyLight = new THREE.DirectionalLight(isBlue ? 0xe0f2fe : 0xfff8ee, 3.4);
      keyLight.position.set(6, 8, 7);
      scene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(isBlue ? 0x0284c7 : 0x0088cc, 2.4);
      fillLight.position.set(-6, -4, -5);
      scene.add(fillLight);

      const rimLight = new THREE.PointLight(isBlue ? 0x38bdf8 : 0xfc6a03, 3.4, 30);
      rimLight.position.set(0, 5, -6);
      scene.add(rimLight);

      const bounceLight = new THREE.PointLight(0x0284c7, 2.2, 20);
      bounceLight.position.set(0, -6, 3);
      scene.add(bounceLight);

      // 3. 2048x2048 Anti-Aliased Sub-Pixel Perforation Texture
      const texCanvas = document.createElement("canvas");
      texCanvas.width = 2048;
      texCanvas.height = 2048;
      const ctx = texCanvas.getContext("2d")!;
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";

      // White solid base
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, 2048, 2048);

      // Soft anti-aliased circular aperture cutouts
      const holeR = 58.0;
      const stepX = 184.0;
      const stepY = 159.34; // 184 * sqrt(3)/2

      for (let y = -80; y < 2128; y += stepY) {
        const row = Math.round(y / stepY);
        const offsetX = (row % 2 === 0) ? 0 : stepX / 2;
        for (let x = -80; x < 2128; x += stepX) {
          const grad = ctx.createRadialGradient(x + offsetX, y, holeR * 0.88, x + offsetX, y, holeR);
          grad.addColorStop(0, "rgba(0,0,0,1)");
          grad.addColorStop(0.85, "rgba(0,0,0,1)");
          grad.addColorStop(1, "rgba(255,255,255,1)");

          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(x + offsetX, y, holeR, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      const perforatedTex = new THREE.CanvasTexture(texCanvas);
      perforatedTex.wrapS = THREE.RepeatWrapping;
      perforatedTex.wrapT = THREE.RepeatWrapping;
      perforatedTex.repeat.set(3.8, 2.8);
      perforatedTex.anisotropy = renderer.capabilities?.getMaxAnisotropy ? renderer.capabilities.getMaxAnisotropy() : 16;
      perforatedTex.generateMipmaps = true;
      perforatedTex.minFilter = THREE.LinearMipmapLinearFilter;
      perforatedTex.magFilter = THREE.LinearFilter;

      // 4. Smooth Anti-Aliased Materials
      const rimMaterial = new THREE.MeshStandardMaterial({
        color: isBlue ? 0x60c5ff : 0xd4b06a,
        metalness: isBlue ? 0.88 : 0.92,
        roughness: 0.2,
      });

      const meshMaterial = new THREE.MeshStandardMaterial({
        color: isBlue ? 0x0284c7 : 0xc49f56,
        metalness: isBlue ? 0.85 : 0.9,
        roughness: 0.26,
        alphaMap: perforatedTex,
        transparent: true,
        opacity: 0.98,
        depthWrite: false,
        side: THREE.DoubleSide,
      });

      const group = new THREE.Group();
      scene.add(group);

      // 5. Build 3 Ultra-High-Density Interlocking Geometries (512 radial segments)
      const a = 2.25;
      const b = 1.35;
      const h = 0.38;
      const planes: Array<"xy" | "yz" | "zx"> = ["xy", "yz", "zx"];
      const geometries: any[] = [];

      planes.forEach((plane) => {
        const curve = new (THREE.Curve as any)();
        curve.getPoint = function (t: number) {
          const theta = t * Math.PI * 2;
          const cos = Math.cos(theta);
          const sin = Math.sin(theta);
          const saddle = h * Math.sin(2 * theta);

          if (plane === "xy") {
            return new THREE.Vector3(a * cos, b * sin, saddle);
          } else if (plane === "yz") {
            return new THREE.Vector3(saddle, a * cos, b * sin);
          } else {
            return new THREE.Vector3(b * sin, saddle, a * cos);
          }
        };

        const tubeGeom = new THREE.TubeGeometry(curve, 512, 0.045, 32, true);
        const tubeMesh = new THREE.Mesh(tubeGeom, rimMaterial);
        group.add(tubeMesh);
        geometries.push(tubeGeom);

        const surfGeom = new THREE.BufferGeometry();
        const uSegs = 240;
        const vSegs = 64;
        const positions: number[] = [];
        const uvs: number[] = [];
        const indices: number[] = [];

        for (let j = 0; j <= vSegs; j++) {
          const v = j / vSegs;
          const curA = (a - 0.02) * v;
          const curB = (b - 0.02) * v;
          const curH = h * Math.pow(v, 1.4);

          for (let i = 0; i <= uSegs; i++) {
            const u = i / uSegs;
            const theta = u * Math.PI * 2;
            const cos = Math.cos(theta);
            const sin = Math.sin(theta);
            const saddle = curH * Math.sin(2 * theta);

            let x = 0, y = 0, z = 0;
            if (plane === "xy") {
              x = curA * cos;
              y = curB * sin;
              z = saddle;
            } else if (plane === "yz") {
              x = saddle;
              y = curA * cos;
              z = curB * sin;
            } else {
              x = curB * sin;
              y = saddle;
              z = curA * cos;
            }

            positions.push(x, y, z);
            uvs.push(u * 5, v * 3);
          }
        }

        for (let j = 0; j < vSegs; j++) {
          for (let i = 0; i < uSegs; i++) {
            const p1 = j * (uSegs + 1) + i;
            const p2 = (j + 1) * (uSegs + 1) + i;
            const p3 = (j + 1) * (uSegs + 1) + (i + 1);
            const p4 = j * (uSegs + 1) + (i + 1);
            indices.push(p1, p2, p4);
            indices.push(p2, p3, p4);
          }
        }

        surfGeom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
        surfGeom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
        surfGeom.setIndex(indices);
        surfGeom.computeVertexNormals();

        const surfMesh = new THREE.Mesh(surfGeom, meshMaterial);
        group.add(surfMesh);
        geometries.push(surfGeom);
      });

      group.rotation.x = 0.55;
      group.rotation.y = 0.65;
      group.rotation.z = 0.2;

      // 6. Interactive Drag Rotation
      let isDragging = false;
      let prevMouseX = 0;
      let prevMouseY = 0;
      let targetRotX = group.rotation.x;
      let targetRotY = group.rotation.y;
      let targetRotZ = group.rotation.z;

      let onMouseDown: ((e: MouseEvent) => void) | undefined;
      let onMouseMove: ((e: MouseEvent) => void) | undefined;
      let onMouseUp: (() => void) | undefined;

      if (interactive) {
        dom.style.cursor = "grab";

        onMouseDown = (e: MouseEvent) => {
          isDragging = true;
          prevMouseX = e.clientX;
          prevMouseY = e.clientY;
        };

        onMouseMove = (e: MouseEvent) => {
          if (!isDragging) return;
          const deltaX = e.clientX - prevMouseX;
          const deltaY = e.clientY - prevMouseY;
          prevMouseX = e.clientX;
          prevMouseY = e.clientY;
          targetRotY += deltaX * 0.007;
          targetRotX += deltaY * 0.007;
        };

        onMouseUp = () => {
          isDragging = false;
        };

        dom.addEventListener("mousedown", onMouseDown);
        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
      } else {
        dom.style.pointerEvents = "none";
      }

      // 7. Dynamic Multi-Directional Organic Animation Loop
      let time = 0;
      const animate = () => {
        animId = requestAnimationFrame(animate);

        time += 0.012 * speedMult;

        // Incommensurate harmonic oscillations create continuous, non-repeating 3D tumble
        const deltaY = (0.0055 + 0.0035 * Math.sin(time * 0.73) + 0.0022 * Math.cos(time * 1.37)) * speedMult;
        const deltaX = (0.0032 * Math.cos(time * 0.51) + 0.0028 * Math.sin(time * 0.93 + 1.2)) * speedMult;
        const deltaZ = (0.0026 * Math.sin(time * 0.41) + 0.0020 * Math.cos(time * 0.81 + 2.3)) * speedMult;

        if (!interactive) {
          group.rotation.y += deltaY;
          group.rotation.x += deltaX;
          group.rotation.z += deltaZ;
        } else {
          if (!isDragging) {
            targetRotY += deltaY;
            targetRotX += deltaX;
            targetRotZ += deltaZ;
          }
          group.rotation.y += (targetRotY - group.rotation.y) * 0.08;
          group.rotation.x += (targetRotX - group.rotation.x) * 0.08;
          group.rotation.z += (targetRotZ - group.rotation.z) * 0.08;
        }

        renderer.render(scene, camera);
      };
      animate();

      // 8. 24/7 Super-Sampled Dynamic Resolution on Resize / Zoom
      const updateResolution = () => {
        if (!containerRef.current) return;
        const w = containerRef.current.clientWidth;
        const h = containerRef.current.clientHeight;
        if (w > 0 && h > 0) {
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setPixelRatio(getOptimalPixelRatio());
          renderer.setSize(w, h, true);
        }
      };

      const ro = new ResizeObserver(updateResolution);
      ro.observe(container);
      window.addEventListener("resize", updateResolution);

      cleanupFn = () => {
        cancelAnimationFrame(animId);
        ro.disconnect();
        window.removeEventListener("resize", updateResolution);

        if (interactive) {
          if (onMouseDown) dom.removeEventListener("mousedown", onMouseDown);
          if (onMouseMove) window.removeEventListener("mousemove", onMouseMove);
          if (onMouseUp) window.removeEventListener("mouseup", onMouseUp);
        }

        if (container.contains(dom)) {
          container.removeChild(dom);
        }

        geometries.forEach((g) => g.dispose());
        rimMaterial.dispose();
        meshMaterial.dispose();
        perforatedTex.dispose();
        renderer.dispose();
      };
    };

    init();

    return () => {
      active = false;
      if (cleanupFn) cleanupFn();
    };
  }, [height, width, speedMult, interactive, color]);

  const h = typeof height === "number" ? `${height}px` : height;
  const w = typeof width === "number" ? `${width}px` : width;

  return (
    <div
      className={className}
      style={{
        display: "inline-flex",
        flexDirection: label ? "column" : undefined,
        alignItems: "center",
        justifyContent: "center",
        gap: label ? "0.5rem" : undefined,
        pointerEvents: interactive ? "auto" : "none",
        userSelect: "none",
        width: w,
        height: h,
        ...style,
      }}
      aria-label="3D Borromean Sculpture"
    >
      <div
        ref={containerRef}
        style={{
          width: w,
          height: h,
          position: "relative",
          overflow: "hidden",
          background: "transparent",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      />
      {label && (
        <span className="text-muted" style={{ fontSize: "0.8125rem", fontWeight: 500 }}>
          {label}
        </span>
      )}
    </div>
  );
}
